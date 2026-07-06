import os
import gradio as gr
from groq import Groq
from duckduckgo_search import DDGS
import json

# =====================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =====================================================================
# Pega tu API Key de Groq aquí conservando las comillas
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)
DB_FILE = "cet_sistema_datos.json"

# =====================================================================
# HERRAMIENTAS DEL AGENTE (Internet)
# =====================================================================
def buscar_en_internet(consulta):
    try:
        with DDGS() as ddgs:
            resultados = [r for r in ddgs.text(consulta, max_results=3)]
            if resultados:
                texto_resultados = ""
                for i, r in enumerate(resultados):
                    texto_resultados += f"[{i+1}] Fuente: {r['title']}\nContenido: {r['body']}\n\n"
                return texto_resultados
    except Exception as e:
        return f"Error al buscar en internet: {str(e)}"
    return "No se encontraron resultados relevantes."

def evaluar_necesidad_internet(mensaje):
    """El cerebro analítico de Cet decide si necesita internet o no"""
    prompt_decision = (
        "Analiza el siguiente mensaje de un usuario. Tu única tarea es decidir si para responder "
        "óptimamente se requiere información en tiempo real, noticias actuales, datos recientes de internet o el clima. "
        "Responde ÚNICAMENTE con la palabra 'SI' o la palabra 'NO'. No añadas puntos ni explicaciones.\n"
        f"Mensaje del usuario: {mensaje}"
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt_decision}],
            temperature=0.0, # 0.0 para que sea totalmente preciso y no invente
            max_tokens=2
        )
        decision = completion.choices[0].message.content.strip().upper()
        return "SI" in decision
    except:
        return False

# =====================================================================
# SISTEMA DE ALMACENAMIENTO MULTI-USUARIO
# =====================================================================
def inicializar_db():
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size == 0:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"usuarios": {}}, f, ensure_ascii=False)

def cargar_db():
    inicializar_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"usuarios": {}}

def guardar_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def obtener_o_crear_usuario(nombre_usuario):
    db = cargar_db()
    nombre = nombre_usuario.strip().lower()
    if not nombre: return None
    if nombre not in db["usuarios"]:
        db["usuarios"][nombre] = {
            "memoria": "Historial de aprendizaje de Cet para este usuario:\n",
            "chats": {"Chat 1": []}
        }
        guardar_db(db)
    return db["usuarios"][nombre]

# =====================================================================
# LÓGICA DE INTELIGENCIA AUTÓNOMA
# =====================================================================
def procesar_chat(usuario, chat_seleccionado, mensaje, historial_visual):
    if not usuario or not usuario.strip():
        historial_visual.append({"role": "assistant", "content": "⚠️ Por favor, introduce tu nombre de usuario arriba y dale a 'Conectar Sesión'."})
        return historial_visual, ""
    
    mensaje_limpio = mensaje.strip()
    if not mensaje_limpio: return historial_visual, ""

    obtener_o_crear_usuario(usuario)
    db = cargar_db()
    usr_key = usuario.strip().lower()
    user_data = db["usuarios"][usr_key]

    # Modo aprendizaje directo
    if mensaje_limpio.lower().startswith("aprende que"):
        conocimiento = mensaje_limpio[12:].strip()
        user_data["memoria"] += f"- {conocimiento}\n"
        guardar_db(db)
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": f"💾 [Cet]: Entendido, {usuario}. He registrado eso en tu memoria a largo plazo."})
        return historial_visual, ""

    if chat_seleccionado not in user_data["chats"]:
        user_data["chats"][chat_seleccionado] = []
    historial_chat = user_data["chats"][chat_seleccionado]
    
    # 🧠 DETECCIÓN AUTÓNOMA: Cet decide por sí mismo si busca en la web
    necesita_web = evaluar_necesidad_internet(mensaje_limpio)
    datos_internet = ""
    
    if necesita_web:
        # Añadimos un mensaje temporal al historial visual para avisar al usuario
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": "🌐 *Cet está evaluando la red en segundo plano de forma autónoma...*"})
        datos_internet = buscar_en_internet(mensaje_limpio)
    
    # Construir el contexto final
    contexto_sistema = (
        f"Eres Cet, el asistente analítico de {usuario}. "
        f"REGLA CRÍTICA: Responde ÚNICAMENTE en español de forma directa, analítica y breve. "
        f"Recuerdos importantes sobre {usuario}:\n{user_data['memoria']}\n"
    )
    
    if datos_internet:
        contexto_sistema += f"Información en tiempo real encontrada en internet de forma autónoma:\n{datos_internet}\n"
    
    mensajes_api = [{"role": "system", "content": contexto_sistema}]
    
    for h in historial_chat[-4:]:
        if isinstance(h, dict) and "user" in h and "bot" in h:
            mensajes_api.append({"role": "user", "content": h["user"]})
            mensajes_api.append({"role": "assistant", "content": h["bot"]})
        
    mensajes_api.append({"role": "user", "content": mensaje_limpio})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=mensajes_api,
            temperature=0.4,
            max_tokens=300
        )
        respuesta = completion.choices[0].message.content.strip()
    except Exception as e:
        respuesta = f"❌ Error de conexión con mi cerebro central: {str(e)}"
        
    user_data["chats"][chat_seleccionado].append({"user": mensaje_limpio, "bot": respuesta})
    guardar_db(db)
    
    # Ajustamos el historial visual según si usó internet o no
    if not necesita_web:
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": respuesta})
    else:
        # Si usó internet, sustituimos el mensaje de carga por la respuesta real final
        historial_visual[-1] = {"role": "assistant", "content": respuesta}
        
    return historial_visual, ""

def actualizar_interfaz_usuario(nombre_usuario):
    if not nombre_usuario or not nombre_usuario.strip():
        return gr.update(choices=["Chat 1"], value="Chat 1"), []
    datos = obtener_o_crear_usuario(nombre_usuario)
    lista_chats = list(datos["chats"].keys())
    historial_visual = []
    for msg in datos["chats"][lista_chats[0]]:
        if isinstance(msg, dict) and "user" in msg and "bot" in msg:
            historial_visual.append({"role": "user", "content": msg["user"]})
            historial_visual.append({"role": "assistant", "content": msg["bot"]})
    return gr.update(choices=lista_chats, value=lista_chats[0]), historial_visual

# =====================================================================
# INTERFAZ VISUAL
# =====================================================================
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Cet OS - Plataforma Multi-Chat Compartida (Turbo + Agente Autónomo)")
    with gr.Row():
        txt_usuario = gr.Textbox(label="👤 Nombre de Usuario", placeholder="Ej: Jairo")
        btn_ingresar = gr.Button("Conectar Sesión", scale=0)
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🗂️ Control")
            selector_chat = gr.Dropdown(choices=["Chat 1"], value="Chat 1", label="Conversación Activa")
            gr.Markdown("*Nota: Cet decidirá por sí mismo cuándo buscar en internet según lo que le preguntes.*")
        with gr.Column(scale=3):
            componente_chat = gr.Chatbot(label="Terminal")
            with gr.Row():
                txt_mensaje = gr.Textbox(placeholder="Escribe a Cet...", label=False, scale=4)
                btn_enviar = gr.Button("Enviar", scale=1)

    btn_ingresar.click(actualizar_interfaz_usuario, inputs=[txt_usuario], outputs=[selector_chat, componente_chat])
    btn_enviar.click(procesar_chat, inputs=[txt_usuario, selector_chat, txt_mensaje, componente_chat], outputs=[componente_chat, txt_mensaje])
    txt_mensaje.submit(procesar_chat, inputs=[txt_usuario, selector_chat, txt_mensaje, componente_chat], outputs=[componente_chat, txt_mensaje])

inicializar_db()
demo.launch()

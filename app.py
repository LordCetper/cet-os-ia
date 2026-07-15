import os
import gradio as gr
import requests
from duckduckgo_search import DDGS
import json

# =====================================================================
# CONFIGURACIÓN DEL CEREBRO ULTRA RÁPIDO DE SAMBANOVA
# =====================================================================
SAMBANOVA_API_KEY = "98d34e3b-fdae-4320-87b6-67c003d6d10a"
DB_FILE = "cet_sistema_datos.json"

def consultar_sambanova(mensajes, max_tokens=300, temperature=0.4):
    url = "https://api.sambanova.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "Meta-Llama-3.2-3B-Instruct",
        "messages": mensajes,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"❌ Error de API ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# =====================================================================
# HERRAMIENTAS DEL AGENTE (Internet)
# =====================================================================
def buscar_en_internet(consulta):
    try:
        ddgs = DDGS()
        resultados = list(ddgs.text(consulta, max_results=3))
        if resultados:
            texto_resultados = ""
            for i, r in enumerate(resultados):
                texto_resultados += f"[{i+1}] Fuente: {r['title']}\nContenido: {r['body']}\n\n"
            return texto_resultados
    except Exception as e:
        return f"Error al buscar en internet: {str(e)}"
    return "No se encontraron resultados relevantes."

def evaluar_necesidad_internet(mensaje):
    prompt_decision = (
        "Analiza el siguiente mensaje de un usuario. Tu única tarea es decidir si para responder "
        "óptimamente se requiere información en tiempo real, noticias actuales, datos recientes de internet o el clima. "
        "Responde ÚNICAMENTE con la palabra 'SI' o la palabra 'NO'. No añadas puntos ni explicaciones.\n"
        f"Mensaje del usuario: {mensaje}"
    )
    mensajes = [{"role": "user", "content": prompt_decision}]
    respuesta = consultar_sambanova(mensajes, max_tokens=2, temperature=0.0)
    return "SI" in respuesta.upper()

# =====================================================================
# SISTEMA DE ALMACENAMIENTO MULTI-USUARIO Y MULTI-CHAT
# =====================================================================
def inicializar_db():
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size == 0:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump({"usuarios": {}}, f, ensure_ascii=False)
        except Exception:
            pass

def cargar_db():
    inicializar_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "usuarios" not in data:
                return {"usuarios": {}}
            return data
    except Exception:
        return {"usuarios": {}}

def guardar_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error guardando base de datos: {e}")

def obtener_o_crear_usuario(nombre_usuario):
    db = cargar_db()
    nombre = nombre_usuario.strip().lower() if nombre_usuario else ""
    if not nombre: 
        return None
    if nombre not in db["usuarios"]:
        db["usuarios"][nombre] = {
            "memoria": "Historial de aprendizaje de Cet:\n",
            "chats": {"Chat 1": []}
        }
        guardar_db(db)
    return db["usuarios"][nombre]

# =====================================================================
# LÓGICA DE CONTROL DE LA APP
# =====================================================================
def procesar_chat(usuario, chat_seleccionado, mensaje, historial_visual):
    if not historial_visual:
        historial_visual = []
        
    if not usuario or not usuario.strip():
        historial_visual.append({"role": "assistant", "content": "⚠️ Por favor, introduce tu nombre de usuario en la barra lateral primero y haz clic en 'Conectar Sesión'."})
        return historial_visual, "", "Por favor inicia sesión para ver tu núcleo de memoria."
    
    mensaje_limpio = mensaje.strip()
    if not mensaje_limpio: 
        return historial_visual, "", ""

    obtener_o_crear_usuario(usuario)
    db = cargar_db()
    usr_key = usuario.strip().lower()
    user_data = db["usuarios"][usr_key]

    if mensaje_limpio.lower().startswith("aprende que"):
        conocimiento = mensaje_limpio[12:].strip()
        user_data["memoria"] += f"- {conocimiento}\n"
        guardar_db(db)
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": f"💾 [Cet]: Registrado en tu memoria a largo plazo."})
        return historial_visual, "", user_data["memoria"]

    if chat_seleccionado not in user_data["chats"]:
        user_data["chats"][chat_seleccionado] = []
    historial_chat = user_data["chats"][chat_seleccionado]
    
    necesita_web = evaluar_necesidad_internet(mensaje_limpio)
    datos_internet = ""
    
    if necesita_web:
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": "🌐 *Cet está evaluando la red de forma autónoma...*"})
        datos_internet = buscar_en_internet(mensaje_limpio)
    
    contexto_sistema = (
        f"Eres Cet, el asistente analítico de {usuario}. "
        f"REGLA CRÍTICA: Responde ÚNICAMENTE en español de forma directa, analítica y breve. "
        f"Recuerdos importantes sobre {usuario}:\n{user_data['memoria']}\n"
    )
    
    if datos_internet:
        contexto_sistema += f"Información en tiempo real de internet:\n{datos_internet}\n"
    
    mensajes_api = [{"role": "system", "content": contexto_sistema}]
    for h in historial_chat[-4:]:
        if isinstance(h, dict) and "user" in h and "bot" in h:
            mensajes_api.append({"role": "user", "content": h["user"]})
            mensajes_api.append({"role": "assistant", "content": h["bot"]})
    mensajes_api.append({"role": "user", "content": mensaje_limpio})
    
    respuesta = consultar_sambanova(mensajes_api)
        
    user_data["chats"][chat_seleccionado].append({"user": mensaje_limpio, "bot": respuesta})
    guardar_db(db)
    
    if not necesita_web:
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": respuesta})
    else:
        historial_visual[-1] = {"role": "assistant", "content": respuesta}
        
    return historial_visual, "", user_data["memoria"]

def conectar_usuario(nombre_usuario):
    if not nombre_usuario or not nombre_usuario.strip():
        return gr.update(choices=["Chat 1"], value="Chat 1"), [], "Historial de aprendizaje vacío. Por favor inicia sesión primero."
    
    datos = obtener_o_crear_usuario(nombre_usuario)
    lista_chats = list(datos["chats"].keys())
    
    historial_visual = []
    primer_chat = lista_chats[0]
    for msg in datos["chats"][primer_chat]:
        if isinstance(msg, dict) and "user" in msg and "bot" in msg:
            historial_visual.append({"role": "user", "content": msg["user"]})
            historial_visual.append({"role": "assistant", "content": msg["bot"]})
            
    return gr.update(choices=lista_chats, value=primer_chat), historial_visual, datos["memoria"]

def cambiar_chat(nombre_usuario, chat_seleccionado):
    if not nombre_usuario or not chat_seleccionado:
        return []
    db = cargar_db()
    usr_key = nombre_usuario.strip().lower()
    if usr_key not in db["usuarios"] or chat_seleccionado not in db["usuarios"][usr_key]["chats"]:
        return []
    
    chat_data = db["usuarios"][usr_key]["chats"][chat_seleccionado]
    historial_visual = []
    for msg in chat_data:
        if isinstance(msg, dict) and "user" in msg and "bot" in msg:
            historial_visual.append({"role": "user", "content": msg["user"]})
            historial_visual.append({"role": "assistant", "content": msg["bot"]})
    return historial_visual

def crear_nuevo_chat(nombre_usuario):
    if not nombre_usuario or not nombre_usuario.strip():
        return gr.update()
    db = cargar_db()
    usr_key = nombre_usuario.strip().lower()
    user_data = db["usuarios"][usr_key]
    
    numero_chat = len(user_data["chats"]) + 1
    nuevo_nombre = f"Chat {numero_chat}"
    user_data["chats"][nuevo_nombre] = []
    guardar_db(db)
    
    lista_chats = list(user_data["chats"].keys())
    return gr.update(choices=lista_chats, value=nuevo_nombre)

# =====================================================================
# DISEÑO VISUAL AVANZADO
# =====================================================================
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 CET OS - Panel Avanzado de Control")
    
    with gr.Row():
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### 👤 Control de Sesión")
            txt_usuario = gr.Textbox(label="Usuario Activo", placeholder="Escribe tu nombre...")
            btn_ingresar = gr.Button("Conectar Sesión", variant="primary")
            
            gr.Markdown("---")
            gr.Markdown("### 🗂️ Historial de Chats")
            selector_chat = gr.Dropdown(choices=["Chat 1"], value="Chat 1", label="Seleccionar Conversación")
            btn_nuevo_chat = gr.Button("➕ Crear Nuevo Chat", variant="secondary")
            
        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.TabItem("💻 Terminal de Comunicación"):
                    # ¡AQUÍ ESTÁ LA MAGIA! Sin parámetro type, pero con formato de diccionarios.
                    componente_chat = gr.Chatbot(label="Mensajes con Cet")
                    with gr.Row():
                        txt_mensaje = gr.Textbox(placeholder="Escribe a Cet aquí...", label=False, scale=4)
                        btn_enviar = gr.Button("Enviar", variant="primary", scale=1)
                        
                with gr.TabItem("🧠 Núcleo de Memoria Persistente"):
                    gr.Markdown("### 📊 Conocimientos guardados sobre ti:")
                    txt_memoria_visual = gr.TextArea(label="Base de Datos a Largo Plazo", interactive=False, lines=15)

    btn_ingresar.click(conectar_usuario, inputs=[txt_usuario], outputs=[selector_chat, componente_chat, txt_memoria_visual])
    selector_chat.change(cambiar_chat, inputs=[txt_usuario, selector_chat], outputs=[componente_chat])
    btn_nuevo_chat.click(crear_nuevo_chat, inputs=[txt_usuario], outputs=[selector_chat])
    
    btn_enviar.click(procesar_chat, inputs=[txt_usuario, selector_chat, txt_mensaje, componente_chat], outputs=[componente_chat, txt_mensaje, txt_memoria_visual])
    txt_mensaje.submit(procesar_chat, inputs=[txt_usuario, selector_chat, txt_mensaje, componente_chat], outputs=[componente_chat, txt_mensaje, txt_memoria_visual])

inicializar_db()
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))

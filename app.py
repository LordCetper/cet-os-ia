import os
import gradio as gr
from openai import OpenAI
from duckduckgo_search import DDGS
import json

# =====================================================================
# CONFIGURACIÓN DEL CEREBRO ULTRA RÁPIDO DE SAMBANOVA (Llama-3.1-8B)
# =====================================================================
# CAMBIA ESTO POR TU LLAVE DE SAMBANOVA CONSERVANDO LAS COMILLAS
SAMBANOVA_API_KEY = "b88a22ad-1783-4fbf-8320-ece765577a12"

client = OpenAI(
    base_url="https://api.sambanova.ai/v1",
    api_key=SAMBANOVA_API_KEY
)
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
    prompt_decision = (
        "Analiza el siguiente mensaje de un usuario. Tu única tarea es decidir si para responder "
        "óptimamente se requiere información en tiempo real, noticias actuales, datos recientes de internet o el clima. "
        "Responde ÚNICAMENTE con la palabra 'SI' o la palabra 'NO'. No añadas puntos ni explicaciones.\n"
        f"Mensaje del usuario: {mensaje}"
    )
    try:
        completion = client.chat.completions.create(
            model="Meta-Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt_decision}],
            temperature=0.0,
            max_tokens=2
        )
        decision = completion.choices[0].message.content.strip().upper()
        return "SI" in decision
    except:
        return False

# =====================================================================
# SISTEMA DE ALMACENAMIENTO MULTI-USUARIO Y MULTI-CHAT (Seguro y Concurrente)
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
        # Recuperación automática si el archivo JSON se corrompe en Render
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
# LÓGICA DE CONTROL DE LA APP (Gradio State Sync)
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

    # Comando de guardado de memorias directo
    if mensaje_limpio.lower().startswith("aprende que"):
        conocimiento = mensaje_limpio[12:].strip()
        user_data["memoria"] += f"- {conocimiento}\n"
        guardar_db(db)
        historial_visual.append({"role": "user", "content": mensaje_limpio})
        historial_visual.append({"role": "assistant", "content": f"💾 [Cet]: Registrado en tu memoria a largo plazo."})
        return historial_visual, "", user_data["memoria"]

    # Aseguramos que el chat seleccionado exista antes de añadirle elementos
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
        context

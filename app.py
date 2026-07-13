import os
import gradio as gr
from openai import OpenAI
from duckduckgo_search import DDGS
import json

# =====================================================================
# CONFIGURACIÓN DEL CEREBRO ULTRA RÁPIDO DE SAMBANOVA
# =====================================================================
# CAMBIA ESTO POR TU LLAVE DE SAMBANOVA CONSERVANDO LAS COMILLAS
SAMBANOVA_API_KEY = "TU_LLAVE_DE_SAMBANOVA_AQUÍ"

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
            model="Meta-Llama-3.3-70B-Instruct",
            messages=[{"role": "user", "content": prompt_decision}],
            temperature=0.0,
            max_tokens=2
        )
        decision = completion.choices[0].message.content.strip().upper()
        return "SI" in decision
    except:
        return False

# =====================================================================
# SISTEMA DE ALMACENAMIENTO MULTI-USUARIO Y MULTI-CHAT
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
            "memoria": "Historial de aprendizaje de Cet:\n",
            "chats": {"Chat 1": []}
        }
        guardar_db(db)
    return db["usuarios"][nombre]

# =====================================================================
# LÓGICA DE CONTROL DE LA APP
# =====================================================================
def procesar_chat(usuario, chat_seleccionado, mensaje, historial_visual):
    if not usuario or not usuario.strip():
        historial_visual.append({"role": "assistant", "content": "⚠️ Por favor, introduce tu nombre de usuario en la barra lateral primero."})
        return historial_visual, "", ""
    
    mensaje_limpio = mensaje.strip()
    if not mensaje_limpio:

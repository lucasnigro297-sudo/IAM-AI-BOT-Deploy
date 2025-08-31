# main.py
# === API FastAPI que expone el bot: /preguntar y /reset_memoria ===

from dotenv import load_dotenv
load_dotenv()  # Permite usar variables del .env en local/desarrollo

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

from bot.qa_engine import responder, memory  # Instancias globales (compartidas por las rutas)

app = FastAPI(title="IAM Bot API", version="1.0.0")

# -------- CORS: define qué orígenes (dominios) pueden llamar a esta API --------
raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if raw_origins in ("", "*"):
    # Modo desarrollo o abierto: permite todos los orígenes
    allowed_origins = ["*"]
else:
    # Producción: lista separada por coma en .env (https://mi-front.com,https://otro.com)
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Static / Templates (opcionales para una landing o /) --------
if os.path.isdir("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

if os.path.isdir("scripts"):
    app.mount("/static", StaticFiles(directory="scripts"), name="static")

# -------- Modelos de entrada --------
class Pregunta(BaseModel):
    texto: str
    sesion_id: str | None = None  # session_id que manda el frontend

class ResetReq(BaseModel):
    sesion_id: str
    mode: str | None = "wipe"   # "wipe": limpia manteniendo session_id; "drop": elimina sesión

# -------- Rutas --------
@app.get("/")
def index(request: Request):
    """Home simple: si hay templates muestra HTML, si no un JSON."""
    if not templates:
        return {"msg": "OK (sin templates). Visita /docs para probar la API."}
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    """Endpoint para health-check (usado en Docker/monitoreo)."""
    return {"status": "ok"}

@app.post("/preguntar")
def preguntar(pregunta: Pregunta):
    """
    Recibe el texto desde el front y el sesion_id.
    Llama a qa_engine.responder() y devuelve {respuesta}.
    """
    texto = (pregunta.texto or "")
    try:
        texto = texto.strip()  # sanitiza (no usar .trim en Python)
    except Exception:
        pass

    if not texto:
        raise HTTPException(status_code=400, detail="El campo 'texto' es obligatorio.")

    try:
        respuesta = responder(texto, pregunta.sesion_id)
        return {"respuesta": respuesta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@app.post("/reset_memoria")
def reset_memoria(req: ResetReq):
    """
    Limpia la memoria de la sesión especificada:
      - mode == "drop": elimina por completo la sesión (como 'nueva conversación').
      - cualquier otro valor (por defecto "wipe"): deja la sesión vacía.
    """
    try:
        if req.mode == "drop":
            memory.clear_session(req.sesion_id)  # elimina sesión completa
        else:
            memory.wipe_session(req.sesion_id)   # mantiene sesión, memoria vacía
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

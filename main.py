# main.py
from dotenv import load_dotenv
load_dotenv()  # <-- necesario para leer .env en local

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

from bot.qa_engine import responder  # tu función de RAG

app = FastAPI(title="IAM Bot API", version="1.0.0")

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = [o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar solo si existen (evita RuntimeError si faltan carpetas)
if os.path.isdir("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

if os.path.isdir("scripts"):
    app.mount("/static", StaticFiles(directory="scripts"), name="static")

class Pregunta(BaseModel):
    texto: str
    sesion_id: str | None = None

@app.get("/")
def index(request: Request):
    if not templates:
        return {"msg": "OK (sin templates). Visita /docs para probar la API."}
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/preguntar")
def preguntar(pregunta: Pregunta):
    try:
        texto = (pregunta.texto or "").strip()
        if not texto:
            raise HTTPException(status_code=400, detail="El campo 'texto' es obligatorio.")
        respuesta = responder(texto, pregunta.sesion_id)
        return {"respuesta": respuesta}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

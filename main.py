from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from bot.qa_engine import responder  # ajustá el path si es distinto
import uuid

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

# Agregá esto debajo de app = FastAPI()
app.add_middleware(
    CORSMiddleware,
   allow_origins=["*"],  # Solo para desarrollo

   # allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates y archivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="scripts"), name="static")


class Pregunta(BaseModel):
    texto: str
    sesion_id: str

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/preguntar")
def preguntar(pregunta: Pregunta):
    respuesta = responder(pregunta.texto, pregunta.sesion_id)
    return {"respuesta": respuesta}

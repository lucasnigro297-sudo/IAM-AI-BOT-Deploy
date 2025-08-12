# bot/qa_engine.py
from __future__ import annotations

import requests
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from .memory import ConversationMemory

# -----------------------------
# Configuración del modelo LLM
# -----------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"  # cambiá aquí si usás otro modelo de Ollama

# -------------------------------------------------
# Cargamos VectorDB global (documentación / RAG)
# -------------------------------------------------
# Usa el mismo modelo de embeddings que generó el índice
_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# allow_dangerous_deserialization=True porque FAISS guarda un pickle con metadatos
vectorstore = FAISS.load_local(
    "faiss_index",
    _embeddings,
    allow_dangerous_deserialization=True
)

# -------------------------------------------------
# Memoria conversacional por sesión (en RAM)
# -------------------------------------------------
memory = ConversationMemory(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cpu"
)


def _buscar_documentos_relacionados(pregunta: str, k: int = 4) -> List[str]:
    """
    Devuelve los top-k chunks de la VectorDB como texto,
    además imprime en consola sus fuentes/páginas para depurar.
    """
    documentos = vectorstore.similarity_search(pregunta, k=k)

    print("\n📚 Chunks utilizados para responder:")
    resumenes = []
    for i, doc in enumerate(documentos):
        fuente = doc.metadata.get("source", "Desconocida")
        pagina = doc.metadata.get("page", "N/A")
        inicio = doc.page_content[:500].replace("\n", " ")
        print(f"\n🔹 Chunk {i + 1} (Fuente: {fuente}, Página: {pagina}):\n{inicio}...")
        resumenes.append(doc.page_content)

    return resumenes


def _construir_prompt(contexto_memoria: str, contexto_docs: str, pregunta: str) -> str:
    """
    Arma un prompt claro en español fusionando memoria de sesión + documentos relevantes.
    """
    instrucciones = (
        "Sos un asistente especializado en Identity & Access Management (IAM). "
        "Respondé en español, con precisión y de forma clara. "
        "Si la respuesta no está en el contexto, reconocelo y proponé una próxima pregunta.\n"
    )

    partes = [
        instrucciones,
    ]

    if contexto_memoria:
        partes.append(f"=== CONTEXTO DE CONVERSACIÓN ===\n{contexto_memoria.strip()}")

    if contexto_docs:
        partes.append(f"=== CONTEXTO DE DOCUMENTACIÓN ===\n{contexto_docs.strip()}")

    partes.append(f"=== PREGUNTA ===\n{pregunta}\n=== RESPUESTA ===")

    return "\n\n".join(partes)


def responder(pregunta: str, session_id: str) -> str:
    """
    Responde usando:
      1) Memoria por sesión (ConversationMemory + FAISS interno por sesión)
      2) RAG de documentos (FAISS global)
      3) LLM vía Ollama (modelo OLLAMA_MODEL)
    """
    try:
        # 1) Guardamos el mensaje del usuario en la memoria de la sesión
        memory.add_message(session_id, role="user", content=pregunta)

        # 2) Construimos contexto semántico desde la memoria de la conversación
        system_hint = (
            "Usá la memoria de la conversación solo para dar continuidad, no inventes datos. "
            "Priorizá la documentación técnica si hay contradicción."
        )
        contexto_memoria = memory.build_context(
            session_id=session_id,
            query=pregunta,
            k=6,
            system_hint=system_hint
        )

        # 3) Recuperamos documentación relevante desde la VectorDB global
        docs = _buscar_documentos_relacionados(pregunta, k=4)
        contexto_docs = "\n\n".join(docs)

        # 4) Construimos el prompt final
        prompt = _construir_prompt(contexto_memoria, contexto_docs, pregunta)

        # 5) Llamamos a Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if not resp.ok:
            texto = resp.text[:200]
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {texto}")

        data = resp.json()
        respuesta = (data.get("response") or "").strip()
        if not respuesta:
            respuesta = "No pude generar una respuesta con el contexto disponible."

        # 6) Guardamos la respuesta del asistente en memoria
        memory.add_message(session_id, role="assistant", content=respuesta)

        return respuesta

    except Exception as e:
        # Log y respuesta legible para el usuario
        print(f"❌ Error en responder(): {e}")
        return f"❌ Error al procesar la respuesta: {str(e)}"

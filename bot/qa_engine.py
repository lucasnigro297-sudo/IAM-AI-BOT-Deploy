# bot/qa_engine.py
from __future__ import annotations
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from .memory import ConversationMemory
from bot.llm_client import generate  # 👈 ahora usamos SIEMPRE esto

# -------------------------------------------------
# Cargamos VectorDB global (documentación / RAG)
# -------------------------------------------------
_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

try:
    vectorstore = FAISS.load_local(
        "faiss_index",
        _embeddings,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    print(f"⚠️ No se pudo cargar faiss_index: {e}")
    vectorstore = None

# -------------------------------------------------
# Memoria conversacional por sesión (en RAM)
# -------------------------------------------------
memory = ConversationMemory(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cpu"
)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _buscar_documentos_relacionados(pregunta: str, k: int = 4) -> List[str]:
    if not vectorstore:
        return []
    documentos = vectorstore.similarity_search(pregunta, k=k)

    print("\n📚 Chunks utilizados para responder:")
    resumenes = []
    for i, doc in enumerate(documentos):
        fuente = doc.metadata.get("source", "Desconocida")
        pagina = doc.metadata.get("page", "N/A")
        inicio = doc.page_content[:200].replace("\n", " ")
        print(f"\n🔹 Chunk {i + 1} (Fuente: {fuente}, Página: {pagina}): {inicio}...")
        resumenes.append(doc.page_content)
    return resumenes


def _construir_prompt(contexto_memoria: str, contexto_docs: str, pregunta: str) -> str:
    instrucciones = (
        "Sos un asistente especializado en Identity & Access Management (IAM). "
        "Respondé en español, con precisión y de forma clara. "
        "Si la respuesta no está en el contexto, reconocelo y proponé una próxima pregunta.\n"
    )

    partes = [instrucciones]

    if contexto_memoria:
        partes.append(f"=== CONTEXTO DE CONVERSACIÓN ===\n{contexto_memoria.strip()}")

    if contexto_docs:
        partes.append(f"=== CONTEXTO DE DOCUMENTACIÓN ===\n{contexto_docs.strip()}")

    partes.append(f"=== PREGUNTA ===\n{pregunta}\n=== RESPUESTA ===")

    return "\n\n".join(partes)

# -------------------------------------------------
# Función principal
# -------------------------------------------------
def responder(pregunta: str, session_id: Optional[str]) -> str:
    try:
        # 1) Guardar mensaje del usuario
        memory.add_message(session_id, role="user", content=pregunta)

        # 2) Contexto de memoria
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

        # 3) RAG de documentos
        docs = _buscar_documentos_relacionados(pregunta, k=4)
        contexto_docs = "\n\n".join(docs)

        # 4) Prompt final
        prompt = _construir_prompt(contexto_memoria, contexto_docs, pregunta)

        # 5) Llamar al LLM vía `llm_client.generate()`
        respuesta = (generate(prompt, system="Asistente IAM") or "").strip()
        if not respuesta:
            respuesta = "No pude generar una respuesta con el contexto disponible."

        # 6) Guardar respuesta en memoria
        memory.add_message(session_id, role="assistant", content=respuesta)
        return respuesta

    except Exception as e:
        print(f"❌ Error en responder(): {e}")
        return f"❌ Error al procesar la respuesta: {str(e)}"

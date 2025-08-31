# bot/qa_engine.py
# === Orquestador: memoria + (opcional) RAG + LLM ===

from __future__ import annotations
from typing import List, Optional

# LangChain opcional/tolerante: si falta, el bot sigue sin RAG
try:
    from langchain_community.vectorstores import FAISS as LCFAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
except Exception as e:
    LCFAISS = None
    HuggingFaceEmbeddings = None
    print(f"⚠️ LangChain community no disponible: {e}")

from .memory import ConversationMemory
from bot.llm_client import generate  # función que llama a tu modelo (Groq/Ollama/etc.)

# ---------- RAG (opcional): embeddings + carga de índice FAISS ----------
_embeddings = None
if HuggingFaceEmbeddings is not None:
    try:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    except Exception as e:
        print(f"⚠️ No se pudo inicializar HuggingFaceEmbeddings: {e}")
        _embeddings = None

vectorstore = None
if LCFAISS is not None and _embeddings is not None:
    try:
        # Carga del índice local generado previamente (faiss_index/)
        vectorstore = LCFAISS.load_local(
            "faiss_index",
            _embeddings,
            allow_dangerous_deserialization=True,
        )
        print("✅ Vectorstore (RAG) cargado.")
    except Exception as e:
        print(f"⚠️ No se pudo cargar faiss_index: {e}")
        vectorstore = None
else:
    print("ℹ️ RAG deshabilitado (faltan dependencias o embeddings).")

# ---------- Memoria conversacional por sesión (global en el proceso) ----------
memory = ConversationMemory(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cpu",
)

# ---------- Helpers ----------
def _buscar_documentos_relacionados(pregunta: str, k: int = 4) -> List[str]:
    """Devuelve textos de los k chunks más similares si RAG está activo; si no, []."""
    if not vectorstore:
        return []
    try:
        documentos = vectorstore.similarity_search(pregunta, k=k)
        print("\n📚 Chunks utilizados para responder:")
        resumenes = []
        for i, doc in enumerate(documentos):
            fuente = doc.metadata.get("source", "Desconocida")
            pagina = doc.metadata.get("page", "N/A")
            inicio = (doc.page_content or "")[:200].replace("\n", " ")
            print(f"\n🔹 Chunk {i + 1} (Fuente: {fuente}, Página: {pagina}): {inicio}...")
            resumenes.append(doc.page_content or "")
        return resumenes
    except Exception as e:
        print(f"⚠️ Error en similarity_search(): {e}")
        return []


def _construir_prompt(contexto_memoria: str, contexto_docs: str, pregunta: str) -> str:
    """Estructura del prompt final: instrucciones + memoria + docs + pregunta."""
    instrucciones = (
        "Sos un asistente especializado en Identity & Access Management (IAM). "
        "Respondé en español, con precisión y de forma clara. "
        "No digas que ‘ya se respondió antes’; aunque se repita, respondé de nuevo con síntesis. "
        "Si la respuesta no está en el contexto, reconocelo y proponé una próxima pregunta.\n"
    )
    partes = [instrucciones]
    if contexto_memoria:
        partes.append(f"=== CONTEXTO DE CONVERSACIÓN ===\n{contexto_memoria.strip()}")
    if contexto_docs:
        partes.append(f"=== CONTEXTO DE DOCUMENTACIÓN ===\n{contexto_docs.strip()}")
    partes.append(f"=== PREGUNTA ===\n{pregunta}\n=== RESPUESTA ===")
    return "\n\n".join(partes)

# ---------- Punto de entrada: responde a una pregunta ----------
def responder(pregunta: str, session_id: Optional[str]) -> str:
    """
    Flujo:
      1) Construir contexto con memoria (ANTES de guardar el turno actual).
      2) Agregar contexto de RAG si disponible.
      3) Llamar al LLM con prompt final.
      4) Guardar (user/assistant) en memoria (DESPUÉS).
    """
    try:
        sid = session_id or "default"

        # 1) Contexto de memoria
        system_hint = (
            "Usá la memoria de la conversación solo para dar continuidad, no inventes datos. "
            "Priorizá la documentación técnica si hay contradicción."
        )
        try:
            contexto_memoria = memory.build_context(
                session_id=sid, query=pregunta, k=6, system_hint=system_hint, recent_k=6
            )
        except Exception as e:
            print(f"⚠️ build_context() falló: {e}")
            contexto_memoria = system_hint

        # 2) Contexto de documentación (RAG)
        docs = _buscar_documentos_relacionados(pregunta, k=4)
        contexto_docs = "\n\n".join(docs) if docs else ""

        # 3) Prompt final y llamado al LLM
        prompt = _construir_prompt(contexto_memoria, contexto_docs, pregunta)
        try:
            respuesta = (generate(prompt, system="Asistente IAM") or "").strip()
        except Exception as e:
            print(f"❌ Error llamando al LLM: {e}")
            respuesta = ""
        if not respuesta:
            respuesta = "No pude generar una respuesta con el contexto disponible."

        # 4) Persistencia en memoria del turno actual
        try:
            memory.add_message(sid, role="user", content=pregunta)
            memory.add_message(sid, role="assistant", content=respuesta)
            print(f"🧠 Guardado turno: sesión={sid} total_msgs={len(memory._sessions.get(sid).texts)}")
        except Exception as e:
            print(f"⚠️ add_message falló: {e}")

        return respuesta

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Error al procesar la respuesta: {str(e)}"


__all__ = ["responder", "memory"]

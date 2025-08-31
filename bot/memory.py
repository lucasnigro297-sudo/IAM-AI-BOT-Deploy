# bot/memory.py
# === Memoria conversacional por sesión usando FAISS + SentenceTransformers ===

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    """Normaliza embeddings (L2=1). Con IndexFlatIP, esto permite usar coseno."""
    norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / norms


@dataclass
class _SessionStore:
    # Índice vectorial de FAISS (producto interno). Con vectores normalizados ~ coseno.
    index: faiss.IndexFlatIP
    # Historial de textos "role: content" en orden
    texts: List[str] = field(default_factory=list)


class ConversationMemory:
    """
    Para cada session_id mantiene:
      - un índice FAISS con embeddings de los turnos,
      - la lista de textos "role: content".
    Permite recuperar contexto por recencia + similitud.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        self._sessions: Dict[str, _SessionStore] = {}
        self._model = SentenceTransformer(model_name, device=device)
        self._dim = self._model.get_sentence_embedding_dimension()

    # ---------- API pública ----------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Agrega un turno a la sesión: embebe y lo incorpora al índice."""
        if not session_id or not content:
            return
        text = f"{role}: {content}".strip()
        emb = self._embed([text])  # (1, dim)
        store = self._get_or_create_session(session_id)
        store.texts.append(text)
        store.index.add(emb)

    def build_context(
        self,
        session_id: str,
        query: str,
        k: int = 6,
        system_hint: str | None = None,
        recent_k: int = 6,
        max_lines: int = 12,
    ) -> str:
        """
        Devuelve un bloque con:
          [System]        -> hint global
          [Memoria ...]   -> últimos 'recent_k' + 'k' más similares a la query
        Se limita a 'max_lines' entradas totales para que el prompt no explote.
        """
        if not session_id or session_id not in self._sessions:
            return (system_hint or "").strip()

        store = self._sessions[session_id]
        if not store.texts:
            return (system_hint or "").strip()

        # Recientes
        recent = store.texts[-max(recent_k, 0):]

        # Semánticos (similaridad contra la query)
        q = self._embed([query])  # (1, dim)
        topk = min(max(k, 1), len(store.texts))
        _, idxs = store.index.search(q, topk)
        idxs = [i for i in idxs[0].tolist() if i != -1]
        sem = [store.texts[i] for i in idxs]

        # Merge manteniendo orden: primero recientes, luego semánticos no repetidos
        merged: List[str] = []
        seen = set()
        for t in recent + sem:
            if t not in seen:
                merged.append(t)
                seen.add(t)

        # Limitar cantidad total de líneas
        if max_lines > 0:
            merged = merged[-max_lines:]

        blocks = []
        if system_hint:
            blocks.append(f"[System]\n{system_hint.strip()}")
        if merged:
            blocks.append("[Memoria relevante]\n" + "\n".join(merged))
        return "\n\n".join(blocks).strip()

    def clear_session(self, session_id: str) -> None:
        """Borra por completo una sesión (índice + textos). Útil para 'drop'."""
        if not session_id:
            return
        self._sessions.pop(session_id, None)

    def wipe_session(self, session_id: str) -> None:
        """Mantiene la sesión pero vacía su contenido. Útil para 'wipe'."""
        if not session_id:
            return
        store = self._sessions.get(session_id)
        if store:
            store.index.reset()
            store.texts.clear()

    def clear_all(self) -> None:
        """Elimina todas las sesiones (peligroso en multiusuario)."""
        self._sessions.clear()

    # ---------- Helpers internos ----------

    def _get_or_create_session(self, session_id: str) -> _SessionStore:
        """Crea la estructura de sesión si no existe aún."""
        if session_id not in self._sessions:
            index = faiss.IndexFlatIP(self._dim)  # IP + L2-normalized = coseno
            self._sessions[session_id] = _SessionStore(index=index)
        return self._sessions[session_id]

    def _embed(self, texts: List[str]) -> np.ndarray:
        """Embebe y normaliza a float32 para FAISS."""
        vec = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return _l2_normalize(vec).astype("float32")

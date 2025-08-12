# bot/memory.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    """Normaliza embeddings a norma 1 para usar similitud coseno con IndexFlatIP."""
    norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / norms


@dataclass
class _SessionStore:
    """Estructura de datos para una sesión."""
    index: faiss.IndexFlatIP
    texts: List[str] = field(default_factory=list)


class ConversationMemory:
    """
    Memoria conversacional vectorial por sesión (FAISS + SentenceTransformers).
    - Guarda "role: content" como texto.
    - Construye contexto relevante vía búsqueda semántica.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        # Índices por session_id
        self._sessions: Dict[str, _SessionStore] = {}

        # Cargamos el encoder
        self._model = SentenceTransformer(model_name, device=device)
        self._dim = self._model.get_sentence_embedding_dimension()

    # ---------- API pública ----------

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Agrega un mensaje a la memoria de la sesión.
        Se guarda como 'role: content' y se indexa en FAISS (normalizado).
        """
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
    ) -> str:
        """
        Devuelve un string con el contexto semántico relevante (top-k).
        Si no hay memoria para la sesión, retorna solo el system_hint (si viene).
        """
        if session_id not in self._sessions or len(self._sessions[session_id].texts) == 0:
            return (system_hint or "").strip()

        store = self._sessions[session_id]
        q = self._embed([query])  # (1, dim)

        # FAISS busca con similitud coseno (por usar IndexFlatIP + embeddings normalizados).
        scores, idxs = store.index.search(q, min(k, len(store.texts)))
        idxs = idxs[0].tolist()

        retrieved = [store.texts[i] for i in idxs if i != -1]

        blocks = []
        if system_hint:
            blocks.append(f"[System]\n{system_hint.strip()}")
        if retrieved:
            blocks.append("[Memoria relevante]\n" + "\n".join(retrieved))

        return "\n\n".join(blocks).strip()

    # ---------- helpers ----------

    def _get_or_create_session(self, session_id: str) -> _SessionStore:
        if session_id not in self._sessions:
            # Usamos IP (inner product) + embeddings normalizados = coseno
            index = faiss.IndexFlatIP(self._dim)
            self._sessions[session_id] = _SessionStore(index=index)
        return self._sessions[session_id]

    def _embed(self, texts: List[str]) -> np.ndarray:
        vec = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return _l2_normalize(vec).astype("float32")

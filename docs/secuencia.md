# Secuencia de pregunta–respuesta

```mermaid
sequenceDiagram
  autonumber
  participant U as Usuario (UI)
  participant F as Frontend (React)
  participant A as API (FastAPI)
  participant Q as QA Engine
  participant M as Memoria (FAISS sesión)
  participant R as VectorDB (FAISS docs)
  participant L as LLM (Ollama)

  U->>F: Escribe pregunta
  F->>A: POST /preguntar {texto, session_id}
  A->>Q: responder(pregunta, session_id)

  Q->>M: add_message(user)
  Q->>M: build_context()
  M-->>Q: contexto_memoria

  Q->>R: similarity_search(pregunta, k)
  R-->>Q: chunks relevantes

  Q->>L: prompt (memoria + docs + pregunta)
  L-->>Q: respuesta

  Q->>M: add_message(assistant)
  Q-->>A: texto respuesta
  A-->>F: JSON {respuesta}
  F-->>U: Renderiza mensaje

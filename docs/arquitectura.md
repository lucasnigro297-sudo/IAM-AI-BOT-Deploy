# Arquitectura General

```mermaid
flowchart LR
  subgraph Frontend["React + chat-ui"]
    UI["Chat UI"]
  end

  subgraph Backend["FastAPI"]
    API["POST /preguntar"]
    QA["qa_engine.py"]
    MEM["Memory (FAISS por sesión)"]
    RAG["RAG docs (FAISS global)"]
    LLM["Ollama · LLaMA 3"]
  end

  subgraph Storage["Persistencia"]
    VDOCS["faiss_index/"]
    DOCS["data/documentos/*.pdf"]
  end

  UI -->|"texto + sesion_id"| API --> QA
  QA --> MEM
  QA --> RAG
  RAG -.-> VDOCS
  QA --> LLM
  LLM --> QA -->|"JSON respuesta"| API --> UI
  RAG -.-> DOCS

# Mapa de módulos backend

```mermaid
graph LR
  main["main.py / FastAPI"] --> qa["qa_engine.py"]
  qa --> mem["memory.py (FAISS por sesión)"]
  qa --> vstore["FAISS.load_local (faiss_index/)"]
  docloader["document_loader.py"] --> vstore

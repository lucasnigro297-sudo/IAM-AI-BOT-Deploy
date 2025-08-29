# Flujo de ingesta e indexación (RAG)

```mermaid
flowchart TD
    Docs["PDFs en data/documentos"]
    Proc["procesar_pdfs.py"]
    Chunk["chunking + metadatos"]
    Embed["Embeddings all-MiniLM-L6-v2"]
    FaissBuild["Construye FAISS"]
    FaissIndex["faiss_index (persistente)"]

    Docs --> Proc
    Proc --> Chunk
    Chunk --> Embed
    Embed --> FaissBuild
    FaissBuild --> FaissIndex

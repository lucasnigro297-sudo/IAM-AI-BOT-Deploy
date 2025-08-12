from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
import os
import pickle

def cargar_chunks(chunks):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Convertir a objetos Document
    documentos = [
        Document(page_content=chunk["texto"], metadata=chunk["metadata"])
        for chunk in chunks
    ]

    # Crear el índice FAISS
    vectorstore = FAISS.from_documents(documentos, embeddings)

    # Guardar localmente
    vectorstore.save_local("faiss_index")

    # Guardar chunks originales
    with open("documentos.pkl", "wb") as f:
        pickle.dump(chunks, f)

    print("✅ Indexación en FAISS completada.")

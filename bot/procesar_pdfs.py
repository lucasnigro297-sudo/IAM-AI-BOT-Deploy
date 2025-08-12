import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

PDF_DIR = "data/documentos"

def cargar_documentos_con_metadata(pdf_dir):
    documentos = []
    for archivo in os.listdir(pdf_dir):
        if archivo.endswith(".pdf"):
            ruta = os.path.join(pdf_dir, archivo)
            loader = PyPDFLoader(ruta)
            paginas = loader.load()

            for i, pagina in enumerate(paginas):
                pagina.metadata["source"] = archivo
                pagina.metadata["page"] = i + 1
                documentos.append(pagina)

    return documentos

def dividir_en_chunks(documentos, tam_max=500, solapamiento=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=tam_max,
        chunk_overlap=solapamiento,
        separators=["\n", ".", " "]
    )
    documentos_chunked = splitter.split_documents(documentos)
    return documentos_chunked

def indexar_y_guardar(chunks):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("faiss_index")
    print("✅ Índice FAISS guardado con metadata.")

if __name__ == "__main__":
    docs = cargar_documentos_con_metadata(PDF_DIR)
    chunks = dividir_en_chunks(docs)
    indexar_y_guardar(chunks)

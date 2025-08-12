import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss

class DocumentIndexer:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)
        self.docs = []

    def cargar_textos_desde_pdfs(self, carpeta):
        textos = []
        for archivo in os.listdir(carpeta):
            if archivo.endswith(".pdf"):
                ruta = os.path.join(carpeta, archivo)
                doc = fitz.open(ruta)
                texto = ""
                for pagina in doc:
                    texto += pagina.get_text()
                textos.append(texto)
        return textos

    def indexar(self, textos):
        embeddings = self.model.encode(textos)
        self.index.add(embeddings)
        self.docs.extend(textos)

    def buscar(self, pregunta, top_k=3):
        embedding = self.model.encode([pregunta])
        distancias, indices = self.index.search(embedding, top_k)
        return [self.docs[i] for i in indices[0]]

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DATA_PATH = "data/docs"

def load_docs():
    all_docs = []

  
    for file in os.listdir(DATA_PATH):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(DATA_PATH, file))
            documents = loader.load()

            # Add source info (optional but useful)
            for doc in documents:
                doc.metadata["source"] = file

            all_docs.extend(documents)

    embeddings = HuggingFaceEmbeddings()

    db = Chroma.from_documents(
        all_docs,
        embeddings,
        persist_directory="rag_db"
    )

    db.persist()
  

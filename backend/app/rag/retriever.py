from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings()

db = Chroma(
persist_directory="rag_db",
embedding_function=embeddings
)

def retrieve_docs(query: str):
    docs = db.similarity_search(query, k=3)
    return [doc.page_content for doc in docs]
    
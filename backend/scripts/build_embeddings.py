# scripts/build_embeddings.py
from core.data_loader import load_all_documents
from core.llm_chain import create_full_retrieval_chain

def build_embeddings():
    docs = load_all_documents()
    retriever = create_full_retrieval_chain(docs)
    # Optionally persist to disk (if using Chroma persistent storage)
    print("Embeddings built and retriever ready")

if __name__ == "__main__":
    build_embeddings()

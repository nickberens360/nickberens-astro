from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredHTMLLoader,
)


def load_all_documents():
    """Loads all data sources and returns them as a single list of documents."""
    print("Loading documents...")

    # For now, let's focus on the most reliable data sources.
    loaders = [
        PyPDFLoader("public/Nick_Berens_Resume.pdf"),
        UnstructuredHTMLLoader("nick_berens_cv.html"),
    ]

    docs = []
    for loader in loaders:
        try:
            docs.extend(loader.load())
        except Exception as e:
            print(f"Error loading from {type(loader).__name__}: {e}")

    print(f"Loaded {len(docs)} documents.")
    return docs
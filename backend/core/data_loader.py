from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredHTMLLoader,
    TextLoader,
    WebBaseLoader,
)


def load_all_documents():
    """Loads all data sources and returns them as a single list of documents."""
    print("Loading documents...")

    # List of loaders to use
    loaders = [
        PyPDFLoader("public/Nick_Berens_Resume.pdf"),
        UnstructuredHTMLLoader("nick_berens_cv.html"),
        TextLoader("README.md"),
        WebBaseLoader("https://raw.githubusercontent.com/nickberens360/atomic-docs-vue-npm/refs/heads/main/README.md"),
    ]

    # Load and combine all documents
    docs = []
    for loader in loaders:
        docs.extend(loader.load())

    print(f"Loaded {len(docs)} documents.")
    return docs
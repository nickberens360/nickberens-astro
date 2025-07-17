from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate


def create_retrieval_chain_from_docs(docs):
    """Creates the full LangChain retrieval chain from a list of documents."""
    print("Splitting texts...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    print("Creating vector store...")
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
    )

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

    prompt = ChatPromptTemplate.from_template(
        """You are an expert assistant for Nick Berens. Answer the user's question based on the following context.
Be friendly and helpful. If the information isn't in the context, say that you can't find that specific information in the provided documents, but you can try to answer other questions.

<context>
{context}
</context>

Question: {input}"""
    )

    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectorstore.as_retriever()

    print("LLM chain created successfully.")
    return create_retrieval_chain(retriever, document_chain)
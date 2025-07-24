import os
import time
import hashlib
import json
import logging
from typing import List, Optional, Dict, Any, Tuple, Iterator

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.retrievers import BaseRetriever
from google.api_core import exceptions
import chromadb

logger = logging.getLogger(__name__)

# Configuration
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20240620")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
_response_cache: Dict[str, Dict[str, Any]] = {}

def create_multi_vector_retriever(docs, embeddings):
    vectorstores = {}
    docs_by_source = {
        "resume": [doc for doc in docs if doc.metadata["source"] == "resume"],
        "about": [doc for doc in docs if doc.metadata["source"] == "about"],
        "illustration": [doc for doc in docs if doc.metadata["source"] == "illustration"],
    }

    for source, source_docs in docs_by_source.items():
        if not source_docs: continue
        try:
            client = chromadb.EphemeralClient()
            vectorstore = Chroma.from_documents(documents=source_docs, embedding=embeddings, client=client, collection_name=f"nickberens_{source}")
            vectorstores[source] = vectorstore
            logger.info(f"Created Chroma vector store for '{source}' with {len(source_docs)} documents.")
        except Exception as e:
            logger.error(f"Failed to create vector store for source '{source}': {e}")
            raise

    retriever_infos = [
        {"name": "resume", "description": "Good for answering questions about Nick's professional work experience, job history, roles, responsibilities, and technical skills.", "retriever": vectorstores["resume"].as_retriever(search_kwargs={"k": 8})},
        {"name": "about", "description": "Good for answering questions about Nick's background, personal story, design philosophy, and general professional approach.", "retriever": vectorstores["about"].as_retriever(search_kwargs={"k": 5})},
        {"name": "illustration", "description": "Good for answering questions about Nick's art, illustrations, characters, and creative work.", "retriever": vectorstores["illustration"].as_retriever(search_kwargs={"k": 5})}
    ]
    return {info["name"]: info["retriever"] for info in retriever_infos}

def get_llm_instances():
    llms = {}
    try:
        llms['claude'] = ChatAnthropic(model=CLAUDE_MODEL, temperature=0.7, timeout=REQUEST_TIMEOUT)
        logger.info(f"Claude model {CLAUDE_MODEL} initialized successfully (PRIMARY)")
    except Exception as e:
        logger.warning(f"Failed to initialize Claude (primary): {e}")
        llms['claude'] = None
    try:
        llms['gemini'] = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.7, timeout=REQUEST_TIMEOUT)
        logger.info(f"Gemini model {GEMINI_MODEL} initialized successfully (FALLBACK)")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini (fallback): {e}")
        llms['gemini'] = None
    if not any(llms.values()):
        raise RuntimeError("No LLM models could be initialized.")
    return llms

def create_qa_chain(llm):
    system_prompt = (
        "You are Nick Berens' expert digital assistant. Your role is to answer questions about his skills, experience, and work based *only* on the provided context. Speak in a helpful and professional tone."
        "\n\n**CRITICAL INSTRUCTIONS:**\n"
        "1.  **Persona:** When the user asks about 'you' or 'your' experience (e.g., 'What is your experience?'), always respond about Nick Berens in the third person (e.g., 'Nick's experience is...').\n"
        "2.  **Resume Requests:** If asked for the resume (e.g., 'Show me your resume'), synthesize the provided resume context into a clear, professional summary. **NEVER** state that you are an AI or do not have a resume. The user is asking for Nick's resume, and the context provided is the source for it.\n"
        "3.  **Stick to the Context:** If the answer is not in the provided context, clearly state that the information is not available. Do not make up answers.\n"
        "4.  **Formatting:** Use markdown, such as bullet points, to structure information like work experience or skills for readability."
        "\n\n**Provided Context:**\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    return create_stuff_documents_chain(llm, prompt)

def get_cache_key(user_input: str) -> str:
    if not ENABLE_CACHING or not isinstance(user_input, str): return None
    sanitized_input = user_input.strip().lower()[:1000]
    return hashlib.sha256(sanitized_input.encode('utf-8')).hexdigest()[:16]

def get_cached_response(cache_key: str) -> Optional[str]:
    if not cache_key or not ENABLE_CACHING: return None
    if cache_key in _response_cache:
        cached_data = _response_cache[cache_key]
        if time.time() - cached_data['timestamp'] < CACHE_TTL:
            logger.info("Returning valid cached response")
            return cached_data['response']
        else: del _response_cache[cache_key]
    return None

def cache_response(cache_key: str, response_chunks: List[str]):
    if not cache_key or not ENABLE_CACHING: return
    full_response = "".join(response_chunks)
    _response_cache[cache_key] = {'response': full_response, 'timestamp': time.time()}

def route_query_to_retrievers(query: str, retrievers: Dict[str, BaseRetriever]) -> List[BaseRetriever]:
    query_lower = query.lower()
    selected_names = set()
    resume_keywords = ["experience", "job", "work", "skill", "resume", "cv", "company", "role", "hillman", "wisnet", "history"]
    about_keywords = ["about", "background", "who is", "philosophy", "approach"]
    illustration_keywords = ["art", "illustration", "drawing", "picture", "character", "design"]
    if any(keyword in query_lower for keyword in resume_keywords): selected_names.add("resume")
    if any(keyword in query_lower for keyword in about_keywords): selected_names.add("about")
    if any(keyword in query_lower for keyword in illustration_keywords): selected_names.add("illustration")
    if not selected_names:
        logger.info("No specific keywords found, routing to 'resume' and 'about' retrievers.")
        selected_names.update(["resume", "about"])
    return [retrievers[name] for name in selected_names if name in retrievers]

def stream_with_fallback(retrievers: Dict[str, BaseRetriever], chat_history: List[BaseMessage], user_input: str, preferred_model: Optional[str] = None) -> Iterator[str]:
    if not retrievers:
        logger.error("No retrievers provided.")
        yield "I'm sorry, the AI service is temporarily unavailable."
        return

    cache_key = get_cache_key(user_input)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        yield cached_response
        return

    try:
        llms = get_llm_instances()
    except Exception as e:
        logger.error(f"Failed to initialize LLM instances: {e}")
        yield "I'm sorry, the AI service is temporarily unavailable."
        return

    if preferred_model == "gemini" and llms.get('gemini'):
        llm_order = [('gemini', llms['gemini']), ('claude', llms.get('claude'))]
    else:
        llm_order = [('claude', llms.get('claude')), ('gemini', llms.get('gemini'))]

    selected_retrievers = route_query_to_retrievers(user_input, retrievers)
    all_docs = []
    for retriever in selected_retrievers:
        all_docs.extend(retriever.get_relevant_documents(user_input))
    unique_docs = list({doc.page_content: doc for doc in all_docs}.values())

    full_response_chunks = []
    stream_successful = False
    for llm_name, llm_instance in llm_order:
        if not llm_instance: continue
        try:
            logger.info(f"Attempting to stream using {llm_name.title()}...")
            qa_chain = create_qa_chain(llm_instance)
            stream = qa_chain.stream({"input": user_input, "context": unique_docs})

            for chunk in stream:
                yield chunk
                full_response_chunks.append(chunk)

            stream_successful = True
            break
        except Exception as e:
            logger.error(f"{llm_name.title()} streaming error: {e}. Trying fallback.")

    if stream_successful:
        cache_response(cache_key, full_response_chunks)
    else:
        logger.error("All LLM streaming attempts failed.")
        yield "I'm sorry, I'm currently experiencing technical difficulties. Please try again in a few minutes."
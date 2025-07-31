import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union, cast

import chromadb
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import AppConfig

logger = logging.getLogger(__name__)

# --- Configuration ---
PRIMARY_LLM = AppConfig.PRIMARY_LLM
GEMINI_MODEL = AppConfig.GEMINI_MODEL
CLAUDE_MODEL = AppConfig.CLAUDE_MODEL
EMBEDDING_MODEL = AppConfig.EMBEDDING_MODEL
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "100"))

# --- LLM Provider Configuration ---
LLM_PROVIDERS = [
    {
        "name": "claude",
        "class": ChatAnthropic,
        "model": CLAUDE_MODEL,
        "init_kwargs": {"model": CLAUDE_MODEL, "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
    },
    {
        "name": "gemini",
        "class": ChatGoogleGenerativeAI,
        "model": GEMINI_MODEL,
        "init_kwargs": {"model": GEMINI_MODEL, "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
    },
]

# --- Rate Limit Tracking ---


class RateLimitTracker:
    """Track rate limit status for different LLM providers"""

    def __init__(self):
        self._rate_limit_status: Dict[str, bool] = {}
        self._rate_limit_reset_time: Dict[str, datetime] = {}
        self._lock = Lock()

    def is_rate_limited(self, provider: str) -> bool:
        """Check if a provider is currently rate limited"""
        with self._lock:

            if provider not in self._rate_limit_status:
                return False

            # Check if rate limit has expired
            if provider in self._rate_limit_reset_time:
                if datetime.now() > self._rate_limit_reset_time[provider]:
                    self.clear_rate_limit(provider)
                    return False

        return self._rate_limit_status.get(provider, False)

    def set_rate_limited(self, provider: str, reset_minutes: int = 60):
        """Mark a provider as rate limited"""
        with self._lock:
            self._rate_limit_status[provider] = True
            self._rate_limit_reset_time[provider] = datetime.now() + timedelta(minutes=reset_minutes)
        logger.warning(f"{provider} rate limit hit, will reset at {self._rate_limit_reset_time[provider]}")

    def clear_rate_limit(self, provider: str):
        """Clear rate limit status for a provider"""
        with self._lock:
            self._rate_limit_status[provider] = False
            if provider in self._rate_limit_reset_time:
                del self._rate_limit_reset_time[provider]
        logger.info(f"{provider} rate limit cleared")

    def get_status(self) -> Dict[str, bool]:
        """Get current rate limit status for all providers"""
        with self._lock:
            current_time = datetime.now()
        for provider, reset_time in list(self._rate_limit_reset_time.items()):
            if current_time > reset_time:
                self.clear_rate_limit(provider)

        return self._rate_limit_status.copy()


# Global rate limit tracker
rate_limit_tracker = RateLimitTracker()

# --- Caching Layers ---
_response_cache: Dict[str, Dict[str, Any]] = {}
_retrieval_cache: Dict[str, Dict[str, Any]] = {}


class VectorStoreManager:
    """Manages vector store creation and retrieval routing"""

    RETRIEVER_DEFINITIONS = {
        "resume": {
            "description": "Good for answering questions about Nick's professional work experience, previous roles, job history, and technical skills.",
            "search_kwargs": {"k": 8},
            "keywords": [
                "experience",
                "job",
                "work",
                "skill",
                "resume",
                "cv",
                "company",
                "role",
                "hillman",
                "wisnet",
                "history",
            ],
        },
        "about": {
            "description": "Good for answering questions about Nick's background, personal interests, and general professional philosophy.",
            "search_kwargs": {"k": 5},
            "keywords": ["about", "background", "who is", "philosophy", "approach"],
        },
        "illustration": {
            "description": "Good for answering questions about Nick's art, illustrations, creative process, and artistic style.",
            "search_kwargs": {"k": 5},
            "keywords": ["art", "illustration", "drawing", "picture", "character", "design"],
        },
    }

    @classmethod
    def create_multi_vector_retriever(cls, docs: List[Document], embeddings) -> Dict[str, BaseRetriever]:
        """Creates and returns a dictionary of Chroma vector store retrievers, one for each document source."""
        vectorstores = {}
        docs_by_source = {
            source: [doc for doc in docs if doc.metadata.get("source") == source]
            for source in cls.RETRIEVER_DEFINITIONS.keys()
        }

        for source, source_docs in docs_by_source.items():
            if not source_docs:
                logger.warning(f"No documents found for source '{source}'. Skipping vector store creation.")
                continue

            try:
                # Using EphemeralClient for in-memory storage
                client = chromadb.EphemeralClient()
                vectorstore = Chroma.from_documents(
                    documents=source_docs,
                    embedding=embeddings,
                    client=client,
                    collection_name=f"nickberens_{source}",
                )
                vectorstores[source] = vectorstore
                logger.info(f"Created Chroma vector store for '{source}' with {len(source_docs)} documents.")
            except Exception as e:
                logger.error(f"Failed to create vector store for source '{source}': {e}")
                raise

        # Create retrievers only for successfully created vector stores
        final_retrievers = {}
        for name, store in vectorstores.items():
            if name in cls.RETRIEVER_DEFINITIONS:
                search_kwargs = cls.RETRIEVER_DEFINITIONS[name]["search_kwargs"]
                final_retrievers[name] = store.as_retriever(search_kwargs=search_kwargs)

        if not final_retrievers:
            logger.warning("No retrievers were created. The application may not be able to answer questions.")

        return final_retrievers

    @classmethod
    def route_query_to_retrievers(cls, query: str, retrievers: Dict[str, BaseRetriever]) -> List[BaseRetriever]:
        """Routes a user query to the most relevant retriever(s) based on keywords."""
        query_lower = query.lower()
        selected_names = set()

        # Check each retriever's keywords
        for source, config in cls.RETRIEVER_DEFINITIONS.items():
            if any(keyword in query_lower for keyword in config["keywords"]):
                selected_names.add(source)

        # Default to broad search if no specific keywords are matched
        if not selected_names:
            selected_names.update(["resume", "about"])

        selected_retrievers = [retrievers[name] for name in selected_names if name in retrievers]
        logger.info(f"Query routed to retrievers: {[name for name in selected_names if name in retrievers]}")
        return selected_retrievers


def create_multi_vector_retriever(docs: List[Document], embeddings) -> Dict[str, BaseRetriever]:
    """Wrapper function for backward compatibility"""
    return VectorStoreManager.create_multi_vector_retriever(docs, embeddings)


def route_query_to_retrievers(query: str, retrievers: Dict[str, BaseRetriever]) -> List[BaseRetriever]:
    """Wrapper function for backward compatibility"""
    return VectorStoreManager.route_query_to_retrievers(query, retrievers)


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error"""
    # Check for status code 429 in exception attributes
    if hasattr(error, "status_code") and error.status_code == 429:
        return True

    # Check error message for rate limit indicators
    error_str = str(error).lower()
    rate_limit_indicators = [
        "rate limit",
        "quota exceeded",
        "too many requests",
        "429",
        "resource exhausted",
        "rate_limit_exceeded",
        "rate_limit_error",
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def get_llm_instances() -> Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]]:
    """Initializes and returns a dictionary of available LLM instances."""
    llms = {}

    for provider_config in LLM_PROVIDERS:
        provider_name = provider_config["name"]
        provider_class = provider_config["class"]
        init_kwargs = provider_config["init_kwargs"]

        try:
            if not rate_limit_tracker.is_rate_limited(provider_name):
                llms[provider_name] = provider_class(**init_kwargs)
                logger.info(f"{provider_name.title()} model initialized successfully")
            else:
                logger.warning(f"{provider_name.title()} is rate limited, skipping initialization")
                llms[provider_name] = None
        except Exception as e:
            logger.warning(f"Failed to initialize {provider_name.title()}: {e}")
            llms[provider_name] = None

    if not any(llms.values()):
        raise RuntimeError("No LLM models could be initialized. Check API keys and model names.")

    return llms


def create_qa_chain(llm):
    """Creates the main question-answering chain."""
    system_prompt = (
        "You are Nick Berens' expert digital assistant. Your role is to answer questions about his skills, experience, and work based *only* on the provided context. Speak in a helpful and professional tone."
        "\n\n"
        "**CRITICAL INSTRUCTIONS:**"
        "\n"
        "1.  **Persona:** When the user asks about 'you' or 'your' experience (e.g., 'What is your experience?'), always respond about Nick Berens in the third person (e.g., 'Nick's experience is...')."
        "\n"
        "2.  **Resume Requests:** If asked for the resume (e.g., 'Show me your resume'), synthesize the provided resume context into a clear, professional summary. **NEVER** state that you are an AI or do not have a resume. The user is asking for Nick's resume, and the context provided is the source for it."
        "\n"
        "3.  **Stick to the Context:** If the answer is not in the provided context, clearly state that the information is not available. Do not make up answers."
        "\n"
        "4.  **Formatting:** Use markdown, such as bullet points, to structure information like work experience or skills for readability."
        "\n\n"
        "**Provided Context:**\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    return create_stuff_documents_chain(llm, prompt)


def create_history_aware_prompt() -> ChatPromptTemplate:
    """Creates a prompt template for reformulating questions based on chat history."""
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question which might reference the chat history, "
        "formulate a standalone question which can be understood without the chat history. "
        "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
    )
    return ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )


class CacheManager:
    """Manages caching operations for responses and retrievals"""

    @staticmethod
    def get_cache_key(user_input: Optional[str]) -> Optional[str]:
        """Generates a SHA256 hash for a given user input string to use as a cache key."""
        if not ENABLE_CACHING or not isinstance(user_input, str):
            return None
        normalized_input = re.sub(r"[^\w\s]", "", user_input.lower()).strip()
        return hashlib.sha256(normalized_input.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def get_cached_response(cache_key: str) -> Optional[str]:
        """Retrieves a final response from the cache if available and not expired."""
        if not cache_key or not ENABLE_CACHING:
            return None

        if cache_key in _response_cache:
            cached_data = _response_cache[cache_key]
            if time.time() - cached_data["timestamp"] < CACHE_TTL:
                logger.info(f"Response cache hit for key: {cache_key}")
                return str(cached_data["response"])
            else:
                del _response_cache[cache_key]
                logger.info(f"Stale response cache entry removed: {cache_key}")
        return None

    @staticmethod
    def cache_response(cache_key: str, response_chunks: List[str]):
        """Caches the final, full response string."""
        if not cache_key or not ENABLE_CACHING:
            return

        if len(_response_cache) >= MAX_CACHE_SIZE:
            oldest_key = min(_response_cache, key=lambda k: _response_cache[k]["timestamp"])
            del _response_cache[oldest_key]
            logger.info(f"Evicted oldest response cache entry: {oldest_key}")

        full_response = "".join(response_chunks)
        _response_cache[cache_key] = {"response": full_response, "timestamp": time.time()}
        logger.info(f"Cached full response for key: {cache_key}")

    @staticmethod
    def get_cached_retrieval(cache_key: str) -> Optional[List[Document]]:
        """Checks the retrieval cache for a list of documents."""
        if not cache_key or not ENABLE_CACHING:
            return None

        if cache_key in _retrieval_cache:
            cached_data = _retrieval_cache[cache_key]
            if time.time() - cached_data["timestamp"] < CACHE_TTL:
                logger.info(f"Retrieval cache hit for key: {cache_key}")
                return cast(List[Document], cached_data["documents"])
            else:
                del _retrieval_cache[cache_key]
                logger.info(f"Stale retrieval cache entry removed: {cache_key}")
        return None

    @staticmethod
    def cache_retrieval(cache_key: str, documents: List[Document]):
        """Stores a list of documents in the retrieval cache."""
        if not cache_key or not ENABLE_CACHING:
            return

        if len(_retrieval_cache) >= MAX_CACHE_SIZE:
            oldest_key = min(_retrieval_cache, key=lambda k: _retrieval_cache[k]["timestamp"])
            del _retrieval_cache[oldest_key]
            logger.info(f"Evicted oldest retrieval cache entry: {oldest_key}")

        _retrieval_cache[cache_key] = {"documents": documents, "timestamp": time.time()}
        logger.info(f"Stored {len(documents)} documents in retrieval cache for key: {cache_key}")


# Wrapper functions for backward compatibility
def get_cache_key(user_input: Optional[str]) -> Optional[str]:
    return CacheManager.get_cache_key(user_input)


def get_cached_response(cache_key: str) -> Optional[str]:
    return CacheManager.get_cached_response(cache_key)


def cache_response(cache_key: str, response_chunks: List[str]):
    return CacheManager.cache_response(cache_key, response_chunks)


def get_cached_retrieval(cache_key: str) -> Optional[List[Document]]:
    return CacheManager.get_cached_retrieval(cache_key)


def cache_retrieval(cache_key: str, documents: List[Document]):
    return CacheManager.cache_retrieval(cache_key, documents)


async def stream_with_fallback(
    retrievers: Dict[str, BaseRetriever],
    chat_history: List[BaseMessage],
    user_input: str,
    preferred_model: Optional[str] = None,
) -> Tuple[AsyncIterator[str], str, Dict[str, Any]]:
    """
    Main async function to handle user input, perform retrieval (with caching),
    and stream a response from an LLM with fallback capabilities.

    Returns:
        Tuple containing the async stream iterator, the name of the model that was used,
        and additional metadata including rate limit status.
    """
    cache_key = CacheManager.get_cache_key(user_input)
    metadata = {"rate_limit_status": rate_limit_tracker.get_status()}

    # 1. Check for a cached FINAL response
    if cache_key and (cached_response := CacheManager.get_cached_response(cache_key)):

        async def cached_stream():
            yield cached_response

        return cached_stream(), "cached", metadata

    try:
        llms = get_llm_instances()
    except RuntimeError as e:
        logger.error(f"Fatal error initializing LLM instances: {e}")

        async def error_stream():
            yield "I'm sorry, the AI service is temporarily unavailable. Please contact support."

        return error_stream(), "error", {"rate_limit_status": {}}

    # 2. Check for cached RETRIEVAL results
    unique_docs = CacheManager.get_cached_retrieval(cache_key) if cache_key else None

    if unique_docs is None:
        logger.info(f"Retrieval cache miss for key: {cache_key}. Performing vector search...")
        selected_retrievers = VectorStoreManager.route_query_to_retrievers(user_input, retrievers)

        # Determine if history-aware retrieval is needed
        if chat_history and (reformulation_llm := llms.get("claude") or llms.get("gemini")):
            try:
                history_prompt = create_history_aware_prompt()
                history_aware_retrievers = [
                    create_history_aware_retriever(reformulation_llm, retriever, history_prompt)
                    for retriever in selected_retrievers
                ]
                tasks = [
                    r.ainvoke({"input": user_input, "chat_history": chat_history}) for r in history_aware_retrievers
                ]
                logger.info("Using history-aware retrievers.")
            except Exception as e:
                logger.warning(f"Failed to create history-aware retrievers: {e}. Falling back to regular retrieval.")
                tasks = [r.ainvoke(user_input) for r in selected_retrievers]
        else:
            tasks = [r.ainvoke(user_input) for r in selected_retrievers]

        if tasks:
            retrieval_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_docs: List[Document] = []
            for result in retrieval_results:
                if isinstance(result, Exception):
                    logger.error(f"Error during document retrieval: {result}")
                elif result:
                    all_docs.extend(cast(List[Document], result))

            # Deduplicate documents based on page_content
            unique_docs = list(
                {
                    hashlib.sha256(
                        f"{doc.page_content}{json.dumps(doc.metadata, sort_keys=True)}".encode("utf-8")
                    ).hexdigest(): doc
                    for doc in all_docs
                }.values()
            )
        else:
            unique_docs = []
            logger.warning("No retrievers were selected for the query, context will be empty.")

        if cache_key:
            CacheManager.cache_retrieval(cache_key, unique_docs)

    # 3. Proceed to LLM generation with smart model selection
    llm_order = _determine_llm_order(preferred_model, llms)

    # Try each LLM in order and return the first successful one
    for llm_name, llm_instance in llm_order:
        if not llm_instance:
            continue

        try:
            logger.info(f"Attempting to stream response using {llm_name.title()}...")
            qa_chain = create_qa_chain(llm_instance)

            async def llm_stream():
                full_response_chunks = []
                async for chunk in qa_chain.astream({"input": user_input, "context": unique_docs}):
                    yield chunk
                    full_response_chunks.append(chunk)

                # Cache the response if successful
                if cache_key:
                    CacheManager.cache_response(cache_key, full_response_chunks)

            logger.info(f"Successfully initialized streaming with {llm_name.title()}.")

            # Update metadata with final rate limit status
            metadata["rate_limit_status"] = rate_limit_tracker.get_status()
            return llm_stream(), llm_name, metadata

        except Exception as e:
            logger.error(f"{llm_name.title()} streaming failed: {type(e).__name__} - {e}")

            # Check if this is a rate limit error
            if is_rate_limit_error(e):
                rate_limit_tracker.set_rate_limited(llm_name)
                logger.warning(f"Rate limit detected for {llm_name}, marking as rate limited")
                metadata["rate_limit_status"] = rate_limit_tracker.get_status()

            logger.info("Trying next available model.")

    # If all LLMs failed
    logger.error("All LLM streaming attempts failed.")

    async def fallback_stream():
        yield "I'm sorry, but I'm currently experiencing technical difficulties and cannot provide a response."

    return fallback_stream(), "error", metadata


def _determine_llm_order(preferred_model: Optional[str], llms: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Determine the order in which to try LLMs based on preference and availability."""
    llm_order = []

    # If user prefers a specific model and it's available, try it first
    if preferred_model and preferred_model in llms and llms[preferred_model]:
        llm_order.append((preferred_model, llms[preferred_model]))
        # Add other available models as fallbacks
        for name, instance in llms.items():
            if name != preferred_model and instance:
                llm_order.append((name, instance))
    else:
        # Default order: Claude first, then others
        if llms.get("claude"):
            llm_order.append(("claude", llms["claude"]))
        for name, instance in llms.items():
            if name != "claude" and instance:
                llm_order.append((name, instance))

    return llm_order


def get_rate_limit_status() -> Dict[str, bool]:
    """Get current rate limit status for all providers"""
    return rate_limit_tracker.get_status()

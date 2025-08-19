import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Type, Union, cast

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import AppConfig
from .query_logger import get_query_logger

logger = logging.getLogger(__name__)

# --- Configuration ---
PRIMARY_LLM = AppConfig.PRIMARY_LLM
GEMINI_MODEL = AppConfig.GEMINI_MODEL

# Default configuration values (replacing legacy data_source_config)
DEFAULT_PROMPTS = {
    "system_template": """You are Nick Berens' AI assistant. You help visitors learn about Nick's professional background, skills, experience, and interests. Use the following pieces of context to answer the question. If you don't know the answer based on the context provided, just say you don't have that information.

Context: {context}

Answer as Nick would, in a friendly and professional tone. Keep responses concise but informative.""",
    "history_aware": """Given a chat history and the latest user question which might reference the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.""",
}


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
        "name": "claude_haiku",
        "class": ChatAnthropic,
        "model": "claude-3-haiku-20240307",
        "init_kwargs": {"model": "claude-3-haiku-20240307", "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
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
        self._lock = RLock()

    def is_rate_limited(self, provider: str) -> bool:
        """Check if a provider is currently rate limited - FIXED thread safety"""
        with self._lock:
            if provider not in self._rate_limit_status:
                return False
            if provider in self._rate_limit_reset_time and datetime.now() > self._rate_limit_reset_time[provider]:
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
        """Get current rate limit status for all providers, clearing expired ones."""
        with self._lock:
            current_time = datetime.now()
            for provider, reset_time in list(self._rate_limit_reset_time.items()):
                if current_time > reset_time:
                    self._rate_limit_status[provider] = False
                    if provider in self._rate_limit_reset_time:
                        del self._rate_limit_reset_time[provider]
            return self._rate_limit_status.copy()


# Global rate limit tracker
rate_limit_tracker = RateLimitTracker()

# --- Caching Layers ---
_response_cache: Dict[str, Dict[str, Any]] = {}
_retrieval_cache: Dict[str, Dict[str, Any]] = {}


def select_optimal_model_for_query(query: str, preferred_model: Optional[str] = None) -> str:
    """
    Select the optimal LLM model based on query complexity.

    Claude Haiku: Fast, cheap, good for simple factual queries
    Claude Sonnet: Slower, expensive, better for complex reasoning
    """
    # If user explicitly prefers a model, respect that
    if preferred_model and preferred_model in [p["name"] for p in LLM_PROVIDERS]:
        return preferred_model

    # Analyze query complexity
    query_lower = query.lower()

    # Simple query indicators (good for Haiku - 30-60% faster)
    simple_indicators = [
        "what programming languages",
        "what technologies",
        "what skills",
        "list",
        "show me",
        "tell me about",
        "experience with",
        "know about",
        "background in",
    ]

    # Complex query indicators (need Sonnet for quality)
    complex_indicators = [
        "how does",
        "why",
        "explain",
        "approach to",
        "philosophy",
        "compare",
        "analyze",
        "strategy",
        "architecture",
        "design pattern",
        "best practices",
    ]

    # Check for simple queries
    is_simple = any(indicator in query_lower for indicator in simple_indicators)
    is_complex = any(indicator in query_lower for indicator in complex_indicators)

    # Short queries are usually simple
    is_short = len(query.split()) <= 10

    # Decision logic
    if is_simple and not is_complex and is_short:
        logger.info(f"Using Claude Haiku for simple query: '{query[:50]}...'")
        return "claude_haiku"
    elif is_complex:
        logger.info(f"Using Claude Sonnet for complex query: '{query[:50]}...'")
        return "claude"
    else:
        # Default to Haiku for moderate queries (speed over perfection)
        logger.info(f"Using Claude Haiku for moderate query: '{query[:50]}...'")
        return "claude_haiku"


def route_query_to_retrievers(query: str, retrievers: Dict[str, BaseRetriever]) -> List[BaseRetriever]:
    """Routes a user query to the unified retriever."""
    if "unified" in retrievers:
        logger.info(f"Using unified retriever for query: '{query}'")
        return [retrievers["unified"]]
    else:
        logger.error("Unified retriever not found in retrievers dictionary")
        return []


async def async_retrieve_documents(query: str, retrievers: Dict[str, BaseRetriever]) -> List[Document]:
    """
    Async document retrieval with enhanced performance optimizations.

    This function tries to use async retrieval methods when available for better performance.
    """
    from .unified_retriever import UnifiedRetriever

    # The actual UnifiedRetriever instance is stored under "_unified_retriever"
    unified_retriever = retrievers.get("_unified_retriever")
    if unified_retriever and isinstance(unified_retriever, UnifiedRetriever):
        logger.info("Using async unified retriever for enhanced performance")
        try:
            # Use async auto-routing for better performance
            docs = await unified_retriever.auto_route_query_async(query)
            logger.info(f"Async retrieval successful, got {len(docs)} documents")
            return docs
        except Exception as e:
            logger.warning(f"Async retrieval failed, falling back to sync: {e}")
            # Fallback to sync method
            return unified_retriever.auto_route_query(query)
    else:
        logger.warning("Unified retriever not available, using standard retrieval")
        return []


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error or overload error"""
    if hasattr(error, "status_code") and error.status_code in [429, 529]:
        return True
    error_str = str(error).lower()
    rate_limit_indicators = [
        "rate limit",
        "quota exceeded",
        "too many requests",
        "429",
        "529",
        "resource exhausted",
        "rate_limit_exceeded",
        "rate_limit_error",
        "overloaded",
        "overloaded_error",
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def get_llm_instances() -> Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]]:
    """Initializes and returns a dictionary of available LLM instances."""
    llms: Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]] = {}
    for provider_config in LLM_PROVIDERS:
        provider_name: str = cast(str, provider_config["name"])
        provider_class: Type[Union[ChatGoogleGenerativeAI, ChatAnthropic]] = cast(
            Type[Union[ChatGoogleGenerativeAI, ChatAnthropic]],
            provider_config["class"],
        )
        init_kwargs: Dict[str, Any] = cast(Dict[str, Any], provider_config["init_kwargs"])

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
    system_prompt = DEFAULT_PROMPTS.get(
        "system_template",
        (
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
        ),
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    return create_stuff_documents_chain(llm, prompt)


def create_history_aware_prompt() -> ChatPromptTemplate:
    """Creates a prompt template for reformulating questions based on chat history."""
    contextualize_q_system_prompt = DEFAULT_PROMPTS.get(
        "history_aware",
        (
            "Given a chat history and the latest user question which might reference the chat history, "
            "formulate a standalone question which can be understood without the chat history. "
            "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
        ),
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
        if not ENABLE_CACHING or not isinstance(user_input, str):
            return None
        normalized_input = re.sub(r"[^\w\s]", "", user_input.lower()).strip()
        return hashlib.sha256(normalized_input.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def get_cached_response(cache_key: str) -> Optional[str]:
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
        if not cache_key or not ENABLE_CACHING:
            return
        if len(_retrieval_cache) >= MAX_CACHE_SIZE:
            oldest_key = min(_retrieval_cache, key=lambda k: _retrieval_cache[k]["timestamp"])
            del _retrieval_cache[oldest_key]
            logger.info(f"Evicted oldest retrieval cache entry: {oldest_key}")
        _retrieval_cache[cache_key] = {"documents": documents, "timestamp": time.time()}
        logger.info(f"Stored {len(documents)} documents in retrieval cache for key: {cache_key}")


# Wrapper functions for backward compatibility (aliases to CacheManager)
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
    client_ip: Optional[str] = None,
    question: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Tuple[AsyncIterator[str], str, Dict[str, Any]]:
    """
    Handle user input, perform retrieval (with caching),
    and stream a response from an LLM with fallback capabilities.
    """
    cache_key = CacheManager.get_cache_key(user_input)
    metadata = {"rate_limit_status": rate_limit_tracker.get_status()}

    # 1) Cached FINAL response?
    if cache_key and (cached_response := CacheManager.get_cached_response(cache_key)):
        logger.info(f"🎯 CACHE HIT! Returning cached response for key: {cache_key}")

        async def cached_stream():
            yield cached_response

        return cached_stream(), "cached", metadata
    else:
        logger.info(f"🔍 CACHE MISS for key: {cache_key}. Will generate new response.")

    # 2) Initialize LLMs
    try:
        llms = get_llm_instances()
    except RuntimeError as e:
        logger.error(f"Fatal error initializing LLM instances: {e}")

        async def error_stream():
            yield "I'm sorry, the AI service is temporarily unavailable. Please contact support."

        return error_stream(), "error", {"rate_limit_status": {}}

    # 3) Cached RETRIEVAL?
    unique_docs = CacheManager.get_cached_retrieval(cache_key) if cache_key else None
    if unique_docs is None:
        logger.info(f"Retrieval cache miss for key: {cache_key}. Performing vector search...")

        # Try async retrieval first for better performance
        try:
            all_docs = await async_retrieve_documents(user_input, retrievers)
            logger.info(f"Async retrieval successful, got {len(all_docs)} documents")

            # Ensure we have documents before proceeding
            if not all_docs:
                logger.warning("Async retrieval returned no documents, falling back to sync")
                raise ValueError("Empty async results")
        except Exception as async_error:
            logger.warning(f"Async retrieval failed: {async_error}. Falling back to standard retrieval...")

            # Fallback to standard retrieval method
            selected_retrievers = route_query_to_retrievers(user_input, retrievers)

            # History-aware?
            if chat_history and (reformulation_llm := llms.get("claude") or llms.get("gemini")):
                try:
                    history_prompt = create_history_aware_prompt()
                    history_aware_retrievers = [
                        create_history_aware_retriever(reformulation_llm, r, history_prompt)
                        for r in selected_retrievers
                    ]
                    tasks = [
                        r.ainvoke({"input": user_input, "chat_history": chat_history}) for r in history_aware_retrievers
                    ]
                    logger.info("Using history-aware retrievers.")
                except Exception as e:
                    logger.warning(
                        f"Failed to create history-aware retrievers: {e}. Falling back to regular retrieval."
                    )
                    tasks = [r.ainvoke(user_input) for r in selected_retrievers]
            else:
                tasks = [r.ainvoke(user_input) for r in selected_retrievers]

            if tasks:
                retrieval_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_docs = []
                for result in retrieval_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error during document retrieval: {result}")
                    elif result:
                        all_docs.extend(cast(List[Document], result))
            else:
                all_docs = []
                logger.warning("No retrievers were selected for the query, context will be empty.")

        # Deduplicate by content + metadata
        unique_docs = list(
            {
                hashlib.sha256(
                    f"{doc.page_content}{json.dumps(doc.metadata, sort_keys=True)}".encode("utf-8")
                ).hexdigest(): doc
                for doc in all_docs
            }.values()
        )

        if cache_key:
            CacheManager.cache_retrieval(cache_key, unique_docs)

    # 4) Generation with smart model selection and fallback order
    llm_order = _determine_llm_order(preferred_model, llms, user_input)
    for llm_name, llm_instance in llm_order:
        if not llm_instance:
            continue
        try:
            logger.info(f"Attempting to stream response using {llm_name.title()}...")
            qa_chain = create_qa_chain(llm_instance)

            # Create true progressive streaming with background caching
            logger.info(f"🚀 STARTING PROGRESSIVE STREAMING for cache key: {cache_key}")

            async def progressive_streaming_with_caching():
                full_response_chunks = []
                try:
                    # Stream LLM response in real-time while collecting for cache
                    async for chunk in qa_chain.astream({"input": user_input, "context": unique_docs}):
                        # Coerce various chunk types to text for streaming and caching
                        if hasattr(chunk, "content"):
                            text_piece = getattr(chunk, "content", "")
                        elif isinstance(chunk, str):
                            text_piece = chunk
                        elif isinstance(chunk, dict):
                            text_piece = str(chunk.get("answer") or chunk.get("output") or chunk.get("content") or "")
                        else:
                            text_piece = str(chunk)

                        if not isinstance(text_piece, str):
                            text_piece = str(text_piece)

                        if text_piece:
                            # Yield immediately for progressive streaming
                            yield text_piece
                            # Collect for caching
                            full_response_chunks.append(text_piece)

                finally:
                    # Background caching after streaming completes
                    if cache_key and full_response_chunks:
                        logger.info(
                            f"💾 BACKGROUND CACHING for key: {cache_key} ({len(full_response_chunks)} chunks, total length: {len(''.join(full_response_chunks))})"
                        )
                        CacheManager.cache_response(cache_key, full_response_chunks)

                        # Update streaming response log with actual content
                        if client_ip and question:
                            try:
                                complete_response = "".join(full_response_chunks)
                                query_logger = get_query_logger()
                                query_logger.update_streaming_response(
                                    cache_key=cache_key,
                                    client_ip=client_ip,
                                    question=question,
                                    actual_response=complete_response,
                                    request_id=request_id,
                                )
                            except Exception as e:
                                logger.warning(f"Failed to update streaming response log: {e}")
                    elif cache_key:
                        logger.warning(f"❌ Not caching response for key {cache_key} - no chunks collected")

            logger.info(f"Successfully initialized progressive streaming with {llm_name.title()}.")
            metadata["rate_limit_status"] = rate_limit_tracker.get_status()
            return progressive_streaming_with_caching(), llm_name, metadata

        except Exception as e:
            logger.error(f"{llm_name.title()} streaming failed: {type(e).__name__} - {e}")
            if is_rate_limit_error(e):
                rate_limit_tracker.set_rate_limited(llm_name)
                logger.warning(f"Rate limit detected for {llm_name}, marking as rate limited")
                metadata["rate_limit_status"] = rate_limit_tracker.get_status()
            logger.info("Trying next available model.")

    # 5) If all fail
    logger.error("All LLM streaming attempts failed.")

    async def fallback_stream():
        yield "I'm sorry, but I'm currently experiencing technical difficulties and cannot provide a response."

    return fallback_stream(), "error", metadata


def _determine_llm_order(
    preferred_model: Optional[str],
    llms: Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]],
    query: Optional[str] = None,
) -> List[Tuple[str, Union[ChatGoogleGenerativeAI, ChatAnthropic]]]:
    """Determine the order in which to try LLMs based on preference, query complexity, and availability."""
    provider_names = [str(p["name"]) for p in LLM_PROVIDERS]

    # Smart model selection based on query complexity
    if query and not preferred_model:
        optimal_model = select_optimal_model_for_query(query)
        if optimal_model in provider_names and llms.get(optimal_model):
            # Put optimal model first
            provider_names.insert(0, provider_names.pop(provider_names.index(optimal_model)))
    elif preferred_model and preferred_model in provider_names and llms.get(preferred_model):
        # User preference overrides smart selection
        provider_names.insert(0, provider_names.pop(provider_names.index(preferred_model)))

    llm_order: List[Tuple[str, Union[ChatGoogleGenerativeAI, ChatAnthropic]]] = []
    for name in provider_names:
        instance = llms.get(name)
        if instance is not None:
            llm_order.append((name, instance))
    return llm_order


def get_rate_limit_status() -> Dict[str, bool]:
    """Get current rate limit status for all providers"""
    return rate_limit_tracker.get_status()

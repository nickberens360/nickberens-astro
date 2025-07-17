import os
import time
import logging
from typing import List, Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage
from google.api_core import exceptions
import chromadb

logger = logging.getLogger(__name__)

# Configuration with fallbacks
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "nickberens_portfolio")

# Rate limiting configuration
CLAUDE_RETRY_DELAY = int(os.getenv("CLAUDE_RETRY_DELAY", "30"))
GEMINI_RETRY_DELAY = int(os.getenv("GEMINI_RETRY_DELAY", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Caching configuration
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Simple in-memory cache
_response_cache: Dict[str, Dict[str, Any]] = {}


def create_full_retrieval_chain(docs):
    """Creates the retriever component from a list of documents with enhanced error handling."""
    logger.info("Creating retrieval chain components...")

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        splits = text_splitter.split_documents(docs)
        logger.info(f"Split {len(docs)} documents into {len(splits)} chunks")

        # Use a purely in-memory Chroma client
        ephemeral_client = chromadb.EphemeralClient()
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            client=ephemeral_client,
            collection_name=COLLECTION_NAME
        )

        retriever = vectorstore.as_retriever()
        logger.info("Retrieval chain created successfully")
        return retriever

    except Exception as e:
        logger.error(f"Failed to create retrieval chain: {e}")
        raise


def get_llm_instances():
    """Initialize LLM instances with proper error handling, Claude first."""
    llms = {}

    # Initialize Claude first (primary)
    try:
        llms['claude'] = ChatAnthropic(
            model=CLAUDE_MODEL,
            temperature=0.7,
            timeout=REQUEST_TIMEOUT
        )
        logger.info(f"Claude model {CLAUDE_MODEL} initialized successfully (PRIMARY)")
    except Exception as e:
        logger.warning(f"Failed to initialize Claude (primary): {e}")
        llms['claude'] = None

    # Initialize Gemini as fallback
    try:
        llms['gemini'] = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0.7,
            request_timeout=REQUEST_TIMEOUT
        )
        logger.info(f"Gemini model {GEMINI_MODEL} initialized successfully (FALLBACK)")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini (fallback): {e}")
        llms['gemini'] = None

    if not any(llms.values()):
        raise RuntimeError("No LLM models could be initialized. Check your API keys and model names.")

    return llms


def create_prompts():
    """Create the prompt templates."""
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    qa_system_prompt = (
        "You are an expert assistant for Nick Berens, a skilled developer and creative professional. "
        "Use the following pieces of retrieved context to answer the question about Nick's work, "
        "experience, projects, or expertise. If you don't know the answer based on the provided context, "
        "just say that you don't have that information. Be friendly, helpful, and concise. "
        "Highlight Nick's strengths and accomplishments when relevant."
        "\n\n"
        "Context: {context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    return contextualize_q_prompt, qa_prompt


def get_cache_key(user_input: str, chat_history: List[BaseMessage]) -> str:
    """Generate a cache key for the request."""
    if not ENABLE_CACHING:
        return None

    # Simple cache key based on input and recent history
    history_str = ""
    if chat_history and len(chat_history) > 0:
        # Use only the last 2 messages for cache key to balance performance and relevance
        recent_history = chat_history[-2:] if len(chat_history) >= 2 else chat_history
        history_str = str([msg.content for msg in recent_history])

    return f"{user_input}:{hash(history_str)}"


def get_cached_response(cache_key: str) -> Optional[str]:
    """Get cached response if available and not expired."""
    if not cache_key or not ENABLE_CACHING:
        return None

    if cache_key in _response_cache:
        cached_data = _response_cache[cache_key]
        if time.time() - cached_data['timestamp'] < CACHE_TTL:
            logger.info("Returning cached response")
            return cached_data['response']
        else:
            # Remove expired cache entry
            del _response_cache[cache_key]

    return None


def cache_response(cache_key: str, response: str):
    """Cache the response."""
    if not cache_key or not ENABLE_CACHING:
        return

    _response_cache[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }

    # Simple cache cleanup: remove oldest entries if cache gets too large
    if len(_response_cache) > 100:
        oldest_key = min(_response_cache.keys(),
                         key=lambda k: _response_cache[k]['timestamp'])
        del _response_cache[oldest_key]


def invoke_chain_with_llm(llm, retriever, contextualize_q_prompt, qa_prompt, user_input, chat_history):
    """Invoke the RAG chain with a specific LLM."""
    try:
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )
        document_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, document_chain)

        response = rag_chain.invoke({
            "input": user_input,
            "chat_history": chat_history
        })

        return response.get("answer", "I'm sorry, I couldn't generate a response.")

    except Exception as e:
        logger.error(f"Error invoking chain: {e}")
        raise


def is_rate_limit_error(error):
    """Check if the error is a rate limit error."""
    if isinstance(error, exceptions.ResourceExhausted):
        return True

    error_str = str(error).lower()
    rate_limit_indicators = [
        "rate limit", "quota", "too many requests", "429",
        "exceeded your current quota", "requests per"
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def invoke_with_fallback(retriever, chat_history: List[BaseMessage], user_input: str) -> str:
    """
    Claude-first approach with Gemini fallback.
    Enhanced with caching and better error handling.
    """
    if not retriever:
        logger.error("No retriever provided")
        return "I'm sorry, the AI service is temporarily unavailable."

    # Check cache first
    cache_key = get_cache_key(user_input, chat_history)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        return cached_response

    # Get LLM instances
    try:
        llms = get_llm_instances()
    except Exception as e:
        logger.error(f"Failed to initialize LLM instances: {e}")
        return "I'm sorry, the AI service is temporarily unavailable. Please try again later."

    # Create prompts
    contextualize_q_prompt, qa_prompt = create_prompts()

    # Define the order of LLM attempts based on PRIMARY_LLM setting
    if PRIMARY_LLM.lower() == "claude":
        llm_order = [('claude', CLAUDE_RETRY_DELAY), ('gemini', GEMINI_RETRY_DELAY)]
    else:
        llm_order = [('gemini', GEMINI_RETRY_DELAY), ('claude', CLAUDE_RETRY_DELAY)]

    # Try each LLM in order
    for llm_name, retry_delay in llm_order:
        if not llms.get(llm_name):
            logger.warning(f"{llm_name.title()} not available, skipping")
            continue

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Attempting to use {llm_name.title()} (attempt {attempt + 1}/{MAX_RETRIES + 1})...")

                response = invoke_chain_with_llm(
                    llms[llm_name], retriever, contextualize_q_prompt,
                    qa_prompt, user_input, chat_history
                )

                logger.info(f"{llm_name.title()} response successful")

                # Cache the successful response
                cache_response(cache_key, response)

                return response

            except exceptions.ResourceExhausted as e:
                logger.warning(f"{llm_name.title()} rate limit reached: {e}")

                if attempt < MAX_RETRIES:
                    logger.info(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                else:
                    logger.info(f"Max retries reached for {llm_name.title()}")
                    break

            except Exception as e:
                logger.error(f"{llm_name.title()} error (attempt {attempt + 1}): {e}")

                # Check if it's a model not found error
                if "not_found_error" in str(e) or "model:" in str(e):
                    logger.error(f"{llm_name.title()} model not found. Please check the model name.")
                    break

                if is_rate_limit_error(e):
                    if attempt < MAX_RETRIES:
                        logger.info(f"Rate limit detected, waiting {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.info(f"Max retries reached for {llm_name.title()}")
                        break
                else:
                    # For non-rate-limit errors, try next LLM immediately
                    logger.info(f"Non-rate-limit error with {llm_name.title()}, trying next LLM")
                    break

    # If we get here, all LLMs failed
    logger.error("All LLM attempts failed")
    return (
        "I'm sorry, I'm currently experiencing technical difficulties. "
        "This might be due to high demand or service issues. Please try again in a few minutes."
    )


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    if not ENABLE_CACHING:
        return {"caching": "disabled"}

    now = time.time()
    valid_entries = sum(1 for data in _response_cache.values()
                        if now - data['timestamp'] < CACHE_TTL)

    return {
        "caching": "enabled",
        "total_entries": len(_response_cache),
        "valid_entries": valid_entries,
        "cache_ttl": CACHE_TTL,
        "primary_llm": PRIMARY_LLM
    }


# Alternative simple fallback function for emergencies
def simple_fallback_response(user_input: str) -> str:
    """Provide a simple response when all AI services fail."""
    keywords_responses = {
        "hello": "Hello! I'm Nick Berens' AI assistant. How can I help you today?",
        "hi": "Hi there! How can I assist you with information about Nick Berens?",
        "help": "I can help you learn about Nick Berens' work, projects, and experience. What would you like to know?",
        "contact": "You can find Nick's contact information in his portfolio. Is there something specific you'd like to know?",
        "portfolio": "I can help you explore Nick's portfolio. What particular aspect interests you?",
        "experience": "Nick has extensive experience in web development and creative projects. What specific area interests you?",
        "projects": "Nick has worked on various interesting projects. What type of project are you curious about?",
        "skills": "Nick has a diverse skill set in development and creative work. What particular skills are you interested in learning about?",
        "background": "I can tell you about Nick's professional background and experience. What would you like to know?",
    }

    user_lower = user_input.lower()
    for keyword, response in keywords_responses.items():
        if keyword in user_lower:
            return response

    return (
        "I'm currently experiencing technical difficulties, but I'm here to help you learn about Nick Berens. "
        "Could you try rephrasing your question or ask something specific about his work, experience, or projects?"
    )
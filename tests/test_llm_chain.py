"""Tests for core.llm_chain module."""

import time
from typing import List
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.messages import BaseMessage

from backend.core.llm_chain import (
    cache_response,
    cache_retrieval,
    get_cache_key,
    get_cached_response,
    get_cached_retrieval,
    get_llm_instances,
    stream_with_fallback,
    VectorStoreManager,
)


class TestLLMChain:
    """Test cases for LLM chain module."""

    def setup_method(self):
        """Setup method to clear caches before each test."""
        # Clear caches before each test
        import backend.core.llm_chain as llm_chain

        llm_chain._response_cache.clear()
        llm_chain._retrieval_cache.clear()

    @pytest.mark.unit
    def test_get_cache_key_valid_input(self):
        """Test cache key generation with valid input."""
        user_input = "What is Nick's experience?"
        cache_key = get_cache_key(user_input)

        # Should return a 16-character hex string
        assert cache_key is not None
        assert len(cache_key) == 16
        assert all(c in "0123456789abcdef" for c in cache_key)

        # Same input should produce same key
        cache_key2 = get_cache_key(user_input)
        assert cache_key == cache_key2

    @pytest.mark.unit
    def test_get_cache_key_normalization(self):
        """Test that cache key normalizes input correctly."""
        # Different punctuation and case should produce same key
        inputs = [
            "What is Nick's experience?",
            "what is nicks experience",
            "WHAT IS NICK'S EXPERIENCE!!!",
            "What... is Nick's experience???",
        ]

        cache_keys = [get_cache_key(inp) for inp in inputs]
        # All should be the same after normalization
        assert len(set(cache_keys)) == 1

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_get_cache_key_caching_disabled(self):
        """Test cache key returns None when caching is disabled."""
        cache_key = get_cache_key("test input")
        assert cache_key is None

    @pytest.mark.unit
    def test_get_cache_key_invalid_input(self):
        """Test cache key with invalid input types."""
        assert get_cache_key(None) is None
        assert get_cache_key(123) is None  # type: ignore
        assert get_cache_key([]) is None  # type: ignore

    @pytest.mark.unit
    def test_cache_response_and_get_cached_response(self):
        """Test response caching and retrieval."""
        cache_key = "test_key_123"
        response_chunks = ["Hello ", "world", "!"]

        # Cache the response
        cache_response(cache_key, response_chunks)

        # Retrieve the cached response
        cached = get_cached_response(cache_key)
        assert cached == "Hello world!"

    @pytest.mark.unit
    def test_get_cached_response_expired(self):
        """Test that expired cache entries are removed."""
        cache_key = "expired_key"
        response_chunks = ["test response"]

        # Cache the response
        cache_response(cache_key, response_chunks)

        # Manually set timestamp to past expiry
        import backend.core.llm_chain as llm_chain

        llm_chain._response_cache[cache_key]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Should return None and remove expired entry
        cached = get_cached_response(cache_key)
        assert cached is None
        assert cache_key not in llm_chain._response_cache

    @pytest.mark.unit
    def test_get_cached_response_not_found(self):
        """Test cache miss returns None."""
        cached = get_cached_response("nonexistent_key")
        assert cached is None

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_cache_response_caching_disabled(self):
        """Test that caching is skipped when disabled."""
        cache_key = "test_key"
        response_chunks = ["test"]

        cache_response(cache_key, response_chunks)
        cached = get_cached_response(cache_key)

        assert cached is None

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_cache_retrieval_caching_disabled(self):
        """Test that retrieval caching is skipped when disabled."""
        cache_key = "test_key"
        documents = [Document(page_content="Test", metadata={"source": "test"})]

        cache_retrieval(cache_key, documents)
        cached = get_cached_retrieval(cache_key)

        assert cached is None

    @pytest.mark.unit
    def test_cache_response_eviction(self):
        """Test cache eviction when max size is reached."""
        import backend.core.llm_chain as llm_chain

        # Mock MAX_CACHE_SIZE to be small
        with patch("backend.core.llm_chain.MAX_CACHE_SIZE", 2):
            # Add entries up to limit
            cache_response("key1", ["response1"])
            cache_response("key2", ["response2"])

            # Add one more - should evict oldest
            time.sleep(0.01)  # Ensure different timestamps
            cache_response("key3", ["response3"])

            # key1 should be evicted, key2 and key3 should remain
            assert len(llm_chain._response_cache) == 2
            assert "key1" not in llm_chain._response_cache
            assert "key2" in llm_chain._response_cache
            assert "key3" in llm_chain._response_cache

    @pytest.mark.unit
    def test_cache_retrieval_and_get_cached_retrieval(self):
        """Test document retrieval caching and retrieval."""
        cache_key = "retrieval_key"
        documents = [
            Document(page_content="Test doc 1", metadata={"source": "test"}),
            Document(page_content="Test doc 2", metadata={"source": "test"}),
        ]

        # Cache the documents
        cache_retrieval(cache_key, documents)

        # Retrieve cached documents
        cached_docs = get_cached_retrieval(cache_key)
        assert cached_docs is not None
        assert len(cached_docs) == 2
        assert cached_docs[0].page_content == "Test doc 1"
        assert cached_docs[1].page_content == "Test doc 2"

    @pytest.mark.unit
    def test_route_query_to_retrievers_resume_keywords(self):
        """Test query routing for resume-related queries."""
        mock_retrievers = {
            "resume": MagicMock(spec=BaseRetriever),
            "about": MagicMock(spec=BaseRetriever),
            "illustration": MagicMock(spec=BaseRetriever),
        }

        queries = [
            "What is Nick's work experience?",
            "Tell me about his job history",
            "What skills does he have?",
            "What companies has he worked for?",
        ]

        for query in queries:
            retrievers = VectorStoreManager.route_query_to_retrievers(query, mock_retrievers)
            assert mock_retrievers["resume"] in retrievers

    @pytest.mark.unit
    def test_route_query_to_retrievers_about_keywords(self):
        """Test query routing for about-related queries."""
        mock_retrievers = {
            "resume": MagicMock(spec=BaseRetriever),
            "about": MagicMock(spec=BaseRetriever),
            "illustration": MagicMock(spec=BaseRetriever),
        }

        queries = [
            "Tell me about Nick",
            "What is his background?",
            "Who is Nick?",
            "What's his philosophy?",
        ]

        for query in queries:
            retrievers = VectorStoreManager.route_query_to_retrievers(query, mock_retrievers)
            assert mock_retrievers["about"] in retrievers

    @pytest.mark.unit
    def test_route_query_to_retrievers_illustration_keywords(self):
        """Test query routing for illustration-related queries."""
        mock_retrievers = {
            "resume": MagicMock(spec=BaseRetriever),
            "about": MagicMock(spec=BaseRetriever),
            "illustration": MagicMock(spec=BaseRetriever),
        }

        queries = [
            "Show me his art",
            "What illustrations has he done?",
            "Tell me about his drawings",
            "What's his design style?",
        ]

        for query in queries:
            retrievers = VectorStoreManager.route_query_to_retrievers(query, mock_retrievers)
            assert mock_retrievers["illustration"] in retrievers

    @pytest.mark.unit
    def test_route_query_to_retrievers_default_fallback(self):
        """Test query routing falls back to resume and about for generic queries."""
        mock_retrievers = {
            "resume": MagicMock(spec=BaseRetriever),
            "about": MagicMock(spec=BaseRetriever),
            "illustration": MagicMock(spec=BaseRetriever),
        }

        # Generic query with no specific keywords
        query = "Tell me something interesting"
        retrievers = VectorStoreManager.route_query_to_retrievers(query, mock_retrievers)

        # Should default to resume and about
        assert mock_retrievers["resume"] in retrievers
        assert mock_retrievers["about"] in retrievers
        assert len(retrievers) == 2

    @pytest.mark.unit
    def test_route_query_to_retrievers_missing_retriever(self):
        """Test query routing when some retrievers are missing."""
        # Only provide resume retriever
        mock_retrievers = {"resume": MagicMock(spec=BaseRetriever)}

        query = "Tell me about Nick's background"  # Should route to 'about' but it's missing
        retrievers = VectorStoreManager.route_query_to_retrievers(query, mock_retrievers)

        # Should only return available retrievers
        assert len(retrievers) == 0  # 'about' is not available

    @patch("backend.core.llm_chain.ChatAnthropic")
    @patch("backend.core.llm_chain.ChatGoogleGenerativeAI")
    @pytest.mark.unit
    def test_get_llm_instances_success(self, mock_gemini, mock_claude):
        """Test successful LLM instance creation."""
        mock_claude_instance = MagicMock()
        mock_gemini_instance = MagicMock()
        mock_claude.return_value = mock_claude_instance
        mock_gemini.return_value = mock_gemini_instance

        llms = get_llm_instances()

        # Check that the returned instances are the mocked ones
        assert llms["claude"] is mock_claude_instance
        assert llms["gemini"] is mock_gemini_instance
        mock_claude.assert_called_once()
        mock_gemini.assert_called_once()

    @patch("backend.core.llm_chain.ChatAnthropic")
    @patch("backend.core.llm_chain.ChatGoogleGenerativeAI")
    @pytest.mark.unit
    def test_get_llm_instances_claude_fails(self, mock_gemini, mock_claude):
        """Test LLM instance creation when Claude fails."""
        mock_claude.side_effect = Exception("Claude API error")
        mock_gemini_instance = MagicMock()
        mock_gemini.return_value = mock_gemini_instance

        llms = get_llm_instances()

        assert llms["claude"] is None
        assert llms["gemini"] is mock_gemini_instance

    @patch("backend.core.llm_chain.ChatAnthropic")
    @patch("backend.core.llm_chain.ChatGoogleGenerativeAI")
    @pytest.mark.unit
    def test_get_llm_instances_all_fail(self, mock_gemini, mock_claude):
        """Test LLM instance creation when all models fail."""
        mock_claude.side_effect = Exception("Claude API error")
        mock_gemini.side_effect = Exception("Gemini API error")

        # The function should raise RuntimeError when no models can be initialized
        with pytest.raises(RuntimeError, match="No LLM models could be initialized"):
            get_llm_instances()

    @patch("backend.core.llm_chain.chromadb.EphemeralClient")
    @patch("backend.core.llm_chain.Chroma")
    @pytest.mark.unit
    def test_create_multi_vector_retriever_success(self, mock_chroma, mock_client):
        """Test successful creation of multi-vector retrievers."""
        # Mock documents
        docs = [
            Document(page_content="Resume content", metadata={"source": "resume"}),
            Document(page_content="About content", metadata={"source": "about"}),
            Document(page_content="Art content", metadata={"source": "illustration"}),
        ]

        # Mock embeddings
        mock_embeddings = MagicMock()

        # Mock Chroma vectorstore
        mock_vectorstore = MagicMock()
        mock_retriever = MagicMock(spec=BaseRetriever)
        mock_vectorstore.as_retriever.return_value = mock_retriever
        mock_chroma.from_documents.return_value = mock_vectorstore

        # Mock client
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        retrievers = VectorStoreManager.create_multi_vector_retriever(docs, mock_embeddings)

        # Should create retrievers for all three sources
        assert len(retrievers) == 3
        assert "resume" in retrievers
        assert "about" in retrievers
        assert "illustration" in retrievers

        # Verify Chroma was called for each source
        assert mock_chroma.from_documents.call_count == 3

    @patch("backend.core.llm_chain.chromadb.EphemeralClient")
    @patch("backend.core.llm_chain.Chroma")
    @pytest.mark.unit
    def test_create_multi_vector_retriever_missing_sources(self, mock_chroma, mock_client):
        """Test retriever creation with missing document sources."""
        # Only resume documents
        docs = [
            Document(page_content="Resume content", metadata={"source": "resume"}),
        ]

        mock_embeddings = MagicMock()
        mock_vectorstore = MagicMock()
        mock_retriever = MagicMock(spec=BaseRetriever)
        mock_vectorstore.as_retriever.return_value = mock_retriever
        mock_chroma.from_documents.return_value = mock_vectorstore

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        retrievers = VectorStoreManager.create_multi_vector_retriever(docs, mock_embeddings)

        # Should only create retriever for resume
        assert len(retrievers) == 1
        assert "resume" in retrievers
        assert "about" not in retrievers
        assert "illustration" not in retrievers

    @patch("backend.core.llm_chain.chromadb.EphemeralClient")
    @patch("backend.core.llm_chain.Chroma")
    @pytest.mark.unit
    def test_create_multi_vector_retriever_chroma_error(self, mock_chroma, mock_client):
        """Test retriever creation when Chroma fails."""
        docs = [
            Document(page_content="Resume content", metadata={"source": "resume"}),
        ]

        mock_embeddings = MagicMock()
        mock_chroma.from_documents.side_effect = Exception("Chroma error")

        with pytest.raises(Exception, match="Chroma error"):
            VectorStoreManager.create_multi_vector_retriever(docs, mock_embeddings)

    @pytest.mark.unit
    def test_get_cached_retrieval_expired(self):
        """Test that expired retrieval cache entries are removed."""
        cache_key = "expired_retrieval_key"
        documents = [Document(page_content="Test", metadata={"source": "test"})]

        # Cache the documents
        cache_retrieval(cache_key, documents)

        # Manually set timestamp to past expiry
        import backend.core.llm_chain as llm_chain

        llm_chain._retrieval_cache[cache_key]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Should return None and remove expired entry
        cached = get_cached_retrieval(cache_key)
        assert cached is None
        assert cache_key not in llm_chain._retrieval_cache

    @pytest.mark.unit
    def test_cache_retrieval_eviction(self):
        """Test retrieval cache eviction when max size is reached."""
        import backend.core.llm_chain as llm_chain

        # Mock MAX_CACHE_SIZE to be small
        with patch("backend.core.llm_chain.MAX_CACHE_SIZE", 2):
            doc1 = [Document(page_content="Doc 1", metadata={"source": "test"})]
            doc2 = [Document(page_content="Doc 2", metadata={"source": "test"})]
            doc3 = [Document(page_content="Doc 3", metadata={"source": "test"})]

            # Add entries up to limit
            cache_retrieval("key1", doc1)
            cache_retrieval("key2", doc2)

            # Add one more - should evict oldest
            time.sleep(0.01)  # Ensure different timestamps
            cache_retrieval("key3", doc3)

            # key1 should be evicted, key2 and key3 should remain
            assert len(llm_chain._retrieval_cache) == 2
            assert "key1" not in llm_chain._retrieval_cache
            assert "key2" in llm_chain._retrieval_cache
            assert "key3" in llm_chain._retrieval_cache

    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_cached_response(
            self, mock_get_llms, mock_get_cache_key, mock_cached_response
    ):
        """Test stream_with_fallback returns cached response when available."""
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = "Cached response"

        retrievers = {"resume": MagicMock(spec=BaseRetriever)}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert result == ["Cached response"]
        assert model_used == "cached"
        # Should not call other functions when cache hit
        mock_get_llms.assert_not_called()

    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_llm_init_error(
            self, mock_get_llms, mock_get_cache_key, mock_cached_response
    ):
        """Test stream_with_fallback handles LLM initialization errors."""
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = None  # No cached response
        mock_get_llms.side_effect = RuntimeError("LLM init failed")

        retrievers = {"resume": MagicMock(spec=BaseRetriever)}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert len(result) == 1
        assert "AI service is temporarily unavailable" in result[0]
        assert model_used == "error"

    @patch("backend.core.llm_chain.VectorStoreManager.route_query_to_retrievers")
    @patch("backend.core.llm_chain.CacheManager.get_cached_retrieval")
    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @patch("backend.core.llm_chain.create_qa_chain")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_normal_flow(
            self, mock_create_qa_chain, mock_get_llms, mock_get_cache_key,
            mock_cached_response, mock_cached_retrieval, mock_route
    ):
        """Test stream_with_fallback normal execution flow."""
        # Setup mocks
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = None  # No cached response
        mock_cached_retrieval.return_value = None  # No cached retrieval

        # Mock LLM instances
        mock_claude = MagicMock()
        mock_get_llms.return_value = {"claude": mock_claude, "gemini": None}

        # Mock QA chain
        mock_qa_chain = AsyncMock()

        async def mock_astream(*args, **kwargs):
            for chunk in ["Hello", " world"]:
                yield chunk

        mock_qa_chain.astream = mock_astream
        mock_create_qa_chain.return_value = mock_qa_chain

        # Mock retrievers and routing
        mock_retriever = AsyncMock(spec=BaseRetriever)
        mock_retriever.ainvoke.return_value = [
            Document(page_content="Test content", metadata={"source": "test"})
        ]
        mock_route.return_value = [mock_retriever]

        retrievers = {"resume": mock_retriever}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert result == ["Hello", " world"]
        assert model_used == "claude"
        assert "rate_limit_status" in metadata

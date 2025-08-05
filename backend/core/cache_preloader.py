"""
Cache preloader for common queries.

This module handles pre-loading of frequently asked questions into the response
and retrieval caches to improve response times for common queries.
"""

import asyncio
import logging
from typing import Dict, List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from .data_source_config import config as data_config
from .llm_chain import CacheManager, VectorStoreManager, create_qa_chain, get_llm_instances

logger = logging.getLogger(__name__)


class CachePreloader:
    """Handles pre-loading of common queries into cache."""

    @staticmethod
    def get_preload_queries() -> List[str]:
        """Get the list of queries to pre-load from configuration."""
        preload_config = data_config.cache_preload
        if not preload_config.get("enabled", False):
            return []

        queries = preload_config.get("queries", [])
        return list(queries) if queries else []

    @staticmethod
    async def preload_query_cache(retrievers: Dict[str, BaseRetriever]) -> None:
        """
        Pre-load common queries into both retrieval and response caches.

        Args:
            retrievers: Dictionary of available retrievers
        """
        queries = CachePreloader.get_preload_queries()

        if not queries:
            logger.info("Cache preloading disabled or no queries configured")
            return

        if not retrievers:
            logger.warning("No retrievers available for cache preloading")
            return

        logger.info(f"Starting cache preloading for {len(queries)} queries...")

        try:
            # Get LLM instances for response generation
            llms = get_llm_instances()
            primary_llm = llms.get("claude") or llms.get("gemini")

            if not primary_llm:
                logger.warning("No LLM available for cache preloading")
                return

            qa_chain = create_qa_chain(primary_llm)

            # Process each query
            successful_preloads = 0

            for query in queries:
                try:
                    await CachePreloader._preload_single_query(query, retrievers, qa_chain)
                    successful_preloads += 1
                    logger.debug(f"Successfully preloaded: {query}")

                except Exception as e:
                    logger.warning(f"Failed to preload query '{query}': {e}")

            logger.info(f"Cache preloading completed: {successful_preloads}/{len(queries)} queries cached")

        except Exception as e:
            logger.error(f"Cache preloading failed: {e}")

    @staticmethod
    async def _preload_single_query(query: str, retrievers: Dict[str, BaseRetriever], qa_chain) -> None:
        """
        Pre-load a single query into cache.

        Args:
            query: The query string to pre-load
            retrievers: Dictionary of available retrievers
            qa_chain: The QA chain for generating responses
        """
        cache_key = CacheManager.get_cache_key(query)
        if not cache_key:
            return

        # Check if already cached
        if CacheManager.get_cached_response(cache_key):
            logger.debug(f"Query already cached: {query}")
            return

        # Perform retrieval
        selected_retrievers = VectorStoreManager.route_query_to_retrievers(query, retrievers)

        if not selected_retrievers:
            logger.debug(f"No retrievers selected for query: {query}")
            return

        # Execute retrieval tasks
        tasks = [retriever.ainvoke(query) for retriever in selected_retrievers]
        retrieval_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect documents
        all_docs: List[Document] = []
        for result in retrieval_results:
            if isinstance(result, Exception):
                logger.debug(f"Retrieval error for '{query}': {result}")
            elif result and isinstance(result, list):
                all_docs.extend(result)

        # Deduplicate documents
        import hashlib
        import json

        unique_docs = list(
            {
                hashlib.sha256(
                    f"{doc.page_content}{json.dumps(doc.metadata, sort_keys=True)}".encode("utf-8")
                ).hexdigest(): doc
                for doc in all_docs
            }.values()
        )

        # Cache retrieval results
        CacheManager.cache_retrieval(cache_key, unique_docs)

        # Generate and cache response
        try:
            response_chunks = []
            async for chunk in qa_chain.astream({"input": query, "context": unique_docs}):
                response_chunks.append(chunk)

            # Cache the full response
            CacheManager.cache_response(cache_key, response_chunks)

        except Exception as e:
            logger.debug(f"Response generation failed for '{query}': {e}")

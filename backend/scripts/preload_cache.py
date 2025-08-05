#!/usr/bin/env python
"""
Manual cache pre-loading script.

This script allows you to manually trigger the cache pre-loading process
without starting the full application. Useful for testing and warming up
the cache on demand.

Usage:
    python backend/scripts/preload_cache.py
    python backend/scripts/preload_cache.py --query "specific query to preload"
    python backend/scripts/preload_cache.py --all --force
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.cache_preloader import CachePreloader  # noqa: E402
from core.config import AppConfig  # noqa: E402
from core.data_loader import load_all_documents  # noqa: E402
from core.llm_chain import CacheManager, create_multi_vector_retriever, create_qa_chain, get_llm_instances  # noqa: E402
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def preload_single_query(query: str, force: bool = False) -> bool:
    """
    Pre-load a single query into cache.

    Args:
        query: The query to pre-load
        force: If True, overwrite existing cache entry

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if already cached
        cache_key = CacheManager.get_cache_key(query)
        if cache_key and CacheManager.get_cached_response(cache_key) and not force:
            logger.info(f"Query already cached: '{query}' (use --force to overwrite)")
            return True

        logger.info(f"Pre-loading query: '{query}'")

        # Load documents and create retrievers
        docs, _ = load_all_documents()
        embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)
        retrievers = create_multi_vector_retriever(docs, embeddings)

        if not retrievers:
            logger.error("Failed to create retrievers")
            return False

        # Get LLM and create QA chain
        llms = get_llm_instances()
        primary_llm = llms.get("claude") or llms.get("gemini")

        if not primary_llm:
            logger.error("No LLM available for pre-loading")
            return False

        qa_chain = create_qa_chain(primary_llm)

        # Pre-load the query
        await CachePreloader._preload_single_query(query, retrievers, qa_chain)

        logger.info(f"Successfully pre-loaded: '{query}'")
        return True

    except Exception as e:
        logger.error(f"Failed to pre-load query '{query}': {e}")
        return False


async def preload_all_configured_queries(force: bool = False) -> None:
    """
    Pre-load all queries configured in data_sources.yaml.

    Args:
        force: If True, overwrite existing cache entries
    """
    queries = CachePreloader.get_preload_queries()

    if not queries:
        logger.warning("No queries configured for pre-loading")
        return

    logger.info(f"Pre-loading {len(queries)} configured queries...")

    # Load documents and create retrievers once
    docs, _ = load_all_documents()
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)
    retrievers = create_multi_vector_retriever(docs, embeddings)

    if not retrievers:
        logger.error("Failed to create retrievers")
        return

    # Get LLM and create QA chain
    llms = get_llm_instances()
    primary_llm = llms.get("claude") or llms.get("gemini")

    if not primary_llm:
        logger.error("No LLM available for pre-loading")
        return

    qa_chain = create_qa_chain(primary_llm)

    # Pre-load queries
    if force:
        logger.info("Force mode enabled - overwriting existing cache entries")

    successful = 0
    for query in queries:
        cache_key = CacheManager.get_cache_key(query)
        if cache_key and CacheManager.get_cached_response(cache_key) and not force:
            logger.info(f"Skipping already cached: '{query}'")
            successful += 1
            continue

        try:
            await CachePreloader._preload_single_query(query, retrievers, qa_chain)
            successful += 1
            logger.info(f"✓ Pre-loaded: '{query}'")
        except Exception as e:
            logger.error(f"✗ Failed: '{query}' - {e}")

    logger.info(f"Cache pre-loading completed: {successful}/{len(queries)} queries cached")


async def show_cache_status() -> None:
    """Display current cache status."""
    queries = CachePreloader.get_preload_queries()

    logger.info("Cache Status:")
    logger.info(f"Configured queries: {len(queries)}")

    cached_count = 0
    for query in queries:
        cache_key = CacheManager.get_cache_key(query)
        if cache_key and CacheManager.get_cached_response(cache_key):
            cached_count += 1
            logger.info(f"  ✓ Cached: '{query}'")
        else:
            logger.info(f"  ✗ Not cached: '{query}'")

    logger.info(f"Total cached: {cached_count}/{len(queries)}")


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manually pre-load queries into cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-load all configured queries
  python backend/scripts/preload_cache.py --all

  # Pre-load a specific query
  python backend/scripts/preload_cache.py --query "What is your experience?"

  # Force overwrite existing cache
  python backend/scripts/preload_cache.py --all --force

  # Show cache status
  python backend/scripts/preload_cache.py --status
        """,
    )

    parser.add_argument("--all", action="store_true", help="Pre-load all queries from configuration")
    parser.add_argument("--query", type=str, help="Pre-load a specific query")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing cache entries")
    parser.add_argument("--status", action="store_true", help="Show current cache status")

    args = parser.parse_args()

    # Validate arguments
    if not any([args.all, args.query, args.status]):
        parser.error("Must specify --all, --query, or --status")

    if args.query and args.all:
        parser.error("Cannot use --query and --all together")

    # Execute requested action
    try:
        if args.status:
            await show_cache_status()
        elif args.query:
            success = await preload_single_query(args.query, args.force)
            sys.exit(0 if success else 1)
        elif args.all:
            await preload_all_configured_queries(args.force)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Simplified benchmark runner that works with your actual embedding system.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.core.app_initializer_v2 import initialize_app_v2  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_simple_benchmark():
    """Run a simplified benchmark using your existing system."""
    try:
        logger.info("🚀 Starting Contextual Retrieval Benchmark")

        # Initialize your actual app to get embeddings and retrievers
        logger.info("Initializing app components...")
        app_components = await initialize_app_v2()

        if not app_components or "retrievers" not in app_components:
            logger.error("Failed to initialize app components")
            return

        retrievers = app_components["retrievers"]
        unified_retriever = retrievers.get("unified")

        if not unified_retriever:
            logger.error("Unified retriever not found")
            return

        # Test queries
        test_queries = [
            {
                "question": "What programming languages does Nick know?",
                "expected_types": ["technical", "skills"],
                "difficulty": "easy",
            },
            {
                "question": "Tell me about Nick's work experience",
                "expected_types": ["experience"],
                "difficulty": "medium",
            },
            {
                "question": "What inspires Nick's creative work?",
                "expected_types": ["creative", "about"],
                "difficulty": "hard",
            },
            {
                "question": "How does Nick approach full-stack development?",
                "expected_types": ["technical", "about"],
                "difficulty": "hard",
            },
        ]

        results = []

        logger.info("Running test queries...")
        for i, query in enumerate(test_queries, 1):
            logger.info(f"Query {i}/{len(test_queries)}: {query['question']}")

            # Test with current contextual system
            start_time = asyncio.get_event_loop().time()
            docs = unified_retriever.auto_route_query(query["question"])
            end_time = asyncio.get_event_loop().time()

            retrieval_time = end_time - start_time
            num_docs = len(docs)

            # Analyze results
            has_contextual_chunks = sum(1 for doc in docs if doc.metadata.get("has_document_context", False))

            # Check content type matching
            found_types = set()
            for doc in docs:
                if "content_types" in doc.metadata:
                    found_types.update(doc.metadata["content_types"].split(","))

            expected_types = set(query["expected_types"])
            type_match_ratio = len(found_types.intersection(expected_types)) / len(expected_types)

            result = {
                "question": query["question"],
                "difficulty": query["difficulty"],
                "retrieval_time": retrieval_time,
                "num_documents": num_docs,
                "contextual_chunks": has_contextual_chunks,
                "type_match_ratio": type_match_ratio,
                "found_types": list(found_types),
                "expected_types": query["expected_types"],
                "sample_content": docs[0].page_content[:200] + "..." if docs else "No results",
            }

            results.append(result)
            logger.info(
                f"  → Found {num_docs} docs, {has_contextual_chunks} with context, type match: {type_match_ratio:.2f}"
            )

        # Generate summary
        avg_time = sum(r["retrieval_time"] for r in results) / len(results)
        avg_docs = sum(r["num_documents"] for r in results) / len(results)
        avg_contextual = sum(r["contextual_chunks"] for r in results) / len(results)
        avg_type_match = sum(r["type_match_ratio"] for r in results) / len(results)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "system_type": "contextual_retrieval",
            "total_queries": len(results),
            "averages": {
                "retrieval_time": avg_time,
                "documents_per_query": avg_docs,
                "contextual_chunks_per_query": avg_contextual,
                "type_match_accuracy": avg_type_match,
            },
            "query_results": results,
        }

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contextual_benchmark_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("🔍 CONTEXTUAL RETRIEVAL BENCHMARK RESULTS")
        print("=" * 60)
        print("System Type: Contextual Retrieval")
        print(f"Total Queries: {len(results)}")
        print(f"Average Retrieval Time: {avg_time:.3f}s")
        print(f"Average Documents Retrieved: {avg_docs:.1f}")
        print(f"Average Contextual Chunks: {avg_contextual:.1f}")
        print(f"Average Type Match Accuracy: {avg_type_match:.3f}")

        print("\n📋 INDIVIDUAL QUERY RESULTS:")
        print(f"{'Query':<40} {'Time':<8} {'Docs':<6} {'Context':<8} {'Type Match':<10}")
        print("-" * 80)

        for result in results:
            query_short = result["question"][:37] + "..." if len(result["question"]) > 40 else result["question"]
            print(
                f"{query_short:<40} {result['retrieval_time']:.3f}s  {result['num_documents']:<6} {result['contextual_chunks']:<8} {result['type_match_ratio']:.3f}"
            )

        print(f"\n💾 Detailed results saved to: {filename}")

        # Evidence of contextual enhancement
        contextual_evidence = sum(1 for r in results if r["contextual_chunks"] > 0)
        print("\n🧠 CONTEXTUAL ENHANCEMENT EVIDENCE:")
        print(f"Queries with contextual chunks: {contextual_evidence}/{len(results)}")

        if contextual_evidence > 0:
            print("✅ Contextual retrieval is active and working!")
            print("📈 Chunks are being enhanced with document context")
        else:
            print("⚠️  No contextual chunks detected - may need to rebuild indices")

        print("\n🎯 Sample enhanced chunk content:")
        for result in results:
            if result["contextual_chunks"] > 0:
                print(f"Query: {result['question']}")
                print(f"Sample: {result['sample_content']}")
                break

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_simple_benchmark())

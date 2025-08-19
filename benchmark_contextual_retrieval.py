#!/usr/bin/env python3
"""
Benchmark test comparing contextual retrieval vs non-contextual retrieval.

This script evaluates the performance improvement of adding document context
to chunks for retrieval accuracy.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel

# Import our retrieval systems
from backend.core.unified_retriever import UnifiedRetriever
from backend.core.llm_chain import get_llm_instances

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestQuery:
    """A test query with expected characteristics."""
    question: str
    expected_content_types: List[str]
    expected_keywords: List[str]
    difficulty: str  # 'easy', 'medium', 'hard'
    description: str


@dataclass
class RetrievalResult:
    """Results from a retrieval test."""
    query: str
    retriever_type: str  # 'contextual' or 'non_contextual'
    documents: List[Dict[str, Any]]
    retrieval_time: float
    relevance_score: float
    content_type_accuracy: float
    keyword_coverage: float


@dataclass
class BenchmarkResults:
    """Complete benchmark results."""
    timestamp: str
    contextual_results: List[RetrievalResult]
    non_contextual_results: List[RetrievalResult]
    summary: Dict[str, Any]


class NonContextualRetriever(UnifiedRetriever):
    """
    A version of UnifiedRetriever that doesn't add document context to chunks.
    This represents the "old" way of doing retrieval.
    """
    
    def _enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
        """Override to NOT add document context - this is the old behavior."""
        # Just add metadata but don't modify the content
        enhanced_chunk = Document(
            page_content=chunk.page_content,  # NO context prepended
            metadata={
                **chunk.metadata,
                "has_document_context": False,  # Mark as non-contextual
                "original_content_length": len(chunk.page_content)
            }
        )
        return enhanced_chunk


class RetrievalBenchmark:
    """Benchmark system for comparing retrieval methods."""
    
    def __init__(self, embeddings: Any, llm: BaseLanguageModel):
        self.embeddings = embeddings
        self.llm = llm
        self.test_queries = self._create_test_queries()
        
        # Create both retriever types
        self.contextual_retriever = UnifiedRetriever(
            embeddings=embeddings,
            llm=llm,
            persist_dir="benchmark_contextual_chroma"
        )
        
        self.non_contextual_retriever = NonContextualRetriever(
            embeddings=embeddings, 
            llm=llm,
            persist_dir="benchmark_non_contextual_chroma"
        )
    
    def _create_test_queries(self) -> List[TestQuery]:
        """Create a comprehensive set of test queries."""
        return [
            TestQuery(
                question="What programming languages does Nick know?",
                expected_content_types=["technical", "skills"],
                expected_keywords=["python", "javascript", "react", "typescript"],
                difficulty="easy",
                description="Basic skills query - should find technical content"
            ),
            TestQuery(
                question="Tell me about Nick's work experience at tech companies",
                expected_content_types=["experience"],
                expected_keywords=["company", "role", "position", "work", "experience"],
                difficulty="medium",
                description="Experience query - needs to distinguish work from projects"
            ),
            TestQuery(
                question="What inspires Nick's creative work and artistic style?",
                expected_content_types=["creative", "about"],
                expected_keywords=["inspiration", "artistic", "creative", "art", "style"],
                difficulty="hard",
                description="Complex creative query - needs context to understand artistic inspiration"
            ),
            TestQuery(
                question="How does Nick approach full-stack development?",
                expected_content_types=["technical", "about"],
                expected_keywords=["full-stack", "development", "approach", "philosophy"],
                difficulty="hard", 
                description="Philosophy query - needs context about development approach"
            ),
            TestQuery(
                question="What projects has Nick built with React?",
                expected_content_types=["project", "technical"],
                expected_keywords=["react", "project", "built", "created"],
                difficulty="medium",
                description="Project-specific query - should find React projects"
            ),
            TestQuery(
                question="What is Nick's educational background?",
                expected_content_types=["about", "experience"],
                expected_keywords=["education", "degree", "university", "school"],
                difficulty="easy",
                description="Education query - basic biographical information"
            ),
            TestQuery(
                question="How does Nick balance technical and creative work?",
                expected_content_types=["about", "creative", "technical"],
                expected_keywords=["balance", "technical", "creative", "work"],
                difficulty="hard",
                description="Complex multi-domain query requiring context understanding"
            ),
            TestQuery(
                question="What databases and data technologies does Nick use?",
                expected_content_types=["technical", "skills"],
                expected_keywords=["database", "data", "sql", "nosql"],
                difficulty="medium",
                description="Specific technical domain query"
            ),
        ]
    
    async def index_test_data(self, force_rebuild: bool = True) -> None:
        """Index test data in both retrievers."""
        logger.info("Indexing data for both retriever types...")
        
        # Use existing knowledge directory
        knowledge_dir = "backend/knowledge"
        public_dir = "public"
        
        # Index in contextual retriever
        logger.info("Indexing with contextual retriever...")
        ctx_files, ctx_chunks = self.contextual_retriever.index_directory(knowledge_dir, force_rebuild)
        ctx_pub_files, ctx_pub_chunks = self.contextual_retriever.index_directory(public_dir, force_rebuild)
        
        # Index in non-contextual retriever  
        logger.info("Indexing with non-contextual retriever...")
        non_ctx_files, non_ctx_chunks = self.non_contextual_retriever.index_directory(knowledge_dir, force_rebuild)
        non_ctx_pub_files, non_ctx_pub_chunks = self.non_contextual_retriever.index_directory(public_dir, force_rebuild)
        
        logger.info(f"Contextual: {ctx_files + ctx_pub_files} files, {ctx_chunks + ctx_pub_chunks} chunks")
        logger.info(f"Non-contextual: {non_ctx_files + non_ctx_pub_files} files, {non_ctx_chunks + non_ctx_pub_chunks} chunks")
    
    def _evaluate_retrieval_quality(self, query: TestQuery, documents: List[Document]) -> Tuple[float, float, float]:
        """
        Evaluate the quality of retrieved documents.
        
        Returns:
            relevance_score: Overall relevance (0-1)
            content_type_accuracy: How well content types match expected (0-1) 
            keyword_coverage: How many expected keywords are covered (0-1)
        """
        if not documents:
            return 0.0, 0.0, 0.0
        
        # Relevance score based on document metadata and content
        relevance_scores = []
        for doc in documents:
            score = 0.0
            
            # Check content type matching
            if "content_types" in doc.metadata:
                doc_types = doc.metadata["content_types"].split(",")
                type_matches = sum(1 for expected in query.expected_content_types 
                                 if any(expected in doc_type for doc_type in doc_types))
                score += type_matches / len(query.expected_content_types) * 0.4
            
            # Check keyword presence in content
            content_lower = doc.page_content.lower()
            keyword_matches = sum(1 for keyword in query.expected_keywords 
                                if keyword.lower() in content_lower)
            score += keyword_matches / len(query.expected_keywords) * 0.6
            
            relevance_scores.append(score)
        
        # Overall relevance (weighted by position)
        relevance_score = sum(score * (1.0 / (i + 1)) for i, score in enumerate(relevance_scores)) / sum(1.0 / (i + 1) for i in range(len(relevance_scores)))
        
        # Content type accuracy
        all_doc_types = []
        for doc in documents:
            if "content_types" in doc.metadata:
                all_doc_types.extend(doc.metadata["content_types"].split(","))
        
        type_accuracy = 0.0
        if all_doc_types:
            matching_types = sum(1 for expected in query.expected_content_types 
                               if any(expected in doc_type for doc_type in all_doc_types))
            type_accuracy = matching_types / len(query.expected_content_types)
        
        # Keyword coverage
        all_content = " ".join(doc.page_content.lower() for doc in documents)
        covered_keywords = sum(1 for keyword in query.expected_keywords 
                             if keyword.lower() in all_content)
        keyword_coverage = covered_keywords / len(query.expected_keywords)
        
        return relevance_score, type_accuracy, keyword_coverage
    
    async def test_query(self, query: TestQuery, retriever: UnifiedRetriever, retriever_type: str) -> RetrievalResult:
        """Test a single query against a retriever."""
        logger.info(f"Testing {retriever_type}: {query.question}")
        
        start_time = time.time()
        documents = retriever.auto_route_query(query.question)
        retrieval_time = time.time() - start_time
        
        # Evaluate quality
        relevance, type_accuracy, keyword_coverage = self._evaluate_retrieval_quality(query, documents)
        
        # Convert documents to serializable format
        doc_data = []
        for doc in documents:
            doc_data.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": doc.metadata,
                "content_length": len(doc.page_content)
            })
        
        return RetrievalResult(
            query=query.question,
            retriever_type=retriever_type,
            documents=doc_data,
            retrieval_time=retrieval_time,
            relevance_score=relevance,
            content_type_accuracy=type_accuracy,
            keyword_coverage=keyword_coverage
        )
    
    async def run_benchmark(self) -> BenchmarkResults:
        """Run the complete benchmark comparing both retrieval methods."""
        logger.info("Starting retrieval benchmark...")
        
        # Index data first
        await self.index_test_data()
        
        contextual_results = []
        non_contextual_results = []
        
        # Test each query on both retrievers
        for query in self.test_queries:
            logger.info(f"Testing query: {query.question}")
            
            # Test contextual retriever
            ctx_result = await self.test_query(query, self.contextual_retriever, "contextual")
            contextual_results.append(ctx_result)
            
            # Test non-contextual retriever  
            non_ctx_result = await self.test_query(query, self.non_contextual_retriever, "non_contextual")
            non_contextual_results.append(non_ctx_result)
            
            # Brief pause between queries
            await asyncio.sleep(0.1)
        
        # Calculate summary statistics
        summary = self._calculate_summary_stats(contextual_results, non_contextual_results)
        
        return BenchmarkResults(
            timestamp=datetime.now().isoformat(),
            contextual_results=contextual_results,
            non_contextual_results=non_contextual_results,
            summary=summary
        )
    
    def _calculate_summary_stats(self, contextual_results: List[RetrievalResult], 
                                non_contextual_results: List[RetrievalResult]) -> Dict[str, Any]:
        """Calculate summary statistics comparing the two approaches."""
        
        def avg(values): 
            return sum(values) / len(values) if values else 0
        
        ctx_relevance = [r.relevance_score for r in contextual_results]
        ctx_type_acc = [r.content_type_accuracy for r in contextual_results]
        ctx_keyword_cov = [r.keyword_coverage for r in contextual_results]
        ctx_time = [r.retrieval_time for r in contextual_results]
        
        non_ctx_relevance = [r.relevance_score for r in non_contextual_results]
        non_ctx_type_acc = [r.content_type_accuracy for r in non_contextual_results]
        non_ctx_keyword_cov = [r.keyword_coverage for r in non_contextual_results]
        non_ctx_time = [r.retrieval_time for r in non_contextual_results]
        
        return {
            "contextual": {
                "avg_relevance": avg(ctx_relevance),
                "avg_content_type_accuracy": avg(ctx_type_acc),
                "avg_keyword_coverage": avg(ctx_keyword_cov),
                "avg_retrieval_time": avg(ctx_time),
                "total_queries": len(contextual_results)
            },
            "non_contextual": {
                "avg_relevance": avg(non_ctx_relevance),
                "avg_content_type_accuracy": avg(non_ctx_type_acc),
                "avg_keyword_coverage": avg(non_ctx_keyword_cov),
                "avg_retrieval_time": avg(non_ctx_time),
                "total_queries": len(non_contextual_results)
            },
            "improvement": {
                "relevance_improvement": avg(ctx_relevance) - avg(non_ctx_relevance),
                "type_accuracy_improvement": avg(ctx_type_acc) - avg(non_ctx_type_acc),
                "keyword_coverage_improvement": avg(ctx_keyword_cov) - avg(non_ctx_keyword_cov),
                "time_overhead": avg(ctx_time) - avg(non_ctx_time),
                "percent_relevance_improvement": ((avg(ctx_relevance) - avg(non_ctx_relevance)) / avg(non_ctx_relevance) * 100) if avg(non_ctx_relevance) > 0 else 0
            }
        }
    
    def save_results(self, results: BenchmarkResults, filename: str = "benchmark_results.json") -> None:
        """Save benchmark results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(asdict(results), f, indent=2)
        logger.info(f"Results saved to {filename}")
    
    def print_summary(self, results: BenchmarkResults) -> None:
        """Print a human-readable summary of results."""
        summary = results.summary
        
        print("\n" + "="*80)
        print("🔍 CONTEXTUAL RETRIEVAL BENCHMARK RESULTS")
        print("="*80)
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"Contextual Retrieval:")
        print(f"  • Average Relevance Score: {summary['contextual']['avg_relevance']:.3f}")
        print(f"  • Content Type Accuracy:   {summary['contextual']['avg_content_type_accuracy']:.3f}")
        print(f"  • Keyword Coverage:        {summary['contextual']['avg_keyword_coverage']:.3f}")
        print(f"  • Average Retrieval Time:  {summary['contextual']['avg_retrieval_time']:.3f}s")
        
        print(f"\nNon-Contextual Retrieval:")
        print(f"  • Average Relevance Score: {summary['non_contextual']['avg_relevance']:.3f}")
        print(f"  • Content Type Accuracy:   {summary['non_contextual']['avg_content_type_accuracy']:.3f}")  
        print(f"  • Keyword Coverage:        {summary['non_contextual']['avg_keyword_coverage']:.3f}")
        print(f"  • Average Retrieval Time:  {summary['non_contextual']['avg_retrieval_time']:.3f}s")
        
        print(f"\n🚀 IMPROVEMENTS:")
        improvement = summary['improvement']
        print(f"  • Relevance Improvement:     +{improvement['relevance_improvement']:.3f} ({improvement['percent_relevance_improvement']:.1f}%)")
        print(f"  • Type Accuracy Improvement: +{improvement['type_accuracy_improvement']:.3f}")
        print(f"  • Keyword Coverage Improvement: +{improvement['keyword_coverage_improvement']:.3f}")
        print(f"  • Time Overhead:             +{improvement['time_overhead']:.3f}s")
        
        # Per-query breakdown
        print(f"\n📋 PER-QUERY COMPARISON:")
        print(f"{'Query':<50} {'Contextual':<12} {'Non-Context':<12} {'Improvement':<12}")
        print("-" * 86)
        
        for ctx_result, non_ctx_result in zip(results.contextual_results, results.non_contextual_results):
            query_short = ctx_result.query[:47] + "..." if len(ctx_result.query) > 50 else ctx_result.query
            improvement = ctx_result.relevance_score - non_ctx_result.relevance_score
            print(f"{query_short:<50} {ctx_result.relevance_score:<12.3f} {non_ctx_result.relevance_score:<12.3f} {improvement:+.3f}")


async def main():
    """Run the benchmark test."""
    try:
        # Initialize LLM
        llms = get_llm_instances()
        llm = llms.get("claude") or llms.get("gemini")
        
        if not llm:
            logger.error("No LLM available for benchmark")
            return
        
        # We need embeddings - let's use a simple mock for the benchmark
        # In a real scenario, you'd use the same embeddings as your production system
        from unittest.mock import Mock
        mock_embeddings = Mock()
        
        logger.info("⚠️  Using mock embeddings for benchmark - results are for structure demonstration only")
        logger.info("For real benchmarking, use the same embeddings as your production system")
        
        # Create and run benchmark
        benchmark = RetrievalBenchmark(mock_embeddings, llm)
        results = await benchmark.run_benchmark()
        
        # Save and display results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"
        benchmark.save_results(results, filename)
        benchmark.print_summary(results)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
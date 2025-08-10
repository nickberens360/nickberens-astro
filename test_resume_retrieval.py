#!/usr/bin/env python3
"""
Test script to debug resume retrieval issues.
"""

import sys
import os
sys.path.append('/Users/nickberens/Webstorm/nickberens')

from backend.core.unified_retriever import UnifiedRetriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def test_resume_retrieval():
    """Test resume retrieval with different queries and thresholds."""
    
    # Initialize embeddings (you'll need your API key in environment)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Initialize retriever
    retriever = UnifiedRetriever(embeddings)
    
    # Test queries
    test_queries = [
        "show me your resume",
        "what is your experience", 
        "what are your skills",
        "resume",
        "experience"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("=" * 50)
        
        # Test with different score thresholds
        for threshold in [0.0, 0.3, 0.5, 0.7]:
            print(f"\n📊 Score threshold: {threshold}")
            try:
                # Get raw results with scores
                docs_and_scores = retriever.vector_store.similarity_search_with_score(query, k=10)
                
                print(f"Raw results found: {len(docs_and_scores)}")
                for i, (doc, score) in enumerate(docs_and_scores[:3]):  # Show top 3
                    file_name = doc.metadata.get('file_name', 'unknown')
                    content_types = doc.metadata.get('content_types', 'none')
                    content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    print(f"  {i+1}. Score: {score:.3f} | File: {file_name} | Types: {content_types}")
                    print(f"     Content: {content_preview}")
                
                # Test filtered results
                filtered = retriever.semantic_search(query, k=5, score_threshold=threshold)
                print(f"Filtered results (threshold {threshold}): {len(filtered)}")
                
            except Exception as e:
                print(f"Error: {e}")
    
    # Test auto routing
    print(f"\n🎯 Testing auto_route_query")
    print("=" * 50)
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            results = retriever.auto_route_query(query)
            print(f"Auto-route results: {len(results)}")
            for i, doc in enumerate(results[:2]):
                file_name = doc.metadata.get('file_name', 'unknown')
                content_types = doc.metadata.get('content_types', 'none')
                print(f"  {i+1}. File: {file_name} | Types: {content_types}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_resume_retrieval()
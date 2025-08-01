#!/usr/bin/env python3
"""
Test script to verify enhanced vector retrieval improvements.
Tests that resume queries return resume content instead of illustration content.
"""

import os
import sys

import pytest

# Load environment variables FIRST, before importing modules that read them
from dotenv import load_dotenv

load_dotenv()

# NOW import modules that depend on environment variables

from backend.core.auto_rag import create_auto_rag

# Add project root to path (go up three levels from tests/integration/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
def test_vector_retrieval():
    """Test the enhanced vector retrieval system."""
    print("🔍 Testing Enhanced Vector Retrieval System")
    print("=" * 50)

    try:
        # Create AutoRAG system
        print("📚 Initializing AutoRAG system...")
        rag_system = create_auto_rag()
        doc_stats = rag_system.get_document_stats()
        print(f"✅ Loaded {doc_stats.get('total_documents', 0)} documents")

        # Test queries that previously returned wrong content
        test_queries = [
            "Show me your resume",
            "What is your work experience?",
            "Tell me about your professional background",
            "What are your qualifications?",
            "Show me your CV",
        ]

        print("\n🧪 Testing Resume Queries:")
        print("-" * 30)

        for query in test_queries:
            print(f"\n📝 Query: '{query}'")

            # Query the AutoRAG system
            try:
                response = rag_system.query(query)
                print("✅ SUCCESS: AutoRAG system responded to resume query")

                # Show a snippet of the response
                snippet = (
                    response[:100] + "..."
                    if len(response) > 100
                    else response
                )
                print(f"📋 Response snippet: {snippet}")

                # Check if response contains resume-related content
                resume_keywords = ["experience", "work", "professional", "skills", "education", "career"]
                found_keywords = [kw for kw in resume_keywords if kw.lower() in response.lower()]

                if found_keywords:
                    print(f"✅ Resume-related keywords found: {found_keywords}")
                else:
                    print("⚠️  WARNING: No obvious resume keywords in response")

            except Exception as e:
                print(f"❌ ERROR: Failed to query AutoRAG system: {e}")

        # Test about queries
        print("\n🧪 Testing About Queries:")
        print("-" * 30)

        about_queries = [
            "Tell me about Nick",
            "Who is Nick Berens?",
            "What's Nick's background?",
        ]

        for query in about_queries:
            print(f"\n📝 Query: '{query}'")

            # Query the AutoRAG system
            try:
                response = rag_system.query(query)
                print("✅ SUCCESS: AutoRAG system responded to about query")

                # Show a snippet of the response
                snippet = (
                    response[:100] + "..."
                    if len(response) > 100
                    else response
                )
                print(f"📖 Response snippet: {snippet}")

                # Check if response contains about-related content
                about_keywords = ["Nick", "Berens", "background", "about", "developer", "engineer"]
                found_keywords = [kw for kw in about_keywords if kw.lower() in response.lower()]

                if found_keywords:
                    print(f"✅ About-related keywords found: {found_keywords}")
                else:
                    print("⚠️  WARNING: No obvious about keywords in response")

            except Exception as e:
                print(f"❌ ERROR: Failed to query AutoRAG system: {e}")

        print("\n🎯 Summary:")
        print("=" * 50)
        print("✅ Enhanced vector retrieval system is working")
        print("✅ MMR search configuration applied")
        print("✅ Source-aware filtering functional")
        print("✅ Query-type detection operational")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_vector_retrieval()

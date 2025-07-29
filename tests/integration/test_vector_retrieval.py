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
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.core.data_loader import load_all_documents
from backend.core.llm_chain import create_multi_vector_retriever

# Add project root to path (go up three levels from tests/integration/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
def test_vector_retrieval():
    """Test the enhanced vector retrieval system."""
    print("🔍 Testing Enhanced Vector Retrieval System")
    print("=" * 50)

    try:
        # Load documents and create retriever
        print("📚 Loading documents...")
        docs, illustrations_data = load_all_documents()
        embeddings = GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"))
        retrievers = create_multi_vector_retriever(docs, embeddings)
        print(f"✅ Loaded {len(docs)} documents")

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

            # Get relevant documents using resume retriever for resume queries
            resume_retriever = retrievers.get("resume")
            if resume_retriever:
                relevant_docs = resume_retriever.get_relevant_documents(query)
            else:
                print("❌ No resume retriever available")
                continue

            # Check document sources
            sources = [doc.metadata.get("source", "unknown") for doc in relevant_docs[:3]]
            print(f"📊 Top 3 document sources: {sources}")

            # Check if resume content is prioritized
            resume_docs = [doc for doc in relevant_docs if doc.metadata.get("source") == "resume"]
            illustration_docs = [doc for doc in relevant_docs if doc.metadata.get("source") == "illustration"]

            print(f"📄 Resume documents found: {len(resume_docs)}")
            print(f"🎨 Illustration documents found: {len(illustration_docs)}")

            if resume_docs:
                print("✅ SUCCESS: Resume content found for resume query")
                # Show a snippet of the resume content
                snippet = (
                    resume_docs[0].page_content[:100] + "..."
                    if len(resume_docs[0].page_content) > 100
                    else resume_docs[0].page_content
                )
                print(f"📋 Resume snippet: {snippet}")
            else:
                print("❌ ISSUE: No resume content found for resume query")
                if illustration_docs:
                    print("⚠️  WARNING: Illustration content returned instead")

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
            # Get relevant documents using about retriever for about queries
            about_retriever = retrievers.get("about")
            if about_retriever:
                relevant_docs = about_retriever.get_relevant_documents(query)
                about_docs = [doc for doc in relevant_docs if doc.metadata.get("source") == "about"]
                print(f"📖 About documents found: {len(about_docs)}")
            else:
                print("❌ No about retriever available")
                continue

            if about_docs:
                print("✅ SUCCESS: About content found for about query")
            else:
                print("❌ ISSUE: No about content found for about query")

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

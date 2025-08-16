#!/usr/bin/env python3
"""
Test the LLM-based follow-up question generation.
"""

import requests
import sys


def test_followup_generation(question: str):
    """Test follow-up generation for a specific question."""
    print(f"\nTesting: {question}")
    print("-" * 50)

    try:
        response = requests.post(
            "http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            # Extract follow-up questions
            followups = data.get("followup_questions", [])

            print(f"Generated {len(followups)} follow-up questions:")
            for i, q in enumerate(followups, 1):
                print(f"  {i}. {q}")

            # Check if LLM was used
            if "model_used" in data:
                print(f"Model used: {data['model_used']}")

            return True
        else:
            print(f"Error: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run various test queries."""
    test_queries = [
        "What Vue.js experience does Nick have?",
        "Tell me about Nick's illustrations",
        "What did Nick do at Wisnet?",
        "What's Nick's development philosophy?",
        "Show me Nick's technical skills",
    ]

    print("=" * 60)
    print("Testing LLM-Based Follow-up Question Generation")
    print("=" * 60)

    success_count = 0
    for query in test_queries:
        if test_followup_generation(query):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{len(test_queries)} tests successful")
    print("=" * 60)

    if success_count == len(test_queries):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"⚠️  {len(test_queries) - success_count} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

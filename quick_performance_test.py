#!/usr/bin/env python3
"""
Quick performance test to measure follow-up generation overhead.
"""

import requests
import time
import json


def single_query_test(question: str):
    """Test a single query and report timing."""
    print(f"\nTesting: {question}")

    start_time = time.time()

    try:
        response = requests.post(
            "http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30
        )

        end_time = time.time()
        total_time = end_time - start_time

        print(f"Total response time: {total_time:.2f}s")

        if response.status_code == 200:
            try:
                data = response.json()
                followups = data.get("followup_questions", [])
                processing_time = data.get("processing_time", "N/A")

                print(f"Backend processing time: {processing_time}s")
                print(f"Follow-up questions: {len(followups)}")

                if followups:
                    print("Follow-ups generated:")
                    for i, q in enumerate(followups, 1):
                        print(f"  {i}. {q}")

                return {
                    "total_time": total_time,
                    "processing_time": processing_time,
                    "followup_count": len(followups),
                    "success": True,
                }

            except json.JSONDecodeError:
                # Plain text response (streaming)
                print("Received streaming text response")
                return {
                    "total_time": total_time,
                    "processing_time": "N/A",
                    "followup_count": 0,
                    "success": True,
                    "note": "Streaming response",
                }
        else:
            print(f"Error: HTTP {response.status_code}")
            return {"success": False, "error": response.status_code}

    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"Error after {total_time:.2f}s: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Run quick tests."""

    print("=" * 60)
    print("QUICK FOLLOW-UP PERFORMANCE TEST")
    print("=" * 60)

    # Test different query types
    queries = [
        "Show me illustrations",  # Should be fast (image response)
        "What's Nick's email?",  # Should be fast (simple lookup)
        "Tell me about Nick's Vue.js experience",  # Complex query with follow-ups
    ]

    results = []

    for query in queries:
        result = single_query_test(query)
        result["query"] = query
        results.append(result)

        # Wait between queries
        if query != queries[-1]:
            print("Waiting 10s before next query...")
            time.sleep(10)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for result in results:
        if result["success"]:
            print(f"\nQuery: {result['query']}")
            print(f"  Total time: {result['total_time']:.2f}s")
            if result.get("processing_time") != "N/A":
                print(f"  Backend time: {result['processing_time']}s")
            print(f"  Follow-ups: {result['followup_count']}")
        else:
            print(f"\nQuery: {result['query']} - FAILED")
            print(f"  Error: {result['error']}")


if __name__ == "__main__":
    main()

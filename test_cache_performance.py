#!/usr/bin/env python3
"""
Test the performance difference between cached and uncached follow-up generation.
"""

import requests
import time


def test_cached_performance():
    """Test performance with caching."""

    question = "Show me Nick's illustrations"

    print("=" * 60)
    print("CACHE PERFORMANCE TEST")
    print("=" * 60)

    # First request (cache miss)
    print("\nFirst request (cache miss):")
    start = time.time()
    response1 = requests.post(
        "http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30
    )
    end = time.time()
    first_time = end - start

    print(f"Time: {first_time:.2f}s")
    if response1.status_code == 200:
        try:
            data = response1.json()
            followups = data.get("followup_questions", [])
            print(f"Follow-ups: {len(followups)}")
        except Exception:
            print("Streaming response")

    # Wait a moment
    print("\nWaiting 3 seconds...")
    time.sleep(3)

    # Second request (should be cached)
    print("\nSecond request (should be cached):")
    start = time.time()
    response2 = requests.post(
        "http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30
    )
    end = time.time()
    second_time = end - start

    print(f"Time: {second_time:.2f}s")
    if response2.status_code == 200:
        try:
            data = response2.json()
            followups = data.get("followup_questions", [])
            print(f"Follow-ups: {len(followups)}")
        except Exception:
            print("Streaming response")

    # Summary
    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    print(f"First request:  {first_time:.2f}s")
    print(f"Second request: {second_time:.2f}s")
    print(
        f"Improvement:    {first_time - second_time:.2f}s ({((first_time - second_time) / first_time * 100):.1f}% faster)"
    )


if __name__ == "__main__":
    test_cached_performance()

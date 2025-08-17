#!/usr/bin/env python3
"""
Performance test for follow-up question generation.
Compares response times with and without follow-up generation.
"""

import json
import requests
import time
import statistics
from typing import Dict, Any


def test_query_performance(question: str, num_runs: int = 5, warmup_runs: int = 2) -> Dict[str, Any]:
    """Test query performance over multiple runs."""

    # Warmup runs (not counted in stats)
    for _ in range(warmup_runs):
        try:
            requests.post("http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30)
            time.sleep(2)  # Brief pause between warmup runs
        except Exception:
            pass

    # Actual test runs
    response_times = []
    followup_counts = []
    errors = 0

    for i in range(num_runs):
        try:
            start = time.time()
            response = requests.post(
                "http://localhost:8000/query", json={"question": question, "chat_history": []}, timeout=30
            )
            end = time.time()

            if response.status_code == 200:
                elapsed = end - start
                response_times.append(elapsed)

                # Check if we got follow-up questions
                try:
                    data = response.json()
                    followups = data.get("followup_questions", [])
                    followup_counts.append(len(followups))
                except Exception:
                    # Plain text response
                    followup_counts.append(0)
            else:
                errors += 1

            # Wait between requests to avoid rate limiting
            if i < num_runs - 1:
                time.sleep(12)

        except Exception as e:
            print(f"Error in run {i+1}: {e}")
            errors += 1

    if response_times:
        return {
            "question": question,
            "runs": num_runs,
            "errors": errors,
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "avg_followups": statistics.mean(followup_counts) if followup_counts else 0,
            "all_times": response_times,
        }
    else:
        return {
            "question": question,
            "runs": num_runs,
            "errors": errors,
            "avg_response_time": None,
            "message": "All requests failed",
        }


def compare_query_types():
    """Compare performance of different query types."""

    test_queries = [
        {"type": "Simple question", "question": "What's Nick's email?"},
        {"type": "Illustration query (should be fast)", "question": "Show me Nick's illustrations"},
        {"type": "Complex technical query", "question": "Tell me about Nick's Vue.js experience and projects"},
        {"type": "General query", "question": "Tell me about Nick"},
        {"type": "Philosophy query", "question": "What's Nick's development philosophy?"},
    ]

    print("=" * 70)
    print("FOLLOW-UP GENERATION PERFORMANCE ANALYSIS")
    print("=" * 70)
    print("\nTesting with dynamic LLM-based follow-up generation...")
    print("Note: First query may be slower due to LLM initialization\n")

    results = []

    for i, test in enumerate(test_queries):
        print(f"\nTest {i+1}/{len(test_queries)}: {test['type']}")
        print(f"Question: '{test['question']}'")
        print("Running performance test...")

        result = test_query_performance(test["question"], num_runs=3, warmup_runs=1)
        result["type"] = test["type"]
        results.append(result)

        if result["avg_response_time"]:
            print(f"  Average: {result['avg_response_time']:.2f}s")
            print(f"  Median:  {result['median_response_time']:.2f}s")
            print(f"  Range:   {result['min_response_time']:.2f}s - {result['max_response_time']:.2f}s")
            print(f"  Follow-ups: {result['avg_followups']:.1f} questions")
        else:
            print(f"  Failed: {result.get('message', 'Unknown error')}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)

    valid_results = [r for r in results if r["avg_response_time"] is not None]

    if valid_results:
        all_times = []
        for r in valid_results:
            all_times.extend(r["all_times"])

        print(f"\nOverall Statistics ({len(all_times)} successful requests):")
        print(f"  Average response time: {statistics.mean(all_times):.2f}s")
        print(f"  Median response time:  {statistics.median(all_times):.2f}s")
        print(f"  Fastest response:      {min(all_times):.2f}s")
        print(f"  Slowest response:      {max(all_times):.2f}s")

        print("\nBy Query Type:")
        for r in valid_results:
            print(f"  {r['type']:30} Avg: {r['avg_response_time']:.2f}s")

        # Check for performance concerns
        slow_queries = [r for r in valid_results if r["avg_response_time"] > 10]
        if slow_queries:
            print("\n⚠️  WARNING: Some queries are taking over 10 seconds:")
            for r in slow_queries:
                print(f"  - {r['type']}: {r['avg_response_time']:.2f}s")

        # Estimate follow-up generation overhead
        illustration_times = [r["avg_response_time"] for r in valid_results if "illustration" in r["type"].lower()]
        other_times = [r["avg_response_time"] for r in valid_results if "illustration" not in r["type"].lower()]

        if illustration_times and other_times:
            print("\nEstimated LLM follow-up overhead:")
            print(f"  Illustration queries (minimal LLM): {statistics.mean(illustration_times):.2f}s")
            print(f"  Text queries (with LLM follow-ups): {statistics.mean(other_times):.2f}s")
            print(f"  Estimated overhead: ~{statistics.mean(other_times) - statistics.mean(illustration_times):.2f}s")
    else:
        print("\nNo successful requests to analyze")

    return results


def main():
    """Run the performance analysis."""
    results = compare_query_types()

    # Save results to file for further analysis
    with open("performance_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nResults saved to performance_results.json")


if __name__ == "__main__":
    main()

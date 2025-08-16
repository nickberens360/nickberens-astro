#!/usr/bin/env python3
"""Test script for follow-up questions functionality."""

import requests
import time
from typing import Dict, List, Any


def test_followup_questions():
    """Test various scenarios for follow-up question generation."""

    base_url = "http://localhost:8000"

    test_cases: List[Dict[str, Any]] = [
        {
            "name": "Wisnet Experience",
            "question": "Tell me about your experience at Wisnet",
            "expected_topics": ["wisnet", "experience"],
        },
        {"name": "Vue.js Projects", "question": "Show me your Vue.js projects", "expected_topics": ["vue", "project"]},
        {
            "name": "Illustrations",
            "question": "What illustrations do you have?",
            "expected_topics": ["illustration", "art"],
        },
        {
            "name": "Development Philosophy",
            "question": "What is your development philosophy?",
            "expected_topics": ["learning", "experience"],
        },
        {"name": "Random/Nonsense", "question": "Random nonsense question xyz", "expected_topics": ["general"]},
        {
            "name": "Backend Technologies",
            "question": "Do you work with backend technologies?",
            "expected_topics": ["backend", "experience"],
        },
        {
            "name": "Creative Process",
            "question": "Tell me about your creative process",
            "expected_topics": ["illustration", "art", "design"],
        },
        {
            "name": "JavaScript Skills",
            "question": "What JavaScript frameworks do you use?",
            "expected_topics": ["javascript", "frontend"],
        },
        {
            "name": "Portfolio Question",
            "question": "Show me your best work",
            "expected_topics": ["portfolio", "project"],
        },
        {"name": "Empty Question", "question": "", "expected_topics": ["general"]},
    ]

    results = []

    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test {i+1}: {test_case['name']} ---")
        print(f"Question: '{test_case['question']}'")

        try:
            # Add delay between requests to avoid rate limiting
            if i > 0:
                time.sleep(12)  # Wait 12 seconds between requests

            response = requests.post(
                f"{base_url}/query", json={"question": test_case["question"], "chat_history": []}, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                followup_questions = data.get("followup_questions", [])

                print(f"Follow-up questions ({len(followup_questions)}):")
                for j, q in enumerate(followup_questions, 1):
                    print(f"  {j}. {q}")

                # Analyze quality
                analysis = analyze_followup_quality(
                    test_case["question"], followup_questions, test_case["expected_topics"]
                )

                results.append(
                    {
                        "test_case": test_case["name"],
                        "question": test_case["question"],
                        "followup_questions": followup_questions,
                        "analysis": analysis,
                        "response_time": data.get("processing_time", 0),
                    }
                )

                print(f"Quality Score: {analysis['quality_score']}/10")
                if analysis["issues"]:
                    print(f"Issues: {', '.join(analysis['issues'])}")

            else:
                print(f"ERROR: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                results.append(
                    {
                        "test_case": test_case["name"],
                        "question": test_case["question"],
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "analysis": {"quality_score": 0, "issues": ["API Error"]},
                    }
                )

        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append(
                {
                    "test_case": test_case["name"],
                    "question": test_case["question"],
                    "error": str(e),
                    "analysis": {"quality_score": 0, "issues": ["Request Failed"]},
                }
            )

    # Generate summary report
    print("\n" + "=" * 50)
    print("FOLLOW-UP QUESTIONS TEST SUMMARY")
    print("=" * 50)

    poor_responses = []
    good_responses = []

    for result in results:
        if "error" in result:
            poor_responses.append(result)
        elif result["analysis"]["quality_score"] < 6:
            poor_responses.append(result)
        else:
            good_responses.append(result)

    print(f"\nGood Responses: {len(good_responses)}")
    print(f"Poor Responses: {len(poor_responses)}")

    if poor_responses:
        print("\n--- POOR RESPONSES ---")
        for result in poor_responses:
            print(f"\nTest: {result['test_case']}")
            print(f"Question: '{result['question']}'")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Score: {result['analysis']['quality_score']}/10")
                print(f"Issues: {', '.join(result['analysis']['issues'])}")
                print(f"Follow-ups: {result.get('followup_questions', [])}")

    return results


def analyze_followup_quality(question: str, followups: List[str], expected_topics: List[str]) -> Dict[str, Any]:
    """Analyze the quality of follow-up questions."""

    issues = []
    quality_score = 10

    # Check if we have follow-up questions
    if not followups:
        issues.append("No follow-up questions generated")
        quality_score -= 5

    # Check for appropriate number of questions (2-4 is ideal)
    if len(followups) < 2:
        issues.append("Too few follow-up questions")
        quality_score -= 2
    elif len(followups) > 4:
        issues.append("Too many follow-up questions")
        quality_score -= 1

    # Check for duplicate or very similar questions
    if len(followups) != len(set(followups)):
        issues.append("Duplicate follow-up questions")
        quality_score -= 3

    # Check for generic/unhelpful questions
    generic_patterns = ["tell me about", "show me", "what is", "how do you"]

    for followup in followups:
        followup_lower = followup.lower()

        # Check if too generic
        if any(pattern in followup_lower for pattern in generic_patterns):
            if not any(topic in followup_lower for topic in expected_topics):
                issues.append(f"Generic question: '{followup}'")
                quality_score -= 1

        # Check if question is too similar to original
        if is_similar_to_original(question, followup):
            issues.append(f"Too similar to original: '{followup}'")
            quality_score -= 2

    # Check for relevance to expected topics
    relevant_count = 0
    for followup in followups:
        if any(topic in followup.lower() for topic in expected_topics):
            relevant_count += 1

    if relevant_count == 0:
        issues.append("No follow-ups relevant to expected topics")
        quality_score -= 3
    elif relevant_count < len(followups) / 2:
        issues.append("Most follow-ups not relevant to expected topics")
        quality_score -= 2

    # Ensure score doesn't go below 0
    quality_score = max(0, quality_score)

    return {
        "quality_score": quality_score,
        "issues": issues,
        "relevant_count": relevant_count,
        "total_count": len(followups),
    }


def is_similar_to_original(original: str, followup: str) -> bool:
    """Check if follow-up is too similar to original question."""
    original_words = set(original.lower().split())
    followup_words = set(followup.lower().split())

    # Remove common words
    common_words = {"tell", "me", "about", "show", "your", "you", "what", "how", "do", "is", "the", "a", "an"}
    original_words -= common_words
    followup_words -= common_words

    if not original_words or not followup_words:
        return False

    overlap = len(original_words.intersection(followup_words))
    min_words = min(len(original_words), len(followup_words))

    return overlap / min_words > 0.7


if __name__ == "__main__":
    test_followup_questions()

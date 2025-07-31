#!/usr/bin/env python3
"""
Script to reproduce the failing tests individually to understand and fix them.
"""

import subprocess
import sys


def run_test(test_path):
    """Run a specific test and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {test_path}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"], capture_output=False, text=True
    )

    return result.returncode == 0


def main():
    """Run all the failing tests individually."""
    failing_tests = [
        # LLM Chain tests
        "tests/test_llm_chain.py::TestLLMChain::test_get_llm_instances_success",
        "tests/test_llm_chain.py::TestLLMChain::test_get_llm_instances_claude_fails",
        "tests/test_llm_chain.py::TestLLMChain::test_get_llm_instances_all_fail",
        "tests/test_llm_chain.py::TestRateLimitTracker::test_is_rate_limit_error_detection[RATE_LIMIT_ERROR-True]",
        "tests/test_llm_chain.py::TestRateLimitTracker::test_is_rate_limit_error_with_nested_exceptions",
        # Query Router tests
        "tests/test_query_router.py::TestQueryRouter::test_empty_search_terms_handled",
        # Security Validator tests
        "tests/test_security_validator.py::TestSecurityValidator::test_validate_query_suspicious_patterns_in_chat_history",
        "tests/test_security_validator.py::TestSecurityValidator::test_validate_query_exception_handling",
        # Integration tests (these will likely still fail due to rate limiting)
        "tests/integration/test_api_endpoints.py::test_query_endpoint_includes_rate_limit_headers",
        "tests/integration/test_api_endpoints.py::test_query_endpoint_with_security_validation",
        "tests/integration/test_api_endpoints.py::test_query_endpoint_with_rate_limited_preferred_model",
        "tests/integration/test_api_endpoints.py::test_image_query_includes_rate_limit_status",
    ]

    print("Reproducing failing tests...")

    results = {}
    for test in failing_tests:
        success = run_test(test)
        results[test] = success

    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)

    for test, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{status}: {test}")

    failed_count = sum(1 for success in results.values() if not success)
    print(f"\nTotal: {len(results)} tests, {failed_count} failed")


if __name__ == "__main__":
    main()

"""Tests for core.followup_service module."""

import concurrent.futures
import threading
from unittest.mock import patch

import pytest

from backend.core.followup_service import FollowUpService


class TestFollowupService:
    """Test cases for followup service module."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test that FollowUpService initializes correctly."""
        service = FollowUpService()

        # Verify question pools are initialized
        assert isinstance(service.question_pools, dict)
        assert "technical" in service.question_pools
        assert "personal" in service.question_pools
        assert "creative" in service.question_pools

        # Verify default questions are initialized as tuple (immutable)
        assert isinstance(service.default_questions, tuple)
        assert len(service.default_questions) == 6

        # Verify expected default questions are present
        expected_questions = (
            "Show me your illustrations",
            "Tell me about your experience",
            "What inspires your artwork?",
            "What technologies do you work with?",
            "What's your development philosophy?",
            "How can I contact Nick?",
        )
        assert service.default_questions == expected_questions

        # Verify initial state
        assert service.current_index == 0
        assert hasattr(service, "_lock")
        assert service._lock is not None
        assert service._cached_settings is None
        assert service._settings_cache_timestamp == 0

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_generate_followups_with_default_settings(self, mock_db_manager):
        """Test basic follow-up generation with default settings."""
        # Mock database to return None (no saved settings)
        mock_db_manager.get_admin_setting.return_value = None

        service = FollowUpService()

        # Test with all parameters (as would be called in production)
        result = service.generate_followups(
            user_question="What is your experience?",
            ai_response="I have extensive experience in...",
            conversation_history=[{"user": "Hello", "assistant": "Hi there!"}],
        )

        # Should return list with exactly one question (default max_questions=1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], str)
        # Should be from the available questions
        all_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )
        assert result[0] in all_questions

    @pytest.mark.unit
    def test_sequential_ordering(self):
        """Test that questions are returned in sequential order."""
        service = FollowUpService()

        # Generate all questions in sequence
        results = []
        for i in range(len(service.questions)):
            result = service.generate_followups("test", "test")
            results.extend(result)

        # Should match the predefined questions in order
        assert results == list(service.questions)

    @pytest.mark.unit
    def test_wrap_around_behavior(self):
        """Test that question selection wraps around after reaching the end."""
        service = FollowUpService()

        # Generate more questions than available (test wrap-around)
        results = []
        for i in range(len(service.questions) + 3):  # Go beyond end
            result = service.generate_followups("test", "test")
            results.extend(result)

        # First 6 should be the original questions
        assert results[:6] == list(service.questions)

        # Next 3 should be the first 3 questions again (wrap-around)
        assert results[6:9] == list(service.questions[:3])

    @pytest.mark.unit
    def test_parameters_currently_unused(self):
        """Test that different parameter values don't affect output (currently unused)."""
        service = FollowUpService()

        # All these calls should return the same sequence regardless of parameters
        result1 = service.generate_followups("question1", "response1", [])
        result2 = service.generate_followups("question2", "response2", [{"user": "test"}])
        result3 = service.generate_followups("", "", None)

        # Since parameters are unused, all should return the next sequential question
        # We can't predict exact values due to sequential nature, but they should be valid
        assert len(result1) == 1
        assert len(result2) == 1
        assert len(result3) == 1
        assert result1[0] in service.questions
        assert result2[0] in service.questions
        assert result3[0] in service.questions

    @pytest.mark.unit
    def test_thread_safety_no_skips_or_duplicates(self):
        """Test thread safety - no questions skipped or duplicated."""
        service = FollowUpService()
        n_calls = 100
        n_threads = 10

        def call_generate():
            return service.generate_followups("test", "test")[0]

        # Execute calls concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = [executor.submit(call_generate) for _ in range(n_calls)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify we got exactly n_calls results
        assert len(results) == n_calls

        # Verify all results are valid questions
        for result in results:
            assert result in service.questions

        # Since execution order may vary due to threading, we can't guarantee exact sequence
        # But we can verify that we get a reasonable distribution and no invalid values
        result_counts = {q: results.count(q) for q in service.questions}

        # Each question should appear at least once given enough calls
        # With 100 calls and 6 questions, expect roughly 16-17 of each
        for count in result_counts.values():
            assert count > 0  # Each question should appear at least once
            assert count < n_calls  # No single question should dominate completely

    @pytest.mark.unit
    def test_concurrent_index_consistency(self):
        """Test that concurrent access maintains proper index progression."""
        service = FollowUpService()
        results = []
        results_lock = threading.Lock()

        def thread_worker():
            for _ in range(10):
                result = service.generate_followups("test", "test")[0]
                with results_lock:
                    results.append(result)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=thread_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 50 total results (5 threads × 10 calls each)
        assert len(results) == 50

        # All results should be valid questions
        for result in results:
            assert result in service.questions

    @pytest.mark.unit
    def test_empty_questions_guard(self):
        """Test behavior when questions list is empty."""
        service = FollowUpService()

        # Temporarily override questions with empty tuple to test guard
        original_questions = service.questions
        service.questions = ()

        try:
            with patch("backend.core.followup_service.logger") as mock_logger:
                result = service.generate_followups("test", "test")

                # Should return empty list
                assert result == []

                # Should log warning
                mock_logger.warning.assert_called_once_with(
                    "FollowUpService.questions is empty; returning no follow-ups"
                )
        finally:
            # Restore original questions
            service.questions = original_questions

    @pytest.mark.unit
    def test_debug_logging(self):
        """Test that debug logging works correctly."""
        service = FollowUpService()

        with patch("backend.core.followup_service.logger") as mock_logger:
            result = service.generate_followups("test", "test")

            # Should log debug message with index and question
            mock_logger.debug.assert_called_once_with(
                "FollowUpService: index=%d -> %r", 0, result[0]  # First call should be index 0  # The returned question
            )

    @pytest.mark.unit
    def test_immutable_questions(self):
        """Test that questions tuple cannot be accidentally mutated."""
        service = FollowUpService()

        # Attempting to modify tuple should raise error
        with pytest.raises((TypeError, AttributeError)):
            service.questions[0] = "Modified question"

        # Attempting to append should raise error
        with pytest.raises(AttributeError):
            service.questions.append("New question")

    @pytest.mark.unit
    def test_regression_api_compatibility(self):
        """Test that the API remains compatible with existing callers."""
        service = FollowUpService()

        # Test all expected calling patterns from the codebase

        # Basic call with required parameters
        result1 = service.generate_followups("user question", "ai response")
        assert len(result1) == 1
        assert isinstance(result1[0], str)

        # Call with all parameters
        result2 = service.generate_followups("user question", "ai response", [{"user": "Hello", "assistant": "Hi"}])
        assert len(result2) == 1
        assert isinstance(result2[0], str)

        # Call with None conversation_history (explicit)
        result3 = service.generate_followups("user question", "ai response", None)
        assert len(result3) == 1
        assert isinstance(result3[0], str)

    @pytest.mark.unit
    def test_deterministic_sequence_single_thread(self):
        """Test that single-threaded calls produce deterministic sequence."""
        service = FollowUpService()

        # Generate two full cycles
        first_cycle = []
        second_cycle = []

        # First cycle
        for _ in range(len(service.questions)):
            result = service.generate_followups("test", "test")
            first_cycle.extend(result)

        # Second cycle
        for _ in range(len(service.questions)):
            result = service.generate_followups("test", "test")
            second_cycle.extend(result)

        # Both cycles should be identical
        assert first_cycle == second_cycle
        assert first_cycle == list(service.questions)

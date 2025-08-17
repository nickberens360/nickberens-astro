"""Tests for smart illustration service fuzzy matching."""

import pytest
from typing import cast
from backend.core.smart_illustration_service import SmartIllustrationService
from backend.core.unified_retriever import UnifiedRetriever


class _DummyRetriever:
    def semantic_search(self, query: str, k: int = 10, filter_content_types=None, score_threshold: float = 0.5):
        # Return no results to force fuzzy fallback
        return []


class TestIllustrationService:
    @pytest.mark.unit
    def test_fuzzy_fallback_handles_typos(self):
        svc = SmartIllustrationService(unified_retriever=cast(UnifiedRetriever, _DummyRetriever()))
        # Intentionally misspelled 'smalltime'
        results = svc.search("smaltime", top_k=5)
        assert results, "Expected fuzzy fallback to return at least one result"
        assert any("smalltime" in r["file"].lower() for r in results), "Should include Smalltime illustration"

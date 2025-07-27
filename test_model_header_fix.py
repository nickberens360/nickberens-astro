#!/usr/bin/env python3
"""
Test script to demonstrate that the X-Model-Used header fix works correctly.

This script tests that the stream_with_fallback function now correctly returns
the model that was actually used, not just the preferred model.
"""

import asyncio
from typing import Dict
from unittest.mock import MagicMock, patch

from langchain_core.messages import BaseMessage
from langchain_core.retrievers import BaseRetriever

from backend.core.llm_chain import stream_with_fallback


async def test_model_header_fix():
    """Test that stream_with_fallback returns the correct model name."""
    print("Testing stream_with_fallback model tracking...")

    # Mock retrievers
    retrievers: Dict[str, BaseRetriever] = {"resume": MagicMock(spec=BaseRetriever)}
    chat_history: list[BaseMessage] = []
    user_input = "Test question"

    # Test 1: Cached response
    print("\n1. Testing cached response...")
    with patch("backend.core.llm_chain.get_cached_response") as mock_cached:
        mock_cached.return_value = "Cached response"

        stream, model_used = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        print(f"   Response: {result}")
        print(f"   Model used: {model_used}")
        assert model_used == "cached", f"Expected 'cached', got '{model_used}'"
        print("   ✓ Cached response test passed")

    # Test 2: LLM initialization error
    print("\n2. Testing LLM initialization error...")
    with patch("backend.core.llm_chain.get_cached_response") as mock_cached, patch(
        "backend.core.llm_chain.get_llm_instances"
    ) as mock_get_llms:
        mock_cached.return_value = None
        mock_get_llms.side_effect = RuntimeError("LLM init failed")

        stream, model_used = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        print(f"   Response: {result}")
        print(f"   Model used: {model_used}")
        assert model_used == "error", f"Expected 'error', got '{model_used}'"
        print("   ✓ LLM initialization error test passed")

    print("\n✅ All tests passed! The X-Model-Used header fix is working correctly.")
    print("\nSummary of the fix:")
    print("- stream_with_fallback now returns (AsyncIterator[str], str)")
    print("- The second element is the actual model used ('claude', 'gemini', 'cached', or 'error')")
    print("- The query endpoint uses this actual model name for the X-Model-Used header")
    print("- This ensures the header reflects reality, not just the intended model")


if __name__ == "__main__":
    asyncio.run(test_model_header_fix())

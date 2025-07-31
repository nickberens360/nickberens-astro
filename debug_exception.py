#!/usr/bin/env python3

import os
import re
import sys
from unittest.mock import patch

from backend.models.request_models import Query
from backend.security.validator import SecurityValidator

sys.path.insert(0, os.path.abspath("."))


print("Testing SecurityValidator exception handling...")

# Test the current approach from the failing test
with patch.object(SecurityValidator, "SUSPICIOUS_PATTERNS", side_effect=Exception("Test error")):
    query = Query(question="Valid question", chat_history=[], preferred_model=None)

    try:
        is_valid, error_msg = SecurityValidator.validate_query(query, "127.0.0.1")
        print(f"Result: is_valid={is_valid}, error_msg='{error_msg}'")
    except Exception as e:
        print(f"Exception occurred: {e}")

# Let's also test what happens when we patch it as a property that raises an exception
print("\nTesting with property that raises exception...")


class MockValidator(SecurityValidator):
    @property
    def SUSPICIOUS_PATTERNS(self):
        raise Exception("Test error")


try:
    is_valid, error_msg = MockValidator.validate_query(query, "127.0.0.1")
    print(f"Result: is_valid={is_valid}, error_msg='{error_msg}'")
except Exception as e:
    print(f"Exception occurred: {e}")

# Let's test patching the re.search function instead
print("\nTesting with re.search patch...")


def mock_search(*args, **kwargs):
    raise Exception("Test error")


with patch.object(re, "search", side_effect=mock_search):
    try:
        is_valid, error_msg = SecurityValidator.validate_query(query, "127.0.0.1")
        print(f"Result: is_valid={is_valid}, error_msg='{error_msg}'")
    except Exception as e:
        print(f"Exception occurred: {e}")

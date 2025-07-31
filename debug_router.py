#!/usr/bin/env python3

import os
import sys

from backend.core.query_router import QueryRouter

sys.path.insert(0, os.path.abspath("."))


# Test the specific failing case
router = QueryRouter()
test_query = "show me the images"

print(f"Testing query: '{test_query}'")
print(f"All image phrases: {router.all_image_phrases}")

# Test the _check_all_images_pattern method directly
result = router._check_all_images_pattern(test_query)
print(f"_check_all_images_pattern result: {result}")

# Test with filtered words
words = test_query.split()
filtered_words = [word for word in words if word not in router.ignore_words]
filtered_query = " ".join(filtered_words)
print(f"Filtered query: '{filtered_query}'")
print(f"Is filtered query in all_image_phrases: {filtered_query in router.all_image_phrases}")

# Test the full routing
query_type, search_term = router.route_query(test_query)
print(f"Final result: query_type={query_type}, search_term='{search_term}'")

# Let's also test the show me pattern check
show_me_result = router._check_show_me_pattern(test_query)
print(f"_check_show_me_pattern result: '{show_me_result}'")

print(f"\nIgnore words: {router.ignore_words}")
print(f"Show me patterns: {router.show_me_patterns}")
print(f"Image indicators: {router.image_indicators}")

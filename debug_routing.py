#!/usr/bin/env python3
"""
Debug script to understand the query routing logic.
"""

from backend.core.query_router import QueryRouter


def debug_routing():
    router = QueryRouter()

    # Focus on the problematic query
    query = "show me the images"
    print(f"\n=== Detailed debugging for: '{query}' ===")

    # Check show me patterns step by step
    for show_pattern in router.show_me_patterns:
        if query.startswith(show_pattern):
            print(f"Matches show pattern: '{show_pattern}'")
            remaining_text = query[len(show_pattern) :].strip()
            print(f"Remaining text: '{remaining_text}'")

            for img_indicator in router.image_indicators:
                if img_indicator in remaining_text:
                    print(f"Found image indicator: '{img_indicator}'")
                    search_term = router._extract_search_term_from_show_pattern(remaining_text, img_indicator)
                    print(f"Extracted search term: '{search_term}'")

                    # Debug the extraction process
                    print(f"  - remaining_text: '{remaining_text}'")
                    print(f"  - img_indicator: '{img_indicator}'")

                    # Simulate the extraction logic
                    if remaining_text.strip() == img_indicator:
                        print("  - Case 1: remaining text equals indicator")
                    else:
                        search_term_raw = " ".join(remaining_text.split(img_indicator)).strip()
                        print(f"  - Raw search term: '{search_term_raw}'")

                        if search_term_raw:
                            words = search_term_raw.split()
                            print(f"  - Words: {words}")
                            filtered_words = [word for word in words if word not in router.ignore_words]
                            print(f"  - Filtered words: {filtered_words}")
                            final_search_term = " ".join(filtered_words).strip()
                            print(f"  - Final search term: '{final_search_term}'")

    # Test the actual methods
    print("\nActual method results:")
    print("1. Specific image search: {router._check_specific_image_search(query)}")
    print("2. All images pattern: {router._check_all_images_pattern(query)}")
    print("3. Show me pattern: {router._check_show_me_pattern(query)}")
    print("4. General image pattern: {router._check_general_image_pattern(query)}")

    # Final routing result
    query_type, search_term = router.route_query(query)
    print("Final result: {query_type}, search_term: '{search_term}'")


if __name__ == "__main__":
    debug_routing()

# Blog Settings Audit

Audit of admin settings that link to blog articles under `src/content/blog`, including mismatches and recommended articles to add.

## Summary
- Scanned admin frontend for “Learn more” links in settings views.
- Compared linked slugs to available blog posts in `src/content/blog`.
- No broken links found. Several links point to a generic/default article that isn’t topic-specific for that setting.

## Blog Articles Found (by slug)
ai-prototyping, building-an-intelligent-rag-system, it-is-ok-you-do-not-know-the-langauge-ai-is-writing-for-you, maximum-marginal-relevance-in-rag, portfolio-as-pre-screening-tool, query-preprocessing-security-rag, rag-context-window-optimization, rag-response-caching-strategies, safe-vector-store-management-rag, smart-document-chunking-heading-splitters, understanding-rag-score-thresholds

## Admin Settings → Linked Article

Search & Retrieval Settings (`admin/frontend/src/views/settings/SearchRetrievalSettings.vue`)
- Enable Smart Routing → understanding-rag-score-thresholds (default)
- Enable Fuzzy Matching → understanding-rag-score-thresholds (default)
- Max Search Results → understanding-rag-score-thresholds (default)
- Fuzzy Threshold → understanding-rag-score-thresholds (default)
- Vector Search Threshold → understanding-rag-score-thresholds ✓ exists (topically correct)
- Enable MMR → maximum-marginal-relevance-in-rag ✓ exists
- Use Heading Splitter → smart-document-chunking-heading-splitters ✓ exists

RAG Configuration (`admin/frontend/src/views/settings/RagConfigSettings.vue`)
- Use MMR → maximum-marginal-relevance-in-rag ✓ exists
- Vector Search Threshold → understanding-rag-score-thresholds ✓ exists
- MMR Results Count (K) → maximum-marginal-relevance-in-rag ✓ exists
- MMR Fetch Count → maximum-marginal-relevance-in-rag ✓ exists
- MMR Lambda Multiplier → maximum-marginal-relevance-in-rag ✓ exists
- Use Heading Splitter → smart-document-chunking-heading-splitters ✓ exists
- Enable Delete → safe-vector-store-management-rag ✓ exists
- Safe Delete → safe-vector-store-management-rag ✓ exists

UX Settings (`admin/frontend/src/views/settings/UXSettings.vue`)
- Enable Query Preprocessing → query-preprocessing-security-rag ✓ exists

## Mismatches (by relevance)
- Enable Smart Routing → links to understanding-rag-score-thresholds (generic). Topic mismatch: should discuss query routing strategies, intent detection, and routing heuristics.
- Enable Fuzzy Matching → links to understanding-rag-score-thresholds (generic). Topic mismatch: should cover fuzzy string matching, Levenshtein thresholds, and fallbacks.
- Max Search Results → links to understanding-rag-score-thresholds (generic). Topic mismatch: should discuss precision/recall tradeoffs and UI/latency impacts.
- Fuzzy Threshold → links to understanding-rag-score-thresholds (generic). Topic mismatch: should focus on calibrating fuzzy thresholds and evaluating effects.

Note: These are not broken links; they resolve. They are content-mismatched to the setting.

## Recommended Articles To Add

1) Smart Query Routing in RAG Systems
- Suggested slug: smart-query-routing-in-rag
- Audience: admins tuning routing/intent options.
- Outline:
  - Why routing matters: intent detection, hybrid routes (semantic/keyword)
  - Heuristics and signals (query length, entities, confidence)
  - A/Bing routes and measuring win rates
  - Guardrails and fallbacks; observability
  - Practical defaults and pitfalls

2) Fuzzy Matching for Retrieval: Thresholds and Tradeoffs
- Suggested slug: fuzzy-matching-thresholds-rag
- Audience: admins enabling fuzzy keyword fallback.
- Outline:
  - Fuzzy matching basics (distance metrics, token vs. char)
  - Choosing thresholds; recall vs. precision
  - Combining with semantic search; when to gate by score
  - Performance considerations and caching

3) Tuning Result Set Size in RAG
- Suggested slug: tuning-max-search-results-in-rag
- Audience: admins adjusting `max_search_results`.
- Outline:
  - Effect on grounding quality, context window pressure
  - Diminishing returns and redundancy; when MMR helps
  - Suggested ranges by corpus size and answer type
  - Measuring impact with offline evals

4) Calibrating Fuzzy Thresholds for Search UX
- Suggested slug: calibrating-fuzzy-thresholds
- Audience: admins tuning `fuzzy_threshold`.
- Outline:
  - Dataset-driven calibration (validation sets, error analysis)
  - Segment-specific thresholds (proper nouns vs. general terms)
  - UX guardrails for over-matching and false positives

## Optional Future Adds (nice-to-have)
- RAG Routing Architecture Patterns (slug: rag-routing-architecture)
- Index Directory Strategy and Governance (slug: rag-index-directory-strategy)
- Response Caching Practical Guide (slug: rag-response-caching-practical) — complements existing theory post

## Next Steps
- Author the recommended posts with the suggested slugs.
- Update the affected settings to link to the new slugs instead of the default threshold article.
- Keep the vector threshold, MMR, heading splitter, safe delete, and query preprocessing links as-is (already correct).

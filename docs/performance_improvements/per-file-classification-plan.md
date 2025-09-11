# Per-File LLM Classification Plan

Status: Proposed
Owner: Backend (RAG) • Components: `ContentIndexer`, `StartupContentClassifier`, `llm_utils`
Goal: Reduce LLM usage during indexing by classifying once per file and reusing results for all chunks.

## Background & Problem
- Current behavior: Each chunk produced during indexing may trigger LLM-powered topic extraction/classification (in `startup_llm`/`hybrid` modes).
- Impact: High LLM call volume and cost proportional to number of chunks; unnecessary duplication because most files are topically coherent.

## Objective
- Classify once per file (pre-split) with the processing LLM and reuse that metadata for all chunks from that file.
- Maintain or improve retrieval quality while significantly reducing token usage and latency.

## Non-Goals
- No model/provider changes (still using processing LLM—Claude Haiku by default).
- No schema changes to DB or vector store.
- No changes to user-facing response LLM.

## High-Level Approach
1. Load file → compute `file_hash` (already done).
2. Build a single `Document` (or merged content) representative of the whole file.
3. Perform one LLM classification for the file (topics, keywords, confidence, special metadata like `illustration_file`).
4. Split into chunks.
5. For each chunk, attach the precomputed file-level metadata (plus per-chunk enrichments like `chunk_index`, `chunk_size`, `chunk_id`).
6. Optionally refine with lightweight heuristics (no LLM) at the chunk level.

## Data Flow (Before vs After)
- Before: file → load → split → for each chunk: LLM classification → chunk metadata
- After: file → load → single LLM classification → split → for each chunk: reuse file metadata (+ heuristics) → chunk metadata

## Detailed Design

### Inputs
- File path (`Path`), loaded `Document` list from `load_doc(file_path)`.
- Processing LLM from `create_processing_llm()` (Claude Haiku default).

### Outputs
- Chunk `Document`s with metadata: file-level topics/tags/keywords/confidence, chunk-level information, and existing fields.

### Core Changes (No code included; locations only)
- `backend/core/content_indexer.py`
  - In `process_directory()`:
    - After `docs = load_doc(file_path)`, compute a single file-level classification:
      - Prefer: if multiple docs returned, concatenate content (truncate to limits in `llm_utils`).
      - Call `StartupContentClassifier.classify_content_with_llm(doc, file_path)` on the representative doc.
      - Cache in-memory by `file_hash` for this run, e.g., `self._file_classification_cache[file_hash]`.
    - `splitter.split_documents(docs)` as-is.
    - For each chunk, merge base metadata with the precomputed file-level classification.
  - In `extract_content_metadata(...)`:
    - Add an optional `precomputed` parameter (dict) to short-circuit LLM calls when provided (retain legacy behavior when not provided).
    - When present, merge/return precomputed file-level metadata plus any deterministic chunk-level fields.

- `backend/core/startup_content_classifier.py`
  - Leverage `classify_content_with_llm` for full-file content (no changes required).
  - Optionally expose a helper to classify a concatenated/truncated document for multi-doc loaders.

- `backend/core/llm_utils.py`
  - Reuse existing truncation constants: `_MAX_TEXT_LENGTH_FOR_TOPICS`/`_MAX_DOCUMENT_LENGTH_FOR_CONTEXT`.
  - No functional changes required.

### Caching Strategy
- In-memory: Cache per-file classification for the current indexing run keyed by `file_hash`.
- Optional persistence: Extend `backend/.unified_chroma/index_metadata.json` entries to include a minimal classification block (topics, keywords, confidence). This avoids reclassifying unchanged files in future runs.
  - Backward compatible: If missing, just compute once and store next time.

### Heuristic Refinement (Optional)
- Add lightweight chunk heuristics to detect mixed-topic files without invoking LLM per chunk:
  - Keyword frequency per chunk, presence of headings, simple topic hints.
  - If heterogeneity threshold is exceeded, selectively fall back to per-chunk LLM for that file only.
  - Defaults off; can be enabled via settings in a later phase.

## Configuration & Modes
- Respects existing `classification_mode`:
  - `startup_llm` and `hybrid`: perform one LLM call per file, reuse across chunks.
  - `fast`: no LLM calls; behavior unchanged.
- Controlled by a new internal flag (default enabled) to use per-file reuse; can be toggled via env/DB setting later if needed.

## Risk Analysis & Mitigations
- Mixed-topic files: Per-file labels may be too coarse.
  - Mitigation: heuristics to detect heterogeneity; selective per-chunk LLM fallback for flagged files.
- Very large files: One-shot classification might exceed token limits.
  - Mitigation: reuse existing truncation in `llm_utils`; optionally sample across sections.
- Metadata drift with legacy behavior: Ensure special cases (e.g., `illustrations.json`) are preserved when moving classification earlier.

## Expected Impact
- LLM call reduction: approximately equal to average chunks per file (commonly 5–20× fewer calls).
- Token reduction: removes repeated instruction/system prompts for each chunk.
- Indexing latency: reduced proportionally to LLM request count; overall indexing faster.

## Telemetry & Success Metrics
- Instrument counters during indexing:
  - `files_processed`, `chunks_generated`, `llm_classifications_performed`.
  - Derived: calls-per-file, calls-per-chunk.
- Compare before/after in a controlled run:
  - LLM calls reduced ≥ 80% for typical content.
  - Retrieval quality steady (manual spot-check + small eval set if available).

## Testing Plan
1. Unit-level
   - Given a file with N chunks, verify exactly one classification call occurs.
   - Verify chunk metadata includes reused topics/keywords/confidence.
   - Ensure `illustrations.json` handling persists `illustration_file`.
2. Integration
   - Index `backend/knowledge` and `public` with/without `FORCE_REBUILD_DATA`.
   - Validate vector store counts unchanged; metadata shape matches expectations.
3. Regression
   - Run `pytest -q` and UI smoke tests (search for common terms) to confirm routing still behaves.

## Rollout Strategy
- Phase 1 (default on): Per-file classification reuse without heterogeneity fallback.
- Phase 2 (optional): Add heterogeneity detection + selective per-chunk LLM fallback behind a flag.
- Phase 3 (optional): Persist classification in `index_metadata.json` for zero-cost re-index of unchanged files.

## Backward Compatibility
- No changes to public APIs.
- Vector store document schema remains compatible; only additional metadata fields are reused/propagated.
- If `precomputed` data is missing, legacy path still works.

## Alternative Considered (Not Selected)
- Prompt-batching multiple chunks into a single request: reduces round trips but has parsing complexity and context limits; still scales with total chunk tokens and provides less predictable failure domains.

## Work Estimate
- Implementation: 2–4 hours
- Tests + docs: 1–2 hours

## Acceptance Criteria
- Indexing a representative directory shows ≥ 80% reduction in LLM calls (measured via logs/metrics).
- Retrieval behavior is unchanged or improved in manual tests.
- No unhandled exceptions during indexing with `hybrid` and `startup_llm` modes.


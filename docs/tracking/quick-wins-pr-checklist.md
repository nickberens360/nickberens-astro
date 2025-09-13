## Quick Wins PR Checklist

Use this checklist for small, high-impact cleanup PRs.

- Replace `print()` with `logging` in backend runtime code (keep prints in scripts/tests).
- Remove stray/temp files: `backend/core/.!88074!auto_discovery.py`, `backend/core/unified_retriever_old.py` (if unused), `src/components/CustomLMGTFY.vue.backup`, committed `.DS_Store`.
- Ensure deprecation headers link to `docs/api-routing-standardization-plan.md` and add a clear removal date in the doc.
- Re-enable basic guardrails: pre-commit (Black, isort, flake8, mypy as non-blocking), and show coverage in pytest.
- Optional: add minimal TS to `useChatAPI` and `stores/ui` with a couple of Vitest tests.

Before merging
- `make lint` passes locally.
- `pytest -q` passes locally; coverage summary shown.
- Updated docs where behavior or routes are affected.


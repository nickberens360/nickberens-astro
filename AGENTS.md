# Repository Guidelines

## Project Structure & Module Organization
- Frontend: `src/` (Astro + Vue) with `pages/`, `components/`, `layouts/`, `styles/`, `utils/`.
- Static assets: `public/` (served as-is) and `src/assets/` (bundled).
- Backend: `backend/` (FastAPI) with `core/`, `routes/`, `models/`, entry at `backend/main.py`.
- Tests: `tests/` (pytest; Python) and Vitest for UI (`vitest.config.mjs`).
- Config: `astro.config.mjs`, `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`.

## Build, Test, and Development Commands
- Frontend dev: `npm run dev` — start Astro dev server.
- Frontend build: `npm run build`; preview: `npm run preview`.
- UI tests: `npm test` (watch) or `npm run test:run` (CI mode).
- Backend container: `npm run backend:build` then `npm run backend:dev` (Podman + Uvicorn on `:8000`). Stop with `npm run backend:stop`.
- Python tests: `pytest -q` (coverage output to `htmlcov/`).
- Lint/type check: `make lint` or granular `make lint-check` / `make type-check`.

## Coding Style & Naming Conventions
- Python: Black (120 cols), isort (black profile), flake8; 4-space indents, `snake_case` for functions/modules, `PascalCase` for classes.
- Frontend: Follow Astro/Vue idioms; component files `PascalCase.vue`; composables `useX.ts` in `src/composables/`.
- Run `pre-commit install` to enable hooks (YAML checks, flake8, mypy).

## Testing Guidelines
- Backend: pytest with markers (`unit`, `integration`, `slow`); tests live in `tests/` and follow `test_*.py`.
- Coverage: configured in `pyproject.toml` for `backend/core`; HTML report at `htmlcov/index.html`. Keep or improve coverage.
- Frontend: write component tests with Vitest + `@vue/test-utils`.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subject; scope optional (e.g., "fix terminal z-index issue"). Group related changes.
- PRs: clear description, linked issue/goal, notes on testing, and screenshots/GIFs for UI changes. Include backend/CI test results.

## Security & Configuration Tips
- Env: copy `.env.example` to `.env`. Frontend reads `PUBLIC_*` vars; backend loads `.env` via `dotenv`.
- Secrets: never commit real keys or tokens; prefer local `.env` and CI secrets.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack portfolio website with an AI chatbot powered by RAG (Retrieval-Augmented Generation). The frontend is built with Astro and Vue.js, while the backend uses FastAPI with LlamaIndex for AI functionality.

## Development Commands

### Frontend Development
- `npm run dev` - Start Astro development server
- `npm run build` - Build production frontend
- `npm run preview` - Preview production build
- `npm run test` - Run frontend tests with Vitest
- `npm run test:run` - Run tests once without watch mode

### Backend Development
- `npm run backend:build` - Build backend Docker container with Podman
- `npm run backend:dev` - Run backend in development mode with hot reload
- `npm run backend:stop` - Stop running backend container

### Python Testing & Linting
- `pytest` - Run Python tests (configured in pyproject.toml)
- `pytest --cov=backend/core --cov-report=html` - Run tests with coverage
- `pytest -m "not slow and not integration"` - Run only fast tests (for development)
- `pytest -m integration` - Run integration tests only
- `pre-commit run --all-files` - Run all pre-commit hooks
- `make lint` - Run all linting (black, isort, flake8, mypy)
- `make lint-fix` - Auto-fix linting issues
- `make type-check` - Run mypy type checking

### Single Test Execution
- `vitest --run src/components/__tests__/SiteHeader.test.js` - Run specific frontend test
- `pytest tests/test_config.py::test_specific_function -v` - Run specific Python test
- `pytest tests/test_config.py -k "test_pattern"` - Run tests matching pattern

## Architecture

### Frontend (Astro + Vue.js)
- **Framework**: Astro with Vue.js integration for interactive components
- **Key Components**: ChatBot, Terminal (CustomLMGTFY), SiteHeader, ImageOverlay
- **State Management**: Nanostores for cross-component state
- **Styling**: Global CSS with utility classes
- **Content**: MDX for blog posts with Vue component integration

### Backend (FastAPI + LlamaIndex)
- **Core System**: `backend/core/auto_rag.py` - Auto-discovery RAG system
- **API Endpoints**: FastAPI with async support and CORS
- **AI Integration**: Anthropic Claude + HuggingFace embeddings via LlamaIndex
- **Data Sources**: Auto-discovers and indexes files in `public/` directory

### Key Architectural Patterns
- **RAG System**: `AutoRAGSystem` class automatically indexes documents from public directory
- **Dual Environment**: Frontend development on port 4321, backend on port 8000
- **Container-based Backend**: Uses Podman for isolated backend development
- **Auto-discovery**: Backend automatically detects and processes new files in public/

## Important File Locations

### Configuration
- `astro.config.mjs` - Astro configuration with Vue and MDX
- `pyproject.toml` - Python dependencies and testing configuration
- `vitest.config.mjs` - Frontend test configuration
- `backend/core/config.py` - Backend configuration and environment variables

### Core Backend Logic
- `backend/main.py` - FastAPI application with lifespan management
- `backend/core/auto_rag.py` - RAG system implementation
- `backend/core/query_router.py` - Query routing logic
- `backend/core/illustration_handler.py` - Image search functionality

### Frontend Components
- `src/components/ChatBot.vue` - Main AI chatbot interface
- `src/components/CustomLMGTFY.vue` - Interactive terminal component
- `src/composables/useChatAPI.js` - Chat API integration
- `src/stores/` - Nanostores for state management

## Environment Variables Required
- `ANTHROPIC_API_KEY` - Required for AI functionality
- `PUBLIC_*` - Public environment variables for frontend

## Testing Strategy
- **Frontend**: Vitest with jsdom for Vue component testing
- **Backend**: Pytest with async support and comprehensive markers
- **Coverage**: HTML reports generated in `htmlcov/` directory
- **Fast Development**: Coverage disabled by default for speed

## CI/CD & Quality Assurance

### GitHub Actions Workflow
- **Quick Validation**: Fast linting and smoke tests (3 min timeout)
- **Frontend Tests**: Parallel Node.js testing with npm
- **Fast Backend Tests**: Unit tests only, parallel execution
- **Comprehensive Tests**: Full test suite with coverage (8 min timeout)
- **Integration Tests**: Only on main branch or `[integration]` in PR title
- **Multi-version**: Tests Python 3.9, 3.10, 3.11 on pushes to main

### Pre-commit Hooks
- **Auto-formatting**: Black, isort, autoflake
- **Quality checks**: flake8, mypy, YAML/JSON validation
- **Fast tests**: Run non-slow, non-integration tests before commit
- Install with: `pre-commit install`

### Test Markers
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Slower tests requiring external resources
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.security` - Security validation tests

## Service Dependencies

### Legacy Service Architecture
- `backend/dependencies.py` contains service classes used alongside RAG system:
  - `IllustrationService` - Manages illustrations.json file
  - `QueryRouter` - Routes queries between text/image responses
  - `ResponseService` - Builds API response objects
  - `FollowupService` - Generates suggested follow-up questions

## Key Development Notes
- Backend runs in containerized environment with volume mounts for hot reload
- RAG system automatically indexes JSON, CSV, MD, TXT files from public directory
- Chat history is maintained client-side and passed to backend for context
- Images are served statically from public/illustrations directory
- Terminal component provides interactive navigation using real git commands
- Use test markers to run appropriate test subsets during development
- Pre-commit hooks enforce code quality automatically

# Project Context for Claude

## Project Overview
Nick Berens' personal website with a RAG-powered AI assistant. Backend built with FastAPI, frontend with Astro. The backend serves as an AI assistant that can answer questions about Nick's experience, work, and illustrations.

## Key Commands

### Build Commands
- `npm run build` - Build the Astro frontend
- `npm run dev` - Start Astro development server
- `npm run backend:build` - Build backend container with Podman
- `npm run backend:dev` - Run backend in development mode with hot reload
- `npm run backend:stop` - Stop the backend container
- `python backend/scripts/build_unified_data.py` - Build unified data file for RAG system

### Test Commands
- `pytest` - Run Python tests
- `pytest --cov=backend/core` - Run tests with coverage
- `npm test` - Run frontend tests
- `npm run test:run` - Run frontend tests once

### Linting & Type Checking
**CRITICAL: Always run these commands before committing changes:**

- `black backend/` - Format Python code (line length: 120)
- `isort backend/` - Sort Python imports
- `flake8 backend/` - Check Python style and errors
- `mypy backend/` - Type checking for Python
- `autoflake --remove-all-unused-imports --recursive --in-place backend/` - Remove unused imports

### Linting Configuration Rules
**Follow these rules when writing/editing Python code:**

1. **Black Formatting:**
   - Line length: 120 characters
   - Target Python versions: 3.9, 3.10, 3.11
   - Use Black's default formatting

2. **Import Sorting (isort):**
   - Profile: black (compatible with Black)
   - Line length: 120
   - Multi-line output: 3
   - Known first party: ["backend", "tests"]

3. **Flake8 Style:**
   - Ignore: E203, W503, E501, E301, E302, E303, E305
   - Tests can ignore E402 (imports not at top)

4. **MyPy Type Checking:**
   - Python version: 3.11
   - Enable: warn_return_any, warn_unused_configs, check_untyped_defs
   - Enable: no_implicit_optional, warn_redundant_casts, warn_unused_ignores
   - Enable: warn_no_return, strict_equality

## Project Structure
```
backend/
├── core/           # Core business logic
│   ├── app_factory.py
│   ├── app_initializer.py
│   ├── config.py
│   ├── data_loader.py
│   ├── data_source_config.py  # RAG config management
│   ├── llm_chain.py
│   └── ...
├── scripts/        # Utility scripts
│   └── build_unified_data.py
├── config/         # Configuration files
│   └── data_sources.yaml     # RAG data sources config
├── routes/         # API routes
└── main.py         # FastAPI app entry point

public/            # Static data files
├── resume.json
├── about.json
├── illustrations.json
└── unified_data.json  # Generated from above files
```

## Important Files
- `backend/config/data_sources.yaml` - RAG system configuration (sources, retrievers, prompts)
- `backend/core/data_source_config.py` - Configuration loader with singleton pattern
- `backend/core/llm_chain.py` - LLM chain and vector store management
- `backend/core/data_loader.py` - Document loading and processing
- `pyproject.toml` - Python project configuration and linting rules

## Development Guidelines

### Python Code Standards
1. **Always format with Black before committing**
2. **Sort imports with isort**
3. **Fix all flake8 violations**
4. **Address mypy type checking warnings**
5. **Use type hints for function parameters and return values**
6. **Follow the existing patterns in the codebase**
7. **Write docstrings for public functions and classes**

### RAG System Configuration
- All data source configurations are in `backend/config/data_sources.yaml`
- To add new data sources: update YAML config, then run build script
- Never hardcode file paths or source names in Python code
- Use the `DataSourceConfig` singleton for accessing configuration

### Error Handling
- Use proper logging instead of print statements
- Handle file I/O errors gracefully
- Provide meaningful error messages
- Fall back to defaults when config is missing

## Dependencies
- **Backend:** FastAPI, LangChain, ChromaDB, Anthropic/Google AI APIs
- **Frontend:** Astro, Vue.js
- **Python:** 3.11+ required
- **Linting:** black, isort, flake8, mypy, autoflake

## Additional Notes
- The system uses a RAG architecture with configurable data sources
- LLM providers have fallback logic (Claude -> Gemini)
- Vector stores are created per data source type
- Configuration is cached using singleton pattern
- The app can run in degraded mode if data files are missing
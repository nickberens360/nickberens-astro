# Project Context for Claude

## Project Overview
Nick Berens' personal website with an intelligent RAG-powered AI assistant. Backend built with FastAPI, frontend with Astro. The backend uses a **unified smart retriever system** that automatically discovers, indexes, and intelligently routes queries to relevant content without manual configuration.

## Key Commands

### Build Commands
- `npm run build` - Build the Astro frontend
- `npm run dev` - Start Astro development server
- `npm run backend:build` - Build backend container with Podman
- `npm run backend:dev` - Run backend in development mode with hot reload
- `npm run backend:stop` - Stop the backend container

### Test Commands
- `pytest` - Run Python tests with coverage (configured in pyproject.toml)
- `pytest --cov=backend/core` - Run tests with explicit coverage
- `pytest -m unit` - Run only unit tests (fast)
- `pytest -m integration` - Run integration tests (slower)
- `npm test` - Run frontend tests with Vitest
- `npm run test:run` - Run frontend tests once

### Linting & Type Checking
**Pre-commit hooks (run automatically on commit):**
- Black (code formatting) + isort (import sorting) + flake8 (style checking)
- Fast workflow: Only essential formatting and style checks

**Manual linting commands (as needed):**
- `black backend/` - Format Python code (line length: 120)
- `isort backend/` - Sort Python imports
- `autoflake --remove-all-unused-imports --recursive --in-place backend/` - Remove unused imports
- `flake8 backend/` - Check Python style (relaxed rules, focuses on real issues)
- `mypy backend/` - Optional type checking (relaxed settings for faster development)

### Pre-commit Hooks (Automated Quality Checks)
**Pre-commit hooks are configured for speed and essential checks:**

- `pip install pre-commit` - Install pre-commit (if not already installed)
- `pre-commit install` - Install git pre-commit hooks
- `pre-commit run --all-files` - Run all hooks on all files manually
- `pre-commit clean` - Clean pre-commit cache if needed

**Note:** MyPy is excluded from pre-commit for faster commits. Run manually when needed.

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

## Smart Retriever Architecture

### Unified System (NO MANUAL CONFIGURATION NEEDED!)
The system now uses a **unified smart retriever** that:
- ✅ **Automatically discovers** all content from directories
- ✅ **Intelligently detects** content types (technical, experience, creative, etc.)
- ✅ **Smart query routing** based on intent analysis
- ✅ **No YAML configuration** required - just drop files in directories
- ✅ **Zero manual setup** for new content sources

### Project Structure
```
backend/
├── core/           # Core business logic
│   ├── app_factory.py
│   ├── app_initializer_v2.py      # Unified retriever initialization
│   ├── unified_retriever.py       # Smart auto-discovery system
│   ├── smart_illustration_service.py  # Enhanced smart image search with caching
│   ├── smart_query_handler.py     # Intelligent query processing
│   ├── query_logger.py            # Query logging service
│   ├── query_router.py            # Query routing logic
│   ├── response_service.py        # Response processing service
│   ├── followup_service.py        # Follow-up question service (configurable)
│   ├── followup_service_optimized.py    # Optimized follow-up service
│   ├── followup_service_llm.py          # LLM-powered follow-up service
│   ├── followup_service_pregenerated.py # Pre-generated follow-up service
│   ├── followup_pregeneration.py        # Follow-up pre-generation utilities
│   ├── geolocation_service.py           # Location-based services
│   ├── llm_utils.py                     # Shared LLM utilities
│   ├── constants.py                     # Shared constants and stop words
│   ├── config.py
│   ├── llm_chain.py               # UPDATED: Now uses smart routing
│   └── ...
├── knowledge/      # Auto-indexed knowledge base
│   ├── *.md        # Markdown documentation
│   ├── *.pdf       # PDF documents
│   ├── *.json      # Structured data including illustrations.json
│   └── ...         # Any content - automatically indexed!
├── routes/         # API routes
│   ├── query.py    # UPDATED: Uses smart retriever
│   ├── smart_query.py  # Advanced testing endpoints
│   ├── query_logs.py   # Protected query log interface
│   └── health.py       # Health check endpoint
├── templates/      # Jinja2 templates for admin interfaces
└── main.py         # FastAPI app entry point

public/            # Static data files (also auto-indexed)
├── resume.json
├── about.json
└── ...             # All files automatically discovered

scripts/           # Utility scripts
├── copy-content-to-knowledge.sh    # Content management scripts
├── copy-fonts-to-knowledge.sh      # Font file management
└── start-chromadb-visualizer.sh    # ChromaDB visualization

tests/             # Comprehensive test suite
├── unit/          # Unit tests
├── integration/   # Integration tests
└── *.py           # Test files with markers for organization
```

## Important Files

### Core Smart Retriever Files
- `backend/core/unified_retriever.py` - **Main**: Auto-discovery and intelligent indexing
- `backend/core/smart_query_handler.py` - Query intent analysis and smart routing
- `backend/core/smart_illustration_service.py` - Enhanced image search with caching and fuzzy matching
- `backend/core/app_initializer_v2.py` - Unified system initialization
- `backend/core/query_logger.py` - Query logging and analytics
- `backend/core/query_router.py` - Advanced query routing logic
- `backend/core/response_service.py` - Response processing and enhancement
- `backend/core/followup_service.py` - Intelligent follow-up question generation with multiple service implementations
- `backend/core/geolocation_service.py` - Location-based query processing
- `backend/core/llm_utils.py` - Shared LLM utilities
- `backend/core/constants.py` - Shared constants for consistent processing

### Configuration
- `backend/config/data_sources.yaml` - Legacy manual configuration (fallback only)
- `pyproject.toml` - Python project configuration and linting rules
- `.pre-commit-config.yaml` - Pre-commit hooks for code quality automation

## Development Guidelines

### Adding New Content (SUPER SIMPLE!)
1. **Text Content**: Just drop files in `backend/knowledge/` or `public/`
   - Supports: `.md`, `.pdf`, `.json`, `.txt`, `.html`, `.docx`
   - No configuration needed - automatically indexed and searchable!

2. **Illustrations**: Add to `backend/knowledge/illustrations.json` with format:
   ```json
   {
     "file": "filename.jpg",
     "title": "Title",
     "tags": ["tag1", "tag2"]
   }
   ```

3. **Restart Backend**: New content is automatically discovered on startup

### Python Code Standards
1. **Always format with Black before committing**
2. **Sort imports with isort**
3. **Fix all flake8 violations**
4. **Address mypy type checking warnings**
5. **Use type hints for function parameters and return values**
6. **Follow the existing patterns in the codebase**
7. **Write docstrings for public functions and classes**

### Smart System Features

#### Automatic Content Type Detection
The system automatically detects and categorizes content:
- **Technical**: Code, APIs, implementation details
- **Experience**: Work history, roles, companies
- **Skills**: Technologies, expertise, proficiencies
- **About**: Personal information, philosophy, interests
- **Creative**: Illustrations, art, design work
- **Project**: Built projects, developments, creations

#### Intelligent Query Routing
Queries are automatically analyzed for:
- **Intent**: question, retrieval, explanation, general
- **Topics**: technical, experience, skills, personal, creative, project
- **Complexity**: simple, moderate, complex
- **Approach**: focused, comprehensive, list

#### Smart Context Selection
- **Semantic similarity** matching
- **Content type filtering** based on query
- **Duplicate removal** and quality scoring
- **Context length optimization** for token limits
- **Relevance ranking** with metadata boosting

## Testing the Smart System

### Standard Query Endpoint (Your frontend uses this)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Nick's development philosophy?", "chat_history": []}'
```

### Advanced Smart Query Testing
```bash
# Check system status
curl http://localhost:8000/api/smart-query/status

# Analyze query intent
curl -X POST http://localhost:8000/api/smart-query/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "What CSS frameworks does Nick use?", "chat_history": []}'

# Full smart query with metadata
curl -X POST http://localhost:8000/api/smart-query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about Nick's frontend expertise", "chat_history": []}'
```

## Backend Logs - Smart Routing Examples
```
INFO - Smart routing: Query 'What's your development philosophy?' -> Topics: ['personal'] | Complexity: simple
INFO - Using smart routing for query: 'What's your development philosophy?'
INFO - Stored 8 documents in retrieval cache for key: 73ffbd0e3e3a5e87
```

## Current Development Status

### Active Branch: `illustration-updates`
The project is currently on the `illustration-updates` branch with enhanced backend services and improved code quality.

### Recent API Additions
- **Query Logging**: `/api/query-logs` - Admin interface for query analytics with protected access
- **Health Check**: `/health` - Service health monitoring
- **Smart Query Testing**: `/api/smart-query/*` - Advanced query analysis endpoints
- **Query Log Download**: Automated scripts for downloading and analyzing query logs
- **Protected Endpoints**: Security validation for admin interfaces

### New Services & Modules
- `query_logger.py` - Comprehensive query logging and analytics
- `response_service.py` - Enhanced response processing pipeline
- `followup_service.py` - Intelligent follow-up question generation with configurable services
- `followup_service_optimized.py` - Optimized follow-up question service
- `followup_service_llm.py` - LLM-powered follow-up question generation (disabled by default)
- `followup_service_pregenerated.py` - Pre-generated follow-up question service
- `followup_pregeneration.py` - Follow-up question pre-generation utilities
- `query_router.py` - Advanced query routing with intent analysis
- `geolocation_service.py` - Location-based services for user queries
- `llm_utils.py` - Shared LLM utilities and helper functions
- `constants.py` - Shared constants including stop words for query processing

### Testing & Coverage
- **Coverage Reports**: HTML coverage reports generated in `htmlcov/` directory
- **Test Markers**: `unit`, `integration`, `slow` for test organization
- **Coverage Target**: Focuses on `backend/core` modules
- **Async Testing**: Configured for async/await patterns with pytest-asyncio
- **Test Files**: Comprehensive test coverage including:
  - `test_followup_service.py` - Follow-up service testing
  - `test_response_service.py` - Response service testing
  - `test_illustration_service.py` - Illustration service with fuzzy matching tests
  - `test_query_router.py` - Query routing logic tests
  - `test_llm_chain.py` - LLM chain functionality tests
  - `integration/test_*.py` - Integration tests for API endpoints and search functionality

## Environment Variables
- `FORCE_REBUILD_DATA=true` - Force rebuild of vector indices on server startup (optional)

## Dependencies
- **Backend:** FastAPI, LangChain, ChromaDB, Anthropic/Google AI APIs
- **Frontend:** Astro, Vue.js
- **Python:** 3.11+ required
- **Linting:** black, isort, flake8, mypy, autoflake
- **Type Stubs:** types-PyYAML, types-requests, types-urllib3 (required for MyPy)

### Important: Type Stub Packages & Pre-commit
MyPy requires type stub packages for third-party libraries.

**For Pre-commit hooks:** Type stubs are configured in `.pre-commit-config.yaml` under the mypy hook's `additional_dependencies`. Current stubs include:
```yaml
additional_dependencies: [
  types-PyYAML>=1.0.0,
  types-requests>=2.0.0,
  types-urllib3>=1.0.0,
  pyyaml>=6.0,
  langchain,
  langchain-community,
  langchain-core,
  langchain-google-genai,
  fastapi,
  uvicorn
]
```
If you add new dependencies that need type stubs, add them there.

**For local development:** Install type stubs locally:
```bash
pip install types-PyYAML types-requests types-urllib3
# Or install all missing stubs automatically:
mypy --install-types
```

**If pre-commit mypy fails with missing stubs:**
1. Add the type stub to `.pre-commit-config.yaml` under mypy's `additional_dependencies`
2. Clean and reinstall pre-commit:
```bash
pre-commit clean
pre-commit install
```

## Migration Notes

### What Changed (Major Improvements!)
- ✅ **Eliminated unified_data.json dependency** - no more manual data compilation
- ✅ **Eliminated manual YAML configuration** - no more retriever definitions needed
- ✅ **Automatic content discovery** - just drop files in directories
- ✅ **Smart query routing** - understands intent automatically
- ✅ **Better search accuracy** - semantic similarity + metadata filtering
- ✅ **Unified vector store** - more efficient than multiple stores
- ✅ **Intelligent context selection** - better responses with less noise

### Backward Compatibility
- ✅ **Frontend unchanged** - same API, better responses
- ✅ **Query endpoint unchanged** - `/query` works exactly the same
- ✅ **Image search working** - illustrations work without unified_data.json
- ✅ **Fallback system** - gracefully handles missing data

### Performance Improvements
- ✅ **Built-in caching** - faster repeated queries
- ✅ **Single vector store** - more efficient than multiple stores
- ✅ **Smart filtering** - better relevance without over-processing
- ✅ **File hash tracking** - only re-index changed files

## Recent Improvements & Code Quality

### Code Quality Enhancements
- **Static Analysis**: Improved code robustness based on static analysis suggestions
- **Error Handling**: Enhanced error handling across all services
- **Code Deduplication**: Shared constants to eliminate duplication
- **Performance Optimization**: Illustration data caching during initialization
- **Security**: Protected admin endpoints with token authentication
- **Testing**: Comprehensive test coverage with fuzzy matching validation

### Service Architecture Improvements
- **Modular Follow-up Services**: Multiple configurable follow-up question services
- **Smart Caching**: Illustration and query result caching for performance
- **Geolocation Integration**: Location-aware query processing
- **LLM Utilities**: Shared utilities for consistent LLM interactions
- **Query Analytics**: Advanced query logging and analysis capabilities

### Development Experience
- **Better Debugging**: Enhanced logging and error messages
- **Code Organization**: Clear separation of concerns across services
- **Configuration Management**: Environment-based service selection
- **Documentation**: Comprehensive inline documentation and type hints

## Key Advantages of Current System

1. **Zero Configuration**: Drop files → Automatic indexing → Smart search
2. **Intent Understanding**: Analyzes what users actually want
3. **Better Accuracy**: Semantic similarity + intelligent filtering + fuzzy matching
4. **Easier Maintenance**: No YAML files, no manual setup
5. **Scalable**: Handles growing content automatically
6. **Performance**: Multi-level caching, efficient vector operations, smart context limits
7. **Developer Friendly**: Add content without touching code
8. **Robust Error Handling**: Graceful fallbacks and comprehensive error management
9. **Security**: Protected admin interfaces with proper authentication
10. **Analytics**: Query logging and analysis for continuous improvement

The system now operates like a smart assistant that understands both your content and your users' intent, with enterprise-grade reliability and performance!

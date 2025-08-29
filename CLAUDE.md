# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Context for Claude

## Project Overview
Nick Berens' personal website with an intelligent RAG-powered AI assistant. Backend built with FastAPI, frontend with Astro. The backend uses a **unified smart retriever system** that automatically discovers, indexes, and intelligently routes queries to relevant content without manual configuration. Features a comprehensive admin dashboard for monitoring and analytics.

## Key Commands

### Build Commands
- `npm run build` - Build the Astro frontend
- `npm run dev` - Start Astro development server
- `npm run backend:build` - Build backend container with Podman
- `npm run backend:dev` - Run backend in development mode with hot reload
- `npm run backend:dev:reindex` - Run backend with forced data reindexing
- `npm run backend:stop` - Stop the backend container

### Admin Commands
- `npm run admin:backend` - Start admin backend server
- `npm run admin:frontend` - Start admin frontend development server
- `npm run admin:build` - Build admin frontend for production
- `npm run admin` - Start both admin backend and frontend
- `npm run admin:stop` - Stop admin backend processes
- `npm run admin:sync` - Sync query logs with admin database
- `npm run logs:download` - Download query logs using configured script

### Test Commands
- `pytest` - Run Python tests with coverage (configured in pyproject.toml)
- `pytest --cov=backend/core` - Run tests with explicit coverage
- `pytest -m unit` - Run only unit tests (fast)
- `pytest -m integration` - Run integration tests (slower)
- `npm test` - Run frontend tests with Vitest
- `npm run test:run` - Run frontend tests once
- `PYTHONPATH=. pytest tests/` - Run tests with proper Python path
- `pytest tests/integration/test_api_endpoints.py -v` - Run specific test file with verbose output

### Makefile Commands
- `make lint-fix` - Auto-format code with Black, isort, and autoflake
- `make lint-check` - Check code formatting without making changes
- `make type-check` - Run MyPy type checking on backend/core
- `make lint` - Full lint pipeline: fix, check, and type-check
- `make lint-fast` - Quick lint without MyPy (faster for dev cycles)
- `make test-unit` - Run unit tests only (excludes integration and slow tests)
- `make test-integration` - Run integration tests only

### Linting & Type Checking
**Pre-commit hooks (run automatically on commit):**
- Black (code formatting) + isort (import sorting) - **MINIMAL** setup for speed
- Basic safety checks (YAML validation, large files, merge conflicts)
- MyPy and flake8 excluded from pre-commit for faster commits

**Manual linting commands (as needed):**
- `black .` - Format Python code (line length: 120)
- `isort .` - Sort Python imports
- `autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive .` - Remove unused imports
- `flake8 .` - Check Python style (relaxed rules, focuses on real issues)
- `mypy backend/core --ignore-missing-imports` - Type checking on core modules

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
   - Max line length: 120
   - Ignore: E203 (whitespace before ':'), W503 (line break before binary operator)
   - Per-file ignores: __init__.py (F401), tests/* (F401, F811)
   - Excludes: .git, __pycache__, .venv, venv, node_modules, build, dist

4. **MyPy Type Checking (Relaxed for Development):**
   - Python version: 3.11
   - ignore_missing_imports: true
   - follow_imports: silent
   - show_error_codes: true
   - warn_unused_configs: true
   - Relaxed settings: no_implicit_optional: false, strict_optional: false

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
│   ├── app_factory.py             # FastAPI application factory
│   ├── app_initializer_v2.py      # Unified retriever initialization
│   ├── unified_retriever.py       # Smart auto-discovery system
│   ├── smart_illustration_service.py  # Enhanced smart image search with caching
│   ├── smart_query_handler.py     # Intelligent query processing
│   ├── query_logger.py            # Query logging factory (returns SQLiteQueryLogger)
│   ├── sqlite_query_logger.py    # SQLite-based query logging implementation
│   ├── query_logger_dual.py       # Dual-output query logging
│   ├── query_router.py            # Query routing logic
│   ├── response_service.py        # Response processing service
│   ├── response_cache_warmer.py   # Cache warming service
│   ├── followup_service.py        # Follow-up question service (configurable)
│   ├── geolocation_service.py     # Location-based services
│   ├── llm_utils.py               # Shared LLM utilities
│   ├── constants.py               # Shared constants and stop words
│   ├── config.py                  # Centralized configuration with validation
│   ├── llm_chain.py               # LLM chain with smart routing
│   ├── admin_auth.py              # Admin authentication service
│   ├── admin_database.py          # Admin database operations
│   ├── query_data_manager.py      # Query data management
│   ├── content_indexer.py         # Content indexing utilities
│   ├── content_router.py          # Content routing logic
│   └── semantic_searcher.py       # Semantic search functionality
├── knowledge/      # Auto-indexed knowledge base
│   ├── *.md        # Markdown documentation
│   ├── *.pdf       # PDF documents
│   ├── *.json      # Structured data including illustrations.json
│   └── ...         # Any content - automatically indexed!
├── routes/         # API routes
│   ├── query.py            # Main query endpoint with smart retriever
│   ├── smart_query.py      # Advanced testing endpoints
│   ├── query_logs.py       # Protected query log interface
│   ├── health.py           # Health check endpoint
│   ├── admin.py            # Admin dashboard API routes
│   ├── admin_refresh.py    # Admin refresh endpoints
│   ├── content.py          # Content management routes
│   ├── knowledge.py        # Knowledge base routes
│   ├── performance.py      # Performance monitoring routes
│   ├── queries.py          # Query management routes
│   └── stats.py            # Statistics and analytics routes
├── templates/      # Jinja2 templates for admin interfaces
└── main.py         # FastAPI app entry point

admin/              # Admin dashboard system
├── backend/        # Python admin backend services
│   ├── auth.py     # Authentication and authorization
│   ├── database.py # Admin database operations
│   ├── main.py     # Admin FastAPI application
│   ├── models.py   # Database models
│   └── routes.py   # Admin API routes
├── frontend/       # Vue.js admin frontend
│   ├── src/
│   │   ├── components/     # Reusable Vue components
│   │   ├── views/         # Page components
│   │   ├── stores/        # Pinia state management
│   │   ├── services/      # API services
│   │   └── plugins/       # Vuetify configuration
│   └── dist/       # Built frontend files
└── start-admin.py  # Admin server startup script

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
- `backend/core/sqlite_query_logger.py` - SQLite-based query logging and analytics
- `backend/core/query_router.py` - Advanced query routing logic
- `backend/core/response_service.py` - Response processing and enhancement
- `backend/core/followup_service.py` - Intelligent follow-up question generation
- `backend/core/geolocation_service.py` - Location-based query processing
- `backend/core/llm_utils.py` - Shared LLM utilities
- `backend/core/constants.py` - Shared constants for consistent processing
- `backend/core/config.py` - Centralized configuration with enhanced security validation
- `backend/core/admin_auth.py` - Admin authentication and security
- `backend/core/admin_database.py` - Admin database management
- `backend/core/query_data_manager.py` - Query data operations and analytics

### Configuration
- `backend/core/config.py` - **PRIMARY**: Centralized configuration with validation
- `pyproject.toml` - Python project configuration and linting rules
- `.pre-commit-config.yaml` - Pre-commit hooks (minimal setup for speed)
- `Makefile` - Development workflow commands for linting and testing

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

### Current Development Status
The project features a fully integrated admin dashboard system with comprehensive monitoring and analytics capabilities.

### Recent API Additions
- **Query Logging**: `/api/query-logs` - Admin interface for query analytics with protected access
- **Health Check**: `/health` - Service health monitoring
- **Smart Query Testing**: `/api/smart-query/*` - Advanced query analysis endpoints
- **Query Log Download**: Automated scripts for downloading and analyzing query logs
- **Protected Endpoints**: Security validation for admin interfaces

### Admin Dashboard Access
- **Frontend**: http://localhost:3000 (Vue.js + Vuetify interface)
- **Backend**: http://localhost:8000 (FastAPI admin API - integrated with main backend)
- **Authentication**: Session-based with secure cookies
- **Security**: Session fingerprinting and secure cookie attributes
- **Admin Routes**: `/admin/*` endpoints protected with session authentication

#### Admin Dashboard Features
- **Dashboard**: System overview, query metrics, performance statistics
- **Queries**: Real-time query monitoring, analytics, response times
- **Knowledge**: Content management, indexed documents, gap analysis
- **Performance**: System performance metrics, response time analysis
- **Sessions**: User session management and authentication logs

### Admin Dashboard Icon Usage
The admin dashboard uses Vuetify with Material Design Icons (MDI). To maintain consistency and avoid console errors:

#### Icon Configuration (admin/frontend/src/plugins/vuetify.js)
- Icons are configured with aliases in the Vuetify plugin
- MDI icons are imported from `@mdi/js` and mapped to aliases
- **ALWAYS use icon aliases** with the `$` prefix in components

#### How to Add New Icons
1. **Import the MDI icon** in `vuetify.js`:
   ```javascript
   import { mdiNewIcon } from '@mdi/js'
   ```

2. **Add to aliases** in the Vuetify configuration:
   ```javascript
   aliases: {
     'new-icon': mdiNewIcon,
   }
   ```

3. **Use in components** with the `$` prefix:
   ```vue
   <v-icon>$new-icon</v-icon>
   <!-- OR -->
   <v-btn icon="$new-icon">Button</v-btn>
   ```

#### Available Icon Aliases
Common icons already configured:
- `$dashboard` - Dashboard/home icon
- `$search` - Search/magnify icon  
- `$chart` - Chart/analytics icon
- `$document` - Document/file icon
- `$users` - Users/people icon
- `$knowledge` - Knowledge base icon
- `$menu` - Menu/hamburger icon
- `$refresh` - Refresh/reload icon
- `$export` - Export/download icon
- `$logout` - Logout icon
- `$weather-night` - Dark mode icon
- `$light-mode` - Light mode icon

#### Common Mistakes to Avoid
❌ **DON'T** use raw MDI strings:
```vue
<v-icon>mdi-weather-night</v-icon> <!-- WRONG - causes SVG errors -->
```

✅ **DO** use configured aliases:
```vue
<v-icon>$weather-night</v-icon> <!-- CORRECT -->
```

#### Building Admin Frontend
After icon changes, rebuild the admin frontend:
```bash
cd admin/frontend && npm run build
```

### New Services & Modules
- `sqlite_query_logger.py` - SQLite-based query logging and analytics
- `query_logger_dual.py` - Dual-output logging (JSON + SQLite)
- `response_service.py` - Enhanced response processing pipeline
- `response_cache_warmer.py` - Cache warming for improved performance
- `followup_service.py` - Intelligent follow-up question generation
- `query_router.py` - Advanced query routing with intent analysis
- `geolocation_service.py` - Location-based services for user queries
- `llm_utils.py` - Shared LLM utilities and helper functions
- `constants.py` - Shared constants including stop words for query processing
- `admin_auth.py` - Admin authentication and security layer
- `admin_database.py` - Admin database operations and management
- `query_data_manager.py` - Query data analytics and operations
- `content_indexer.py` - Content indexing and processing utilities
- `content_router.py` - Content routing and management
- `semantic_searcher.py` - Advanced semantic search capabilities

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

### Core Backend Variables
- `FORCE_REBUILD_DATA=true` - Force rebuild of vector indices on server startup (optional)
- `WATCHFILES_FORCE_POLLING=true` - Enable file watching for container environments
- `ANTHROPIC_API_KEY` - Required for Anthropic Claude API access
- `GOOGLE_API_KEY` - Required for Google Gemini API access (if used)

### Admin System Variables
- `ADMIN_DB_PATH` - Path to admin SQLite database (defaults to backend/logs/admin_monitoring.db)

### Development Setup
1. **Copy environment template**: `cp .env.example .env` (if available)
2. **Set API keys** in `.env` file
3. **Install dependencies**: 
   - Backend: `pip install -r backend/requirements.txt`
   - Frontend: `npm install`
   - Admin Frontend: `cd admin/frontend && npm install`

## Database Architecture

The system uses multiple SQLite databases for different purposes:

### Core Backend Databases

#### `/backend/logs/rag_monitoring.db`
- **Purpose**: Primary query logging and analytics database
- **Tables**:
  - `query_logs` - All user queries, responses, and performance metrics
  - `content_gaps` - Detected knowledge gaps for content improvement
- **Usage**: Used by `QueryDataManager` for read access and query logging
- **Location fields**: Includes geolocation data (city, region, country) for analytics

#### `/backend/logs/auth_sessions.db`  
- **Purpose**: User session tracking for the main application
- **Tables**: 
  - `user_sessions` - Session tracking for RAG queries
- **Usage**: Session management and user behavior analytics

### Admin System Databases

#### `/backend/logs/admin_monitoring.db` 
- **Purpose**: Admin dashboard user management and settings
- **Tables**:
  - `admin_users` - Admin user accounts and authentication
  - `admin_sessions` - Admin dashboard login sessions
  - `admin_settings` - System configuration and preferences
- **Usage**: Used by `AdminDatabaseManager` for admin-specific operations
- **Security**: Handles admin authentication, roles, and session management

#### Query Log Storage
The system uses SQLite database for all query logging:
- **Database**: `/backend/logs/rag_monitoring.db`
- **Table**: `query_logs` - Stores all user queries and responses
- **Features**: IP filtering, anonymization, geolocation tracking
- **Service**: `SQLiteQueryLogger` - Handles all logging operations
- **Analytics**: Structured query analysis and performance metrics

### Database Separation Strategy
- **Admin databases**: Isolated for security and admin-specific features
- **Backend databases**: Focus on query performance and analytics
- **Dual managers**: `DatabaseManager` (admin) vs `QueryDataManager` (backend data)
- **Read-only access**: Admin system reads backend data without modification rights

## Dependencies

### Backend Dependencies
- **Core Framework:** FastAPI, uvicorn[standard]
- **AI/ML:** LangChain, langchain-anthropic, langchain-google-genai, langchain-community, langchain-chroma
- **Vector Database:** ChromaDB
- **Document Processing:** pdfplumber, pypdf, python-docx, unstructured, lxml, beautifulsoup4
- **Security:** passlib[bcrypt], python-multipart, slowapi (rate limiting)
- **Utilities:** aiofiles, pyyaml, requests, python-dotenv, thefuzz[speed], watchdog
- **Template Engine:** jinja2

### Frontend Dependencies  
- **Framework:** Astro 5.11.0, Vue.js 3.4.0
- **UI Components:** Various FontAwesome packages, astro-icon
- **Utilities:** marked (Markdown), lodash-es, nanostores
- **Testing:** Vitest, jsdom, @vue/test-utils

### Admin Dashboard Dependencies
- **Frontend:** Vue.js 3.4.0, Vuetify 3.6.0, Vue Router 4.2.0
- **State Management:** Pinia 2.1.0
- **Charts:** Chart.js 4.5.0, vue-chartjs 5.3.2
- **Icons:** @mdi/js 7.4.0 (Material Design Icons)
- **Code Editor:** Monaco Editor 0.52.2
- **HTTP Client:** Axios 1.6.0
- **Date Utilities:** date-fns 3.6.0
- **Build Tools:** Vite 5.2.0, TypeScript 5.4.0

### Development Dependencies
- **Python:** 3.11+ required
- **Linting:** black, isort, flake8, mypy, autoflake
- **Pre-commit:** Minimal setup with only Black and isort for speed

### Pre-commit Configuration (Minimal Setup)
The pre-commit configuration is intentionally minimal for faster development:

```yaml
# Only essential checks - no MyPy or flake8 in pre-commit
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - check-yaml
      - check-added-large-files  
      - check-merge-conflict
  - repo: https://github.com/psf/black
    hooks:
      - black (line-length=120)
  - repo: https://github.com/pycqa/isort
    hooks:
      - isort (profile=black)
```

**Philosophy:** Pre-commit only handles auto-formatting. Manual linting and type checking via Makefile commands when needed.

**For MyPy type checking:** Run manually with `make type-check` or `mypy backend/core --ignore-missing-imports`

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
- **Security**: Protected admin endpoints with session-based authentication
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

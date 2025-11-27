# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Nick Berens' personal website with RAG-powered AI assistant. FastAPI backend with **unified smart retriever** (auto-discovery, intelligent routing). Astro frontend with Vue islands. Comprehensive Vue 3 + Vuetify admin dashboard.

## Quick Reference

### Development Commands
```bash
# Frontend Development
npm run dev                    # Astro dev server (localhost:4321)
npm run build                  # Build frontend for production
npm run preview                # Preview production build

# Backend Development (Podman containerized)
npm run backend:dev            # Run with hot reload (localhost:8000)
npm run backend:dev:reindex    # Force reindex all content
npm run backend:stop           # Stop container
npm run backend:build          # Rebuild container image

# Admin Dashboard
npm run admin:frontend         # Admin UI dev server (localhost:3000)
npm run admin:backend          # Admin backend server
npm run admin:build            # Build admin for production
npm run admin:stop             # Stop admin processes
```

### Testing Commands
```bash
# Python Tests
pytest                         # All tests with coverage
pytest -m unit                 # Unit tests only (fast)
pytest -m integration          # Integration tests (slower)
pytest tests/unit/test_file.py # Run specific test file
pytest tests/unit/test_file.py::TestClass::test_method # Single test
pytest -k "test_name"          # Run tests matching pattern
make test-unit                 # Fast unit tests (Makefile shortcut)
make test-integration          # Integration tests (Makefile shortcut)

# E2E Tests (Playwright)
npm run e2e                    # Headless E2E tests
npm run e2e:headed             # E2E with visible browser
npm run e2e:debug              # E2E with debugging
npm run e2e:ui                 # Playwright UI mode
npm run e2e:report             # Show test report

# Frontend Tests (Vitest)
npm test                       # Run frontend tests
npm run test:run               # Run once (no watch)
```

### Linting & Formatting
```bash
# Quick formatting (most common)
make lint-fix                  # Auto-format with Black + isort + autoflake
make lint-fast                 # Format + check (no type checking)

# Full lint pipeline
make lint                      # Format + check + type-check
make lint-check                # Check without modifying
make type-check                # MyPy type checking only
```

### Python Code Standards
1. **Line length:** 120 characters (configured in pyproject.toml)
2. **Formatting:** Black + isort (profile=black) + autoflake
3. **Type hints:** Required for public functions (MyPy for core modules)
4. **Docstrings:** Required for public APIs (Google style)
5. **Pre-commit hooks:** Auto-format only (Black + isort) - never fails
6. **Logging:** Use module-level `logging.getLogger(__name__)`, never `print()`
7. **Async:** Prefer async/await for I/O operations (FastAPI is async)

## API Routes Reference

### Public Endpoints (No Auth)
- `POST /api/query` - Main AI query endpoint (streaming)
- `GET /api/health` - Health check
- `GET /api/status` - System status
- `GET /api/knowledge/documents` - Browse knowledge base
- `GET /api/welcome-questions` - Homepage questions

### Admin Endpoints (Session Auth Required)
**Authentication**
- `POST /api/admin/auth/login` - Login
- `GET /api/admin/auth/me` - Current user

**Dashboard**
- `GET /api/admin/stats/overview` - Dashboard stats
- `GET /api/admin/queries` - Query analytics
- `GET /api/admin/performance/metrics` - Performance data

**Settings** (All under `/admin/api/settings/`)
- `system-config`, `response`, `routing`, `rag-config`, `security`, `features`
- `api-keys/*` - API key management
- `followup/*` - Follow-up question management
- `welcome/*` - Welcome questions

**Knowledge Management** (`/admin/api/knowledge/`)
- `documents`, `sources`, `files/*` - Content CRUD
- `upload` - Upload new files

**Rate Limits:** Auth (5/min), Query logs (60/min), Settings (10/min)

## Architecture

### Smart Retriever System (Zero-Config RAG)
The core innovation is a **unified smart retriever** that eliminates manual configuration:

✅ **Auto-discovery** - Drop files in `backend/knowledge/` or `public/`, automatically indexed
✅ **No configuration** - No YAML, no manual setup, no content type declarations
✅ **Smart routing** - Intent-based query routing with semantic analysis
✅ **Content types** - Auto-detects: Technical, Experience, Skills, Creative, Project, About
✅ **Single vector store** - ChromaDB with intelligent filtering (faster than multi-store)
✅ **Multi-level caching** - Response caching, illustration caching, follow-up pre-generation

### Key Files & Responsibilities

**Core RAG Pipeline** (`backend/core/`)
- `app_initializer_v2.py` - Application startup, unified retriever initialization
- `unified_retriever.py` - **Central file**: Auto-discovery & content indexing
- `smart_query_handler.py` - Query intent analysis & routing decisions
- `query_router.py` - Routes queries to appropriate content types
- `response_service.py` - Response generation & streaming
- `llm_chain.py` - LangChain integration (Anthropic + Google fallback)
- `smart_illustration_service.py` - Image search with fuzzy matching + caching
- `followup_service.py` - Follow-up question generation
- `followup_management_service.py` - Follow-up management with validation
- `config.py` - Centralized configuration (AppConfig class)

**Content Processing** (`backend/core/`)
- `content_indexer.py` - File discovery and document loading
- `fast_content_classifier.py` - Content type detection (technical/experience/etc.)
- `content_router.py` - Content routing logic

**Security & Admin** (`backend/core/`)
- `admin_auth.py` - Session-based authentication + fingerprinting
- `admin_database.py` - All admin database operations
- `api_key_manager.py` - Secure API key storage & rotation
- `settings_manager.py` - Settings management with caching
- `settings_schemas.py` - Pydantic schemas for settings validation
- `security_middleware.py` - Rate limiting & security headers
- `audit_logger.py` - Comprehensive audit logging
- `totp_service.py` - TOTP two-factor authentication

**API Routes** (`backend/routes/`)
- `query.py` - **Main endpoint**: `/api/query` (streaming responses)
- `admin.py` - Admin dashboard API (159KB file - all admin operations)
- `knowledge.py` - Knowledge management (upload, delete, update)
- `health.py` - Health checks & system status
- `query_logs.py` - Protected query log access
- `smart_query.py` - Advanced testing endpoints

**Application Entry** (`backend/`)
- `main.py` - FastAPI app creation, lifespan management, global state
- `dependencies.py` - Dependency injection helpers

### Directory Structure
```
backend/
├── core/          # Business logic
├── knowledge/     # Auto-indexed content (md, pdf, json, etc.)
├── routes/        # API endpoints
└── main.py        # FastAPI entry

admin/
├── frontend/      # Vue + Vuetify UI
│   └── dist/      # Built files
├── create_admin.py
└── change_password.py

tests/
├── unit/          # Unit tests
├── integration/   # API integration tests
├── security/      # Security tests
└── e2e/           # Playwright E2E
```

## Development Workflows

### Adding Content (Zero Config!)
1. **Text content:** Drop files in `backend/knowledge/` or `public/`
   - Supported: `.md`, `.pdf`, `.json`, `.txt`, `.html`, `.docx`
   - No configuration needed - automatically indexed on startup
2. **Images/Illustrations:** Add entry to `backend/knowledge/illustrations.json`
3. **Restart backend:** `npm run backend:stop && npm run backend:dev`
   - Or force reindex: `npm run backend:dev:reindex`

### Adding a New Admin Setting
When adding a new setting to the admin dashboard:
1. **Schema:** Add dataclass to `backend/core/settings_schemas.py`
2. **Manager:** Add getter/setter methods to `backend/core/settings_manager.py`
3. **API Route:** Add endpoint in `backend/routes/admin.py` (settings section)
4. **Frontend Store:** Add to relevant Pinia store in `admin/frontend/src/stores/`
5. **Frontend View:** Create/update view in `admin/frontend/src/views/settings/`
6. **Database:** Settings auto-persist to `admin_monitoring.db` (no migration needed)

### Modifying API Routes
1. **Keep routers thin:** Business logic goes in `backend/core/`, not routes
2. **Use dependency injection:** Import from `backend/dependencies.py`
3. **Add rate limiting:** Use `@limiter.limit()` decorator for protected routes
4. **Document with docstrings:** FastAPI auto-generates OpenAPI docs
5. **Test with pytest:** Add tests in `tests/integration/` for route changes

### Working with the Unified Retriever
The system automatically discovers and indexes content. To modify retrieval:
1. **Content discovery:** `backend/core/content_indexer.py` - File scanning
2. **Content classification:** `backend/core/fast_content_classifier.py` - Type detection
3. **Query routing:** `backend/core/smart_query_handler.py` - Intent analysis
4. **Retrieval logic:** `backend/core/unified_retriever.py` - Main retrieval
5. **Never modify manually:** ChromaDB in `backend/.unified_chroma/` (auto-generated)

### Admin Dashboard Development (Vue 3 + Vuetify 3)

**CRITICAL: Icon Usage Pattern**
ALWAYS use `$` prefix with icon aliases (configured in Vuetify plugin):
```vue
✅ CORRECT: <v-icon>$weather-night</v-icon>
❌ WRONG:   <v-icon>mdi-weather-night</v-icon>
```

**Adding New Icons:**
1. Import from `@mdi/js` in `admin/frontend/src/plugins/vuetify.js`:
```javascript
import { mdiNewIcon } from '@mdi/js'
```
2. Add to aliases object:
```javascript
aliases: {
  'new-icon': mdiNewIcon,
  // ... other aliases
}
```

**Admin Frontend Architecture:**
- **State Management:** Pinia stores in `admin/frontend/src/stores/`
- **API Services:** `admin/frontend/src/services/` - Axios-based API clients
- **Views:** `admin/frontend/src/views/` - Page components
  - `settings/` - Settings management views (API Keys, Follow-ups, etc.)
- **Components:** `admin/frontend/src/components/` - Reusable UI components
- **Router:** `admin/frontend/src/router/` - Vue Router configuration
- **Vuetify Config:** `admin/frontend/src/plugins/vuetify.js` - Theme & icons

**Key Admin Features:**
- Dashboard with real-time query analytics
- Settings management (system, response, routing, RAG, security, features)
- API key rotation (Anthropic, Google)
- Follow-up question management
- Welcome questions configuration
- Knowledge base management
- Performance metrics visualization (Chart.js)

### Testing Smart System
```bash
# Standard query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Nick's philosophy?", "chat_history": []}'

# Advanced testing
curl http://localhost:8000/api/smart-query/status
```

## Database Architecture

### SQLite Databases (Multi-DB Design)
The system uses **separate databases** for different concerns:

**`backend/logs/rag_monitoring.db`** - Public query analytics
- Tables: `query_logs`, `content_gaps`, `performance_metrics`
- Features: IP filtering, anonymization, geolocation tracking
- Access: Public API + Admin dashboard

**`backend/logs/admin_monitoring.db`** - Admin system (isolated)
- Tables: `admin_users`, `admin_sessions`, `admin_settings`, `api_keys`, `audit_log`
- Features: Secure settings storage, API key management, audit logging
- Access: Admin routes only (session auth required)
- **Security:** Isolated from public queries, encrypted passwords (bcrypt)

**`backend/logs/auth_sessions.db`** - User session tracking
- Tables: `user_sessions`, `session_fingerprints`
- Features: Session management, fingerprinting, CSRF protection

### Database Access Patterns
- **Settings Manager:** `backend/core/settings_manager.py` - Centralized settings with caching
- **Admin Database:** `backend/core/admin_database.py` - All admin DB operations
- **Query Logger:** `backend/core/sqlite_query_logger.py` - Query logging with retry logic
- **Connection Management:** WAL mode, busy timeouts, retry logic for concurrency

## Environment Variables
```bash
ANTHROPIC_API_KEY=xxx          # Required
GOOGLE_API_KEY=xxx             # Optional
FORCE_REBUILD_DATA=true        # Force reindex
ADMIN_DB_PATH=path/to/db       # Admin DB path
```

## Key Dependencies
**Backend:** FastAPI, LangChain 0.2.x, ChromaDB 0.5.x, pdfplumber, passlib[bcrypt], slowapi
**Frontend:** Astro 5.11, Vue 3.4
**Admin:** Vue 3.4, Vuetify 3.6, Pinia 2.1, Chart.js 4.5, Monaco Editor
**Testing:** pytest, pytest-asyncio, Playwright, Vitest

## Common Issues & Troubleshooting

### Backend Won't Start
```bash
# Check if container is already running
podman ps | grep nickberens

# Stop existing container
npm run backend:stop

# Rebuild if needed
npm run backend:build

# Check logs
podman logs nickberens
```

### Database Locked Errors (SQLite)
The system uses WAL mode and retry logic, but if you see persistent locks:
```bash
# Set these in .env for development
SQLITE_JOURNAL_MODE=WAL
ADMIN_DB_BUSY_TIMEOUT_MS=15000
ADMIN_DB_CONNECT_RETRIES=7

# For debugging, temporarily disable features
FAST_LOGIN_MODE=true          # Skips audit writes during login
DISABLE_RATE_LIMITING=true    # Skips rate limiting middleware
```

### Content Not Indexed
```bash
# Force rebuild vector database
npm run backend:dev:reindex

# Or set in .env
FORCE_REBUILD_DATA=true

# Check ChromaDB directory
ls -la backend/.unified_chroma/
```

### Admin Dashboard Issues
```bash
# Rebuild admin frontend
cd admin/frontend && npm run build

# Check API base URL (in admin/frontend/.env)
VITE_API_BASE_URL=http://localhost:8000/api/admin

# Verify admin user exists
python3 admin/create_admin.py

# Reset admin password
python3 admin/change_password.py
```

### Tests Failing
```bash
# Clear pytest cache
rm -rf .pytest_cache __pycache__

# Run with verbose output
pytest -vv tests/unit/test_file.py

# Check test coverage
pytest --cov=backend/core --cov-report=html

# Skip slow tests
pytest -m "not slow"
```

## Key Design Principles
1. **Zero Config** - Drop files → auto-indexed (no YAML, no manual setup)
2. **Smart Intent** - Query analysis determines routing (not keyword matching)
3. **Auto Content Types** - Detects technical/experience/creative/etc from content
4. **Multi-level Caching** - Response cache, illustration cache, follow-up pre-generation
5. **Fuzzy Matching** - Better illustration search (handles typos, variations)
6. **Session Security** - Fingerprinting, secure cookies, CSRF protection, audit logging
7. **Separation of Concerns** - Isolated databases, thin routers, core business logic
8. **Comprehensive Testing** - Unit (fast), integration, E2E (Playwright), security tests

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Nick Berens' personal website with RAG-powered AI assistant. FastAPI backend with unified smart retriever (auto-discovery, intelligent routing). Astro frontend. Comprehensive admin dashboard with Vue.js + Vuetify.

## Quick Commands

### Development
- `npm run dev` - Astro dev server
- `npm run backend:dev` - Backend with hot reload
- `npm run admin` - Admin dashboard
- `pytest -m unit` - Fast unit tests
- `make lint-fast` - Quick format (Black + isort)

### Testing
- `pytest` - All tests with coverage
- `npm run e2e` - Playwright E2E tests
- `make test-unit` - Unit tests only

### Linting (Line length: 120)
- `make lint-fix` - Auto-format (Black, isort, autoflake)
- `make type-check` - MyPy type checking
- Pre-commit: Only Black + isort (MyPy excluded for speed)

### Deployment
- `npm run railway:deploy` - Deploy to Railway

## Backend API Routes

### Public Endpoints (`/api/*`)
**Health & Status**
- `GET /api/health` - Health check
- `GET /api/status` - System status + rate limits
- `GET /api/welcome-questions` - Homepage questions

**Query API**
- `POST /api/query` - Main AI query endpoint (streaming)
- `GET /api/default-model` - Default model config

**Knowledge Base (Read-Only)**
- `GET /api/knowledge/{documents|stats|sources}` - Browse indexed content

### Admin Endpoints (`/api/admin/*` - Session Auth Required)
**Authentication**
- `POST /api/admin/auth/{login|logout}` - Auth operations
- `POST /api/admin/auth/change-password` - Update password

**Dashboard & Analytics**
- `GET /api/admin/{stats/overview|queries|performance/*}` - Analytics
- `GET /api/admin/queries/insights` - Query insights

**Settings Management**
- `GET|PUT /admin/api/settings/{response|routing|security|features}` - Configuration
- `/admin/api/settings/api-keys/*` - API key management (CRUD + validation)
- `/admin/api/settings/followup/*` - Follow-up questions & categories
- `/admin/api/settings/cache/*` - Cache management

**Content & Knowledge**
- `/admin/api/knowledge/*` - Document management, upload, editing
- `/admin/api/content/*` - Gap analysis, popular topics

**User Management (Admin Role)**
- `GET|POST /admin/api/users` - List/create users
- `POST /admin/api/users/{user_id}/{deactivate|reactivate}` - User status
- `DELETE /admin/api/users/{user_id}` - Delete user

**Rate Limits**: Auth (5/min), Queries (60/min), Stats (30/min), Settings (10/min)

## Architecture

### Smart Retriever (Zero Config!)
- ✅ Auto-discovers content from `backend/knowledge/` and `public/`
- ✅ Smart query routing with intent analysis
- ✅ Semantic search + metadata filtering
- ✅ Multi-level caching
- ✅ Supports: `.md`, `.pdf`, `.json`, `.txt`, `.html`, `.docx`

### Project Structure
```
backend/core/          # Core business logic
├── unified_retriever.py        # Auto-discovery system
├── smart_query_handler.py      # Query intent analysis
├── smart_illustration_service.py # Image search + caching
├── response_service.py         # Response processing
├── followup_service.py         # Follow-up generation
├── query_router.py             # Routing logic
├── sqlite_query_logger.py      # Query analytics
├── admin_auth.py               # Admin authentication
├── settings_manager.py         # Settings management
├── api_key_manager.py          # API key rotation
└── config.py                   # Centralized config

backend/routes/        # API endpoints
admin/frontend/        # Vue.js dashboard (Vuetify)
tests/{unit,integration,e2e,security}  # Test suite
```

### Key Files
**Core**: `unified_retriever.py`, `smart_query_handler.py`, `config.py`, `sqlite_query_logger.py`
**Admin**: `admin_auth.py`, `settings_manager.py`, `api_key_manager.py`
**Performance**: `fast_content_classifier.py`, `performance_config.py`

## Development Guidelines

### Adding Content (Simple!)
1. Drop files in `backend/knowledge/` or `public/` - auto-indexed!
2. For illustrations: Add to `backend/knowledge/illustrations.json`
3. Restart backend - content discovered automatically

### Python Standards
1. Format with Black (120 chars), sort imports (isort)
2. Type hints required, docstrings for public functions
3. Fix flake8 violations, address mypy warnings
4. Follow existing patterns

### Admin Dashboard Icons
- Use Vuetify with MDI icons from `@mdi/js`
- **Always use `$` prefix**: `<v-icon>$dashboard</v-icon>`
- Import in `admin/frontend/src/plugins/vuetify.js` first
- Rebuild: `cd admin/frontend && npm run build`

## Database Architecture

### Core Databases (SQLite)
**`/backend/logs/rag_monitoring.db`**
- `query_logs` - User queries, responses, metrics
- `content_gaps` - Knowledge gap detection

**`/backend/logs/admin_monitoring.db`**
- `admin_users` - User accounts & auth
- `admin_sessions` - Login sessions
- `admin_settings` - Configuration

**Strategy**: Isolated admin DB for security; read-only backend access

## Environment Variables
- `ANTHROPIC_API_KEY` - Required for Claude API
- `GOOGLE_API_KEY` - Optional for Gemini
- `FORCE_REBUILD_DATA=true` - Force reindex (optional)
- `ADMIN_DB_PATH` - Admin DB path (default: backend/logs/admin_monitoring.db)

## Dependencies

### Backend
FastAPI, LangChain (~0.2.0), ChromaDB (~0.5.0), langchain-anthropic, passlib[bcrypt], slowapi, thefuzz[speed]

### Frontend
Astro 5.11.0, Vue.js 3.4.0, marked, @vue/test-utils

### Admin Dashboard
Vue 3.4.0, Vuetify 3.6.0, Pinia 2.1.0, Chart.js 4.5.0, @mdi/js 7.4.0, Monaco Editor 0.52.2

### Dev Tools
Python 3.11+, black, isort, flake8, mypy, pytest, Playwright

## System Features

### Smart Retriever
- **Auto Content Detection**: Technical, Experience, Skills, Creative, Project
- **Query Analysis**: Intent, topics, complexity, approach
- **Context Selection**: Semantic similarity, deduplication, relevance ranking

### Testing
```bash
# Standard query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Your question", "chat_history": []}'

# Advanced analysis
curl -X POST http://localhost:8000/api/smart-query/analyze \
  -d '{"question": "Your question", "chat_history": []}'
```

## Key Advantages
1. **Zero Config**: Drop files → Auto-index → Smart search
2. **Intent Understanding**: Analyzes user intent automatically
3. **Performance**: Multi-level caching, efficient vectors
4. **Security**: Session auth, API key rotation, audit logging
5. **Analytics**: Query logging, gap analysis, insights
6. **Developer Friendly**: No YAML, no manual setup

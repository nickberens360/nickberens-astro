# CLAUDE.md

Claude Code guidance for this repository.

## Project Overview
Nick Berens' personal website with RAG-powered AI assistant. FastAPI backend with **unified smart retriever** (auto-discovery, intelligent routing). Astro frontend. Comprehensive admin dashboard.

## Quick Reference

### Essential Commands
```bash
# Frontend
npm run dev                    # Astro dev server
npm run build                  # Build frontend

# Backend
npm run backend:dev            # Run with hot reload
npm run backend:dev:reindex    # Force reindex
npm run backend:stop           # Stop container

# Admin
npm run admin:frontend         # Admin UI dev server
npm run admin:build            # Build admin for production

# Testing
pytest                         # Run all tests
pytest -m unit                 # Unit tests only
npm run e2e                    # Playwright E2E tests

# Linting
make lint-fix                  # Auto-format (Black + isort)
make lint-fast                 # Quick lint without MyPy
make type-check                # MyPy type checking
```

### Python Code Standards
1. Line length: 120 characters
2. Format with Black before committing
3. Sort imports with isort (profile=black)
4. Use type hints for public functions
5. Write docstrings for public APIs
6. Pre-commit: Black + isort only (MyPy manual)

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

### Smart Retriever System
✅ **Auto-discovery** - Drop files, automatic indexing
✅ **No configuration** - No YAML needed
✅ **Smart routing** - Intent-based query routing
✅ **Content types** - Technical, Experience, Skills, Creative, Project, About

### Key Files
**Core Logic** (`backend/core/`)
- `unified_retriever.py` - Auto-discovery & indexing
- `smart_query_handler.py` - Query intent analysis
- `smart_illustration_service.py` - Image search with fuzzy matching
- `query_router.py` - Smart routing logic
- `response_service.py` - Response processing
- `followup_management_service.py` - Follow-up questions
- `config.py` - Centralized configuration

**Security & Admin**
- `admin_auth.py` - Admin authentication
- `api_key_manager.py` - API key rotation
- `security_middleware.py` - Security layer
- `settings_manager.py` - Settings management

**Routes** (`backend/routes/`)
- `query.py` - Main query endpoint
- `admin.py` - Admin dashboard API
- `knowledge.py` - Knowledge management

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

### Adding Content
1. Drop files in `backend/knowledge/` (supports: .md, .pdf, .json, .txt, .html, .docx)
2. For images: Add to `backend/knowledge/illustrations.json`
3. Restart backend - auto-indexed!

### Admin Dashboard Icons (Vue + Vuetify)
**ALWAYS use `$` prefix with aliases:**
```vue
✅ <v-icon>$weather-night</v-icon>
❌ <v-icon>mdi-weather-night</v-icon>
```

Add new icons in `admin/frontend/src/plugins/vuetify.js`:
```javascript
import { mdiNewIcon } from '@mdi/js'
aliases: { 'new-icon': mdiNewIcon }
```

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

### SQLite Databases
**`/backend/logs/rag_monitoring.db`**
- Query logs, responses, performance metrics
- Content gap analysis

**`/backend/logs/admin_monitoring.db`**
- Admin users, sessions, settings
- Isolated for security

**`/backend/logs/auth_sessions.db`**
- User session tracking

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

## Key Advantages
1. **Zero Config** - Drop files → auto-indexed
2. **Smart Intent** - Understands what users want
3. **Auto Content Types** - Detects technical/experience/creative/etc
4. **Multi-level Caching** - Fast performance
5. **Fuzzy Matching** - Better illustration search
6. **Session Security** - Fingerprinting & secure cookies
7. **Comprehensive Testing** - Unit, integration, E2E, security

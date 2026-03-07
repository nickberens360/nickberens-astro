# Nick Berens - Portfolio Website

Nick Berens' personal website with an intelligent RAG-powered AI assistant. Backend built with FastAPI, frontend with Astro. The backend uses a **unified smart retriever system** that automatically discovers, indexes, and intelligently routes queries to relevant content without manual configuration. Features a comprehensive admin dashboard for monitoring and analytics.

---

## Features

This website is packed with interactive and dynamic features designed to provide an engaging user experience:

* **🤖 AI-Powered Chatbot ("nick.AI")**: A fully functional chatbot built with a Retrieval-Augmented Generation (RAG) system featuring:
    * **Smart Auto-Discovery**: Automatically indexes content from directories without manual configuration
    * **Intelligent Query Routing**: Analyzes query intent and routes to relevant content types
    * **Dual LLM Support**: Anthropic Claude & Google Gemini with fallback
    * **Streaming Responses**: Real-time interaction with progressive response building
    * **Smart Follow-ups**: AI-generated follow-up question suggestions
    * **Enhanced Image Search**: Fuzzy matching and caching for illustration queries
    * **Geolocation Integration**: Location-aware query processing

* **📊 Admin Dashboard**: Comprehensive monitoring and analytics system featuring:
    * **Vue.js + Vuetify Interface**: Modern, responsive admin UI with Material Design
    * **Real-time Query Analytics**: Monitor user queries, response times, and system performance
    * **Knowledge Management**: Content gap analysis and indexed document overview
    * **Session Management**: Secure admin authentication with session tracking
    * **Performance Metrics**: System health monitoring and detailed analytics
    * **Settings Management**: Centralized configuration for API keys, followup questions, and system features
    * **Security Features**: TOTP authentication, audit logging, and session fingerprinting
    * **API Key Management**: Secure storage and rotation of Anthropic/Google API keys

* **🖥️ Interactive Terminal**: A draggable, resizable, and minimizable terminal window that allows users to navigate the site and access information using command-line instructions.

* **🎨 Illustrations Gallery**: Dynamic gallery showcasing artwork with smart search capabilities and parallax effects.

* **📝 MDX-Powered Blog**: Blog with seamless Vue component integration within Markdown content.

* **📄 Dynamic Resume Page**: Online resume with PDF download option.

---

## Technology Stack

This project utilizes a modern, full-stack technology setup.

### Frontend

* **Framework**: **Astro** for the core static site generation and component islands architecture.
* **UI Components**: **Vue.js** for creating interactive components like the AI Chatbot and Terminal.
* **State Management**: **Nanostores** for managing global UI state across different components and frameworks.
* **Styling**: Global CSS with utility classes for a consistent design system.
* **Icons**: **Font Awesome** for a wide range of icons used throughout the site.

### Backend

* **Framework**: **FastAPI** with full async support for high-performance API operations
* **Smart Retriever System**: **Unified auto-discovery** system that eliminates manual configuration
* **Database**: **SQLite** for query logging, analytics, and admin management
* **Security**: **Session-based authentication**, rate limiting, and admin access controls
* **Monitoring**: **Comprehensive logging** and performance tracking

### Admin Dashboard

* **Frontend Framework**: **Vue.js 3** with **Vuetify 3** for modern Material Design UI
* **State Management**: **Pinia** for reactive state across dashboard components
* **Charts & Analytics**: **Chart.js** integration for data visualization
* **Authentication**: **Secure session management** with fingerprinting and CSRF protection

### AI & Machine Learning

* **Core AI Logic**: **LangChain** for RAG pipeline with smart query routing and intent analysis
* **Language Models (LLMs)**:
    * **Anthropic Claude Sonnet 4.5** (primary - claude-sonnet-4-5) - **Recently upgraded** from Claude 3.5 Sonnet
    * **Google Gemini 1.5 Flash** (fallback)
* **Embeddings**: **GoogleGenerativeAIEmbeddings** (models/embedding-001) for semantic search capabilities
* **Vector Database**: **ChromaDB 0.5.x** with intelligent content type filtering and caching
* **Smart Features**: **Fuzzy matching**, geolocation integration, multi-level response caching, and session fingerprinting

---

## Project Structure

The project features a modern full-stack architecture with auto-discovery content management and comprehensive admin dashboard.

```text
/
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules  
├── README.md                        # Project documentation
├── CLAUDE.md                        # Development instructions for Claude Code
├── astro.config.mjs                 # Astro configuration
├── package.json                     # Node.js dependencies and scripts
├── Makefile                         # Development workflow commands
├── pyproject.toml                   # Python project configuration
├── .pre-commit-config.yaml          # Pre-commit hooks configuration
├── public/                          # Static assets (auto-indexed)
│   ├── favicon.svg                  # Site favicon
│   ├── Nick_Berens_Resume.pdf       # PDF resume
│   ├── resume.json                  # Structured resume data
│   ├── about.json                   # About information
│   └── illustrations/               # Illustration image files
├── src/                             # Frontend source code (Astro)
│   ├── assets/                      # Static assets
│   ├── components/                  # Vue components
│   │   ├── ChatBot.vue              # Main chatbot component
│   │   ├── ChatInput.vue            # Chat input interface
│   │   ├── ChatMessageList.vue      # Message display
│   │   ├── CustomLMGTFY.vue         # Terminal component
│   │   └── ...                      # Other UI components
│   ├── pages/                       # Astro pages (routes)
│   │   ├── index.astro              # Homepage
│   │   ├── illustrations.astro      # Gallery page
│   │   ├── resume.astro             # Resume page
│   │   ├── nick-ai.astro            # Chatbot page
│   │   └── blog/                    # Blog routes
│   ├── content/blog/                # MDX blog posts
│   ├── layouts/                     # Astro layout components
│   ├── stores/                      # Nanostores state management
│   └── styles/                      # Global CSS styles
├── backend/                         # FastAPI backend with unified smart retriever
│   ├── main.py                      # FastAPI application entry point
│   ├── knowledge/                   # Auto-indexed knowledge base
│   │   ├── *.md                     # Markdown documentation  
│   │   ├── *.pdf                    # PDF documents
│   │   ├── *.json                   # Structured data (including illustrations.json)
│   │   └── ...                      # Any content - automatically indexed!
│   ├── core/                        # Core business logic
│   │   ├── app_factory.py           # FastAPI application factory
│   │   ├── app_initializer_v2.py    # Unified retriever initialization
│   │   ├── unified_retriever.py     # Smart auto-discovery system
│   │   ├── smart_query_handler.py   # Intelligent query processing
│   │   ├── smart_illustration_service.py # Enhanced image search with caching
│   │   ├── query_router.py          # Advanced query routing
│   │   ├── response_service.py      # Response processing service  
│   │   ├── followup_service.py      # Follow-up question service
│   │   ├── followup_management_service.py # Enhanced followup management
│   │   ├── geolocation_service.py   # Location-based services
│   │   ├── geolocation_validator.py # Geolocation validation and security
│   │   ├── sqlite_query_logger.py   # SQLite-based query logging
│   │   ├── admin_auth.py            # Admin authentication service
│   │   ├── admin_database.py        # Admin database operations
│   │   ├── query_data_manager.py    # Query data management
│   │   ├── api_key_manager.py       # API key management and rotation
│   │   ├── audit_logger.py          # Comprehensive audit logging
│   │   ├── security_middleware.py   # Security middleware and validation
│   │   ├── session_fingerprint.py   # Session fingerprinting for security
│   │   ├── totp_service.py          # Time-based one-time password service
│   │   ├── settings_manager.py      # Settings management service
│   │   ├── settings_schemas.py      # Settings validation schemas
│   │   ├── database_utils.py        # Database utility functions
│   │   ├── config.py                # Centralized configuration
│   │   └── ...                      # Other core modules
│   ├── routes/                      # API routes
│   │   ├── query.py                 # Main query endpoint
│   │   ├── smart_query.py           # Advanced testing endpoints
│   │   ├── admin.py                 # Admin dashboard API routes  
│   │   ├── query_logs.py            # Protected query log interface
│   │   ├── health.py                # Health check endpoint
│   │   ├── knowledge_public.py      # Public knowledge base access
│   │   └── ...                      # Other route modules
│   ├── templates/                   # Jinja2 templates for admin
│   └── logs/                        # Database and log files
├── admin/                           # Admin dashboard system
│   ├── backend/                     # Python admin backend services (DEPRECATED - logic moved to backend/core)
│   ├── frontend/                    # Vue.js + Vuetify admin frontend
│   │   ├── src/
│   │   │   ├── components/          # Reusable Vue components
│   │   │   │   └── settings/        # Settings-specific components
│   │   │   ├── views/               # Page-level components
│   │   │   │   ├── settings/        # Settings management views (API Keys, Followups, Welcome, etc.)
│   │   │   │   ├── user-settings/   # User preference views
│   │   │   │   └── knowledge/       # Knowledge base management views
│   │   │   ├── stores/              # Pinia state management stores
│   │   │   ├── services/            # API client services
│   │   │   │   └── settings/        # Settings API services
│   │   │   ├── composables/         # Vue composables for reusable logic
│   │   │   │   └── queries/         # Query-related composables
│   │   │   ├── types/               # TypeScript type definitions
│   │   │   ├── utils/               # Utility functions
│   │   │   ├── styles/              # Global styles and themes
│   │   │   ├── router/              # Vue Router configuration
│   │   │   └── plugins/             # Vuetify configuration with icon aliases
│   │   └── dist/                    # Built frontend files (production)
│   ├── create_admin.py              # Admin user creation script
│   ├── change_password.py           # Admin password management script
│   └── start-admin.py               # Admin server startup script
├── scripts/                         # Utility scripts
│   ├── copy-content-to-knowledge.sh # Content management
│   └── ...                          # Other utility scripts
├── tests/                           # Comprehensive test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── security/                    # Security tests
│   ├── e2e/                         # End-to-end tests with Playwright
│   └── ...                          # Test files with pytest markers
└── htmlcov/                         # Test coverage reports

---

## Development Commands

### Frontend Commands
- `npm run dev` - Start Astro development server (localhost:4321)
- `npm run build` - Build the Astro frontend for production
- `npm run preview` - Preview production build locally

### Backend Commands (Podman Containerized)
- `npm run backend:build` - Copy content & build backend container with Podman
- `npm run backend:dev` - Run backend with hot reload & volume mounts (localhost:8000)
- `npm run backend:dev:reindex` - Force reindex all content on startup (when content changes)
- `npm run backend:stop` - Stop the backend container

### Admin Dashboard Commands
- `npm run admin:frontend` - Start admin UI dev server (localhost:3000)
- `npm run admin:backend` - Start admin backend server (uses backend/routes/admin.py)
- `npm run admin:build` - Build admin frontend for production
- `npm run admin` - Alias for admin:frontend
- `npm run admin:stop` - Stop admin backend processes

### Test Commands
- `pytest` - Run Python tests with coverage (configured in pyproject.toml)
- `pytest -m unit` - Run only unit tests (fast)
- `pytest -m integration` - Run integration tests (slower)
- `npm test` - Run frontend tests with Vitest
- `PYTHONPATH=. pytest tests/` - Run tests with proper Python path

### E2E Test Commands (Playwright with MCP)
- `npm run e2e` - Run end-to-end tests with Playwright in headless mode
- `npm run e2e:headed` - Run E2E tests in headed mode (visible browser for debugging)
- `npm run e2e:debug` - Run E2E tests with step-by-step debugging enabled
- `npm run e2e:ui` - Run E2E tests with interactive Playwright UI mode
- `npm run e2e:report` - Show detailed HTML test report from last run
- `npm run e2e:install` - Install Playwright browsers (Chromium, Firefox, WebKit)

### Makefile Commands
- `make lint-fix` - Auto-format code with Black, isort, and autoflake
- `make lint-check` - Check code formatting without making changes
- `make type-check` - Run MyPy type checking on backend/core
- `make lint` - Full lint pipeline: fix, check, and type-check
- `make test-unit` - Run unit tests only (excludes integration and slow tests)
- `make test-integration` - Run integration tests only

---

## Smart Retriever Architecture

### Unified System (NO MANUAL CONFIGURATION NEEDED!)
The system now uses a **unified smart retriever** that:
- ✅ **Automatically discovers** all content from directories
- ✅ **Intelligently detects** content types (technical, experience, creative, etc.)
- ✅ **Smart query routing** based on intent analysis
- ✅ **No YAML configuration** required - just drop files in directories
- ✅ **Zero manual setup** for new content sources

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

### Key Features
- **Automatic Content Type Detection**: Technical, experience, skills, about, creative, project
- **Intelligent Query Routing**: Analyzes intent, topics, complexity, and approach
- **Smart Context Selection**: Semantic similarity + content type filtering + relevance ranking
- **Built-in Caching**: Faster repeated queries with multi-level caching
- **Performance**: Single vector store, smart filtering, context length optimization

---

## Environment Variables

### Core Backend Variables
- `ANTHROPIC_API_KEY` - Required for Anthropic Claude API access
- `GOOGLE_API_KEY` - Required for Google Gemini API access (if used)
- `FORCE_REBUILD_DATA=true` - Force rebuild of vector indices on startup (optional)
- `ADMIN_DB_PATH` - Path to admin SQLite database (defaults to backend/logs/admin_monitoring.db)

### Security & Authentication Variables
- `ADMIN_DEFAULT_USERNAME` - Default admin username for initial setup
- `ADMIN_DEFAULT_PASSWORD` - Default admin password for initial setup (change immediately)
- `SESSION_SECRET_KEY` - Secret key for session management (generated automatically)
- `TOTP_SECRET_KEY` - Secret key for TOTP authentication (generated automatically)
- `ENABLE_AUDIT_LOGGING=true` - Enable comprehensive audit logging (default: true)

### Stability & Debugging Variables (Backend)
- `SQLITE_JOURNAL_MODE` — SQLite journaling mode. Use `WAL` in development for better concurrency.
- `ADMIN_DB_BUSY_TIMEOUT_MS` — Busy timeout milliseconds for SQLite (default 5000; recommended 15000 in dev).
- `ADMIN_DB_CONNECT_RETRIES` — Retries for transient connection/lock errors (default 5).
- `ADMIN_DB_CONNECT_RETRY_DELAY_MS` — Delay between connection retries in ms (default 200).
- `DISABLE_RATE_LIMITING` — If `true`, bypasses dynamic rate limiting middleware during debug.
- `FAST_LOGIN_MODE` — If `true`, minimizes DB writes during admin login (skips audit/fingerprint writes) to avoid local lockups.
- `ADMIN_DB_AUDIT_TIMEOUT_SECONDS` — Very short timeout for audit/security event writes so they never block requests (default 0.05).
- `ADMIN_DB_WRITE_RETRIES` / `ADMIN_DB_WRITE_RETRY_DELAY_MS` — Quick retries for non-blocking audit writes.

### Admin Frontend Variables
- `VITE_API_BASE_URL` — Admin API base URL.
  - Development: `http://localhost:8000/api/admin` (frontend now honors this in dev, bypassing the Vite proxy if set)
  - Production behind same-origin reverse proxy: `/api/admin`

### Follow-up Configuration
- `FOLLOWUP_MODE=pre_generated|optimized|static` - Follow-up question strategy (default: pre_generated)
- `ENABLE_FOLLOWUP_PREGENERATION=true|false` - Cache follow-ups at startup (default: true)
- `FOLLOWUP_VALIDATION_SCORE_THRESHOLD=0.5` - Minimum similarity score for follow-up validation

### Development Setup
1. **Copy environment template**: `cp .env.example .env` (if available)
2. **Set API keys** in `.env` file
3. **Install dependencies**: 
   - Backend: `pip install -r backend/requirements.txt`
   - Frontend: `npm install`
   - Admin Frontend: `cd admin/frontend && npm install`

---

## Database Architecture

The system uses multiple SQLite databases for different purposes:

### Backend Databases
- **`/backend/logs/rag_monitoring.db`** - Primary query logging and analytics
  - Tables: `query_logs`, `content_gaps`, `performance_metrics`
  - Features: IP filtering, anonymization, geolocation tracking
- **`/backend/logs/auth_sessions.db`** - User session tracking for main application
  - Tables: `user_sessions`, `session_fingerprints`
  - Features: Session management, fingerprinting, and user behavior analytics
- **`/backend/logs/security_events.db`** - Security monitoring and threat detection
  - Tables: Security event logs, threat patterns, blocked IPs
  - Features: Real-time security monitoring, attack pattern detection
- **`/backend/logs/knowledge_index.db`** - Content indexing metadata
  - Tables: Document metadata, indexing status, content checksums
  - Features: Content tracking, indexing optimization, duplicate detection

### Admin System Databases
- **`/backend/logs/admin_monitoring.db`** - Admin user management and settings
  - Tables: `admin_users`, `admin_sessions`, `admin_settings`, `api_keys`, `audit_log`
  - Features: Admin authentication, roles, session management, API key storage, and comprehensive audit logging

### Security Features
- **Session-based Authentication**: Secure cookies with fingerprinting
- **TOTP Multi-factor Authentication**: Time-based one-time passwords
- **Audit Logging**: Comprehensive tracking of all admin actions
- **API Key Management**: Secure storage and rotation of provider keys
- **Database Separation**: Isolated admin and backend databases for security

### Access Points
- **Admin Dashboard**: http://localhost:3000 (Vue.js + Vuetify interface)
- **Backend API**: http://localhost:8000 (FastAPI with protected admin routes)
- **Health Monitoring**: Real-time system status and performance metrics
- **Analytics**: Query monitoring, response time analysis, and usage patterns

---

## Railway Production Env Snippet (copy/paste)

Append these to your Railway environment to improve stability without weakening protections:

```
# Connection retries for transient SQLite locks
ADMIN_DB_CONNECT_RETRIES=7
ADMIN_DB_CONNECT_RETRY_DELAY_MS=300

# Non-blocking audit/security event writes
ADMIN_DB_AUDIT_TIMEOUT_SECONDS=0.05
ADMIN_DB_WRITE_RETRIES=3
ADMIN_DB_WRITE_RETRY_DELAY_MS=50

# Ensure protections remain enabled in production
DISABLE_RATE_LIMITING=false
FAST_LOGIN_MODE=false
```

Note: Keep `SQLITE_JOURNAL_MODE=WAL`, `ADMIN_DB_BUSY_TIMEOUT_MS=15000`, and `ADMIN_DB_TIMEOUT_SECONDS=15` as you have them.

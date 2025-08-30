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
    * **Vue.js + Vuetify Interface**: Modern, responsive admin UI
    * **Real-time Query Analytics**: Monitor user queries, response times, and system performance
    * **Knowledge Management**: Content gap analysis and indexed document overview
    * **Session Management**: Secure admin authentication with session tracking
    * **Performance Metrics**: System health monitoring and detailed analytics

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
    * **Anthropic Claude 3.5 Sonnet** (primary)
    * **Google Gemini 1.5 Flash** (fallback)
* **Embeddings**: **GoogleGenerativeAIEmbeddings** for semantic search capabilities
* **Vector Database**: **ChromaDB** with intelligent content type filtering and caching
* **Smart Features**: **Fuzzy matching**, geolocation integration, and response caching

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
│   │   ├── geolocation_service.py   # Location-based services
│   │   ├── sqlite_query_logger.py   # SQLite-based query logging
│   │   ├── admin_auth.py            # Admin authentication service
│   │   ├── admin_database.py        # Admin database operations
│   │   ├── query_data_manager.py    # Query data management
│   │   ├── config.py                # Centralized configuration
│   │   └── ...                      # Other core modules
│   ├── routes/                      # API routes
│   │   ├── query.py                 # Main query endpoint
│   │   ├── smart_query.py           # Advanced testing endpoints
│   │   ├── admin.py                 # Admin dashboard API routes  
│   │   ├── query_logs.py            # Protected query log interface
│   │   ├── health.py                # Health check endpoint
│   │   └── ...                      # Other route modules
│   ├── templates/                   # Jinja2 templates for admin
│   └── logs/                        # Database and log files
├── admin/                           # Admin dashboard system
│   ├── backend/                     # Python admin backend services
│   │   ├── main.py                  # Admin FastAPI application
│   │   ├── auth.py                  # Authentication and authorization
│   │   ├── database.py              # Admin database operations
│   │   ├── models.py                # Database models
│   │   └── routes.py                # Admin API routes
│   ├── frontend/                    # Vue.js + Vuetify admin frontend
│   │   ├── src/
│   │   │   ├── components/          # Vue components
│   │   │   ├── views/               # Page components  
│   │   │   ├── stores/              # Pinia state management
│   │   │   ├── services/            # API services
│   │   │   └── plugins/             # Vuetify configuration
│   │   └── dist/                    # Built frontend files
│   └── start-admin.py               # Admin server startup script
├── scripts/                         # Utility scripts
│   ├── copy-content-to-knowledge.sh # Content management
│   └── ...                          # Other utility scripts
├── tests/                           # Comprehensive test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── security/                    # Security tests
│   └── ...                          # Test files with pytest markers
└── htmlcov/                         # Test coverage reports

---

## Development Commands

### Build Commands
- `npm run build` - Build the Astro frontend
- `npm run dev` - Start Astro development server
- `npm run backend:build` - Build backend container with Podman
- `npm run backend:dev` - Run backend in development mode with hot reload
- `npm run backend:stop` - Stop the backend container

### Admin Commands
- `npm run admin:backend` - Start admin backend server
- `npm run admin:frontend` - Start admin frontend development server
- `npm run admin:build` - Build admin frontend for production
- `npm run admin` - Start both admin backend and frontend
- `npm run admin:stop` - Stop admin backend processes

### Test Commands
- `pytest` - Run Python tests with coverage (configured in pyproject.toml)
- `pytest -m unit` - Run only unit tests (fast)
- `pytest -m integration` - Run integration tests (slower)
- `npm test` - Run frontend tests with Vitest
- `PYTHONPATH=. pytest tests/` - Run tests with proper Python path

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
- **`/backend/logs/auth_sessions.db`** - User session tracking

### Admin System Databases  
- **`/backend/logs/admin_monitoring.db`** - Admin user management and settings
- **Query Log Storage** - SQLite-based logging with IP filtering, anonymization, geolocation

### Features
- **Admin Dashboard Access**: http://localhost:3000 (Vue.js + Vuetify)
- **Backend API**: http://localhost:8000 (FastAPI with admin routes)
- **Security**: Session-based authentication with fingerprinting
- **Analytics**: Real-time query monitoring and performance metrics

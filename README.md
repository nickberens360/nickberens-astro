# Nick Berens - Portfolio Website

Personal website with intelligent RAG-powered AI assistant. Built with FastAPI backend and Astro frontend, featuring a **unified smart retriever system** that automatically discovers and indexes content without configuration.

## Features

* **🤖 AI Chatbot ("nick.AI")**: RAG system with auto-discovery, dual LLM support (Claude/Gemini), streaming responses, and smart follow-ups

* **📊 Admin Dashboard**: Vue.js + Vuetify interface with real-time analytics, settings management, and secure authentication

* **🖥️ Interactive Terminal**: Draggable terminal for site navigation with command-line interface

* **🎨 Smart Gallery**: Illustrations with fuzzy search and parallax effects

* **📝 Blog & Resume**: MDX-powered blog and dynamic resume with PDF download

---

## Technology Stack

### Frontend
* **Astro** - Static site generation with component islands
* **Vue.js** - Interactive components (chatbot, terminal)
* **Nanostores** - Global state management

### Backend
* **FastAPI** - Async API with unified smart retriever
* **SQLite** - Query logging and admin data
* **LangChain** - RAG pipeline with smart routing
* **ChromaDB** - Vector database for semantic search

### AI Models
* **Claude 3.5 Sonnet** (primary) + **Gemini 1.5 Flash** (fallback)
* **GoogleGenerativeAI** embeddings

### Admin Dashboard
* **Vue.js 3 + Vuetify 3** - Material Design UI
* **Pinia** - State management
* **Chart.js** - Data visualization

---

## Project Structure

```text
├── src/                    # Astro frontend
│   ├── components/         # Vue components (ChatBot, Terminal)
│   ├── pages/             # Routes (index, blog, resume)
│   └── stores/            # Nanostores state
├── backend/               # FastAPI backend
│   ├── core/              # Business logic (unified_retriever, config)
│   ├── knowledge/         # Auto-indexed content (.md, .pdf, .json)
│   ├── routes/            # API endpoints
│   └── logs/              # SQLite databases
├── admin/frontend/        # Vue.js admin dashboard
│   └── src/               # Components, views, stores
├── tests/                 # Unit, integration, e2e tests
└── Makefile               # Development commands
```

## Quick Start

```bash
# Development
npm run dev                # Frontend
npm run backend:dev        # Backend
npm run admin:frontend     # Admin dashboard

# Code Quality
make lint-fix             # Format code
pytest -m unit           # Run tests
```

## Smart Retriever (Zero Configuration!)

**Just drop content files and go!**

1. **Add content**: Drop `.md`, `.pdf`, `.json` files in `backend/knowledge/` or `public/`
2. **Restart backend**: Content automatically indexed and searchable
3. **No config needed**: System auto-detects content types and routes queries intelligently

### Key Features
- **Auto-discovery**: Finds all content automatically
- **Smart routing**: Understands query intent (technical, personal, creative)
- **Semantic search**: ChromaDB with intelligent filtering
- **Multi-level caching**: Fast repeated queries

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Optional
FORCE_REBUILD_DATA=true    # Force rebuild vector indices
```

## Admin Dashboard

* **Frontend**: `npm run admin:frontend` (Vue.js + Vuetify)
* **Backend**: Integrated at http://localhost:8000
* **Authentication**: Session-based with secure cookies
* **Features**: Analytics, settings, API key management

---

## License

This project is a personal portfolio and is not licensed for reuse.
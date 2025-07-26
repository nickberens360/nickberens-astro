# Nick Berens - Portfolio Website

This is the repository for my personal portfolio website, a project that showcases my skills in frontend development, UI/UX, AI integration, and backend services. It's more than just a portfolio; it's a playground for experimenting with modern web technologies.

---

## Features

This website is packed with interactive and dynamic features designed to provide an engaging user experience:

* **🤖 AI-Powered Chatbot ("nick.AI")**: A fully functional chatbot built with a Retrieval-Augmented Generation (RAG) system. It can answer questions about my skills, experience, and illustrations based on a structured knowledge base. It features:
    * Dual LLM support with fallback (Anthropic Claude & Google Gemini).
    * Streaming responses for real-time interaction.
    * Follow-up question suggestions to guide the conversation.
    * Image search capabilities for my illustration work.

* **🖥️ Interactive Terminal**: A draggable, resizable, and minimizable terminal window that allows users to navigate the site and access information using command-line instructions. It includes commands like `git log` and `git graph` to fetch real-time data from the GitHub repository.

* **🎨 Illustrations Gallery**: A dynamic gallery page showcasing my artwork with engaging parallax scroll effects.

* **📝 MDX-Powered Blog**: A blog that leverages MDX to allow for the seamless integration of Vue components directly within Markdown content, creating rich and interactive articles.

* **📄 Dynamic Resume Page**: An online resume page with the option to download a PDF version.

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

* **Framework**: **Python** with **FastAPI** to create a robust and high-performance API backend.
* **Asynchronous Processing**: The backend is fully asynchronous to handle multiple concurrent requests efficiently.

### AI & Machine Learning

* **Core AI Logic**: **LangChain** for building the RAG pipeline, managing prompts, and orchestrating LLM interactions.
* **Language Models (LLMs)**:
    * **Anthropic Claude 3.5 Sonnet** as the primary model.
    * **Google Gemini 1.5 Flash** as the fallback model.
* **Embeddings**: **GoogleGenerativeAIEmbeddings** for creating vector representations of the source data.
* **Vector Database**: **ChromaDB** for efficient similarity searches and retrieval of relevant information for the RAG system.

---

## Project Structure

The project is organized into two main parts: the Astro frontend and the FastAPI backend.

```text
/
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── README.md                        # Project documentation
├── astro.config.mjs                 # Astro configuration
├── package.json                     # Node.js dependencies and scripts
├── package-lock.json                # Locked dependency versions
├── requirements.txt                 # Python dependencies
├── tsconfig.json                    # TypeScript configuration
├── server.log                       # Server log file
├── public/                          # Static assets and knowledge base
│   ├── favicon.svg                  # Site favicon
│   ├── Nick_Berens_Resume.pdf       # PDF resume
│   ├── about-nick-berens.md         # About content
│   ├── unified_data.json            # AI knowledge base
│   ├── illustrations.json           # Illustration metadata
│   └── illustrations/               # Illustration image files
├── src/                             # Frontend source code
│   ├── assets/                      # Static assets
│   │   └── images/                  # Image assets
│   ├── components/                  # Reusable Vue components
│   │   ├── blog/                    # Blog-specific components
│   │   ├── ChatBot.vue              # Main chatbot component
│   │   ├── ChatInput.vue            # Chat input interface
│   │   ├── ChatMessageList.vue      # Message display
│   │   ├── CustomLMGTFY.vue         # Terminal component
│   │   ├── SiteHeader.vue           # Site navigation
│   │   ├── SiteFooter.vue           # Site footer
│   │   └── ...                      # Other UI components
│   ├── composables/                 # Vue composables
│   ├── config/                      # Configuration files
│   ├── content/                     # Content management
│   │   └── blog/                    # Blog posts
│   ├── layouts/                     # Astro layout components
│   ├── lib/                         # Utility libraries
│   ├── pages/                       # Astro pages (routes)
│   │   ├── blog/                    # Blog page routes
│   │   ├── index.astro              # Homepage
│   │   ├── illustrations.astro      # Gallery page
│   │   ├── resume.astro             # Resume page
│   │   └── nick-ai.astro            # Chatbot page
│   ├── plugins/                     # Astro plugins
│   ├── stores/                      # State management (Nanostores)
│   ├── styles/                      # Global CSS styles
│   └── utils/                       # Utility functions
├── backend/                         # FastAPI backend
│   ├── main.py                      # FastAPI application entrypoint
│   ├── core/                        # Core backend logic
│   │   ├── __init__.py              # Package initialization
│   │   ├── config.py                # Backend configuration
│   │   ├── data_loader.py           # Data loading utilities
│   │   ├── llm_chain.py             # LangChain LLM integration
│   │   ├── query_router.py          # Query routing logic
│   │   ├── followup_service.py      # Follow-up suggestions
│   │   ├── illustration_service.py  # Image search service
│   │   └── response_service.py      # Response formatting
│   └── scripts/                     # Utility scripts
├── tests/                           # Test suite
│   ├── integration/                 # Integration tests
│   │   ├── test_vector_retrieval.py # RAG system integration tests
│   │   ├── test_search.py           # Search functionality tests
│   │   └── test_large_input.py      # Input handling tests
│   ├── test_config.py               # Unit tests for config module
│   ├── test_data_loader.py          # Unit tests for data loader
│   ├── test_llm_chain.py            # Unit tests for LLM chain
│   ├── test_query_router.py         # Unit tests for query router
│   ├── test_followup_service.py     # Unit tests for followup service
│   ├── test_illustration_service.py # Unit tests for illustration service
│   └── test_response_service.py     # Unit tests for response service
└── pytest.ini                      # Pytest configuration
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
├── public/              # Static assets and the unified_data.json knowledge base
├── src/
│   ├── components/      # Reusable Vue components
│   ├── layouts/         # Astro layout components
│   └── pages/           # Astro pages (routes)
├── backend/
│   ├── core/            # Core backend logic (LLM chains, data loading, etc.)
│   └── main.py          # FastAPI application entrypoint
└── package.json
# ---- Builder Stage ----
FROM python:3.11-slim as builder

# Install build-essential tools for compiling Python packages, then install poetry
# This prevents build failures for packages that don't have pre-compiled wheels
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/* && pip install poetry

WORKDIR /app

# Copy only files needed for dependency installation
COPY poetry.lock pyproject.toml ./

# Configure poetry to create the virtualenv in the project's root
# Then, install dependencies from the lock file
RUN poetry config virtualenvs.in-project true && poetry install --no-root --without dev

# ---- Final Stage ----
FROM python:3.11-slim

# Create a non-root user and group for security
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --chown=app:app --from=builder /app/.venv /app/.venv

# Activate the virtual environment for all subsequent commands
ENV PATH="/app/.venv/bin:$PATH"

# [cite_start]Set environment variables to disable tokenizer warnings and fix permissions [cite: 2]
ENV TOKENIZERS_PARALLELISM=false
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app public/ ./public/

# Create cache directories for RAG system and HuggingFace
RUN mkdir -p .rag_cache .cache/huggingface && chown -R app:app .rag_cache .cache

# Set home directory to the app's workdir to ensure writability
ENV HOME=/app

USER app

# Expose port
EXPOSE 8000

# Update healthcheck to use the correct endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production-ready command (no reload)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
# ---- Builder Stage ----
FROM python:3.11-slim as builder

# Install build-essential tools for compiling Python packages, then install poetry
# This prevents build failures for packages that don't have pre-compiled wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/* \
    && pip install poetry

WORKDIR /app

# Copy only files needed for dependency installation
COPY poetry.lock pyproject.toml ./

# Configure poetry to create the virtualenv in the project's root
# Then, install dependencies only (not the project itself)
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root --no-cache && \
    # Clean up Python bytecode and cache files to reduce size
    find /app/.venv -name "*.pyc" -delete && \
    find /app/.venv -name "__pycache__" -type d -exec rm -rf {} + || true

# ---- Final Stage ----
FROM python:3.11-slim

# Create a non-root user and group for security
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --chown=app:app --from=builder /app/.venv /app/.venv

# Activate the virtual environment for all subsequent commands
ENV PATH="/app/.venv/bin:$PATH"

# Set environment variables to disable tokenizer warnings and configure caching
ENV TOKENIZERS_PARALLELISM=false \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HOME=/app

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app public/ ./public/

# Create cache directories for RAG system and HuggingFace
RUN mkdir -p .rag_cache .cache/huggingface && \
    chown -R app:app .rag_cache .cache

USER app

# Expose port
EXPOSE 8000

# Optional: Add healthcheck (uncomment if you have a /health endpoint)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production-ready command (no reload)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
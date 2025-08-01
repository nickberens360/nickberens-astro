# ---- Builder Stage ----
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python requirements
# This is done in a separate step to leverage Docker's layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Final Stage ----
FROM python:3.11-slim

# Create a non-root user and group for security
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy virtual environment from builder stage
COPY --chown=app:app --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set environment variables to disable tokenizer warnings and fix permissions
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
# ---- Builder Stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# System packages needed to build and run deps (lxml, python-magic, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python dependencies early for better caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# ---- Runtime (same image; we already built wheels in venv) ----

RUN groupadd --system app && useradd --system --no-create-home --gid app app
USER app

WORKDIR /app

# Copy application code (after deps for better cache hit rate)
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app public/ ./public/

# Expose port
EXPOSE 8000

# Healthcheck to verify the app is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/status')" || exit 1

# Production command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

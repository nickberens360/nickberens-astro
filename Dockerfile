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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Create a virtual environment to isolate dependencies
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python dependencies early for better caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Build admin frontend
COPY admin/frontend/package*.json /app/admin/frontend/
WORKDIR /app/admin/frontend
RUN npm ci

COPY admin/frontend/ /app/admin/frontend/
RUN npm run build

WORKDIR /app

# ---- Runtime Stage ----
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN groupadd --system app && useradd --system --no-create-home --gid app app && \
    mkdir -p /home/app && chown app:app /home/app

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app public/ ./public/

# Copy built admin frontend from builder stage
COPY --from=builder --chown=app:app /app/admin/frontend/dist ./admin/frontend/dist

# Create logs directory with proper permissions for the app user
RUN mkdir -p /app/backend/logs && chown -R app:app /app/backend/logs

# Create /data directory for Railway volume mounting (must be accessible by app user)
RUN mkdir -p /data && chown -R app:app /data

# Create a startup script to ensure volume permissions are correct
# Using command group for better readability and maintainability
RUN { \
        echo '#!/bin/bash'; \
        echo 'set -e'; \
        echo ''; \
        echo '# Fix volume permissions if needed'; \
        echo 'if [ -d "/data" ] && [ "$(stat -c %U /data 2>/dev/null)" != "app" ]; then'; \
        echo '    echo "Fixing /data directory permissions..."'; \
        echo '    chown -R app:app /data'; \
        echo 'else'; \
        echo '    echo "/data permissions already correct or directory not found"'; \
        echo 'fi'; \
        echo ''; \
        echo '# Execute the main command'; \
        echo 'exec "$@"'; \
    } > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Switch to app user for runtime
USER app

# Expose port
EXPOSE 8000

# Healthcheck to verify the app is running - use PORT env var if set
# Longer start period and timeout for ChromaDB initialization and content indexing
HEALTHCHECK --interval=60s --timeout=15s --start-period=120s --retries=3 \
  CMD python3 -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/health')" || exit 1

# Set entrypoint to fix permissions on startup
ENTRYPOINT ["/entrypoint.sh"]

# Production command - use PORT env var if provided (Railway sets this)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

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
RUN npm ci --only=production

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
RUN mkdir -p /data/logs && chown -R app:app /data

USER app

# Expose port
EXPOSE 8000

# Healthcheck to verify the app is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production command - use PORT env var if provided (Railway sets this)
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

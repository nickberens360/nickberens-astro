# ---- Builder Stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# System packages needed for building dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Final Stage ----
FROM python:3.11-slim

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -ms /bin/bash app

WORKDIR /app

# Copy virtual environment from builder stage
COPY --chown=app:app --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app public/ ./public/

# Activate virtual environment and set user
ENV PATH="/opt/venv/bin:$PATH"
USER app

# Expose port
EXPOSE 8000

# Healthcheck to verify the app is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/status')" || exit 1

# Production command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
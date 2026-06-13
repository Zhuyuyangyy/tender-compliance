# ─── Build stage ────────────────────────────────────────────────────
FROM python:3.12-slim AS base

LABEL maintainer="ZYY Project"
LABEL description="Tender Compliance - Intelligent bidding document compliance analysis"
LABEL version="1.0.0"

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TENDER_DB_PATH=/app/data/tender_compliance.db

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (separate layer for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY tests/ ./tests/

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8012

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8012"]

# Multi-stage Dockerfile for RAMP Backend
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for layer caching
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy source code and config
COPY src/ ./src/
COPY tests/ ./tests/

# Install ramp package in editable mode
RUN pip install --no-cache-dir -e .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "ramp.main:app", "--host", "0.0.0.0", "--port", "8000"]

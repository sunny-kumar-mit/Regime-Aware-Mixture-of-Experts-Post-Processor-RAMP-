# ==============================================================================
# RAMP — Regime-Aware Mixture-of-Experts Post-Processor (SIH26080)
# Multi-Stage Production Dockerfile for Render Web Service Deployment
# Build Context: Repository ROOT (.)
# Target Architecture: Single Container (Nginx :$PORT -> React SPA + FastAPI Uvicorn)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Frontend SPA Builder (Node 20 Alpine)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Install dependencies deterministically
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build production SPA bundle
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Backend + Nginx Reverse Proxy (Python 3.11 Slim)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Set production environment flags
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app:/app/backend/src" \
    APP_ENV="production" \
    DEBUG="false" \
    LOG_LEVEL="INFO" \
    RAMP_DATA_MODE="SYNTHETIC_DEMO" \
    RAMP_DATA_ROOT="/app/data" \
    RAMP_CONFIG_PATH="/app/config/model_config.yaml" \
    STORAGE_MODE="LOCAL_FALLBACK" \
    PORT=8080

WORKDIR /app

# Install system dependencies: Nginx, envsubst (gettext-base), curl, and OpenMP (libgomp1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Clean default Nginx virtual hosts
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

# Install deterministic production Python dependencies
COPY requirements.render.txt /app/requirements.render.txt
RUN pip install --no-cache-dir -r requirements.render.txt

# Install backend package
COPY backend/ /app/backend/
RUN pip install --no-cache-dir -e /app/backend

# Copy application source code, configurations, and test fixtures
COPY ml/ /app/ml/
COPY config/ /app/config/
COPY configs/ /app/configs/
COPY data/ /app/data/
COPY tests/ /app/tests/
COPY deployment/ /app/deployment/

# Copy compiled React SPA from Stage 1 into Nginx HTML root
COPY --from=frontend-builder /build/frontend/dist /usr/share/nginx/html

# Copy Nginx configuration template
COPY deployment/render/nginx.conf.template /etc/nginx/conf.d/ramp.conf.template

# Ensure startup script is executable
RUN chmod +x /app/deployment/render/start.sh

# Render exposes dynamic $PORT
EXPOSE 8080

# Health check on Render
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/live || exit 1

ENTRYPOINT ["/bin/bash"]
CMD ["/app/deployment/render/start.sh"]

# Professional Multi-stage Dockerfile for CapiAgentes Backend
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as base

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MPLCONFIGDIR=/app/tmp/mpl \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Create non-root user with specific UID/GID for security
RUN groupadd -g 1000 appgroup && \
    useradd -r -u 1000 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup ./src ./src
COPY --chown=appuser:appgroup ./ia_workspace ./ia_workspace
COPY --chown=appuser:appgroup ./database ./database
COPY --chown=appuser:appgroup ./.env.example ./.env

# Create logs directory according to architecture
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

# Build validation: ensure critical endpoints exist
RUN grep -n 'api_route("/api/command"' /app/src/api/main.py || (echo 'ERROR: api_route /api/command not found in main.py' && exit 1)

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/uploads /app/tmp /app/data && \
    chown -R appuser:appgroup /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Health check with improved robustness
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Start server directly bypassing uvicorn logging issues
CMD ["python", "src/api/main.py"]

# Multi-stage build for development
FROM base as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy

USER appuser

# Override CMD for development with auto-reload
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# Multi-stage build for testing
FROM development as testing

USER root

# Copy test files
COPY --chown=appuser:appgroup ./tests ./tests
COPY --chown=appuser:appgroup ./pytest.ini ./

USER appuser

# Run tests by default
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=src", "--cov-report=term-missing"]

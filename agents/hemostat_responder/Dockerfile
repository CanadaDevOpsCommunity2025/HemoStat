# Multi-stage build for HemoStat Responder Agent using UV

# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim as builder

WORKDIR /build

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Copy agents directory for local imports
COPY agents/ ./agents/

# Install dependencies with UV (agents extra includes docker SDK)
RUN uv sync --extra agents --no-dev

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy agents directory
COPY agents/ ./agents/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH=/app/.venv/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 hemostat && \
    chown -R hemostat:hemostat /app

USER hemostat

# Health check: verify Redis connectivity
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import redis; redis.Redis(host='redis').ping()" || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "agents.hemostat_responder.main"]

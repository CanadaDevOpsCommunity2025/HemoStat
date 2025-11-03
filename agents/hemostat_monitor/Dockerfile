# Multi-stage build for HemoStat Monitor Agent using UV
# Stage 1: Builder - Install dependencies with UV
FROM python:3.11-slim AS builder

WORKDIR /build

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY README.md pyproject.toml uv.lock ./
COPY agents/ ./agents/

# Set UV timeout for slow networks (HuggingFace dependencies can be large)
ENV UV_HTTP_TIMEOUT=1000

# Install dependencies using UV with agents extra group
# This includes docker==7.0.0 and all base dependencies
# BuildKit cache mount persists UV cache between builds for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra agents --no-dev

# Stage 2: Runtime - Minimal image with only runtime dependencies
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY agents/ /app/agents/

# Copy environment file (optional, for Docker Compose override)
COPY .env* /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 hemostat && \
    chown -R hemostat:hemostat /app

# Switch to non-root user
USER hemostat

# Health check - verify Redis connectivity
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import redis; redis.Redis(host='redis').ping()" || exit 1

# Run the monitor agent
ENTRYPOINT ["python", "-m", "agents.hemostat_monitor.main"]

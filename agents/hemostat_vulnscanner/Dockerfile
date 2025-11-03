# Multi-stage build for HemoStat Vulnerability Scanner Agent using UV
# Stage 1: Builder - Install dependencies with UV
FROM python:3.11-slim AS builder

WORKDIR /build

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY README.md pyproject.toml uv.lock ./
COPY agents/ ./agents/

# Set UV timeout for slow networks
ENV UV_HTTP_TIMEOUT=300

# Install dependencies using UV with agents extra group
# This includes requests==2.32.5 and all base dependencies
RUN uv sync --extra agents --no-dev

# Stage 2: Runtime - Minimal image with only runtime dependencies
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for curl (needed for health checks)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Run the vulnerability scanner agent
ENTRYPOINT ["python", "-m", "agents.hemostat_vulnscanner.main"]

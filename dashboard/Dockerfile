# Multi-stage build for HemoStat Dashboard using UV
# Stage 1: Builder - Install dependencies with UV
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Install build dependencies for pyarrow and other compiled packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration
COPY README.md pyproject.toml uv.lock* ./

# Copy source code
COPY agents/ ./agents/
COPY dashboard/ ./dashboard/

# Install dependencies with UV
# Create .venv at /app/.venv so shebangs are correct in runtime stage
RUN uv sync --extra dashboard --extra agents
RUN ls -la /app/.venv/bin/ && \
    /app/.venv/bin/streamlit --version || \
    (echo "ERROR: streamlit not installed!" && exit 1)

# Stage 2: Runtime - Minimal image with only runtime dependencies
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy virtual environment from builder (same path so shebangs work)
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY agents/ ./agents/
COPY dashboard/ ./dashboard/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH

# Expose Streamlit port
EXPOSE 8501

# Create non-root user for security
RUN useradd -m -u 1000 hemostat && \
    chown -R hemostat:hemostat /app

# Switch to non-root user
USER hemostat

# Health check using Python stdlib (curl not available in slim image)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit dashboard
ENTRYPOINT ["streamlit", "run", "dashboard/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=false"]

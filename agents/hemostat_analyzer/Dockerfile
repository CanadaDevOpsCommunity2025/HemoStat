# Multi-stage build for HemoStat Analyzer Agent using UV
# Stage 1: Builder - Install dependencies using UV
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /build

# Copy dependency files
COPY README.md pyproject.toml uv.lock* ./

# Copy agents directory for local imports
COPY agents/ ./agents/

# Set UV timeout for slow networks (HuggingFace dependencies can be large)
ENV UV_HTTP_TIMEOUT=1000

# Install dependencies with UV (agents group includes langchain, openai, anthropic)
# BuildKit cache mount persists UV cache between builds for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra agents --no-dev

# Stage 2: Runtime - Minimal image with installed packages
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy the UV-managed virtual environment from builder
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

# Switch to non-root user
USER hemostat

# Set entrypoint
ENTRYPOINT ["python", "-m", "agents.hemostat_analyzer.main"]

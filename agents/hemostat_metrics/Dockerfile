# Multi-stage Dockerfile for HemoStat Metrics Exporter Agent
# Uses UV for fast dependency management

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using UV (fast package manager)
RUN uv pip install --system --no-cache \
    redis==7.0.1 \
    python-dotenv==1.2.1 \
    python-json-logger==4.0.0 \
    prometheus-client==0.21.0

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY agents/ ./agents/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose Prometheus metrics port
EXPOSE 9090

# Run the metrics exporter agent
CMD ["python", "-m", "agents.hemostat_metrics.main"]

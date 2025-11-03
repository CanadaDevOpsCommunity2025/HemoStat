# Quick Start Guide

Get HemoStat up and running in minutes.

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- `uv` package manager

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/jondmarien/HemoStat.git
cd HemoStat
```

### 2. Configure Environment

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `OPENAI_API_KEY` - For GPT-4 analysis (optional, use Claude instead)
- `ANTHROPIC_API_KEY` - For Claude analysis (recommended)
- `SLACK_WEBHOOK_URL` - For Slack notifications (optional)

### 3. Install Dependencies

Install all dependencies including agents, dashboard, and dev tools:

```bash
uv sync --all-extras
```

Or just the core dependencies:

```bash
uv sync
```

### 4. Start Redis

Redis is required for all agents to communicate:

```bash
docker compose up -d redis
```

### 5. Run the System

Start all services (agents and dashboard):

```bash
docker compose up -d
```

View logs:

```bash
docker compose logs -f
```

View specific service logs:

```bash
docker compose logs -f monitor      # Monitor Agent
docker compose logs -f analyzer     # Analyzer Agent
docker compose logs -f responder    # Responder Agent
docker compose logs -f alert        # Alert Agent
docker compose logs -f dashboard    # Dashboard
docker compose logs -f metrics      # Prometheus metrics exporter
docker compose logs -f prometheus   # Time-series metrics database
docker compose logs -f grafana      # Metrics visualization dashboards
```

## Quick Test

### Verify System Status

Check that all services are running:

```bash
docker compose ps
```

You should see:
- `hemostat-redis` - Redis message broker
- `hemostat-monitor` - Container health monitoring
- `hemostat-analyzer` - AI-powered analysis
- `hemostat-responder` - Automated remediation
- `hemostat-alert` - Notification system
- `hemostat-metrics` - Prometheus metrics exporter
- `hemostat-prometheus` - Time-series metrics database
- `hemostat-grafana` - Metrics visualization dashboards
- `hemostat-dashboard` - Streamlit UI

### View the Dashboards

HemoStat provides two complementary dashboards:

**Streamlit Dashboard (Real-time Monitoring)**
- URL: http://localhost:8501
- Live event streaming and container status

**Grafana Dashboard (Historical Metrics)**
- URL: http://localhost:3000
- Username: `admin`, Password: `admin` (change on first login)
- Historical metrics, performance trends, and alerts
- Navigate to: Dashboards → HemoStat → HemoStat Overview

**Prometheus Query UI**
- URL: http://localhost:9091
- Direct metric queries and alert status

See the [Monitoring documentation](monitoring.md) for detailed information on metrics and dashboards.

### Run Demo Scenarios

Test the system with automated demo scenarios:

**Linux/macOS:**
```bash
./scripts/linux/demo_trigger_cpu_spike.sh
```

**Windows:**
```powershell
.\scripts\windows\demo_trigger_cpu_spike.ps1
```

## Next Steps

- **Monitoring**: Explore [Prometheus metrics and Grafana dashboards](monitoring.md) for observability
- **Architecture**: Learn about the [system architecture](architecture.md) and agent communication
- **API Reference**: Explore the [complete API documentation](api/index.rst) auto-generated from code docstrings
- **Deployment**: See [production deployment guides](deployment.md)
- **Troubleshooting**: Check [common issues and solutions](troubleshooting.md)
- **Development**: Start [contributing to the project](development.md)

## Stopping Services

Stop all services:

```bash
docker compose down
```

Stop and remove volumes (clean slate):

```bash
docker compose down -v
```

## Common Commands

```bash
# Rebuild a service after code changes
docker compose build analyzer --no-cache
docker compose up -d analyzer

# View real-time logs
docker compose logs -f

# Run agents locally (requires Redis running)
make monitor
make analyzer
make responder
make alert

# Run quality checks
make quality

# Run tests
make test
```

# HemoStat: Autonomous Container Health Monitoring System

HemoStat is a multi-agent system that autonomously monitors, analyzes, and remediates Docker container health issues using AI-powered decision making.

## Key Features

- **Real-time Monitoring**: Continuous health checks on Docker containers
- **Intelligent Analysis**: AI-powered root cause analysis using GPT-4 or Claude
- **Safe Remediation**: Automated container recovery with safety constraints and cooldown periods
- **Slack Alerts**: Real-time notifications for critical events
- **Live Dashboard**: Streamlit-based monitoring interface
- **Demo Scripts**: Automated scenarios for testing and hackathon presentations

## Documentation

Comprehensive documentation is available at **[https://quartz.chron0.tech/HemoStat/](https://quartz.chron0.tech/HemoStat/)**

The documentation includes:

- **Getting Started** - Installation and quickstart guide
- **Architecture** - System design and agent communication
- **API Reference** - **Auto-generated from code docstrings** (all classes, methods, parameters)
- **Deployment** - Production deployment guides
- **Troubleshooting** - Common issues and solutions
- **Development** - Contributing and code quality

### Building Docs Locally

```bash
# Install documentation dependencies
make docs-install
# or: uv sync --extra docs

# Build and serve locally
make docs-serve
# or: sphinx-build -b html docs/source docs && python -m http.server -d docs 8000

# View at http://localhost:8000
```

## Tech Stack

- **Python 3.11+**: Core language
- **Redis**: Pub/sub messaging and shared state management
- **Docker & Docker Compose**: Container orchestration
- **LangChain**: LLM orchestration for AI analysis
- **Streamlit**: Web-based dashboard
- **Sphinx**: Documentation generation with autodoc from docstrings

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    HemoStat Multi-Agent System              │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   Monitor    │  Detects container health issues
    │    Agent     │  (CPU, memory, disk, process status)
    └──────┬───────┘
           │ (health_events)
           ▼
    ┌──────────────┐
    │  Analyzer    │  Analyzes root causes using AI
    │    Agent     │  (GPT-4 or Claude)
    └──────┬───────┘
           │ (analysis_results)
           ▼
    ┌──────────────┐
    │  Responder   │  Executes safe remediation actions
    │    Agent     │  (restart, scale, cleanup)
    └──────┬───────┘
           │ (remediation_events)
           ▼
    ┌──────────────┐
    │    Alert     │  Sends notifications
    │    Agent     │  (Slack, email, webhooks)
    └──────────────┘

All agents communicate via Redis pub/sub and share state through Redis KV store
```

### Agent Roles

- **Monitor Agent**: Continuously polls container metrics and publishes health events
- **Analyzer Agent**: Consumes health events, performs AI-powered root cause analysis using GPT-4 or Claude, distinguishes real issues from false alarms with confidence scoring, and publishes remediation recommendations or false alarm notifications
- **Responder Agent**: Executes remediation actions (restart, scale, cleanup, exec) with comprehensive safety constraints including cooldown periods (1 hour default), circuit breakers (max 3 retries/hour), dry-run mode support, and audit logging for compliance
- **Alert Agent**: Sends notifications to external systems (Slack webhooks), stores events in Redis for dashboard consumption, provides comprehensive audit trail of all system actions, and implements event deduplication to prevent notification spam

All agents inherit from the shared `HemoStatAgent` base class, which provides Redis pub/sub primitives and state management.

## Demo & Testing

### Running Demo Scenarios

**Linux (Bash):**

```bash
# Start all services
docker-compose up -d

# Verify and run demos
./scripts/linux/verify_message_flow.sh
./scripts/linux/demo_trigger_cpu_spike.sh
```

**macOS (Zsh):**

```zsh
# Start all services
docker-compose up -d

# Verify and run demos
./scripts/macos/verify_message_flow.zsh
./scripts/macos/demo_trigger_cpu_spike.zsh
```

**Windows (PowerShell):**

```powershell
# Start all services
docker-compose up -d

# Verify and run demos
.\scripts\windows\verify_message_flow.ps1
.\scripts\windows\demo_trigger_cpu_spike.ps1
```

### Test Services

- **hemostat-test-api**: HTTP API with controllable resource usage (port 5001)
- **hemostat-test-worker**: Background worker with periodic spikes

See `scripts/README.md` for detailed documentation.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd HemoStat-test
   ```

2. **Copy environment template**

   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables** (especially API keys)

   ```bash
   # Edit .env and set:
   # - OPENAI_API_KEY (required for GPT-4 analysis)
   # - ANTHROPIC_API_KEY (required for Claude analysis)
   # - SLACK_WEBHOOK_URL (required for Slack notifications)
   # - RESPONDER_COOLDOWN_SECONDS (default: 3600 = 1 hour)
   # - RESPONDER_MAX_RETRIES_PER_HOUR (default: 3)
   # - RESPONDER_DRY_RUN (set to true for testing without actual remediation)
   # - ALERT_ENABLED (set to false to disable all notifications)
   # - Other optional settings
   
   # Get Slack webhook URL from: https://api.slack.com/messaging/webhooks
   # Note: If AI API keys are not set, the Analyzer Agent will fall back to rule-based analysis.
   ```

4. **Start Redis**

   ```bash
   docker-compose up -d redis
   ```

5. **Install Python dependencies with uv**

   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies from pyproject.toml
   uv sync
   ```

6. **Verify Redis connection**

   ```bash
   redis-cli ping
   # Should return: PONG
   ```

### Running Agents (Phase 2+) and Dashboard (Phase 3)

#### Running with Test Services

```bash
# Start all services including test-api and test-worker
docker-compose up -d

# Verify all services are running
docker-compose ps

# View logs for specific services
docker-compose logs -f test-api test-worker
```

#### Local Development (Auto-Detected Platform)

All agents and dashboard are available. The system automatically detects your OS and uses the appropriate Docker socket configuration.

```bash
# Terminal 1: Start Monitor Agent
uv run python -m agents.hemostat_monitor.main

# Terminal 2: Start Analyzer Agent
uv run python -m agents.hemostat_analyzer.main

# Terminal 3: Start Responder Agent
uv run python -m agents.hemostat_responder.main

# Terminal 4: Start Alert Agent
uv run python -m agents.hemostat_alert.main

# Terminal 5: Start Dashboard
uv run streamlit run dashboard/app.py
# Access at http://localhost:8501
```

#### Docker Compose (Recommended for Team Development)

The system automatically detects your platform and configures Docker sockets appropriately.

**On Windows (Docker Desktop):**

```bash
# Start all services with Windows Docker socket override
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d

# View logs
docker compose logs -f dashboard

# Access dashboard at http://localhost:8501
```

**On Linux:**

```bash
# Start all services with Linux Docker socket override
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d

# View logs
docker compose logs -f dashboard

# Access dashboard at http://localhost:8501
```

**On macOS:**

```bash
# Start all services with macOS Docker socket override
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d

# View logs
docker compose logs -f dashboard

# Access dashboard at http://localhost:8501
```

**Stop all services:**

```bash
docker compose down
```

#### Building & Rebuilding Services

When making code changes or updating environment variables, you need to rebuild the affected service(s). Always use the platform-specific compose files and env files:

**On Windows (Docker Desktop):**

```bash
# Rebuild a single service
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows build --no-cache

# Rebuild all services
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows build --no-cache

# Rebuild and restart a service
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d --build

# Rebuild and restart all services
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d --build
```

**On Linux:**

```bash
# Rebuild a single service
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux build --no-cache

# Rebuild all services
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux build --no-cache

# Rebuild and restart a service
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d --build 

# Rebuild and restart all services
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d --build
```

**On macOS:**

```bash
# Rebuild a single service 
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos build --no-cache

# Rebuild all services
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos build --no-cache

# Rebuild and restart a service
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d --build

# Rebuild and restart all services
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d --build
```

**Important Notes:**

- **`--env-file .env.docker.{platform}`** - Ensures API keys and platform-specific settings are loaded correctly
- **`-f docker-compose.yml -f docker-compose.{platform}.yml`** - Applies platform-specific Docker socket overrides (critical for container monitoring)
- **`--no-cache`** - Forces a fresh build, useful when dependencies or code changes need to be picked up
- **`--build`** - Rebuilds images before starting containers (shorthand for build + up)

#### Platform Detection

HemoStat automatically detects your operating system and configures the Docker daemon socket appropriately:

- **Windows**: Uses `npipe:////./pipe/docker_engine` (Docker Desktop named pipe)
- **Linux**: Uses `unix:///var/run/docker.sock` (Unix socket)
- **macOS**: Uses `unix:///var/run/docker.sock` (Unix socket)

When running inside Docker containers, the system uses `unix:///var/run/docker.sock` for all platforms (Docker Desktop on Windows maps the named pipe to this path inside containers).

You can override the auto-detected socket by setting the `DOCKER_HOST` environment variable if needed.

## Project Structure

```text
HemoStat-test/
├── agents/                          # Agent implementations
│   ├── __init__.py
│   ├── agent_base.py               # Base class for all agents
│   ├── hemostat_monitor/           # Monitor agent ✅
│   ├── hemostat_analyzer/          # Analyzer agent ✅
│   ├── hemostat_responder/         # Responder agent ✅
│   └── hemostat_alert/             # Alert agent ✅
├── dashboard/                       # Streamlit UI (Phase 3) ✅
├── scripts/                         # Demo and test scripts ✅
│   ├── windows/                     # PowerShell scripts (.ps1)
│   ├── macos/                       # Zsh scripts (.zsh)
│   ├── linux/                       # Bash scripts (.sh)
│   ├── test_api.py                  # Test API service
│   ├── test_worker.py               # Test worker service
│   └── README.md                    # Scripts documentation
├── tests/                           # Test suite (Phase 5)
├── docs/                            # Detailed documentation
├── docker-compose.yml               # Docker Compose configuration
├── .env.example                     # Environment template
├── .env                             # Local environment (gitignored)
├── pyproject.toml                   # Python project configuration
└── README.md                        # This file
```

## Development

### Phase 1: Infrastructure Setup ✅ (Complete)

- Redis service with health checks
- Base agent class with pub/sub primitives
- Environment configuration
- Docker Compose orchestration

### Phase 2: Agent Implementations ✅ (Complete)

- ✅ Monitor Agent: Container health polling
- ✅ Analyzer Agent: AI-powered root cause analysis
- ✅ Responder Agent: Safe remediation execution
- ✅ Alert Agent: Multi-channel notifications

### Phase 3: Dashboard & Visualization ✅ (Complete)

- ✅ Streamlit-based monitoring UI
- ✅ Real-time event streaming with auto-refresh
- ✅ Container health grid and metrics cards
- ✅ Active issues feed and remediation history
- ✅ Event timeline with filtering
- ✅ Docker Compose integration

### Phase 4: Integration Testing & Demo Infrastructure ✅ (Complete)

- ✅ Demo scripts and test services
- ✅ End-to-end message flow verification
- ✅ Test API with controllable resource usage
- ✅ Test worker with periodic spikes

### Phase 5: Testing & Optimization

- ⏳ Unit and integration tests
- ⏳ Performance profiling
- ⏳ Production deployment guide

## Documentation Links

**Live Documentation:** [https://quartz.chron0.tech/HemoStat/](https://quartz.chron0.tech/HemoStat/)

- **[Getting Started](https://quartz.chron0.tech/HemoStat/quickstart.html)** - Installation and quickstart guide
- **[Architecture](https://quartz.chron0.tech/HemoStat/architecture.html)** - Detailed system design and data flow ([source](docs/ARCHITECTURE.md))
- **[API Reference](https://quartz.chron0.tech/HemoStat/api/index.html)** - Auto-generated from code docstrings
- **[API Protocol](https://quartz.chron0.tech/HemoStat/api_protocol.html)** - Redis channel schemas and event formats ([source](docs/API_PROTOCOL.md))
- **[Deployment](https://quartz.chron0.tech/HemoStat/deployment.html)** - Production deployment guide ([source](docs/DEPLOYMENT.md))
- **[Troubleshooting](https://quartz.chron0.tech/HemoStat/troubleshooting.html)** - Common issues and solutions ([source](docs/TROUBLESHOOTING.md))
- **[Development](https://quartz.chron0.tech/HemoStat/development.html)** - Contributing and code quality ([source](docs/WARP.md))

## License

MIT License - See LICENSE file for details

## Team

**Event**: Canada DevOps Community of Practice Hackathon Toronto - Team 1

**Team Mentor**: Kanwarpreet Singh Khurana

**Team Lead**: Jonathan Marien

**Team Members**: Imran Yafith, Adam Shaldam, Seyon Sri, Audrey Man

---

*HemoStat is building a multi-agent container health monitoring system. Phase 1 infrastructure complete, Phase 2 all four agents (Monitor/Analyzer/Responder/Alert) implemented, Phase 3 Streamlit dashboard complete.*

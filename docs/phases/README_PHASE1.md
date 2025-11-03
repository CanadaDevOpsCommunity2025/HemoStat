# HemoStat: Autonomous Container Health Monitoring System

HemoStat is a multi-agent system that autonomously monitors, analyzes, and remediates Docker container health issues using AI-powered decision making.

## Key Features

- **Real-time Monitoring**: Continuous health checks on Docker containers
- **Intelligent Analysis**: AI-powered root cause analysis using GPT-4 or Claude
- **Safe Remediation**: Automated container recovery with safety constraints and cooldown periods
- **Slack Alerts**: Real-time notifications for critical events
- **Live Dashboard**: Streamlit-based monitoring interface

## Tech Stack

- **Python 3.11+**: Core language
- **Redis**: Pub/sub messaging and shared state management
- **Docker & Docker Compose**: Container orchestration
- **LangChain**: LLM orchestration for AI analysis
- **Streamlit**: Web-based dashboard

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
- **Analyzer Agent**: Consumes health events, performs AI analysis, and suggests remediation
- **Responder Agent**: Executes remediation actions with safety constraints and cooldowns
- **Alert Agent**: Sends notifications to external systems (Slack, email, etc.)

All agents inherit from the shared `HemoStatAgent` base class, which provides Redis pub/sub primitives and state management.

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
   # - OPENAI_API_KEY (for Analyzer agent)
   # - SLACK_WEBHOOK_URL (for Alert agent)
   # - Other optional settings
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

### Running Agents (Phase 2+)

Once agent implementations are added:

```bash
# Terminal 1: Start Monitor Agent
python -m agents.hemostat_monitor.main

# Terminal 2: Start Analyzer Agent
python -m agents.hemostat_analyzer.main

# Terminal 3: Start Responder Agent
python -m agents.hemostat_responder.main

# Terminal 4: Start Alert Agent
python -m agents.hemostat_alert.main

# Terminal 5: Start Dashboard
streamlit run dashboard/app.py
```

## Project Structure

```text
HemoStat-test/
├── agents/                          # Agent implementations
│   ├── __init__.py
│   ├── agent_base.py               # Base class for all agents
│   ├── hemostat_monitor/           # Monitor agent (Phase 2)
│   ├── hemostat_analyzer/          # Analyzer agent (Phase 2)
│   ├── hemostat_responder/         # Responder agent (Phase 2)
│   └── hemostat_alert/             # Alert agent (Phase 2)
├── dashboard/                       # Streamlit UI (Phase 3)
├── scripts/                         # Demo and test scripts (Phase 3)
├── tests/                           # Test suite (Phase 4)
├── docs/                            # Detailed documentation
├── docker-compose.yml               # Docker Compose configuration
├── .env.example                     # Environment template
├── .env                             # Local environment (gitignored)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Development

### Phase 1: Infrastructure Setup ✅ (Current)

- Redis service with health checks
- Base agent class with pub/sub primitives
- Environment configuration
- Docker Compose orchestration

### Phase 2: Agent Implementations (In Progress)

- Monitor Agent: Container health polling
- Analyzer Agent: AI-powered root cause analysis
- Responder Agent: Safe remediation execution
- Alert Agent: Multi-channel notifications

### Phase 3: Dashboard & Visualization

- Streamlit-based monitoring UI
- Real-time event streaming
- Historical analytics

### Phase 4: Testing & Optimization

- Unit and integration tests
- Performance profiling
- Production deployment guide


## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed system design and data flow (Phase 2)
- **[API_PROTOCOL.md](docs/API_PROTOCOL.md)** - Redis channel schemas and event formats (Phase 2)
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide (Phase 3)
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions (Phase 3)

## License

MIT License - See LICENSE file for details

## Team

**Team Lead**: Jonathan Marien

**Team Members**: Imran Yafith, Adam Shaldam, Seyon Sri, Audrey Man

**Team Mentor**: Kanwarpreet Singh Khurana

---

**Event**: Canada DevOps Community of Practice Hackathon Toronto - Team 1

# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

HemoStat is an **Autonomous Container Health Monitoring System** - a multi-agent system that autonomously monitors, analyzes, and remediates Docker container health issues using AI-powered decision making. The system uses Redis for pub/sub messaging between agents and shared state management.

## Quick Commands

### Setup & Environment
```bash
# Install dependencies using uv (fast package manager)
uv sync

# Install all optional dependencies (agents, dashboard, dev tools)
uv sync --all-extras

# Load environment configuration (copy from template)
cp .env.example .env
# Then edit .env with required API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL)
```

### Running Services
```bash
# Start Redis (required for all agents)
docker-compose up -d redis

# Start all agents and Redis together
docker-compose up -d

# View logs for a specific service
docker-compose logs -f monitor    # or analyzer, responder, alert
docker-compose logs -f             # all services

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Running Individual Agents Locally
```bash
# Using make (preferred):
make monitor
make analyzer
make responder
make alert

# Or directly:
python -m agents.hemostat_monitor.main
python -m agents.hemostat_analyzer.main
python -m agents.hemostat_responder.main
python -m agents.hemostat_alert.main
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_monitor.py -v

# Run single test
pytest tests/test_monitor.py::TestMonitorAgent::test_cpu_threshold -v

# Run with coverage report
pytest --cov=agents --cov-report=html
# View report at htmlcov/index.html
```

### Code Quality
```bash
# Using make (preferred):
make format              # Format code with ruff
make lint               # Lint code with auto-fix
make typecheck          # Run type checker (ty)
make quality            # Run all quality checks

# Or manually:
ruff format
ruff check --fix
ty check

# Install pre-commit hooks (optional - runs checks on git commit)
pre-commit install
```

## Architecture & Key Concepts

### Multi-Agent Message Flow
HemoStat uses a **pub/sub architecture** with four specialized agents communicating via Redis:

1. **Monitor Agent** → Continuously polls container metrics (CPU, memory, disk, process status)
2. **Analyzer Agent** ← Receives health events, performs AI-powered root cause analysis using GPT-4 or Claude
3. **Responder Agent** ← Receives remediation recommendations, executes safe container actions (restart, scale, cleanup)
4. **Alert Agent** ← Receives remediation events, sends Slack notifications and stores event history

All agents inherit from `HemoStatAgent` base class (`agents/agent_base.py`) which provides:
- Redis pub/sub communication primitives (`publish_event`, `subscribe_to_channel`)
- Shared state management (`get_shared_state`, `set_shared_state`)
- Graceful shutdown handling and connection retry logic with exponential backoff

### Redis Channel Schema
```
hemostat:events:health       → Monitor publishes container health events
hemostat:events:analysis     → Analyzer publishes root cause analysis results
hemostat:events:remediation  → Responder publishes remediation action results
hemostat:events:alert        → Alert Agent publishes notifications sent
hemostat:state:*             → Shared state (agent timestamps, cooldown periods, etc.)
```

### Key Design Patterns

**Safety Constraints (Responder Agent)**
- **Cooldown Period**: 1 hour default between remediation attempts per container (configurable via `RESPONDER_COOLDOWN_SECONDS`)
- **Circuit Breaker**: Max 3 remediation attempts per hour (configurable via `RESPONDER_MAX_RETRIES_PER_HOUR`)
- **Dry-run Mode**: Set `RESPONDER_DRY_RUN=true` to test without actual container modifications
- **Audit Logging**: All remediation actions are logged for compliance

**AI Fallback Logic (Analyzer Agent)**
- If API keys present and `AI_FALLBACK_ENABLED=true`: Uses GPT-4 or Claude for analysis
- On AI failure: Falls back to rule-based analysis
- Confidence scoring (0.0-1.0) determines if remediation should be triggered (threshold: `ANALYZER_CONFIDENCE_THRESHOLD`)
- False alarm detection to prevent unnecessary remediation

**Slack Integration & Event Deduplication (Alert Agent)**
- Event deduplication cache (TTL: 60s default) prevents duplicate Slack notifications
- Event history stored in Redis with TTL (1 hour default) for dashboard consumption
- Webhook-based notifications to Slack channels

## Project Structure

```
HemoStat-test/
├── agents/                          # All agent implementations
│   ├── __init__.py
│   ├── agent_base.py               # Base class: Redis pub/sub + state mgmt
│   │
│   ├── hemostat_monitor/           # Phase 2 ✅ Container health polling
│   │   ├── main.py                 # Entry point
│   │   ├── monitor.py              # Monitor implementation
│   │   └── Dockerfile
│   │
│   ├── hemostat_analyzer/          # Phase 2 ✅ AI-powered analysis
│   │   ├── main.py                 # Entry point
│   │   ├── analyzer.py             # Analyzer implementation
│   │   └── Dockerfile
│   │
│   ├── hemostat_responder/         # Phase 2 ✅ Safe remediation
│   │   ├── main.py                 # Entry point
│   │   ├── responder.py            # Responder implementation
│   │   └── Dockerfile
│   │
│   └── hemostat_alert/             # Phase 2 ✅ Notifications & history
│       ├── main.py                 # Entry point
│       ├── alert.py                # Alert implementation
│       └── Dockerfile
│
├── dashboard/                       # Phase 3 (Streamlit UI - planned)
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_PROTOCOL.md
│   └── DEPLOYMENT.md
├── tests/                           # Phase 4 (pytest suite - planned)
├── docker-compose.yml               # Orchestrates all services
├── pyproject.toml                   # Python project config (uv)
├── .env.example                     # Environment template
└── README.md                        # Full project documentation
```

## Environment Configuration

Key variables in `.env.example`:

**Redis**
- `REDIS_HOST`: Redis server (default: `redis` for Docker Compose, `localhost` for local dev)
- `REDIS_PORT`: Port (default: 6379)

**Monitoring Thresholds (Monitor Agent)**
- `AGENT_POLL_INTERVAL`: Health check frequency (default: 30s)
- `THRESHOLD_CPU_PERCENT`: Alert when CPU > 85%
- `THRESHOLD_MEMORY_PERCENT`: Alert when memory > 80%

**Safety Settings (Responder Agent)**
- `RESPONDER_COOLDOWN_SECONDS`: Min time between remediation (default: 3600 = 1 hour)
- `RESPONDER_MAX_RETRIES_PER_HOUR`: Circuit breaker limit (default: 3)
- `RESPONDER_DRY_RUN`: Set to `true` for testing without actual changes

**AI Configuration (Analyzer Agent)**
- `OPENAI_API_KEY`: Required for GPT-4 analysis
- `ANTHROPIC_API_KEY`: Required for Claude analysis
- `AI_MODEL`: Which model to use (default: `gpt-4`)
- `ANALYZER_CONFIDENCE_THRESHOLD`: Min confidence for remediation (default: 0.7)

**Alerts (Alert Agent)**
- `SLACK_WEBHOOK_URL`: Slack incoming webhook (get from https://api.slack.com/messaging/webhooks)
- `ALERT_ENABLED`: Master switch for all notifications

## Development Workflow

### Adding a New Feature

1. **Identify the agent** that should handle it (Monitor, Analyzer, Responder, or Alert)
2. **Understand the message flow**: Check what events the agent subscribes to and what it publishes
3. **Reference `agent_base.py`**: All agents use `publish_event()` and `subscribe_to_channel()` primitives
4. **Test with dry-run mode**: Use `RESPONDER_DRY_RUN=true` to test remediation logic without side effects
5. **Add to Redis channel schema** documentation if introducing new event types

### Adding a New Remediation Action

1. Implement in `agents/hemostat_responder/responder.py`
2. Apply safety constraints: cooldown period, max retries circuit breaker, audit logging
3. Test with `RESPONDER_DRY_RUN=true` first
4. Update documentation about the new action

### AI Provider Additions

1. Add new LLM provider to `agents/hemostat_analyzer/analyzer.py`
2. Implement fallback to rule-based analysis on provider failure
3. Set confidence scores appropriately for the new provider
4. Test with both API keys present and with fallback

## Debugging

**Agent Connection Issues**
- Check Redis is running: `redis-cli ping` (should return `PONG`)
- Verify `REDIS_HOST` and `REDIS_PORT` in `.env`
- Check logs for connection retry messages (exponential backoff: 1s, 2s, 4s)

**Message Flow Issues**
- Monitor Redis channels: `redis-cli SUBSCRIBE 'hemostat:events:*'`
- Monitor shared state: `redis-cli KEYS 'hemostat:state:*'`
- Check agent logs for message serialization/deserialization errors

**AI Analysis Failures**
- Verify API keys are set if using GPT-4 or Claude
- Set `AI_FALLBACK_ENABLED=true` to use rule-based analysis as backup
- Check agent logs for provider-specific errors

**Remediation Not Triggering**
- Check confidence threshold: `ANALYZER_CONFIDENCE_THRESHOLD` (default: 0.7)
- Verify cooldown period hasn't blocked action: Check Redis key `hemostat:state:responder:last_action:{container_id}`
- Set `RESPONDER_DRY_RUN=false` to actually execute (default is `false`)

## Phase Roadmap

- ✅ **Phase 1**: Infrastructure (Redis, base agent class, Docker Compose)
- ✅ **Phase 2**: All four agents (Monitor, Analyzer, Responder, Alert)
- ⏳ **Phase 3**: Streamlit dashboard with real-time event streaming
- ⏳ **Phase 4**: Comprehensive test suite and production deployment guide

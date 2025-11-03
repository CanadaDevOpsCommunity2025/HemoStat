# HemoStat Quick Start Guide

Get HemoStat up and running in 5 minutes. This guide is for hackathon judges, new team members, and anyone wanting to quickly see HemoStat in action.

## Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose (included with Docker Desktop)
- Git (for cloning repository)
- curl (usually pre-installed)
- Web browser (for Dashboard)

## 5-Minute Setup

### Step 1: Clone and Configure (1 minute)

```bash
# Clone repository
git clone <repository-url>
cd HemoStat-test

# Copy environment template
cp .env.example .env

# Optional: Add API keys for AI analysis
# Edit .env and set OPENAI_API_KEY or ANTHROPIC_API_KEY
# (System works without API keys using rule-based analysis)
```

### Step 2: Start Services (2 minutes)

```bash
# Start all services (Redis, 4 agents, Dashboard, test services)
docker-compose up -d

# Wait for services to initialize
sleep 30

# Verify all services are running
docker-compose ps
```

Expected services:
- `hemostat-redis` - Message broker and state storage
- `hemostat-monitor` - Container health monitoring
- `hemostat-analyzer` - AI-powered analysis
- `hemostat-responder` - Safe remediation execution
- `hemostat-alert` - Notifications and event storage
- `hemostat-dashboard` - Real-time web UI
- `hemostat-test-api` - Test service with HTTP endpoints
- `hemostat-test-worker` - Background worker with periodic spikes

### Step 3: Verify System (1 minute)

```bash
# Run automated verification
./scripts/verify_message_flow.sh

# Expected output: All checks should pass with green checkmarks
```

### Step 4: Open Dashboard (30 seconds)

```bash
# Open Dashboard in browser
# macOS
open http://localhost:8501

# Linux
xdg-open http://localhost:8501

# Windows
start http://localhost:8501

# Or manually navigate to: http://localhost:8501
```

### Step 5: Run Demo (30 seconds)

```bash
# Trigger CPU spike demo
./scripts/demo_trigger_cpu_spike.sh

# Watch Dashboard update in real-time
# Monitor detects high CPU → Analyzer recommends restart → Responder executes → Alert notifies
```

## What You Should See

### In the Dashboard

- **Metrics cards** showing system statistics
- **Container health grid** with test-api and test-worker
- **Active issues feed** (when demo is running)
- **Event timeline** showing agent activity
- **Auto-refresh** every 5 seconds

### In the Terminal

- Demo script output showing triggered scenario
- Instructions for monitoring Redis events
- Verification messages

### In Docker Logs (optional)

```bash
docker-compose logs -f monitor analyzer responder alert
```

Expected log messages:
- **Monitor**: "Health alert published for hemostat-test-api"
- **Analyzer**: "Remediation needed: restart (confidence: 0.9)"
- **Responder**: "Container restarted successfully"
- **Alert**: "Notification sent to Slack"

## Demo Scenarios

### Scenario 1: CPU Spike Detection

```bash
./scripts/demo_trigger_cpu_spike.sh
```

- **Demonstrates**: High CPU detection, AI analysis, container restart
- **Duration**: ~60 seconds
- **Expected**: Monitor detects >85% CPU, Analyzer recommends restart, Responder executes

### Scenario 2: Memory Leak Detection

```bash
./scripts/demo_trigger_high_memory.sh
```

- **Demonstrates**: High memory detection, memory leak analysis, container restart
- **Duration**: ~60 seconds
- **Expected**: Monitor detects >80% memory, Analyzer recommends restart, Responder executes

### Scenario 3: Cleanup Remediation

```bash
./scripts/demo_trigger_cleanup.sh
```

- **Demonstrates**: Cleanup action (remove stopped containers, prune resources)
- **Duration**: ~30 seconds
- **Expected**: Responder removes stopped containers and prunes unused resources

## Understanding the Workflow

### Agent Pipeline

1. **Monitor Agent**: Polls Docker containers every 30 seconds, detects anomalies (CPU >85%, memory >80%)
2. **Analyzer Agent**: Analyzes health alerts using AI (GPT-4/Claude) or rule-based logic, calculates confidence score
3. **Responder Agent**: Executes remediation actions (restart, scale, cleanup) with safety constraints (cooldown, circuit breaker)
4. **Alert Agent**: Sends Slack notifications, stores events in Redis for Dashboard
5. **Dashboard**: Displays real-time system health, active issues, remediation history, event timeline

### Safety Mechanisms

- **Cooldown Period**: 1 hour between actions per container (prevents restart loops)
- **Circuit Breaker**: Max 3 retries per hour (stops infinite loops)
- **Dry-Run Mode**: Test without actual remediation (set `RESPONDER_DRY_RUN=true`)
- **Audit Logging**: All actions logged to Redis for compliance

## Monitoring Tips

### View Real-Time Events

```bash
# Subscribe to all HemoStat channels
docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'

# Subscribe to specific channel
docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert
```

### View Agent Logs

```bash
# All agents
docker-compose logs -f

# Specific agents
docker-compose logs -f monitor analyzer responder alert

# Last 100 lines
docker-compose logs --tail=100 monitor
```

### Check Container Stats

```bash
# Docker stats
docker stats hemostat-test-api

# Test API metrics
curl http://localhost:5000/metrics
```

## Troubleshooting

### Services not starting

- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs`
- Restart services: `docker-compose restart`

### Dashboard not accessible

- Wait 30 seconds for Streamlit to initialize
- Check Dashboard logs: `docker-compose logs dashboard`
- Verify port 8501 is not in use: `lsof -i :8501` (macOS/Linux) or `netstat -ano | findstr :8501` (Windows)

### No events detected

- Wait for Monitor polling cycle (30 seconds)
- Check Monitor is running: `docker-compose ps monitor`
- Verify test-api is running: `docker ps | grep test-api`
- Check Redis connectivity: `docker exec hemostat-redis redis-cli ping`

### Responder not executing

- Check cooldown period (default 1 hour)
- Verify dry-run mode is disabled: `RESPONDER_DRY_RUN=false` in `.env`
- Check Responder logs: `docker-compose logs responder`

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Stop specific service
docker-compose stop monitor
```

## Next Steps

- **Customize Configuration**: Edit `.env` file to adjust thresholds, cooldown periods, API keys
- **Add Slack Notifications**: Set `SLACK_WEBHOOK_URL` in `.env` (see https://api.slack.com/messaging/webhooks)
- **Enable AI Analysis**: Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to `.env`
- **Explore Architecture**: Read `docs/ARCHITECTURE.md` for detailed system design
- **Review API Protocol**: Read `docs/API_PROTOCOL.md` for Redis channel schemas
- **Run Tests**: See `docs/TESTING_GUIDE.md` for formal test suite (Phase 5)

## For Hackathon Judges

### Key Points to Highlight

1. **Autonomous operation** (no human intervention required)
2. **AI-powered analysis** (GPT-4/Claude with rule-based fallback)
3. **Safety mechanisms** (cooldown, circuit breaker, dry-run mode)
4. **Real-time dashboard** with auto-refresh
5. **Comprehensive audit trail** for compliance
6. **Multi-agent architecture** with Redis pub/sub
7. **Docker-native** (works with any containerized application)

### Demo Flow (5 minutes)

1. **Setup** (30s): Show Dashboard, explain architecture
2. **Trigger** (1m): Run `demo_trigger_cpu_spike.sh` and narrate the workflow
3. **Monitor** (1m): Show Dashboard updating in real-time
4. **Analyze** (1m): Show Analyzer decision in logs
5. **Respond** (1m): Show Responder action and Dashboard timeline
6. **Summary** (30s): Explain safety mechanisms and audit trail

### Talking Points

- "HemoStat autonomously detects container health issues"
- "AI-powered analysis distinguishes real problems from false alarms"
- "Safe remediation with cooldown periods prevents restart loops"
- "Real-time dashboard provides visibility into system health"
- "All actions logged for audit trail and compliance"

## Resources

- **Main README**: [../README.md](../README.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Protocol**: [API_PROTOCOL.md](API_PROTOCOL.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Demo Scripts**: [../scripts/README.md](../scripts/README.md)

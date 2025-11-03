# HemoStat Demo Scripts

Collection of scripts for demonstrating HemoStat's autonomous container health monitoring and remediation capabilities. These scripts are designed for hackathon demos, testing, and verification of the end-to-end agent workflow.

## 🚀 Quick Start: Enable BuildKit (Recommended)

**Enable Docker BuildKit for 95% faster rebuilds!**

Choose your platform:
- **Windows:** `.\scripts\windows\enable_buildkit.ps1`
- **Linux:** `./scripts/linux/enable_buildkit.sh`
- **macOS:** `./scripts/macos/enable_buildkit.zsh`

See [BUILDKIT_SETUP.md](BUILDKIT_SETUP.md) for detailed instructions.

## Directory Structure

Scripts are organized by platform for easier navigation:

- **`windows/`** - PowerShell scripts (`.ps1`) for Windows
- **`macos/`** - Zsh scripts (`.zsh`) for macOS
- **`linux/`** - Bash scripts (`.sh`) for Linux/WSL

## Prerequisites

- Docker and Docker Compose installed and running
- HemoStat services started: `docker-compose up -d`
- curl installed (for HTTP requests)

## Available Scripts

All scripts are available in all three platform directories:

### 1. `demo_trigger_cpu_spike.sh`

Triggers high CPU usage on test-api service to demonstrate CPU spike detection and remediation.

**Usage:**

```bash
./demo_trigger_cpu_spike.sh [duration] [intensity]
```

**Parameters:**

- `duration`: Spike duration in seconds (default: 60)
- `intensity`: CPU intensity 0.0-1.0 (default: 0.9 = 90%)

**Example:**

```bash
./demo_trigger_cpu_spike.sh 45 0.95
```

**Expected Outcome:**

- Monitor detects CPU >85% threshold
- Analyzer recommends container restart
- Responder executes restart (if not in cooldown)
- Alert sends Slack notification
- Dashboard shows event in timeline

---

### 2. `demo_trigger_high_memory.sh`

Triggers high memory usage to demonstrate memory leak detection.

**Usage:**

```bash
./demo_trigger_high_memory.sh [duration] [size_mb]
```

**Parameters:**

- `duration`: Spike duration in seconds (default: 60)
- `size_mb`: Memory to allocate in MB (default: 500)

**Example:**

```bash
./demo_trigger_high_memory.sh 45 600
```

**Expected Outcome:**

- Monitor detects memory >80% threshold
- Analyzer recommends container restart
- Responder executes restart
- Alert sends notification
- Dashboard updates

---

### 3. `demo_trigger_cleanup.sh`

Demonstrates cleanup remediation action (remove stopped containers, prune resources).

**Usage:**

```bash
./demo_trigger_cleanup.sh
```

**No parameters required**

**Expected Outcome:**

- Script creates stopped test containers
- Manually publishes cleanup remediation request
- Responder removes stopped containers
- Alert logs cleanup completion

---

### 4. `verify_message_flow.sh`

Automated verification of end-to-end message flow through all agents.

**Usage:**

```bash
./verify_message_flow.sh
```

**No parameters required**

**Expected Outcome:**

- Checks all services are running
- Triggers test scenario
- Monitors Redis pub/sub channels
- Verifies each agent responds correctly
- Prints verification summary

---

### 5. `clear_redis_data.sh`

Clears all HemoStat data from Redis for a fresh start between test runs.

**Usage:**

```bash
./clear_redis_data.sh   # Bash
./clear_redis_data.zsh  # Zsh
```

```powershell
.\scripts\clear_redis_data.ps1  # PowerShell
```

**What gets cleared:**

- All events (timeline, history)
- Remediation state and cooldowns
- Circuit breaker state
- Alert history
- Audit logs

**Note:** Prompts for confirmation before clearing data.

---

### 6. `backup_redis_data.sh`

Exports all HemoStat data to a JSON file for later analysis or archival.

**Usage:**

```bash
# Default timestamped file
./backup_redis_data.sh

# Custom filename
./backup_redis_data.sh my_backup.json
```

```powershell
# Default timestamped file
.\scripts\backup_redis_data.ps1

# Custom filename
.\scripts\backup_redis_data.ps1 -OutputFile "my_backup.json"
```

**Output:**

- Timestamped JSON file (e.g., `hemostat_backup_20251103_052000.json`)
- Includes all events, state, and metadata
- Can be used for debugging or demo replay

---

## Quick Start

### Linux (Bash)

```bash
cd scripts/linux
chmod +x *.sh  # Make executable (first time only)

# 1. Start HemoStat
docker-compose up -d
sleep 30

# 2. Verify system
./verify_message_flow.sh

# 3. Run demos
./demo_trigger_cpu_spike.sh
./demo_trigger_high_memory.sh
```

### macOS (Zsh)

```zsh
cd scripts/macos
chmod +x *.zsh  # Make executable (first time only)

# 1. Start HemoStat
docker-compose up -d
sleep 30

# 2. Verify system
./verify_message_flow.zsh

# 3. Run demos
./demo_trigger_cpu_spike.zsh
./demo_trigger_high_memory.zsh
```

### Windows (PowerShell)

```powershell
cd scripts\windows

# 1. Start HemoStat
docker-compose up -d
Start-Sleep -Seconds 30

# 2. Verify system
.\verify_message_flow.ps1

# 3. Run demos
.\demo_trigger_cpu_spike.ps1
.\demo_trigger_high_memory.ps1
```

## Monitoring Tips

### View Agent Logs

```bash
# All agents
docker-compose logs -f monitor analyzer responder alert

# Specific agent
docker-compose logs -f monitor

# Last 100 lines
docker-compose logs --tail=100 monitor
```

### Monitor Redis Events

```bash
# Subscribe to all HemoStat channels
docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'

# Subscribe to specific channel
docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert

# View stored events
docker exec hemostat-redis redis-cli LRANGE hemostat:events:all 0 -1

# View remediation events
docker exec hemostat-redis redis-cli LRANGE hemostat:events:remediation_complete 0 -1
```

### Check Container Metrics

```bash
# View test-api metrics
curl http://localhost:5001/metrics

# View Docker stats
docker stats hemostat-test-api

# Check all containers
docker stats
```

## Troubleshooting

### "Service not running" error

Run `docker-compose up -d` to start all services.

```bash
docker-compose up -d
docker-compose ps
```

### "Connection refused" error

Wait 30 seconds for services to initialize, then check service status:

```bash
docker-compose ps
docker-compose logs
```

### "No events detected" warning

- Increase wait time in scripts
- Check Monitor polling interval (default 30s)
- Verify Monitor is running: `docker-compose logs monitor`

### "Responder not executing" issue

- Check cooldown period (default 1 hour): May need to wait or adjust `RESPONDER_COOLDOWN_SECONDS` in `.env`
- Verify dry-run mode is disabled: Set `RESPONDER_DRY_RUN=false` in `.env`
- Check Responder logs: `docker-compose logs responder`

### Scripts not executable

Make scripts executable:

```bash
# On Linux/macOS
chmod +x scripts/*.sh

# On Windows (Git Bash)
# Scripts should be executable by default
```

## Demo Presentation Tips

### For Hackathon Judges

1. Start with `verify_message_flow.sh` to show system is working
2. Open Dashboard in browser before triggering scenarios
3. Run `demo_trigger_cpu_spike.sh` and narrate the workflow
4. Show Dashboard updating in real-time
5. Show Slack notifications (if configured)
6. Explain safety mechanisms (cooldown, circuit breaker)

### Talking Points

- "HemoStat autonomously detects container health issues"
- "AI-powered analysis distinguishes real problems from false alarms"
- "Safe remediation with cooldown periods prevents restart loops"
- "Real-time dashboard provides visibility into system health"
- "All actions logged for audit trail and compliance"

### Demo Flow (5 minutes)

1. **Setup** (30s): Show Dashboard, explain architecture
2. **Trigger** (1m): Run CPU spike demo, explain what's happening
3. **Monitor** (2m): Show Monitor detection in logs
4. **Analyze** (30s): Show Analyzer decision
5. **Respond** (30s): Show Responder execution
6. **Dashboard** (30s): Show event timeline and metrics

## Test Services

### test-api

HTTP API with stress test endpoints.

- **Endpoint**: `http://localhost:5001`
- **Health check**: `GET /health`
- **Trigger CPU spike**: `POST /stress/cpu`
- **Trigger memory spike**: `POST /stress/memory`
- **Stop stress**: `POST /stress/stop`
- **View metrics**: `GET /metrics`

**Example Usage:**

```bash
# Trigger CPU spike
curl -X POST http://localhost:5001/stress/cpu \
  -H "Content-Type: application/json" \
  -d '{"duration": 60, "intensity": 0.9}'

# Check metrics
curl http://localhost:5001/metrics

# Stop stress
curl -X POST http://localhost:5001/stress/stop
```

### test-worker

Background worker with random spikes.

- Automatically spikes CPU or memory periodically
- Configurable via environment variables in `docker-compose.yml`:
  - `WORKER_INTERVAL`: Time between work cycles (default: 60s)
  - `WORKER_SPIKE_PROBABILITY`: Chance of spike per cycle (default: 0.1 = 10%)
  - `WORKER_SPIKE_DURATION`: Spike duration (default: 30s)
- Useful for continuous demo scenarios

**View Logs:**

```bash
docker-compose logs -f test-worker
```

## Next Steps

- **Main README**: [../README.md](../README.md)
- **Architecture**: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **API Protocol**: [../docs/API_PROTOCOL.md](../docs/API_PROTOCOL.md)
- **Troubleshooting**: [../docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)
- **Quick Start Guide**: [../docs/QUICKSTART.md](../docs/QUICKSTART.md)
- **Phase 5**: Formal test suite (pytest) for comprehensive testing

---

**Note**: These scripts are designed for demonstration and testing purposes. For production deployment, see [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

# HemoStat Usage Guide

Complete guide for running and using HemoStat's test infrastructure, demo scripts, and integration testing.

## Table of Contents

- [Quick Start](#quick-start)
- [Step-by-Step Setup](#step-by-step-setup)
- [Running Demo Scenarios](#running-demo-scenarios)
- [Monitoring in Real-Time](#monitoring-in-real-time)
- [Using Test Services](#using-test-services)
- [Checking System State](#checking-system-state)
- [Hackathon Demo Script](#hackathon-demo-script)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### TL;DR - Get Running in 2 Minutes

```bash
# 1. Start everything
docker-compose up -d

# 2. Wait for initialization
sleep 30

# 3. Verify it works
./scripts/macos/verify_message_flow.zsh    # macOS
./scripts/linux/verify_message_flow.sh     # Linux
.\scripts\windows\verify_message_flow.ps1  # Windows

# 4. Open Dashboard
open http://localhost:8501  # macOS
```

---

## Step-by-Step Setup

### Step 1: Start All Services

Start all HemoStat services including test infrastructure:

```bash
docker-compose up -d
```

This starts **8 services**:

- `hemostat-redis` - Message broker and state storage
- `hemostat-monitor` - Container health monitoring
- `hemostat-analyzer` - AI-powered analysis
- `hemostat-responder` - Safe remediation execution
- `hemostat-alert` - Notifications and event storage
- `hemostat-dashboard` - Real-time web UI
- `hemostat-test-api` - Test service with HTTP endpoints
- `hemostat-test-worker` - Background worker with periodic spikes

**Verify all services are running:**

```bash
docker-compose ps
```

All services should show `Up` status.

### Step 2: Wait for Initialization

Give services ~30 seconds to fully initialize:

```bash
sleep 30
```

### Step 3: Verify the System Works

Run the end-to-end verification script to ensure everything is communicating correctly.

**macOS (Zsh - default shell):**

```bash
# Make scripts executable (first time only)
chmod +x scripts/*.zsh

# Run verification
./scripts/verify_message_flow.zsh
```

**Linux (Bash):**

```bash
# Make scripts executable (first time only)
chmod +x scripts/*.sh

# Run verification
./scripts/verify_message_flow.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\verify_message_flow.ps1
```

**What this script does:**

- ✅ Checks all 8 services are running
- ✅ Tests Redis connectivity
- ✅ Triggers a test CPU spike
- ✅ Waits for Monitor to detect (~35 seconds)
- ✅ Verifies Analyzer processes the alert
- ✅ Verifies Responder executes remediation
- ✅ Verifies Alert stores events
- ✅ Checks Dashboard is accessible
- ✅ Prints color-coded verification summary

**Expected Output:**

```
================================================================
  HemoStat End-to-End Message Flow Verification
================================================================

Step 1: Checking Prerequisites
✓ redis is running
✓ monitor is running
✓ analyzer is running
✓ responder is running
✓ alert is running
✓ dashboard is running
✓ test-api is running

...

Status: ✓ VERIFIED
All agents are communicating correctly via Redis pub/sub!
```

### Step 4: Open the Dashboard

While scripts run, open the dashboard in your browser:

```bash
# macOS
open http://localhost:8501

# Linux
xdg-open http://localhost:8501

# Windows
start http://localhost:8501
```

**Dashboard Features:**

- **Metrics Cards** - Container count, CPU/memory stats
- **Container Health Grid** - Visual status of monitored containers
- **Active Issues Feed** - Current health problems
- **Event Timeline** - Recent agent activity (filterable)
- **Remediation History** - Audit trail of automated actions
- **Auto-refresh** - Updates every 5 seconds

---

## Running Demo Scenarios

Demo scripts trigger specific failure scenarios to demonstrate HemoStat's capabilities.

### Demo 1: CPU Spike Detection

Triggers high CPU usage to demonstrate detection and remediation.

**macOS/Linux:**

```bash
./scripts/demo_trigger_cpu_spike.zsh 60 0.9  # macOS (zsh)
./scripts/demo_trigger_cpu_spike.sh 60 0.9   # Linux (bash)
```

**Windows:**

```powershell
.\scripts\demo_trigger_cpu_spike.ps1 -Duration 60 -Intensity 0.9
```

**Parameters:**

- `duration`: Spike duration in seconds (default: 60)
- `intensity`: CPU intensity 0.0-1.0 (default: 0.9 = 90%)

**What Happens:**

1. **Script triggers** 90% CPU load on `test-api` for 60 seconds
2. **Monitor Agent** polls every 30s, detects CPU >85% threshold
3. **Monitor publishes** to `hemostat:health_alert` Redis channel
4. **Analyzer receives** alert, performs analysis (AI or rule-based)
5. **Analyzer decides** restart action (confidence: 0.9)
6. **Analyzer publishes** to `hemostat:remediation_needed` channel
7. **Responder checks** cooldown period (1 hour default)
8. **Responder restarts** container (if not in cooldown)
9. **Responder publishes** to `hemostat:remediation_complete` channel
10. **Alert stores** event in Redis for Dashboard
11. **Alert sends** Slack notification (if webhook configured)
12. **Dashboard updates** in real-time with new events

**Total Flow Time:** ~45-60 seconds from trigger to completion

### Demo 2: Memory Leak Detection

Triggers high memory usage to demonstrate memory leak detection.

**macOS/Linux:**

```bash
./scripts/demo_trigger_high_memory.zsh 60 500  # macOS
./scripts/demo_trigger_high_memory.sh 60 500   # Linux
```

**Windows:**

```powershell
.\scripts\demo_trigger_high_memory.ps1 -Duration 60 -SizeMB 500
```

**Parameters:**

- `duration`: Spike duration in seconds (default: 60)
- `size_mb`: Memory to allocate in MB (default: 500)

**What Happens:**

- Allocates 500MB of memory in `test-api` container
- Monitor detects memory usage >80% threshold
- Follows same workflow as CPU spike (analyze → remediate → alert)
- Container restart frees the allocated memory

### Demo 3: Cleanup Remediation

Demonstrates cleanup action (removing stopped containers, pruning resources).

**macOS/Linux:**

```bash
./scripts/demo_trigger_cleanup.zsh  # macOS
./scripts/demo_trigger_cleanup.sh   # Linux
```

**Windows:**

```powershell
.\scripts\demo_trigger_cleanup.ps1
```

**What Happens:**

1. Script creates 3 stopped test containers
2. Script manually publishes cleanup request to Redis
3. Responder removes stopped containers
4. Responder prunes unused Docker resources
5. Demonstrates direct Redis event publishing (advanced usage)

---

## Monitoring in Real-Time

### Watch the Complete Message Flow

Open **multiple terminal windows** to see the full agent workflow in real-time:

**Terminal 1 - Health Alerts:**

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert
```

**Terminal 2 - Remediation Decisions:**

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_needed
```

**Terminal 3 - Remediation Results:**

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_complete
```

**Terminal 4 - All Events (Wildcard):**

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'
```

**Terminal 5 - Agent Logs:**

```bash
docker-compose logs -f monitor analyzer responder alert
```

**Terminal 6 - Dashboard (Browser):**

Navigate to `http://localhost:8501`

### View Agent Logs

**All agents:**

```bash
docker-compose logs -f
```

**Specific agent:**

```bash
docker-compose logs -f monitor    # Just Monitor Agent
docker-compose logs -f analyzer   # Just Analyzer Agent
docker-compose logs -f responder  # Just Responder Agent
docker-compose logs -f alert      # Just Alert Agent
```

**Last N lines:**

```bash
docker-compose logs --tail=50        # Last 50 lines from all
docker-compose logs --tail=100 monitor  # Last 100 from Monitor
```

**Test services only:**

```bash
docker-compose logs -f test-api test-worker
```

---

## Using Test Services

### Test API Service

HTTP API with endpoints for triggering controllable resource stress.

**Base URL:** `http://localhost:5000`

#### Endpoints

**Health Check:**

```bash
curl http://localhost:5000/health
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-03T05:23:00Z"
}
```

**Get Current Metrics:**

```bash
curl http://localhost:5000/metrics
```

Response:

```json
{
  "cpu_percent": 12.5,
  "memory_percent": 35.2,
  "memory_used_mb": 256.3,
  "memory_total_mb": 1024.0,
  "active_tests": [],
  "timestamp": "2025-11-03T05:23:00Z"
}
```

**Trigger CPU Spike:**

```bash
curl -X POST http://localhost:5000/stress/cpu \
  -H "Content-Type: application/json" \
  -d '{"duration": 60, "intensity": 0.9}'
```

Response:

```json
{
  "status": "started",
  "duration": 60,
  "intensity": 0.9
}
```

**Trigger Memory Spike:**

```bash
curl -X POST http://localhost:5000/stress/memory \
  -H "Content-Type: application/json" \
  -d '{"duration": 60, "size_mb": 500}'
```

Response:

```json
{
  "status": "started",
  "duration": 60,
  "size_mb": 500
}
```

**Stop All Active Stress Tests:**

```bash
curl -X POST http://localhost:5000/stress/stop
```

Response:

```json
{
  "status": "stopped",
  "tests_stopped": 2
}
```

### Test Worker Service

Background worker that **randomly** creates resource spikes.

**Default Behavior:**

- Polls every 60 seconds
- 10% chance of spike per cycle
- Randomly picks CPU or memory spike
- Holds spike for 30 seconds

**Configure via Environment Variables:**

Edit `.env` file:

```bash
WORKER_INTERVAL=120           # Check every 2 minutes
WORKER_SPIKE_PROBABILITY=0.2  # 20% chance per cycle
WORKER_SPIKE_DURATION=45      # Hold spike for 45 seconds
```

Then restart:

```bash
docker-compose restart test-worker
```

**Watch Worker Activity:**

```bash
docker-compose logs -f test-worker
```

Example output:

```
[TEST-WORKER] 2025-11-03 05:23:00 - INFO - Worker started (interval: 60s, spike_probability: 0.1)
[TEST-WORKER] 2025-11-03 05:24:00 - INFO - Work cycle 1 completed (no spike)
[TEST-WORKER] 2025-11-03 05:25:00 - INFO - CPU spike started (duration: 30s)
[TEST-WORKER] 2025-11-03 05:25:30 - INFO - CPU spike completed
[TEST-WORKER] 2025-11-03 05:26:00 - INFO - Work cycle 3 completed (no spike)
```

---

## Checking System State

### Redis Data

**List all keys:**

```bash
docker exec hemostat-redis redis-cli KEYS '*'
```

**View recent events:**

```bash
# All events
docker exec hemostat-redis redis-cli LRANGE hemostat:events:all 0 10

# Remediation events only
docker exec hemostat-redis redis-cli LRANGE hemostat:events:remediation_complete 0 5

# Health alerts only
docker exec hemostat-redis redis-cli LRANGE hemostat:events:health_alert 0 5
```

**Get event count:**

```bash
docker exec hemostat-redis redis-cli LLEN hemostat:events:all
```

**Check cooldown state:**

```bash
# Check if container is in cooldown
docker exec hemostat-redis redis-cli GET "hemostat:state:responder:last_action:hemostat-test-api"
```

### Container Stats

**Real-time container stats:**

```bash
docker stats

# Specific container
docker stats hemostat-test-api
```

**Service status:**

```bash
docker-compose ps
```

**Container health:**

```bash
docker inspect hemostat-test-api | grep -A 10 Health
```

---

## Managing Redis Data

### Clear Redis Data (Fresh Start)

Between test runs, you may want to clear old data from Redis for a clean slate.

**Option 1: Manual Clear Script**

Use the clear script when you want to reset data:

**Windows:**

```powershell
.\scripts\windows\clear_redis_data.ps1
```

**macOS:**

```zsh
./scripts/macos/clear_redis_data.zsh
```

**Linux:**

```bash
./scripts/linux/clear_redis_data.sh
```

This will prompt for confirmation and clear:

- All events (timeline, history)
- Remediation state and cooldowns
- Circuit breaker state
- Alert history
- Audit logs

**Option 2: Auto-Clear on Startup**

To automatically clear Redis every time services start, set in `.env`:

```bash
REDIS_CLEAR_ON_STARTUP=true
```

Then restart services:

```powershell
docker-compose down
docker-compose up -d
```

⚠️ **Warning:** This deletes all data on every startup. Use for testing/demos only!

### Backup Redis Data

Save current data before clearing (useful for demos, analysis, or debugging):

**Windows:**

```powershell
.\scripts\windows\backup_redis_data.ps1
.\scripts\windows\backup_redis_data.ps1 -OutputFile "my_demo_backup.json"
```

**macOS:**

```zsh
./scripts/macos/backup_redis_data.zsh
./scripts/macos/backup_redis_data.zsh my_demo_backup.json
```

**Linux:**

```bash
./scripts/linux/backup_redis_data.sh
./scripts/linux/backup_redis_data.sh my_demo_backup.json
```

Backup files are JSON format and include:

- All events and timeline data
- Remediation history
- State information
- Timestamps

### Typical Workflow for Testing

```powershell
# 1. Backup current data (if you want to keep it)
.\scripts\backup_redis_data.ps1

# 2. Clear Redis for fresh start
.\scripts\clear_redis_data.ps1

# 3. Run your tests/demos
.\scripts\demo_trigger_cpu_spike.ps1

# 4. Review results in Dashboard
start http://localhost:8501

# 5. Backup results
.\scripts\backup_redis_data.ps1 -OutputFile "test_run_results.json"
```

---

## Hackathon Demo Script

### 5-Minute Demo for Judges

**Preparation (Before Demo):**

```bash
# Start everything (do this before judges arrive)
docker-compose up -d
sleep 30

# Open Dashboard in browser
open http://localhost:8501
```

**Demo Script:**

**Minute 1: Introduction**

- "HemoStat is an autonomous container health monitoring system"
- "Uses AI to detect, analyze, and remediate container issues"
- "Let me show you a live demo"

**Minute 2: Show Architecture**

- Open Dashboard, show clean state
- Explain: "4 agents work together: Monitor, Analyzer, Responder, Alert"
- Point out: "Everything communicates via Redis pub/sub"

**Minute 3: Trigger Failure**

```bash
# Run this in terminal (visible to judges)
./scripts/demo_trigger_cpu_spike.zsh
```

- "I'm triggering a CPU spike on our test container"
- "Watch the Monitor detect it in about 30 seconds"

**Minute 4: Show Response**

- Point to Dashboard updating
- Show logs: `docker-compose logs -f monitor analyzer responder`
- Highlight timeline: "Here's the Monitor detecting high CPU"
- "Analyzer used AI to determine this needs a restart"
- "Responder safely restarted the container"

**Minute 5: Explain Safety & Wrap-Up**

- "Notice the cooldown period - prevents restart loops"
- "Circuit breaker limits retries per hour"
- "Complete audit trail for compliance"
- "Slack notifications sent automatically"
- "All autonomous - no human intervention needed"

### Key Talking Points

✅ **Autonomous Operation**

- "No human intervention required"
- "Detects, analyzes, and remediates automatically"

✅ **AI-Powered Analysis**

- "Uses GPT-4 or Claude for intelligent decision-making"
- "Falls back to rule-based analysis if API unavailable"
- "Confidence scoring prevents false positives"

✅ **Safety Mechanisms**

- "1-hour cooldown prevents restart loops"
- "Circuit breaker limits retries (3/hour)"
- "Dry-run mode for testing without side effects"

✅ **Real-Time Visibility**

- "Dashboard auto-refreshes every 5 seconds"
- "Complete event timeline"
- "Container health grid with visual indicators"

✅ **Production-Ready**

- "Comprehensive audit trail for compliance"
- "Slack integration for team notifications"
- "Docker-native - works with any containerized app"

---

## Troubleshooting

### Services Not Starting

**Problem:** Services fail to start or show errors

**Solution:**

```bash
# Check logs for errors
docker-compose logs

# Rebuild images
docker-compose build --no-cache

# Restart services
docker-compose restart

# Clean start
docker-compose down -v
docker-compose up -d
```

### Dashboard Not Accessible

**Problem:** Cannot access `http://localhost:8501`

**Solution:**

```bash
# Wait for Streamlit to initialize (30 seconds)
sleep 30

# Check Dashboard logs
docker-compose logs dashboard

# Verify port not in use
# macOS/Linux:
lsof -i :8501

# Windows:
netstat -ano | findstr :8501

# Restart Dashboard
docker-compose restart dashboard
```

### No Events Detected

**Problem:** Verification script shows no events

**Solution:**

```bash
# Wait for Monitor polling cycle (30 seconds)
sleep 35

# Check Monitor is running
docker-compose ps monitor

# Verify test-api is running
docker ps | grep test-api

# Check Redis connectivity
docker exec hemostat-redis redis-cli ping
# Should return: PONG

# Check Monitor logs
docker-compose logs monitor
```

### Responder Not Executing

**Problem:** Responder doesn't restart containers

**Solution:**

```bash
# Check cooldown period (default: 1 hour)
# Wait 1 hour or adjust RESPONDER_COOLDOWN_SECONDS in .env

# Verify dry-run mode is disabled
# In .env: RESPONDER_DRY_RUN=false

# Check Responder logs
docker-compose logs responder

# Check for circuit breaker limit
# Max 3 retries/hour - may need to wait
```

### Scripts Not Executable

**Problem:** Permission denied when running scripts

**Solution:**

```bash
# macOS/Linux - make executable
chmod +x scripts/*.sh
chmod +x scripts/*.zsh

# Windows - use PowerShell versions
.\scripts\verify_message_flow.ps1
```

### Port Conflicts

**Problem:** Port already in use

**Solution:**

```bash
# Check what's using port 5000 (test-api)
# macOS/Linux:
lsof -i :5000

# Windows:
netstat -ano | findstr :5000

# Kill conflicting process or change port in docker-compose.yml
```

---

## Stopping Everything

**Stop all services:**

```bash
docker-compose down
```

**Stop and remove all data (clean slate):**

```bash
docker-compose down -v
```

**Stop specific service:**

```bash
docker-compose stop monitor
```

**Restart specific service:**

```bash
docker-compose restart monitor
```

---

## Additional Resources

- **[README.md](README.md)** - Project overview and quick start
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design details
- **[docs/API_PROTOCOL.md](docs/API_PROTOCOL.md)** - Redis channel schemas
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues
- **[scripts/README.md](scripts/README.md)** - Demo scripts documentation

---

## Quick Reference

### Common Commands

```bash
# Start everything
docker-compose up -d

# Verify system
./scripts/verify_message_flow.zsh  # macOS
./scripts/verify_message_flow.sh   # Linux
.\scripts\verify_message_flow.ps1  # Windows

# Run demos
./scripts/demo_trigger_cpu_spike.zsh
./scripts/demo_trigger_high_memory.zsh
./scripts/demo_trigger_cleanup.zsh

# View logs
docker-compose logs -f monitor analyzer responder alert

# Monitor Redis
docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'

# Check events
docker exec hemostat-redis redis-cli LRANGE hemostat:events:all 0 10

# Stop everything
docker-compose down
```

### URLs

- **Dashboard:** <http://localhost:8501>
- **Test API:** <http://localhost:5000>
- **Redis:** localhost:6379

---

**Happy Testing! 🚀**

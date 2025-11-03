# HemoStat Testing Guide - Phase 2 Complete

Comprehensive testing guide for all four Phase 2 agents: Monitor, Analyzer, Responder, and Alert.

**Status**: ✅ Phase 2 Complete - All four agents implemented and ready for testing

---

## Quick Start Testing

### Prerequisites

```bash
# 1. Verify Python version
python --version  # Should be 3.11+

# 2. Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --extra agents

# 4. Copy environment template
cp .env.example .env

# 5. Start Redis
docker-compose up -d redis

# 6. Verify Redis connection
redis-cli ping  # Should return PONG
```

---

## Test 1: Environment & Dependencies Verification

**Objective**: Verify all dependencies are installed and environment is configured correctly.

### Commands

```bash
# Check Python version
python --version

# Verify uv installation
uv --version

# Verify key imports
python -c "import redis; print('✓ redis')"
python -c "import docker; print('✓ docker')"
python -c "import langchain; print('✓ langchain')"
python -c "from langchain_openai import ChatOpenAI; print('✓ langchain-openai')"
python -c "from langchain_anthropic import ChatAnthropic; print('✓ langchain-anthropic')"
python -c "import requests; print('✓ requests')"

# Verify Redis connection
redis-cli ping

# Check .env file
test -f .env && echo "✓ .env exists" || echo "✗ .env missing"

# Check Docker
docker ps
```

### Expected Results

✅ All imports succeed  
✅ Redis returns `PONG`  
✅ `.env` file exists  
✅ Docker is accessible

---

## Test 2: Monitor Agent - Container Polling & Metrics

**Objective**: Verify Monitor Agent detects running containers and publishes health alerts.

### Setup

```bash
# Terminal 1: Start Redis
docker-compose up -d redis

# Terminal 2: Start Monitor Agent
uv run python -m agents.hemostat_monitor.main
```

### Verification

```bash
# Terminal 3: Subscribe to health alerts
redis-cli SUBSCRIBE hemostat:health_alert

# Terminal 4: Start a test container
docker run -d --name test-nginx nginx:latest

# Expected in Terminal 3:
# - Message on hemostat:health_alert channel
# - JSON payload with container metrics (cpu_percent, memory_percent, etc.)
# - Anomalies array (may be empty for healthy container)

# Terminal 2 logs should show:
# "Publishing health alert for test-nginx"
# "Detected anomalies: 0"
```

### Manual Inspection

```bash
# Check container is running
docker ps | grep test-nginx

# View Monitor logs
docker-compose logs monitor

# Check Redis keys created by Monitor
redis-cli KEYS "hemostat:state:*"

# View a specific container's state
redis-cli GET "hemostat:state:container:test-nginx"
```

### Cleanup

```bash
docker stop test-nginx
docker rm test-nginx
```

### Success Criteria

✅ Monitor publishes health alerts every 30 seconds  
✅ Metrics include CPU, memory, network, disk I/O  
✅ Anomalies detected for high resource usage  
✅ Redis keys created for container state

---

## Test 3: Analyzer Agent - Health Analysis & Routing

**Objective**: Verify Analyzer receives health alerts and routes to remediation or false alarm.

### Setup

```bash
# Terminal 1: Start Redis
docker-compose up -d redis

# Terminal 2: Start Monitor Agent
uv run python -m agents.hemostat_monitor.main

# Terminal 3: Start Analyzer Agent (with rule-based fallback)
AI_FALLBACK_ENABLED=true uv run python -m agents.hemostat_analyzer.main
```

### Test Case 1: Transient Spike (False Alarm)

```bash
# Terminal 4: Subscribe to false alarms
redis-cli SUBSCRIBE hemostat:false_alarm

# Terminal 5: Create container with temporary CPU spike
docker run -d --name spike-test busybox sh -c "while true; do : ; done" &
sleep 5
kill %1

# Expected in Terminal 4:
# - Message on hemostat:false_alarm channel
# - Reason: "Transient CPU spike; no historical pattern detected"
# - Confidence: 0.65
```

### Test Case 2: Sustained Issue (Remediation)

```bash
# Terminal 4: Subscribe to remediation events
redis-cli SUBSCRIBE hemostat:remediation_needed

# Terminal 5: Create container with sustained high CPU
docker run -d --name sustained-test busybox sh -c "while true; do : ; done"

# Wait 60-90 seconds for Monitor to collect multiple samples
# Expected in Terminal 4:
# - Message on hemostat:remediation_needed channel
# - Action: "restart"
# - Confidence: 0.75+
# - Reason: "Sustained high CPU usage detected"
```

### Test Case 3: Rule-Based Fallback

```bash
# Terminal 4: Check Analyzer logs
docker-compose logs analyzer | grep -i "rule-based\|fallback"

# Expected output:
# "Using rule-based analysis (AI disabled or unavailable)"
# "Rule matched: Sustained high CPU"
```

### Test Case 4: Unhealthy Container

```bash
# Terminal 5: Create container that exits immediately
docker run -d --name unhealthy-test busybox sh -c "exit 1"

# Wait 30-60 seconds
# Expected in Terminal 4:
# - Message on hemostat:remediation_needed
# - Action: "restart"
# - Confidence: 0.9
# - Reason: "Container exited with non-zero code"
```

### Manual Inspection

```bash
# View Analyzer logs
docker-compose logs analyzer

# Check alert history stored in Redis
redis-cli GET "hemostat:state:alert_history:sustained-test"

# View remediation events
redis-cli LRANGE "hemostat:events:remediation_needed" 0 -1

# View false alarm events
redis-cli LRANGE "hemostat:events:false_alarm" 0 -1
```

### Cleanup

```bash
docker stop spike-test sustained-test unhealthy-test 2>/dev/null
docker rm spike-test sustained-test unhealthy-test 2>/dev/null
```

### Success Criteria

✅ Analyzer receives health alerts from Monitor  
✅ Routes to `hemostat:remediation_needed` for real issues  
✅ Routes to `hemostat:false_alarm` for transient spikes  
✅ Confidence scores are reasonable (0.5-0.9)  
✅ Rule-based fallback works when AI is disabled  
✅ Alert history tracked in Redis

---

## Test 4: Responder Agent - Remediation Execution

**Objective**: Verify Responder executes remediation actions with safety constraints.

### Setup

```bash
# Terminal 1: Start Redis
docker-compose up -d redis

# Terminal 2: Start Monitor Agent
uv run python -m agents.hemostat_monitor.main

# Terminal 3: Start Analyzer Agent
AI_FALLBACK_ENABLED=true uv run python -m agents.hemostat_analyzer.main

# Terminal 4: Start Responder Agent
uv run python -m agents.hemostat_responder.main
```

### Test Case 1: Container Restart

```bash
# Terminal 5: Subscribe to remediation complete events
redis-cli SUBSCRIBE hemostat:remediation_complete

# Terminal 6: Create a test container
docker run -d --name restart-test nginx:latest

# Wait 60 seconds for Monitor to detect it
# Manually trigger remediation (simulate Analyzer publishing):
redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"Test restart","confidence":0.9}'

# Expected in Terminal 5:
# - Message on hemostat:remediation_complete
# - Status: "success"
# - Action: "restart"
# - Container should be restarted (check with: docker ps)

# Verify container was restarted
docker ps | grep restart-test
```

### Test Case 2: Dry-Run Mode

```bash
# Terminal 4: Stop Responder and restart with dry-run
RESPONDER_DRY_RUN=true uv run python -m agents.hemostat_responder.main

# Terminal 6: Trigger remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"Test dry-run","confidence":0.9}'

# Expected in Terminal 5:
# - Message on hemostat:remediation_complete
# - Status: "success"
# - dry_run: true
# - Container should NOT be restarted (verify with: docker ps)
```

### Test Case 3: Cooldown Period

```bash
# Terminal 4: Restart Responder with short cooldown for testing
RESPONDER_COOLDOWN_SECONDS=10 uv run python -m agents.hemostat_responder.main

# Terminal 6: Trigger first remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"First attempt","confidence":0.9}'

# Wait 2 seconds, trigger second remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"Second attempt","confidence":0.9}'

# Expected in Terminal 5:
# - First message: status "success"
# - Second message: status "rejected", reason "cooldown_active"
# - Container only restarted once
```

### Test Case 4: Circuit Breaker

```bash
# Terminal 4: Restart Responder with low retry limit
RESPONDER_MAX_RETRIES_PER_HOUR=2 uv run python -m agents.hemostat_responder.main

# Terminal 6: Trigger remediation 3 times (with cooldown=0 for testing)
for i in {1..3}; do
  redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"Attempt '$i'","confidence":0.9}'
  sleep 1
done

# Expected in Terminal 5:
# - First two messages: status "success"
# - Third message: status "rejected", reason "circuit_breaker_open"
```

### Manual Inspection

```bash
# View Responder logs
docker-compose logs responder

# Check remediation history
redis-cli LRANGE "hemostat:audit:restart-test" 0 -1

# Check circuit breaker state
redis-cli GET "hemostat:state:circuit_breaker:restart-test"

# Check cooldown state
redis-cli GET "hemostat:state:remediation_history:restart-test"
```

### Cleanup

```bash
docker stop restart-test 2>/dev/null
docker rm restart-test 2>/dev/null
```

### Success Criteria

✅ Responder receives remediation requests  
✅ Executes restart action successfully  
✅ Dry-run mode simulates without executing  
✅ Cooldown period prevents rapid-fire restarts  
✅ Circuit breaker stops after max retries  
✅ Audit logging captures all actions  
✅ Publishes completion events to Redis

---

## Test 5: Alert Agent - Event Storage & Notifications

**Objective**: Verify Alert Agent stores events and sends Slack notifications.

### Setup

```bash
# Terminal 1: Start Redis
docker-compose up -d redis

# Terminal 2: Start all agents
docker-compose up -d monitor analyzer responder alert
```

### Test Case 1: Event Storage

```bash
# Terminal 3: Subscribe to remediation complete events
redis-cli SUBSCRIBE hemostat:remediation_complete

# Terminal 4: Create a test container and trigger remediation
docker run -d --name alert-test nginx:latest

# Wait 60 seconds for Monitor to detect it
# Manually trigger remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"alert-test","action":"restart","reason":"Test alert","confidence":0.9}'

# Expected in Terminal 3:
# - Message on hemostat:remediation_complete
# - Alert Agent should store this event

# Verify event was stored
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1
redis-cli LRANGE "hemostat:events:all" 0 -1
```

### Test Case 2: Event Deduplication

```bash
# Terminal 4: Trigger same remediation twice within 60 seconds
redis-cli PUBLISH hemostat:remediation_needed '{"container":"alert-test","action":"restart","reason":"Test dedup","confidence":0.9}'
sleep 2
redis-cli PUBLISH hemostat:remediation_needed '{"container":"alert-test","action":"restart","reason":"Test dedup","confidence":0.9}'

# Expected:
# - Both events stored in Redis
# - But only one Slack notification sent (deduplication)
# - Check Alert Agent logs for deduplication message
```

### Test Case 3: Slack Notifications (Optional)

```bash
# 1. Get Slack webhook URL:
#    - Visit https://api.slack.com/messaging/webhooks
#    - Create new app or use existing
#    - Add Incoming Webhooks
#    - Copy webhook URL

# 2. Set in .env
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL" >> .env

# 3. Restart Alert Agent
docker-compose restart alert

# 4. Trigger remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"alert-test","action":"restart","reason":"Test Slack","confidence":0.9}'

# Expected:
# - Slack notification posted to channel
# - Message includes container name, action, status, confidence
# - Color-coded (green for success, red for failure)
```

### Test Case 4: False Alarm Storage

```bash
# Terminal 4: Manually publish false alarm
redis-cli PUBLISH hemostat:false_alarm '{"container":"alert-test","reason":"Transient spike","confidence":0.65,"analysis_method":"rule_based"}'

# Verify event was stored
redis-cli LRANGE "hemostat:events:false_alarm" 0 -1
```

### Manual Inspection

```bash
# View Alert Agent logs
docker-compose logs alert

# Check all stored events
redis-cli LRANGE "hemostat:events:all" 0 -1

# Check specific event types
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1
redis-cli LRANGE "hemostat:events:false_alarm" 0 -1

# Check deduplication cache
redis-cli KEYS "hemostat:dedupe:*"
```

### Cleanup

```bash
docker stop alert-test 2>/dev/null
docker rm alert-test 2>/dev/null
```

### Success Criteria

✅ Alert Agent receives remediation complete events  
✅ Events stored in Redis with proper structure  
✅ Deduplication prevents duplicate notifications  
✅ Slack notifications sent (if webhook configured)  
✅ Event timestamps and metadata captured  
✅ False alarms stored separately

---

## Test 6: End-to-End Integration Test

**Objective**: Verify complete message flow from Monitor → Analyzer → Responder → Alert.

### Setup

```bash
# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps

# Expected: All services should be "Up" with health status "healthy"
```

### Scenario 1: High CPU Detection & Remediation

```bash
# Terminal 1: Monitor all Redis events
redis-cli SUBSCRIBE 'hemostat:*'

# Terminal 2: Create container with high CPU
docker run -d --name cpu-test busybox sh -c "while true; do : ; done"

# Wait 60-90 seconds and observe:
# 1. Monitor publishes health alert with high CPU
# 2. Analyzer publishes remediation_needed
# 3. Responder executes restart
# 4. Alert publishes remediation_complete
# 5. Container is restarted

# Verify timeline
redis-cli LRANGE "hemostat:events:all" 0 -1
```

### Scenario 2: High Memory Detection

```bash
# Terminal 2: Create container with high memory usage
docker run -d --name mem-test -m 256m busybox sh -c "dd if=/dev/zero of=/tmp/test bs=1M count=200"

# Wait 60-90 seconds and observe same flow as Scenario 1
```

### Scenario 3: Health Check Failure

```bash
# Terminal 2: Create container with failing health check
docker run -d --name health-test \
  --health-cmd='test -f /tmp/healthy' \
  --health-interval=5s \
  nginx:latest

# Wait 30 seconds for health check to fail
# Observe Monitor → Analyzer → Responder → Alert flow
```

### Verification

```bash
# Check complete event timeline
redis-cli LRANGE "hemostat:events:all" 0 -1

# Check audit logs for each container
redis-cli LRANGE "hemostat:audit:cpu-test" 0 -1
redis-cli LRANGE "hemostat:audit:mem-test" 0 -1
redis-cli LRANGE "hemostat:audit:health-test" 0 -1

# Check agent logs
docker-compose logs monitor | tail -20
docker-compose logs analyzer | tail -20
docker-compose logs responder | tail -20
docker-compose logs alert | tail -20
```

### Cleanup

```bash
docker stop cpu-test mem-test health-test 2>/dev/null
docker rm cpu-test mem-test health-test 2>/dev/null
```

### Success Criteria

✅ Monitor detects issues within 30 seconds  
✅ Analyzer analyzes within 5 seconds  
✅ Responder executes within 5 seconds  
✅ Alert stores/notifies within 2 seconds  
✅ Total detection-to-remediation: < 60 seconds  
✅ All events properly logged to Redis  
✅ Audit trail complete for each action

---

## Test 7: Safety Mechanisms Validation

**Objective**: Verify cooldown periods and circuit breakers prevent cascading failures.

### Setup

```bash
# Start Responder with short timeouts for testing
RESPONDER_COOLDOWN_SECONDS=30 RESPONDER_MAX_RETRIES_PER_HOUR=3 \
  uv run python -m agents.hemostat_responder.main
```

### Test Cooldown Period

```bash
# Terminal 2: Create test container
docker run -d --name cooldown-test nginx:latest

# Terminal 3: Trigger first remediation
redis-cli PUBLISH hemostat:remediation_needed '{"container":"cooldown-test","action":"restart","reason":"First","confidence":0.9}'

# Verify success
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1 | head -1

# Immediately trigger second remediation (within 30s cooldown)
redis-cli PUBLISH hemostat:remediation_needed '{"container":"cooldown-test","action":"restart","reason":"Second","confidence":0.9}'

# Expected: Second request rejected with "cooldown_active" status
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1 | head -1

# Wait 30 seconds and try again
sleep 30
redis-cli PUBLISH hemostat:remediation_needed '{"container":"cooldown-test","action":"restart","reason":"Third","confidence":0.9}'

# Expected: Third request succeeds (cooldown expired)
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1 | head -1
```

### Test Circuit Breaker

```bash
# Terminal 2: Create test container
docker run -d --name circuit-test nginx:latest

# Terminal 3: Trigger remediation 3 times rapidly
for i in {1..3}; do
  redis-cli PUBLISH hemostat:remediation_needed '{"container":"circuit-test","action":"restart","reason":"Attempt '$i'","confidence":0.9}'
  sleep 1
done

# Expected:
# - First two: status "success"
# - Third: status "rejected", reason "circuit_breaker_open"

# Verify in events
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1 | head -3
```

### Success Criteria

✅ Cooldown period prevents rapid-fire restarts  
✅ Circuit breaker stops after max retries  
✅ Requests rejected with clear reason  
✅ Safety constraints logged in audit trail  
✅ Prevents cascading restart loops

---

## Test 8: Docker Compose Full System Test

**Objective**: Verify entire system boots and runs from Docker Compose.

### Commands

```bash
# Clean start
docker-compose down -v
docker-compose up -d

# Wait for services to be healthy
sleep 30

# Verify all services are running
docker-compose ps

# Expected: All services "Up" with health status "healthy"

# Check logs for any errors
docker-compose logs --tail=50

# Trigger a test scenario
docker run -d --name compose-test busybox sh -c "while true; do : ; done"

# Wait 90 seconds and check events
redis-cli LRANGE "hemostat:events:all" 0 -1

# Cleanup
docker stop compose-test
docker rm compose-test
docker-compose down
```

### Success Criteria

✅ All services start without errors  
✅ Health checks pass for all services  
✅ Services communicate via Redis  
✅ Full workflow completes successfully  
✅ Clean shutdown with `docker-compose down`

---

## Troubleshooting

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping

# Check Redis logs
docker-compose logs redis

# Verify network connectivity
docker-compose exec monitor ping redis
```

### Agent Connection Issues

```bash
# Check agent logs for connection errors
docker-compose logs monitor | grep -i "error\|connection"
docker-compose logs analyzer | grep -i "error\|connection"
docker-compose logs responder | grep -i "error\|connection"
docker-compose logs alert | grep -i "error\|connection"

# Verify agents can reach Redis
docker-compose exec monitor redis-cli -h redis ping
```

### Message Flow Issues

```bash
# Subscribe to all channels
redis-cli SUBSCRIBE 'hemostat:*'

# Check specific channel
redis-cli SUBSCRIBE hemostat:health_alert

# View all keys
redis-cli KEYS 'hemostat:*'

# Debug specific container state
redis-cli GET "hemostat:state:container:test-container"
```

### Docker Socket Issues

```bash
# Verify Docker socket is accessible
ls -la /var/run/docker.sock

# Check Monitor can access Docker
docker-compose exec monitor docker ps

# Check Responder can access Docker
docker-compose exec responder docker ps
```

---

## Performance Metrics

### Expected Timings

| Component | Operation | Expected Time |
|-----------|-----------|---------------|
| Monitor | Poll interval | 30 seconds |
| Monitor | Publish alert | < 1 second |
| Analyzer | Analyze issue | 2-5 seconds |
| Analyzer | Publish decision | < 1 second |
| Responder | Execute action | 2-10 seconds |
| Responder | Publish result | < 1 second |
| Alert | Store event | < 1 second |
| Alert | Send Slack | 1-3 seconds |
| **Total** | **Detection to remediation** | **< 60 seconds** |

### Resource Usage

```bash
# Monitor resource usage
docker stats

# Expected:
# - Monitor: < 50MB memory, < 5% CPU
# - Analyzer: < 100MB memory, < 10% CPU
# - Responder: < 50MB memory, < 5% CPU
# - Alert: < 50MB memory, < 5% CPU
# - Redis: < 100MB memory, < 5% CPU
```

---

## Summary

**Phase 2 Testing Checklist**:

- [ ] Test 1: Environment & Dependencies ✅
- [ ] Test 2: Monitor Agent ✅
- [ ] Test 3: Analyzer Agent ✅
- [ ] Test 4: Responder Agent ✅
- [ ] Test 5: Alert Agent ✅
- [ ] Test 6: End-to-End Integration ✅
- [ ] Test 7: Safety Mechanisms ✅
- [ ] Test 8: Docker Compose Full System ✅

**All Phase 2 agents are implemented and ready for production use.**

Next: Phase 3 - Dashboard & Visualization

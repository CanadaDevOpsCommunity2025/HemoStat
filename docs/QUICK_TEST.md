# HemoStat Quick Test Reference

Fast commands to test Phase 2 implementation.

## One-Liner Setup

```bash
cp .env.example .env && uv sync --extra agents && docker-compose up -d redis
```

## Test 1: Dependencies (30 seconds)

```bash
python -c "import redis, docker; from langchain_openai import ChatOpenAI; print('✓ All imports OK')"
redis-cli ping
```

## Test 2: Monitor Agent (2 minutes)

**Terminal 1:**
```bash
docker-compose up -d redis
uv run python -m agents.hemostat_monitor.main
```

**Terminal 2:**
```bash
redis-cli SUBSCRIBE hemostat:health_alert
```

**Terminal 3:**
```bash
docker run -d --name test-nginx nginx:latest
# Wait 30 seconds, should see health alert in Terminal 2
docker stop test-nginx && docker rm test-nginx
```

## Test 3: Analyzer Agent (3 minutes)

**Terminal 1:**
```bash
docker-compose up -d redis
uv run python -m agents.hemostat_monitor.main
```

**Terminal 2:**
```bash
AI_FALLBACK_ENABLED=true uv run python -m agents.hemostat_analyzer.main
```

**Terminal 3:**
```bash
redis-cli SUBSCRIBE hemostat:remediation_needed hemostat:false_alarm
```

**Terminal 4:**
```bash
# Create container with sustained high CPU
docker run -d --name cpu-test busybox sh -c "while true; do : ; done"
# Wait 90 seconds, should see remediation_needed in Terminal 3
docker stop cpu-test && docker rm cpu-test
```

## Test 4: Responder Agent (3 minutes)

**Terminal 1:**
```bash
docker-compose up -d redis
uv run python -m agents.hemostat_monitor.main
```

**Terminal 2:**
```bash
AI_FALLBACK_ENABLED=true uv run python -m agents.hemostat_analyzer.main
```

**Terminal 3:**
```bash
uv run python -m agents.hemostat_responder.main
```

**Terminal 4:**
```bash
redis-cli SUBSCRIBE hemostat:remediation_complete
```

**Terminal 5:**
```bash
docker run -d --name restart-test nginx:latest
# Wait 90 seconds for Monitor/Analyzer to detect
# Then manually trigger:
redis-cli PUBLISH hemostat:remediation_needed '{"container":"restart-test","action":"restart","reason":"Test","confidence":0.9}'
# Should see remediation_complete in Terminal 4
docker stop restart-test && docker rm restart-test
```

## Test 5: Alert Agent (2 minutes)

**Terminal 1:**
```bash
docker-compose up -d
```

**Terminal 2:**
```bash
redis-cli LRANGE "hemostat:events:all" 0 -1
```

**Terminal 3:**
```bash
docker run -d --name alert-test nginx:latest
# Wait 90 seconds for full workflow
redis-cli PUBLISH hemostat:remediation_needed '{"container":"alert-test","action":"restart","reason":"Test","confidence":0.9}'
# Check Terminal 2 for stored events
docker stop alert-test && docker rm alert-test
```

## Test 6: Full End-to-End (5 minutes)

```bash
# Start all services
docker-compose up -d

# Verify all healthy
docker-compose ps

# Create test container with high CPU
docker run -d --name e2e-test busybox sh -c "while true; do : ; done"

# Monitor events in real-time
redis-cli SUBSCRIBE 'hemostat:*'

# In another terminal, check timeline
redis-cli LRANGE "hemostat:events:all" 0 -1

# Cleanup
docker stop e2e-test && docker rm e2e-test
docker-compose down
```

## Test 7: Safety Mechanisms (3 minutes)

**Cooldown Test:**
```bash
# Terminal 1
RESPONDER_COOLDOWN_SECONDS=10 uv run python -m agents.hemostat_responder.main

# Terminal 2
docker run -d --name cooldown-test nginx:latest

# Terminal 3 - Trigger twice rapidly
redis-cli PUBLISH hemostat:remediation_needed '{"container":"cooldown-test","action":"restart","reason":"1","confidence":0.9}'
sleep 2
redis-cli PUBLISH hemostat:remediation_needed '{"container":"cooldown-test","action":"restart","reason":"2","confidence":0.9}'

# Expected: First succeeds, second rejected with "cooldown_active"
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1

docker stop cooldown-test && docker rm cooldown-test
```

## Verify Events in Redis

```bash
# All events
redis-cli LRANGE "hemostat:events:all" 0 -1

# Remediation events
redis-cli LRANGE "hemostat:events:remediation_complete" 0 -1

# False alarms
redis-cli LRANGE "hemostat:events:false_alarm" 0 -1

# Audit trail for container
redis-cli LRANGE "hemostat:audit:CONTAINER_NAME" 0 -1

# Container state
redis-cli GET "hemostat:state:container:CONTAINER_NAME"
```

## Check Logs

```bash
# Monitor
docker-compose logs monitor | tail -20

# Analyzer
docker-compose logs analyzer | tail -20

# Responder
docker-compose logs responder | tail -20

# Alert
docker-compose logs alert | tail -20

# All
docker-compose logs --tail=20
```

## Troubleshooting

```bash
# Redis not responding
redis-cli ping

# Docker socket issue
docker ps

# Agent can't reach Redis
docker-compose exec monitor redis-cli -h redis ping

# Check all Redis keys
redis-cli KEYS '*'

# Monitor specific channel
redis-cli SUBSCRIBE hemostat:health_alert
```

## Expected Timings

- Monitor publishes alert: ~30 seconds
- Analyzer analyzes: ~2-5 seconds
- Responder executes: ~2-10 seconds
- Alert stores: ~1 second
- **Total detection to fix: < 60 seconds**

## Quick Cleanup

```bash
docker-compose down -v
docker system prune -f
redis-cli FLUSHALL
```

---

**Full testing guide**: [TESTING_GUIDE.md](TESTING_GUIDE.md)  
**Phase 2 summary**: [PHASE2_SUMMARY.md](PHASE2_SUMMARY.md)

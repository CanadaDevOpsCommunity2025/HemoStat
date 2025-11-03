# HemoStat Testing Guide

This guide explains how to test HemoStat using intentionally broken containers and how to configure container filtering.

## Container Blacklist

HemoStat automatically excludes its own containers from monitoring using a blacklist. By default, all containers matching `hemostat-*` are excluded.

### Configuration

Set the `MONITOR_CONTAINER_BLACKLIST` environment variable in your `.env.docker.*` files:

```bash
# Exclude HemoStat's own containers (default)
MONITOR_CONTAINER_BLACKLIST=hemostat-*

# Exclude multiple patterns (comma-separated)
MONITOR_CONTAINER_BLACKLIST=hemostat-*,test-healthy,my-app-*

# Disable blacklist (monitor all containers)
MONITOR_CONTAINER_BLACKLIST=
```

**Pattern matching supports wildcards:**
- `hemostat-*` matches `hemostat-monitor`, `hemostat-analyzer`, etc.
- `*-db` matches `postgres-db`, `mysql-db`, etc.
- `exact-name` matches only `exact-name`

## Testing with Broken Containers

The `docker-compose.test.yml` file includes several intentionally broken containers to test HemoStat's detection and remediation capabilities.

### Available Test Containers

| Container Name | Purpose | Simulates |
|---|---|---|
| `test-crash-loop` | Crashes and restarts continuously | Application crashes |
| `test-cpu-stress` | High CPU usage (>85%) | CPU saturation |
| `test-memory-stress` | High memory usage (>80%) | Memory leaks |
| `test-failing-healthcheck` | Always fails healthcheck | Unhealthy services |
| `test-oom-killer` | Exceeds memory limit | OOM kills |
| `test-random-exit` | Exits after random time | Unstable services |
| `test-combined-stress` | CPU + Memory stress | Multiple issues |
| `test-healthy` | Normal nginx container | Baseline (not monitored) |

### Running Tests

#### 1. Start HemoStat with Test Containers (Windows)

```bash
# Build and start HemoStat + test containers
docker compose -f docker-compose.yml -f docker-compose.windows.yml -f docker-compose.test.yml --env-file .env.docker.windows up -d

# Or use the Makefile
make windows
docker compose -f docker-compose.yml -f docker-compose.windows.yml -f docker-compose.test.yml up -d
```

#### 2. Start HemoStat with Test Containers (Linux)

```bash
docker compose -f docker-compose.yml -f docker-compose.linux.yml -f docker-compose.test.yml --env-file .env.docker.linux up -d
```

#### 3. Start HemoStat with Test Containers (macOS)

```bash
docker compose -f docker-compose.yml -f docker-compose.macos.yml -f docker-compose.test.yml --env-file .env.docker.macos up -d
```

### Monitoring Test Results

#### View Dashboard
Visit http://localhost:8501 to see HemoStat's real-time monitoring dashboard.

#### View Logs
```bash
# Monitor agent logs
docker compose logs -f monitor

# Analyzer agent logs
docker compose logs -f analyzer

# Responder agent logs
docker compose logs -f responder

# Alert agent logs
docker compose logs -f alert

# All HemoStat logs
docker compose logs -f monitor analyzer responder alert
```

#### Check Redis Events
```bash
# Connect to Redis
docker exec -it hemostat-redis redis-cli

# Subscribe to health alerts
SUBSCRIBE hemostat:health_alert

# View all keys
KEYS hemostat:*
```

### Expected Behavior

After starting test containers, you should see:

1. **Monitor Agent**: Detects high CPU/memory, failing healthchecks, crashes
2. **Analyzer Agent**: Analyzes issues and recommends remediation actions
3. **Responder Agent**: Attempts to remediate (restart, cleanup, etc.)
4. **Alert Agent**: Sends notifications (if configured)
5. **Dashboard**: Displays real-time metrics and alerts

### Cleanup

Stop and remove test containers:

```bash
# Stop all containers
docker compose -f docker-compose.yml -f docker-compose.windows.yml -f docker-compose.test.yml down

# Remove volumes
docker compose -f docker-compose.yml -f docker-compose.windows.yml -f docker-compose.test.yml down -v
```

## Advanced Testing Scenarios

### Test Specific Issues

Start only specific test containers:

```bash
# Test only CPU stress
docker compose -f docker-compose.test.yml up -d test-cpu-stress

# Test only crash loop
docker compose -f docker-compose.test.yml up -d test-crash-loop

# Test multiple specific containers
docker compose -f docker-compose.test.yml up -d test-cpu-stress test-memory-stress
```

### Adjust Test Duration

Modify the `--timeout` parameter in `docker-compose.test.yml`:

```yaml
test-cpu-stress:
  command: --cpu 2 --timeout 60s  # Run for 60 seconds instead of 600
```

### Add Custom Broken Containers

Add your own test containers to `docker-compose.test.yml`:

```yaml
  my-custom-test:
    image: your-image:latest
    container_name: my-custom-test
    command: your-failing-command
    restart: unless-stopped
    networks:
      - hemostat-network
```

## Blacklist Configuration Examples

### Example 1: Exclude HemoStat and Test Containers

```bash
MONITOR_CONTAINER_BLACKLIST=hemostat-*,test-*
```

### Example 2: Exclude Everything Except Production Apps

```bash
# Monitor only containers starting with 'prod-'
MONITOR_CONTAINER_BLACKLIST=hemostat-*,test-*,dev-*,staging-*
```

### Example 3: Exclude Specific Containers by Name

```bash
MONITOR_CONTAINER_BLACKLIST=hemostat-*,my-db-backup,legacy-service
```

## Troubleshooting

### Test Containers Not Being Monitored

- Check that `MONITOR_CONTAINER_BLACKLIST` doesn't include `test-*`
- Verify containers are running: `docker ps`
- Check monitor logs: `docker compose logs monitor`

### No Alerts Being Generated

- Ensure thresholds are set appropriately in `.env.docker.*`:
  - `THRESHOLD_CPU_PERCENT=85`
  - `THRESHOLD_MEMORY_PERCENT=80`
- Test containers may not exceed thresholds immediately
- Check monitor polling interval: `AGENT_POLL_INTERVAL=30`

### AI Analysis Not Working

- Verify AI API keys are set in `.env.docker.*`:
  - `ANTHROPIC_API_KEY=your-key`
  - `OPENAI_API_KEY=your-key`
  - `HUGGINGFACE_API_KEY=your-key`
- Check analyzer logs for API errors
- Rule-based analysis will be used as fallback

## Performance Impact

Test containers are designed to stress your system. Monitor your host resources:

```bash
# Check Docker stats
docker stats

# Check host resources
htop  # Linux/macOS
# or Task Manager (Windows)
```

**Recommended:** Run tests on a development machine, not production.

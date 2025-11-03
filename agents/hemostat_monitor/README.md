# HemoStat Monitor Agent

## Overview

The Monitor Agent continuously polls Docker containers to detect health issues, resource anomalies, and failures. It collects comprehensive metrics and publishes structured health alerts to Redis for consumption by downstream agents.

### Key Responsibilities

- **Container Polling**: Monitors all running containers every 30 seconds (configurable)
- **Metric Collection**: Gathers CPU, memory, network, and disk I/O metrics using Docker SDK
- **Health Checks**: Inspects container health status, exit codes, and restart counts
- **Anomaly Detection**: Identifies resource usage anomalies against configurable thresholds
- **Alert Publishing**: Publishes structured events to Redis `hemostat:health_alert` channel

## Architecture

The Monitor Agent inherits from `HemoStatAgent` base class and leverages:

- **Docker SDK 7.0.0**: Official Python Docker client for container inspection and metrics
- **Redis Pub/Sub**: Publishes health alerts for consumption by Analyzer Agent
- **Structured Logging**: JSON-formatted logs for centralized monitoring
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals cleanly

### Metric Calculation

- **CPU**: Two-sample calculation using Docker's official formula: `(delta_cpu / delta_system) × online_cpus × 100`
- **Memory**: Usage minus cache (matches `docker stats` behavior)
- **Network**: Bytes sent/received across all network interfaces
- **Disk I/O**: Bytes read/written from block devices

## Configuration

Configure the Monitor Agent via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_POLL_INTERVAL` | 30 | Polling interval in seconds |
| `THRESHOLD_CPU_PERCENT` | 85 | CPU usage alert threshold (%) |
| `THRESHOLD_MEMORY_PERCENT` | 80 | Memory usage alert threshold (%) |
| `REDIS_HOST` | redis | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FORMAT` | json | Log format (json or text) |

## Usage

### Docker Compose (Recommended)

```sh
# Start all services including monitor
docker-compose up -d

# View monitor logs
docker-compose logs -f monitor

# Stop monitor
docker-compose down
```

### Local Development

```sh
# Install dependencies (from project root)
uv sync --extra agents

# Run the monitor agent
uv run python -m agents.hemostat_monitor.main
```

### Testing Event Publishing

Subscribe to health alerts in another terminal:

```sh
redis-cli SUBSCRIBE hemostat:health_alert
```

## Event Schema

### Published Events

**Channel**: `hemostat:health_alert`  
**Event Type**: `container_unhealthy`

**Payload Structure**:

```json

{
  "container_id": "abc123def456",
  "container_name": "my-app",
  "image": "myapp:latest",
  "status": "running",
  "metrics": {
    "cpu_percent": 87.5,
    "memory_percent": 82.3,
    "memory_usage": 512000000,
    "memory_limit": 1073741824,
    "network_rx_bytes": 1000000,
    "network_tx_bytes": 500000,
    "blkio_read_bytes": 2000000,
    "blkio_write_bytes": 1000000
  },
  "anomalies": [
    {
      "type": "high_cpu",
      "severity": "high",
      "threshold": 85,
      "actual": 87.5
    },
    {
      "type": "high_memory",
      "severity": "high",
      "threshold": 80,
      "actual": 82.3
    }
  ],
  "health_status": "healthy",
  "exit_code": 0,
  "restart_count": 0
}
```

## Anomaly Detection

The Monitor Agent detects the following anomalies:

| Anomaly Type | Condition | Severity |
|--------------|-----------|----------|
| `high_cpu` | CPU > threshold (default 85%) | high/critical (>95%); medium (>68%) |
| `high_memory` | Memory > threshold (default 80%) | high/critical (>95%); medium (>64%) |
| `unhealthy_status` | Health status != healthy/unknown | high |
| `non_zero_exit` | Exit code != 0 for stopped containers | high |
| `excessive_restarts` | Restart count > 5 | medium |

### Severity Levels

- **Critical**: Metric exceeds 95% or immediate action required
- **High**: Metric exceeds configured threshold
- **Medium**: Metric exceeds 80% of threshold (e.g., CPU > 68% when threshold is 85%)

## Metrics Explained

### CPU Percentage

Uses Docker's official two-sample calculation to avoid spurious readings:

```python
cpu_delta = current_total_usage - previous_total_usage

system_delta = current_system_usage - previous_system_usage

cpu_percent = (cpu_delta / system_delta) * online_cpus * 100
```

### Memory Percentage

Excludes cache to match `docker stats` behavior:

```python
usage = memory_stats['usage']
cache = memory_stats['stats'].get('inactive_file', 0)
actual_usage = usage - cache
memory_percent = (actual_usage / limit) * 100
```

## Troubleshooting

### "Cannot connect to Docker daemon"

**Cause**: Docker socket not accessible or not mounted

**Solution**:

- Ensure Docker socket is mounted: `/var/run/docker.sock:/var/run/docker.sock:ro`
- Verify user has Docker group membership: `groups $USER`
- Check Docker daemon is running: `docker ps`

### "Redis connection failed"

**Cause**: Redis service not running or incorrect host/port

**Solution**:

- Verify Redis is running: `redis-cli ping`
- Check `REDIS_HOST` and `REDIS_PORT` in `.env`
- Ensure Redis is accessible from agent container

### "No containers found"

**Cause**: No containers running or Docker API permissions issue

**Solution**:

- List running containers: `docker ps`
- Check Docker socket permissions: `ls -la /var/run/docker.sock`
- Verify agent user has Docker access

### "Permission denied on Docker socket"

**Cause**: Agent user lacks Docker socket permissions

**Solution**:

- Add user to docker group: `sudo usermod -aG docker $USER`
- Or run with appropriate permissions in Docker

### "High CPU usage by monitor"

**Cause**: Polling interval too short or too many containers

**Solution**:

- Increase `AGENT_POLL_INTERVAL` in `.env` (default 30s)
- Reduce number of monitored containers
- Check Docker daemon performance

## Development

### Adding New Metrics

1. Update `_get_container_stats()` to extract metric from Docker stats
2. Add calculation method if needed (e.g., `_calculate_custom_metric()`)
3. Add anomaly detection in `_detect_anomalies()`
4. Include in published alert payload

### Customizing Anomaly Detection

Edit `_detect_anomalies()` method to:
- Add new anomaly types
- Adjust severity levels
- Modify threshold logic

### Running Tests

Tests are planned for Phase 4. See main project README for testing setup.

## Dependencies

All dependencies are managed through UV and defined in the root `pyproject.toml`:

**Base dependencies** (Phase 1):
- `redis==5.0.1` - Redis client library
- `python-dotenv==1.0.0` - Environment variable loading
- `python-json-logger==2.0.7` - Structured JSON logging

**Agent dependencies** (Phase 2 - agents extra group):
- `docker==7.0.0` - Docker SDK for Python (Monitor Agent)
- `langchain==0.1.0` - LLM orchestration (Analyzer Agent)
- `openai==1.10.0` - OpenAI GPT-4 integration
- `anthropic==0.8.0` - Anthropic Claude integration
- `requests==2.31.0` - HTTP client (Alert Agent)

Install with: `uv sync --extra agents`

## Next Steps

The Monitor Agent publishes health alerts to the `hemostat:health_alert` Redis channel. These events are consumed by:

- **Analyzer Agent** (Phase 2 - Next): Performs AI-powered root cause analysis
- **Responder Agent** (Phase 2): Executes safe remediation actions
- **Alert Agent** (Phase 2): Sends notifications to Slack, email, etc.

See the main project README for architecture overview and integration details.
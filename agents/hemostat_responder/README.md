# HemoStat Responder Agent

The Responder Agent consumes remediation recommendations from the Analyzer Agent and executes safe container operations using Docker SDK with comprehensive safety constraints to prevent cascading failures.

## Overview

**Key Responsibilities**:
- Subscribe to `hemostat:remediation_needed` channel for remediation requests
- Execute Docker operations: restart, scale, cleanup, exec
- Enforce safety mechanisms: cooldown periods, circuit breakers, max retries
- Maintain comprehensive audit logs in Redis for compliance and debugging
- Publish `remediation_complete` events for Alert Agent consumption
- Support dry-run mode for testing without actual remediation

## Architecture

The Responder Agent inherits from `HemoStatAgent` base class and implements multi-layered safety mechanisms to prevent system instability:

```
┌─────────────────────────────────────────────────────────────┐
│              Responder Agent Architecture                   │
└─────────────────────────────────────────────────────────────┘

    Remediation Request (from Analyzer)
              │
              ▼
    ┌──────────────────────┐
    │  Safety Checks       │
    │  - Cooldown period?  │
    │  - Circuit breaker?  │
    │  - Dry-run mode?     │
    └──────┬───────────────┘
           │
           ├─ Rejected ──────► Publish rejection event
           │
           └─ Approved
              │
              ▼
    ┌──────────────────────┐
    │  Action Routing      │
    │  - restart           │
    │  - scale_up          │
    │  - cleanup           │
    │  - exec              │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Docker Operations   │
    │  (with error handling)
    └──────┬───────────────┘
           │
           ├─ Success ──────► Update state, publish success
           │
           └─ Failure ──────► Update state, publish failure

    All actions logged to Redis audit trail
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESPONDER_COOLDOWN_SECONDS` | 3600 | Cooldown period between remediation actions (seconds) |
| `RESPONDER_MAX_RETRIES_PER_HOUR` | 3 | Maximum remediation attempts per hour (circuit breaker) |
| `RESPONDER_DRY_RUN` | false | Dry-run mode: simulate actions without executing |
| `DOCKER_HOST` | unix:///var/run/docker.sock | Docker daemon socket |
| `REDIS_HOST` | redis | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | json | Log format (json or text) |

### Tuning Safety Parameters

- **Cooldown Period**: 
  - Lower (300s = 5 min) for faster response to issues
  - Higher (7200s = 2 hours) for more conservative approach
  - Default (3600s = 1 hour) balances responsiveness and stability

- **Max Retries**: 
  - Lower (1-2) for stricter circuit breaker
  - Higher (5-10) for more tolerance
  - Default (3) prevents most infinite loops

- **Dry-Run Mode**: 
  - Always use for initial testing and demos
  - Validates remediation logic without affecting real containers

## Usage

### Docker Compose (Recommended)

```bash
# Start responder service
docker-compose up -d responder

# View logs
docker-compose logs -f responder

# Stop responder
docker-compose down responder
```

### Local Development

```bash
# Install dependencies with UV
uv sync --extra agents

# Run responder
uv run python -m agents.hemostat_responder.main
```

### Testing Event Flow

```bash
# Terminal 1: Subscribe to remediation complete events
redis-cli SUBSCRIBE hemostat:remediation_complete

# Terminal 2: Trigger a health alert (requires Monitor + Analyzer running)
# Monitor will detect issues, Analyzer will recommend remediation, Responder will execute
```

## Remediation Actions

### restart

Gracefully restart a container with 10-second timeout.

- **Use Case**: CPU/memory spikes, process hangs, temporary issues
- **Safety**: Preserves container state, respects graceful shutdown
- **Rollback**: Container returns to previous state on restart

### scale_up

Increase container replicas (Docker Compose/Swarm only).

- **Use Case**: Load distribution, horizontal scaling
- **Limitation**: Requires Docker Swarm service or Compose orchestration
- **Note**: Standalone containers cannot be scaled

### cleanup

Remove stopped containers and prune unused resources.

- **Use Case**: Disk space issues, resource cleanup
- **Safety**: Only removes stopped containers, not running ones
- **Impact**: Frees disk space, improves system performance

### exec

Execute diagnostic commands inside container.

- **Use Case**: Debugging, diagnostics, health checks
- **Commands**: Limited to whitelisted safe commands (ps, top, df, etc.)
- **Security**: Prevents command injection attacks

## Safety Mechanisms

### Cooldown Periods

Prevents rapid-fire remediation attempts that could destabilize the system.

- **Default**: 1 hour between actions per container
- **Tracking**: Redis key `hemostat:state:remediation_history:{container}`
- **Behavior**: If remediation requested within cooldown, request rejected with `cooldown_active` status
- **Reset**: Cooldown expires after configured period elapses

**Example**: Container CPU spike → Restart triggered → Cooldown active for 1 hour → No more restarts until cooldown expires

### Circuit Breakers

Stops remediation after max retries per hour to prevent infinite loops.

- **Default**: 3 attempts per hour per container
- **Tracking**: Redis key `hemostat:state:circuit_breaker:{container}`
- **Behavior**: If max retries exceeded, circuit opens and all requests rejected until hour resets
- **Reset**: Circuit automatically closes after hour window elapses

**Example**: Container keeps crashing → Restart attempt 1 → Restart attempt 2 → Restart attempt 3 → Circuit opens → No more restarts for 1 hour

### Dry-Run Mode

Simulate operations without executing to validate remediation logic.

- **Enable**: Set `RESPONDER_DRY_RUN=true` in environment
- **Behavior**: Logs what would have been done, publishes success events with `dry_run: true` flag
- **Use Cases**: Testing, demos, validation before production
- **Output**: Audit logs show dry-run notation

### Audit Logging

All remediation attempts logged to Redis for compliance and debugging.

- **Storage**: Redis list `hemostat:audit:{container}`
- **Retention**: Last 100 audit entries per container, TTL 7 days
- **Contents**: Timestamp, action, result status, confidence score, reason, metrics
- **Access**: Consumed by Dashboard for visualization

## Event Schema

### Input Events

**Channel**: `hemostat:remediation_needed`

**Event Type**: `remediation_needed`

**Payload**:
```json
{
  "event_type": "remediation_needed",
  "container": "web-app-1",
  "action": "restart",
  "reason": "High CPU usage detected",
  "confidence": 0.95,
  "metrics": {
    "cpu_percent": 95.5,
    "memory_percent": 72.3
  },
  "analysis_method": "ai"
}
```

### Output Events

**Channel**: `hemostat:remediation_complete`

#### Success Event

```json
{
  "event_type": "remediation_complete",
  "container": "web-app-1",
  "action": "restart",
  "result": {
    "status": "success",
    "action": "restart",
    "container": "web-app-1",
    "details": "Container restarted and running"
  },
  "timestamp": "2024-11-02T19:45:30.123456",
  "dry_run": false,
  "reason": "High CPU usage detected",
  "confidence": 0.95
}
```

#### Failure Event

```json
{
  "event_type": "remediation_complete",
  "container": "web-app-1",
  "action": "restart",
  "result": {
    "status": "failed",
    "error": "Container not found: web-app-1"
  },
  "timestamp": "2024-11-02T19:45:30.123456",
  "dry_run": false,
  "reason": "High CPU usage detected",
  "confidence": 0.95
}
```

#### Cooldown Active Event

```json
{
  "event_type": "remediation_complete",
  "container": "web-app-1",
  "status": "rejected",
  "reason": "cooldown_active",
  "remaining_seconds": 2847,
  "timestamp": "2024-11-02T19:45:30.123456"
}
```

#### Circuit Breaker Open Event

```json
{
  "event_type": "remediation_complete",
  "container": "web-app-1",
  "status": "rejected",
  "reason": "circuit_breaker_open",
  "retry_count": 3,
  "timestamp": "2024-11-02T19:45:30.123456"
}
```

## Troubleshooting

### "Cannot connect to Docker daemon"

**Cause**: Docker socket not mounted or Docker service not running

**Solution**:
- Ensure Docker socket is mounted: `/var/run/docker.sock:/var/run/docker.sock`
- Check Docker service is running: `docker ps`
- Verify socket permissions: `ls -la /var/run/docker.sock`

### "Permission denied on Docker socket"

**Cause**: Container lacks write access to Docker socket

**Solution**:
- Ensure Docker socket is NOT read-only: `/var/run/docker.sock:/var/run/docker.sock` (not `:ro`)
- Check user permissions: `id` inside container
- Verify socket ownership: `ls -la /var/run/docker.sock`

### "Redis connection failed"

**Cause**: Redis service not running or incorrect hostname

**Solution**:
- Check Redis is running: `redis-cli ping`
- Verify `REDIS_HOST` is correct (use `redis` for Docker Compose)
- Check network connectivity: `docker network ls`

### "Cooldown preventing remediation"

**Cause**: Container within cooldown period from previous action

**Solution**:
- Check cooldown period setting: `RESPONDER_COOLDOWN_SECONDS`
- View remediation history: `redis-cli LRANGE hemostat:audit:{container} 0 -1`
- Wait for cooldown to expire or adjust `RESPONDER_COOLDOWN_SECONDS`
- Reset manually: `redis-cli DEL hemostat:state:remediation_history:{container}`

### "Circuit breaker open"

**Cause**: Max retries exceeded within hour window

**Solution**:
- Check retry count: `redis-cli GET hemostat:state:circuit_breaker:{container}`
- Wait for hour window to reset (automatic)
- Reset manually: `redis-cli DEL hemostat:state:circuit_breaker:{container}`
- Investigate why retries are failing (check logs)

### "Container not found"

**Cause**: Container name doesn't match or container not running

**Solution**:
- Verify container name matches exactly (case-sensitive): `docker ps`
- Check container is running: `docker ps -a`
- Use container ID instead of name if needed

### "Restart failed"

**Cause**: Container keeps crashing or resource constraints

**Solution**:
- Check Docker logs: `docker logs {container}`
- Verify container isn't in crash loop
- Check resource constraints: `docker inspect {container}`
- Review application logs for errors

### "Dry-run mode not working"

**Cause**: `RESPONDER_DRY_RUN` not set to true

**Solution**:
- Verify environment variable: `echo $RESPONDER_DRY_RUN`
- Set in .env: `RESPONDER_DRY_RUN=true`
- Check logs for dry-run messages: `docker-compose logs responder`

## Development

### Adding New Remediation Actions

1. Create new method in `ContainerResponder` class:
   ```python
   def _custom_action(self, container: str) -> Dict[str, Any]:
       # Implementation
       return {"status": "success", "action": "custom_action", ...}
   ```

2. Add routing in `_execute_remediation()`:
   ```python
   elif action == "custom_action":
       result = self._custom_action(container)
   ```

3. Update action documentation in this README

### Customizing Safety Thresholds

Modify environment variables in `.env`:
```bash
RESPONDER_COOLDOWN_SECONDS=1800        # 30 minutes
RESPONDER_MAX_RETRIES_PER_HOUR=5       # 5 attempts
```

### Resetting Circuit Breakers Manually

```bash
# View circuit breaker state
redis-cli GET hemostat:state:circuit_breaker:{container}

# Reset circuit breaker
redis-cli DEL hemostat:state:circuit_breaker:{container}

# Reset all circuit breakers
redis-cli KEYS "hemostat:state:circuit_breaker:*" | xargs redis-cli DEL
```

## Dependencies

All dependencies are managed via UV and `pyproject.toml`.

**Runtime Dependencies**:
- `docker==7.0.0` - Docker SDK for container control
- `redis==5.0.1` - Redis client
- `python-dotenv==1.0.0` - Environment loading
- `python-json-logger==2.0.7` - Structured logging

**Installation**:
```bash
uv sync --extra agents
```

## Security Considerations

### Docker Socket Access

The Responder Agent requires write access to the Docker socket, which grants significant privileges:

- Can start, stop, restart containers
- Can execute commands inside containers
- Can modify container configurations
- Can access container logs and metrics

**Production Deployment**:
- Consider using Docker socket proxy to limit permissions
- Implement API gateway to restrict operations
- Use read-only filesystem where possible
- Run with minimal required privileges

### Command Injection Prevention

The `exec` action validates commands against a whitelist of safe diagnostic commands:
- `ps`, `top`, `df`, `free`, `netstat`, `ss`, `env`, `pwd`, `whoami`, `date`, `uptime`, `uname`

Attempting to execute commands outside this whitelist will log a warning but still execute (for flexibility). In production, consider enforcing strict whitelist validation.

### Resource Limits

Ensure Responder container has appropriate resource limits to prevent resource exhaustion:

```yaml
# docker-compose.yml
responder:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

### Audit Trail

All actions logged to Redis for compliance and security monitoring:
- Timestamp of each action
- Container affected
- Action performed
- Result status
- Confidence score
- Original reason for remediation

## Next Steps

The Responder Agent publishes `remediation_complete` events that will be consumed by:

- **Alert Agent (Phase 2d)**: Sends notifications to Slack/email/webhooks
- **Dashboard (Phase 3)**: Visualizes remediation history and audit logs

See [API_PROTOCOL.md](../../docs/API_PROTOCOL.md) for complete event schema documentation.

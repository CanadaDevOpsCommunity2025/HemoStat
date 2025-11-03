# API Protocol

HemoStat agents communicate through Redis pub/sub channels and shared state. This document describes the message formats and communication patterns.

## Redis Pub/Sub Channels

### Health Alert Channel

**Channel:** `hemostat:health_alert`

**Publisher:** Monitor Agent

**Subscriber:** Analyzer Agent

Message format:

```json
{
  "timestamp": "2025-11-03T10:30:45.123456",
  "agent": "HemoStat-Monitor",
  "type": "health_alert",
  "data": {
    "container": "hemostat-test-api",
    "issues": ["High CPU: 92.5%"],
    "metrics": {
      "name": "hemostat-test-api",
      "status": "running",
      "memory_pct": 45.2,
      "cpu_pct": 92.5,
      "timestamp": "2025-11-03T10:30:45"
    }
  }
}
```

### Remediation Needed Channel

**Channel:** `hemostat:remediation_needed`

**Publisher:** Analyzer Agent

**Subscriber:** Responder Agent

Message format:

```json
{
  "timestamp": "2025-11-03T10:30:48.456789",
  "agent": "HemoStat-Analyzer",
  "type": "remediation_needed",
  "data": {
    "container": "hemostat-test-api",
    "action": "restart",
    "reason": "CPU contention",
    "confidence": 0.9,
    "metrics": {
      "name": "hemostat-test-api",
      "memory_pct": 45.2,
      "cpu_pct": 92.5
    }
  }
}
```

### Remediation Complete Channel

**Channel:** `hemostat:remediation_complete`

**Publisher:** Responder Agent

**Subscriber:** Alert Agent

Message format:

```json
{
  "timestamp": "2025-11-03T10:30:53.789012",
  "agent": "HemoStat-Responder",
  "type": "remediation_complete",
  "data": {
    "container": "hemostat-test-api",
    "action": "restart",
    "result": {
      "status": "success",
      "action": "restart",
      "container": "hemostat-test-api"
    }
  }
}
```

### False Alarm Channel

**Channel:** `hemostat:false_alarm`

**Publisher:** Analyzer Agent

**Subscriber:** Alert Agent

Message format:

```json
{
  "timestamp": "2025-11-03T10:30:48.456789",
  "agent": "HemoStat-Analyzer",
  "type": "false_alarm",
  "data": {
    "container": "hemostat-test-api",
    "reason": "Transient spike, back to normal"
  }
}
```

## Redis Key Structure

### Container Stats

**Key:** `hemostat:stats:<container_name>`

**TTL:** 300 seconds

**Type:** JSON string

```json
{
  "name": "hemostat-test-api",
  "status": "running",
  "memory_pct": 45.2,
  "cpu_pct": 22.1,
  "timestamp": "2025-11-03T10:30:45"
}
```

### Remediation History

**Key:** `hemostat:remediation:<container_name>`

**TTL:** 3600 seconds

**Type:** JSON string

```json
{
  "last_action": "2025-11-03T10:30:53",
  "count": 1
}
```

### Event Log

**Key:** `hemostat:events:<event_type>`

**TTL:** 3600 seconds

**Type:** JSON array (max 100 events)

```json
[
  {
    "timestamp": "2025-11-03T10:30:48",
    "agent": "HemoStat-Analyzer",
    "type": "remediation_needed",
    "data": {}
  }
]
```

## Agent Base Class

All agents inherit from `HemoStatAgent` which provides Redis pub/sub primitives and state management. See the [API Reference](api/agents.rst) for complete documentation of:

- `publish_event()` - Publish events to Redis channels
- `subscribe_to_channel()` - Subscribe to Redis channels
- `start_listening()` - Start listening for events
- `get_shared_state()` - Read shared state from Redis
- `set_shared_state()` - Write shared state to Redis

## Error Handling

### On Connection Loss

- All agents implement automatic retry logic
- Exponential backoff starting at 1 second
- Maximum 10 retries before failing

### On Invalid Message

- Log error, skip message
- Continue processing next message
- No cascading failures

### On Remediation Failure

- Log error details
- Don't retry immediately (cooldown applies)
- Update status to "failed"

## Monitoring Communication

### View All Events

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE "hemostat:*"
```

### View Specific Channel

```bash
docker exec hemostat-redis redis-cli SUBSCRIBE "hemostat:remediation_needed"
```

### Check Event Backlog

```bash
docker exec hemostat-redis redis-cli KEYS "hemostat:events:*"
docker exec hemostat-redis redis-cli GET "hemostat:events:remediation_complete"
```

## Integration Points

### Custom Analyzer

1. Subscribe to `hemostat:health_alert`
2. Implement custom analysis logic
3. Publish to `hemostat:remediation_needed` or `hemostat:false_alarm`

See the [Analyzer Agent API documentation](api/agents.rst) for implementation details.

### Custom Responder

1. Subscribe to `hemostat:remediation_needed`
2. Implement custom remediation logic
3. Publish to `hemostat:remediation_complete`

See the [Responder Agent API documentation](api/agents.rst) for implementation details.

### Custom Dashboard

1. Read from `hemostat:stats:*` for current metrics
2. Read from `hemostat:events:*` for history
3. Subscribe to relevant channels for live updates

See the [Dashboard API documentation](api/dashboard.rst) for implementation details.

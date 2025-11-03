# HemoStat Agent Communication Protocol

## Redis Pub/Sub Channels

### Health Alert Channel

**Channel:** `hemostat:health_alert`
**Publisher:** HemoStat Monitor
**Subscriber:** HemoStat Analyzer

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
**Publisher:** HemoStat Analyzer
**Subscriber:** HemoStat Responder

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
**Publisher:** HemoStat Responder
**Subscriber:** HemoStat Alert

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
**Publisher:** HemoStat Analyzer
**Subscriber:** HemoStat Alert

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
    "data": {...}
  }
]
```

## Agent Base Class

All agents inherit from `HemoStatAgent`:

```python
class HemoStatAgent:
    def publish_event(self, event_type: str, data: Dict) -> None
    def get_shared_state(self, key: str) -> Optional[Dict]
    def set_shared_state(self, key: str, value: Dict) -> None
```

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

### Custom Responder

1. Subscribe to `hemostat:remediation_needed`
2. Implement custom remediation logic
3. Publish to `hemostat:remediation_complete`

### Custom Dashboard

1. Read from `hemostat:stats:*` for current metrics
2. Read from `hemostat:events:*` for history
3. Subscribe to relevant channels for live updates

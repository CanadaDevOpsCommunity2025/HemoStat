# HemoStat Alert Agent

## Overview

The Alert Agent consumes remediation completion and false alarm events, sends human-readable Slack notifications, stores events in Redis for dashboard consumption, and provides a comprehensive audit trail of all system actions.

### Key Responsibilities

- Subscribe to `hemostat:remediation_complete` and `hemostat:false_alarm` channels
- Send rich, color-coded Slack notifications with event details
- Store events in Redis lists (`hemostat:events:*` keys) for dashboard consumption
- Implement event deduplication to prevent notification spam
- Provide comprehensive audit trail of all system actions
- Support graceful degradation (continue processing if Slack fails)

## Architecture

The Alert Agent inherits from `HemoStatAgent` base class and implements the following architecture:

- **Event Subscription**: Dual-channel subscription to `hemostat:remediation_complete` and `hemostat:false_alarm`
- **Slack Integration**: Uses `requests` library for HTTP webhook calls (already in pyproject.toml)
- **Event Storage**: Redis lists with TTL for automatic cleanup and dashboard consumption
- **Deduplication**: Redis cache with short TTL to prevent duplicate notifications
- **Error Handling**: Graceful degradation with exponential backoff retry logic

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_WEBHOOK_URL` | (empty) | Slack incoming webhook URL (leave empty to disable) |
| `ALERT_ENABLED` | `true` | Master switch for all notifications |
| `ALERT_EVENT_TTL` | `3600` | Redis event storage TTL in seconds (1 hour) |
| `ALERT_MAX_EVENTS` | `100` | Maximum events to keep per event type |
| `ALERT_DEDUPE_TTL` | `60` | Event deduplication cache TTL in seconds |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_PASSWORD` | (empty) | Redis password (if required) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `text` | Log format (text or json) |

### Obtaining Slack Webhook URL

1. Visit https://api.slack.com/messaging/webhooks
2. Create a new Slack app or use existing app
3. Enable Incoming Webhooks feature
4. Add webhook to workspace and copy URL
5. Paste URL into `.env` file as `SLACK_WEBHOOK_URL`

Example:

```sh
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/
```

## Usage

### Docker Compose (Recommended)

```sh
# Ensure SLACK_WEBHOOK_URL is set in .env
docker-compose up -d alert

# View logs
docker-compose logs -f alert
```

### Local Development

```sh
# Install dependencies with UV
uv sync --extra agents

# Set Slack webhook URL in .env
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Run alert agent
uv run python -m agents.hemostat_alert.main
```

### Testing Event Flow

```sh
# Terminal 1: Run all agents
docker-compose up -d

# Terminal 2: Monitor Slack notifications (check Slack channel)
# Or subscribe to Redis events
redis-cli SUBSCRIBE hemostat:remediation_complete hemostat:false_alarm

# Terminal 3: View stored events
redis-cli LRANGE hemostat:events:remediation_complete 0 -1
redis-cli LRANGE hemostat:events:false_alarm 0 -1
redis-cli LRANGE hemostat:events:all 0 -1
```

## Slack Notification Format

### Message Structure

The Alert Agent sends rich Slack messages with color-coded attachments:

- **Attachments**: Rich formatting with color coding
- **Color Coding**:
  - Green (#36a64f): Successful remediation
  - Red (#ff0000): Failed remediation
  - Orange (#ff9900): Rejected (cooldown/circuit breaker)
  - Yellow (#ffcc00): False alarm
  - Gray (#cccccc): Not applicable
- **Fields**: Container, Action, Status, Reason, Confidence, Dry Run flag, Error details
- **Footer**: Timestamp and agent attribution
- **Emojis**: ✅ success, ❌ failed, ⏸️ rejected, ⚠️ false alarm

### Example Notifications

**Successful Remediation**:
```
✅ Container Remediation: Success
Container: web-app-1
Action: restart
Status: Success
Confidence: 95%
```

**Failed Remediation**:
```
❌ Container Remediation: Failed
Container: db-service
Action: scale_up
Status: Failed
Reason: Docker API error
Error: Connection refused
```

**False Alarm**:
```
⚠️ False Alarm Detected
Container: cache-service
Reason: Temporary CPU spike
Confidence: 65%
Analysis Method: AI
```

## Event Storage

### Redis Structure

Events are stored in Redis lists for dashboard consumption:

- **Keys**: `hemostat:events:remediation_complete`, `hemostat:events:false_alarm`, `hemostat:events:all`
- **Type**: Redis lists (LPUSH for newest first)
- **TTL**: Configurable (default 1 hour)
- **Max Size**: Configurable (default 100 events per type)
- **Trimming**: Automatic via LTRIM to prevent unbounded growth

### Event Entry Structure

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "agent": "alert",
  "event_type": "remediation_complete",
  "data": {
    "container": "web-app-1",
    "action": "restart",
    "result": "success",
    "dry_run": false,
    "reason": "High CPU detected",
    "confidence": 0.95
  }
}
```

### Dashboard Integration (Phase 3)

The Dashboard will consume these events by:

- Reading from Redis lists using `LRANGE hemostat:events:all 0 99`
- Displaying in timeline view
- Filtering by event type
- Showing event details on click

## Event Deduplication

### Mechanism

The Alert Agent implements deduplication to prevent duplicate Slack notifications:

- Generates hash from key fields: `container`, `action`/`reason`, `timestamp` (rounded to minute)
- Checks Redis cache for recent sends
- Skips Slack notification if duplicate detected
- Caches event hash with short TTL (default 60 seconds)

### Why Deduplication Matters

- Prevents spam if same event published multiple times
- Reduces Slack notification noise
- Improves user experience

**Note**: Events are still stored in Redis even if Slack notification is skipped.

## Event Schema

### Input Events

#### Remediation Complete

- **Channel**: `hemostat:remediation_complete`
- **Event Type**: `remediation_complete`
- **Payload**:
  - `container` (string): Container name or ID
  - `action` (string): Remediation action (restart, scale_up, cleanup, exec)
  - `result` (string): Result status (success, failed, rejected, not_applicable)
  - `dry_run` (boolean): Whether action was simulated
  - `reason` (string): Reason for rejection or failure
  - `confidence` (float): Confidence score (0-1)
  - `error` (string, optional): Error details if failed

Example:

```json
{
  "container": "web-app-1",
  "action": "restart",
  "result": "success",
  "dry_run": false,
  "reason": "High CPU detected",
  "confidence": 0.95
}
```

#### False Alarm

- **Channel**: `hemostat:false_alarm`
- **Event Type**: `false_alarm`
- **Payload**:
  - `container` (string): Container name or ID
  - `reason` (string): Reason for false alarm classification
  - `confidence` (float): Confidence score (0-1)
  - `analysis_method` (string): Analysis method (AI or rule-based)

Example:

```json
{
  "container": "cache-service",
  "reason": "Temporary CPU spike",
  "confidence": 0.65,
  "analysis_method": "AI"
}
```

### Stored Events

Events stored in Redis have the same structure as input events, wrapped with metadata:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "agent": "alert",
  "event_type": "remediation_complete",
  "data": {
    "container": "web-app-1",
    "action": "restart",
    "result": "success",
    "dry_run": false,
    "reason": "High CPU detected",
    "confidence": 0.95
  }
}
```

## Troubleshooting

### Slack notifications not working

**Problem**: Slack notifications are not being sent.

**Solutions**:
- Check `SLACK_WEBHOOK_URL` is set correctly in `.env`
- Verify webhook URL is valid (starts with `https://hooks.slack.com/`)
- Test webhook with curl: `curl -X POST -H 'Content-type: application/json' --data '{"text":"test"}' YOUR_WEBHOOK_URL`
- Check logs for HTTP errors: `docker-compose logs alert | grep -i slack`

### Invalid webhook URL error

**Problem**: "Invalid Slack webhook URL format" warning in logs.

**Solutions**:
- Verify webhook URL format (must start with `https://hooks.slack.com/`)
- Ensure no extra spaces or quotes in URL
- Regenerate webhook URL in Slack if needed

### Slack rate limit errors (429)

**Problem**: "Slack rate limit (429)" warnings in logs.

**Solutions**:
- Reduce notification frequency by increasing `ALERT_DEDUPE_TTL`
- Increase `ALERT_DEDUPE_TTL` to reduce duplicate notifications
- Contact Slack support for rate limit increase if necessary

### Events not stored in Redis

**Problem**: Events are not appearing in Redis lists.

**Solutions**:
- Check Redis connection: `redis-cli ping`
- Verify `ALERT_ENABLED=true` in `.env`
- Check logs for Redis errors: `docker-compose logs alert | grep -i redis`
- Verify Redis has sufficient memory: `redis-cli INFO memory`

### Duplicate notifications

**Problem**: Receiving duplicate Slack notifications for the same event.

**Solutions**:
- Increase `ALERT_DEDUPE_TTL` (default 60s)
- Check if multiple Alert Agent instances are running
- Verify event hash generation logic in logs

### Redis connection failed

**Problem**: "Redis connection failed" error in logs.

**Solutions**:
- Check Redis service is running: `docker-compose ps redis`
- Verify `REDIS_HOST` is correct (default: `redis` in Docker Compose)
- Check network connectivity: `docker-compose exec alert ping redis`

### Agent crashes on Slack failure

**Problem**: Alert Agent crashes when Slack webhook fails.

**Solutions**:
- This should not happen - check logs for unexpected exceptions
- Verify error handling is working: `docker-compose logs alert | grep -i exception`
- Report issue if error handling is not working as expected

## Development

### Adding New Notification Channels

To add support for email, PagerDuty, or other notification channels:

1. Create new method: `_send_email_notification()` or `_send_pagerduty_notification()`
2. Add configuration variables to `.env.example`
3. Update `_send_slack_notification()` to call new method
4. Update documentation with new channel details

### Customizing Slack Message Format

To customize Slack message format:

1. Modify `_format_remediation_notification()` method
2. Modify `_format_false_alarm_notification()` method
3. Adjust color coding, fields, emojis as needed
4. Test with `docker-compose up -d alert`

### Adding New Event Types

To subscribe to additional event types:

1. Add new channel subscription in `__init__()`: `self.subscribe_to_channel("new:channel", self._handle_new_event)`
2. Create handler method: `_handle_new_event(message)`
3. Call `_store_event()` and `_send_slack_notification()` as needed
4. Update documentation with new event type

## Dependencies

All dependencies are managed via UV and `pyproject.toml`.

### Runtime Dependencies

From `[project.optional-dependencies.agents]`:

- `requests==2.31.0` - HTTP client for Slack webhooks
- `redis==5.0.1` - Redis client (from base dependencies)
- `python-dotenv==1.0.0` - Environment loading (from base dependencies)
- `python-json-logger==2.0.7` - Structured logging (from base dependencies)

### Installation

```sh
# Install with UV
uv sync --extra agents
```

## Security Considerations

### Webhook URL Security

- Never commit `.env` file to version control
- Rotate webhook URL if compromised
- Use Slack's webhook URL validation
- Store webhook URL in secure environment variable

### Event Data

- Sensitive data (API keys, passwords) should never be included in events
- Sanitize error messages before sending to Slack
- Review event payloads for sensitive information

### Rate Limiting

- Implement deduplication to prevent abuse
- Respect Slack's rate limits
- Monitor rate limit errors in logs

### Network Security

- Use HTTPS for webhook calls (enforced by Slack)
- Validate SSL certificates
- Use secure Redis connections if exposed to network

## Next Steps

### Phase 3: Dashboard

The Dashboard will consume events stored in Redis and provide:

- Timeline view of all system actions
- Filtering by event type, container, status
- Event details on click
- Real-time updates via WebSocket

See Dashboard documentation (Phase 3) for integration details.

### Phase 2 Complete

All four Phase 2 agents are now implemented:

- ✅ Monitor Agent: Container health polling
- ✅ Analyzer Agent: AI-powered root cause analysis
- ✅ Responder Agent: Safe remediation execution
- ✅ Alert Agent: Multi-channel notifications

The system is ready for Phase 3 (Dashboard) integration.
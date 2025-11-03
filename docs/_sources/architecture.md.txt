# System Architecture

HemoStat uses a multi-agent architecture where specialized agents communicate through Redis pub/sub to monitor, analyze, and remediate container health issues.

## System Overview

```{mermaid}
graph TD
    A["Monitor Agent<br/>Polls Docker every 30s"] -->|publishes health_alert| B["Analyzer Agent<br/>AI-powered root cause analysis"]
    B -->|publishes remediation_needed| C["Responder Agent<br/>Executes safe fixes"]
    C -->|publishes remediation_complete| D["Alert Agent<br/>Sends notifications"]
    D -->|updates Redis| E["Dashboard<br/>Real-time visualization"]
    B -->|publishes false_alarm| D
    A -->|events| M["Metrics Exporter<br/>Prometheus metrics"]
    B -->|events| M
    C -->|events| M
    D -->|events| M
    M -->|scraped by| P["Prometheus + Grafana<br/>Historical analysis"]
```

## Agent Roles and Responsibilities

### Monitor Agent

- Continuously polls Docker container metrics every 30 seconds
- Collects CPU, memory, disk, and process status
- Detects anomalies using statistical analysis
- Publishes `health_alert` events to Redis

### Analyzer Agent

- Subscribes to `health_alert` channel
- Performs AI-powered root cause analysis using Claude or GPT-4
- Distinguishes real issues from false alarms with confidence scoring
- Publishes `remediation_needed` or `false_alarm` events

### Responder Agent

- Subscribes to `remediation_needed` channel
- Executes remediation actions (restart, scale, cleanup, exec)
- Enforces comprehensive safety constraints:
  - Cooldown periods (1 hour default)
  - Circuit breakers (max 3 retries/hour)
  - Dry-run mode support
  - Audit logging for compliance
- Publishes `remediation_complete` events

### Alert Agent

- Subscribes to `remediation_complete` and `false_alarm` channels
- Sends notifications to external systems (Slack webhooks)
- Stores events in Redis for dashboard consumption
- Provides comprehensive audit trail
- Implements event deduplication to prevent notification spam

### Metrics Exporter Agent

- Subscribes to all HemoStat event channels
- Converts events into Prometheus-compatible metrics
- Exposes HTTP endpoint for Prometheus scraping (port 9090)
- Tracks container health, agent performance, and system operations
- Enables historical analysis and trend identification via Grafana

See the [Monitoring documentation](monitoring.md) for detailed information on metrics and observability.

## Communication Model

All agents communicate via Redis pub/sub channels:

```text
hemostat:health_alert           (Monitor → Analyzer)
hemostat:remediation_needed     (Analyzer → Responder)
hemostat:remediation_complete   (Responder → Alert)
hemostat:false_alarm            (Analyzer → Alert)
```

## Data Flow

1. **Monitor** collects container metrics every 30 seconds
2. **Monitor** publishes `health_alert` event if anomalies detected
3. **Analyzer** subscribes to `health_alert` channel
4. **Analyzer** processes alert, decides if real issue
5. If real, **Analyzer** publishes `remediation_needed` event
6. **Responder** subscribes to `remediation_needed` channel
7. **Responder** checks safety constraints, executes fix
8. **Responder** publishes `remediation_complete` event
9. **Alert** subscribes to `remediation_complete` channel
10. **Alert** sends Slack notification, updates Redis
11. **Dashboard** reads from Redis, displays in real-time

## Redis Key Structure

```text
hemostat:stats:<container>       Current metrics for container
hemostat:remediation:<container> Action history for container
hemostat:events:<type>           Event log by type
hemostat:containers              List of monitored containers
```

## Safety Mechanisms

### Cooldown Period

- After restart, 1 hour cooldown before next restart
- Prevents restart loops and cascading failures

### Max Actions Per Hour

- Maximum 3 restarts per hour per container
- Circuit breaker for repeated failures

### Fallback Analysis

- If Claude fails, fall back to rule-based analysis
- System continues operating without AI

### Error Handling

- All agents catch and log exceptions
- Graceful degradation, no cascading failures
- Automatic restart on failure

## Scaling Considerations

### Horizontal Scaling

- Run multiple Monitor instances (one per cluster)
- Run multiple Analyzer instances (share load via Redis)
- Run multiple Responder instances (Redis ensures atomicity)
- Keep single Alert and Dashboard

### Performance Characteristics

- Monitor: O(n) where n = number of containers
- Analyzer: O(1) per alert, limited by Claude API rate
- Responder: O(1) per remediation request
- Alert: O(1) per completion event
- Dashboard: O(1) for display updates

### Redis as Bottleneck

For large-scale deployments:

- Use Redis Cluster for horizontal scaling
- Add message queue (RabbitMQ) for very high volume
- Add persistent storage for audit logs

## Extensibility

### Adding New Agents

1. Create `agents/my_agent/my_agent.py`
2. Import `HemoStatAgent` from `agents.agent_base`
3. Override `run()` method
4. Subscribe to relevant Redis channels
5. Publish events to specific channels
6. Add Dockerfile and update docker-compose.yml

See the [API Reference](api/agents.rst) for the `HemoStatAgent` base class documentation.

### Adding New Remediation Actions

1. Edit `agents/hemostat_responder/responder.py`
2. Add new method (e.g., `scale_container()`)
3. Update `_handle_remediation_request()` to call new method
4. Update Analyzer to suggest new action

### Customizing Monitor Thresholds

Edit `agents/hemostat_monitor/monitor.py` to adjust detection thresholds:

```python
self.thresholds = {
    'memory_pct': 80,   # Change to 70 for earlier alerts
    'cpu_pct': 85       # Change to 75 for earlier alerts
}
```

## Deployment Options

### Local Docker Compose (Demo)

- Simplest setup
- All services on single machine
- Perfect for testing and development

### Kubernetes

- Horizontal scaling
- High availability
- Production-grade
- More complex setup

### AWS ECS

- Managed containers
- Auto-scaling
- Integration with CloudWatch

### Multi-Cloud

- Deploy across multiple cloud providers
- Redis cluster for centralized state
- Cloud-specific agents for remediation

## Monitoring HemoStat Itself

HemoStat includes comprehensive monitoring through Prometheus and Grafana. See the [Monitoring documentation](monitoring.md) for complete details.

### Key Metrics to Track

1. Monitor cycle time (should be ~30s)
2. Analyzer response time (should be <5s)
3. Responder execution time (should be <10s)
4. Alert notification latency
5. False alarm rate (should be low)
6. Mean time to detection (should be <30s)
7. Mean time to fix (should be ~13s)

### Available Metrics

- **Container Health**: CPU, memory, restarts, network I/O
- **Analysis Performance**: Duration, confidence scores, request rates
- **Remediation Tracking**: Attempts, success rates, execution time
- **System Health**: Agent uptime, Redis operations, alert rates

Access metrics at:
- **Grafana Dashboard**: http://localhost:3000
- **Prometheus UI**: http://localhost:9091
- **Raw Metrics**: http://localhost:9090/metrics

### Health Checks

- All agents restart automatically on failure
- Redis connectivity verified at startup
- Docker socket connectivity verified at startup
- Health check endpoints available
- Prometheus monitors agent availability

## Security Considerations

### API Keys

- Store in environment variables, not code
- Never commit `.env` file
- Rotate keys regularly

### Docker Socket

- Only accessible from within container network
- Read-only where possible
- Audit all container operations

### Redis Access

- Localhost only by default
- Add authentication for production
- Use TLS for remote access

### Logs and Audit Trail

- All actions logged
- No sensitive data in logs
- Retain logs for compliance

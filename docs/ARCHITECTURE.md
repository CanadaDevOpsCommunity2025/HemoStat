# HemoStat Architecture

## System Design

### Agent Communication Model

```mermaid
┌─────────────┐
│   Monitor   │ Polls Docker every 30s
└──────┬──────┘
       │ publishes health_alert
       │ via Redis pub/sub
       ▼
┌─────────────────┐
│   Analyzer      │ Analyzes with Claude/GPT-4
└──────┬──────────┘
       │ publishes remediation_needed
       │ via Redis pub/sub
       ▼
┌─────────────────┐
│   Responder     │ Executes fixes safely
└──────┬──────────┘
       │ publishes remediation_complete
       │ via Redis pub/sub
       ▼
┌─────────────┐
│   Alert     │ Sends notifications
└──────┬──────┘
       │ updates Redis keys
       │ for dashboard consumption
       ▼
┌────────────────────┐
│ Streamlit + Arcane │ Visualizes in real-time
└────────────────────┘
```

### Data Flow

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

### Redis Channel Structure

```text
hemostat:health_alert           (Monitor → Analyzer)
hemostat:remediation_needed     (Analyzer → Responder)
hemostat:remediation_complete   (Responder → Alert)
hemostat:false_alarm            (Analyzer → Alert)

hemostat:stats:<container>      (Current metrics)
hemostat:remediation:<container> (Action history)
hemostat:events:<type>          (Event log)
```

### Safety Mechanisms

1. **Cooldown Period**
   - After restart, 1 hour cooldown before next restart
   - Prevents restart loops

2. **Max Actions Per Hour**
   - Maximum 3 restarts per hour per container
   - Circuit breaker for repeated failures

3. **Fallback Analysis**
   - If Claude fails, fall back to rule-based analysis
   - System continues operating

4. **Error Handling**
   - All agents catch and log exceptions
   - Graceful degradation, no cascading failures

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

- For large scale, use Redis Cluster
- For very high volume, add message queue (RabbitMQ)
- Add persistent storage for audit logs

## Extensibility

### Adding New Agents

1. Create `agents/my_agent/my_agent.py`
2. Import `HemoStatAgent` from `agent_base.py`
3. Override `run()` method
4. Subscribe to relevant Redis channels
5. Publish events to specific channels
6. Add Dockerfile and requirements.txt
7. Add service to docker-compose.yml

### Adding New Remediation Actions

1. Edit `agents/hemostat_responder/hemostat_responder.py`
2. Add new method (e.g., `scale_container()`)
3. Update `execute_remediation()` to call new method
4. Update Analyzer to suggest new action

### Customizing Monitor Thresholds

```python
# In agents/hemostat_monitor/hemostat_monitor.py
self.thresholds = {
    'memory_pct': 80,   # Change to 70 for earlier alerts
    'cpu_pct': 85       # Change to 75 for earlier alerts
}
```

## Deployment Options

### Option 1: Local Docker Compose (Demo)

- Simplest setup
- All services on single machine
- Perfect for testing

### Option 2: Kubernetes

- Horizontal scaling
- High availability
- Production-grade
- More complex setup

### Option 3: AWS ECS

- Managed containers
- Auto-scaling
- Integration with CloudWatch

### Option 4: Multi-Cloud

- Deploy across multiple cloud providers
- Redis cluster for centralized state
- Cloud-specific agents for remediation

## Monitoring HemoStat Itself

### Key Metrics to Track

1. Monitor cycle time (should be ~30s)
2. Analyzer response time (should be <5s)
3. Responder execution time (should be <10s)
4. Alert notification latency
5. False alarm rate (should be low)
6. Mean time to detection (should be <30s)
7. Mean time to fix (should be ~13s)

### Health Checks

- All agents restart automatically on failure
- Redis connectivity verified at startup
- Docker socket connectivity verified at startup
- API health endpoints available

## Security Considerations

1. **API Keys**
   - Store in environment variables, not code
   - Never commit .env file
   - Rotate keys regularly

2. **Docker Socket**
   - Only accessible from within container network
   - Read-only where possible
   - Audit all container operations

3. **Redis Access**
   - Localhost only by default
   - Add authentication for production
   - Use TLS for remote access

4. **Logs and Audit Trail**
   - All actions logged
   - No sensitive data in logs
   - Retain logs for compliance

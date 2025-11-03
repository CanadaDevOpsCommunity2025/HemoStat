# Monitoring & Observability

HemoStat includes a comprehensive monitoring stack built on Prometheus and Grafana, providing deep insights into system performance, container health, and agent operations.

## Overview

The monitoring stack consists of three key components:

1. **Metrics Exporter Agent** - Subscribes to HemoStat events and exposes Prometheus metrics
2. **Prometheus** - Time-series database for metrics collection and alerting
3. **Grafana** - Visualization dashboards for historical analysis

```{mermaid}
graph LR
    A[Monitor Agent] -->|events| R[Redis]
    B[Analyzer Agent] -->|events| R
    C[Responder Agent] -->|events| R
    D[Alert Agent] -->|events| R
    R -->|subscribe| M[Metrics Exporter]
    M -->|:9090/metrics| P[Prometheus]
    P -->|data source| G[Grafana Dashboards]
```

## Architecture

### Metrics Exporter Agent

The Metrics Exporter is a specialized HemoStat agent that:

- Subscribes to all HemoStat Redis pub/sub channels
- Converts events into Prometheus-compatible metrics
- Exposes an HTTP endpoint at `http://localhost:9090/metrics`
- Tracks container health, agent performance, and system operations

**Implementation**: `agents/hemostat_metrics/metrics.py`

### Data Flow

1. HemoStat agents publish events to Redis
2. Metrics Exporter subscribes and converts events to metrics
3. Prometheus scrapes metrics endpoint every 10 seconds
4. Grafana queries Prometheus for visualization
5. Alert rules trigger notifications on anomalies

## Metrics Catalog

### Container Health Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_container_cpu_percent` | Gauge | CPU usage percentage per container |
| `hemostat_container_memory_percent` | Gauge | Memory usage percentage per container |
| `hemostat_container_memory_bytes` | Gauge | Memory usage in bytes |
| `hemostat_container_restart_count` | Gauge | Container restart count |
| `hemostat_container_network_rx_bytes_total` | Counter | Network bytes received |
| `hemostat_container_network_tx_bytes_total` | Counter | Network bytes transmitted |
| `hemostat_container_blkio_read_bytes_total` | Counter | Block I/O read bytes |
| `hemostat_container_blkio_write_bytes_total` | Counter | Block I/O write bytes |

### Health Alert Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_health_alerts_total` | Counter | Total health alerts by severity |
| `hemostat_anomalies_detected_total` | Counter | Total anomalies by type |

### Analysis Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_analysis_requests_total` | Counter | Total analysis requests by result type |
| `hemostat_analysis_duration_seconds` | Histogram | Analysis response time distribution |
| `hemostat_analysis_confidence` | Histogram | AI confidence score distribution |

### Remediation Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_remediation_attempts_total` | Counter | Total attempts by action and status |
| `hemostat_remediation_duration_seconds` | Histogram | Remediation execution time |
| `hemostat_remediation_cooldown_active` | Gauge | Cooldown status per container |

### Alert Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_alerts_sent_total` | Counter | Total alerts sent by channel and status |
| `hemostat_alerts_deduped_total` | Counter | Total deduplicated alerts |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hemostat_agent_uptime_seconds` | Gauge | Agent uptime tracking |
| `hemostat_redis_operations_total` | Counter | Redis operations by type |
| `hemostat_time_to_detection_seconds` | Histogram | Time from issue to detection |
| `hemostat_time_to_remediation_seconds` | Histogram | Time from detection to fix |

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start all services including monitoring
docker compose up -d

# Or start just monitoring components
docker compose up -d redis metrics prometheus grafana
```

### 2. Access Dashboards

**Grafana Dashboard**
- URL: http://localhost:3000
- Username: `admin`
- Password: `admin` (change on first login)

**Prometheus Query UI**
- URL: http://localhost:9091
- Direct metric queries and exploration

**Metrics Endpoint**
- URL: http://localhost:9090/metrics
- Raw Prometheus metrics

### 3. View HemoStat Overview Dashboard

1. Login to Grafana
2. Navigate to **Dashboards** → **HemoStat** folder
3. Select **HemoStat Overview**

The dashboard displays:
- Container CPU and memory usage graphs
- Health alerts by severity
- Analysis performance metrics (response time, confidence)
- Remediation attempts and success rates
- Agent uptime and system health

## Prometheus Configuration

### Scrape Configuration

Prometheus is configured to scrape the Metrics Exporter every 10 seconds:

```yaml
scrape_configs:
  - job_name: 'hemostat-metrics'
    static_configs:
      - targets: ['metrics:9090']
    scrape_interval: 10s
    scrape_timeout: 5s
```

**Configuration file**: `monitoring/prometheus/prometheus.yml`

### Alert Rules

Pre-configured alert rules monitor system health:

**Container Health Alerts**
- `HighContainerCPU` - CPU > 90% for 2+ minutes
- `HighContainerMemory` - Memory > 90% for 2+ minutes
- `ExcessiveContainerRestarts` - Frequent restart rate

**System Performance Alerts**
- `SlowAnalysisResponse` - p95 latency > 10 seconds
- `HighRemediationFailureRate` - Failure rate > 30%
- `HighAlertFailureRate` - Notification failures > 20%

**System Health Alerts**
- `MetricsExporterDown` - Exporter unavailable for 1+ minute
- `NoHealthAlertsDetected` - No alerts for 30+ minutes (possible monitor issue)

**Configuration file**: `monitoring/prometheus/rules/hemostat_alerts.yml`

## Grafana Dashboards

### HemoStat Overview Dashboard

The main dashboard provides 11 panels across four sections:

**Summary Metrics**
- Monitored containers count
- Health alerts per minute
- Median analysis confidence
- Remediations per minute

**Container Health Graphs**
- CPU usage time-series per container
- Memory usage time-series per container

**System Activity**
- Health alerts by severity
- Analysis requests by result type
- Remediation attempts by action and status

**Performance Metrics**
- Analysis duration percentiles (p50, p95, p99)
- Remediation duration percentiles (p50, p95, p99)

### Auto-Provisioning

Dashboards and data sources are automatically configured on startup:

- **Data Source**: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- **Dashboard**: `monitoring/grafana/provisioning/dashboards/hemostat_overview.json`

## PromQL Query Examples

### Container Metrics

```promql
# Average CPU across all containers
avg(hemostat_container_cpu_percent)

# Containers with high memory usage
hemostat_container_memory_percent > 80

# Container restart rate
rate(hemostat_container_restart_count[5m])
```

### Analysis Performance

```promql
# Analysis p95 latency
histogram_quantile(0.95, rate(hemostat_analysis_duration_seconds_bucket[5m]))

# Median confidence score
histogram_quantile(0.5, rate(hemostat_analysis_confidence_bucket[5m]))

# Analysis requests per second
rate(hemostat_analysis_requests_total[1m])
```

### Remediation Tracking

```promql
# Remediation success rate
sum(rate(hemostat_remediation_attempts_total{status="success"}[5m])) /
sum(rate(hemostat_remediation_attempts_total[5m]))

# Failed remediations per minute
rate(hemostat_remediation_attempts_total{status="failed"}[5m]) * 60

# Remediation duration p99
histogram_quantile(0.99, rate(hemostat_remediation_duration_seconds_bucket[5m]))
```

### System Health

```promql
# Agent uptime
hemostat_agent_uptime_seconds{agent_name="metrics"}

# Total health alerts in last hour
sum(increase(hemostat_health_alerts_total[1h]))

# Alert deduplication rate
rate(hemostat_alerts_deduped_total[5m])
```

## Configuration

### Environment Variables

**Metrics Exporter**
```bash
METRICS_PORT=9090          # HTTP server port
REDIS_HOST=redis           # Redis hostname
REDIS_PORT=6379           # Redis port
LOG_LEVEL=INFO            # Logging level
```

**Prometheus**
- Data retention: 15 days (configurable via `--storage.tsdb.retention.time`)
- Scrape interval: 10 seconds (configurable in `prometheus.yml`)

**Grafana**
```bash
GF_SECURITY_ADMIN_USER=admin           # Admin username
GF_SECURITY_ADMIN_PASSWORD=admin       # Admin password (change this!)
GF_USERS_ALLOW_SIGN_UP=false          # Disable user signup
```

### Customizing Scrape Intervals

Edit `monitoring/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'hemostat-metrics'
    scrape_interval: 5s  # More frequent scraping
```

### Adjusting Alert Thresholds

Edit `monitoring/prometheus/rules/hemostat_alerts.yml`:

```yaml
- alert: HighContainerCPU
  expr: hemostat_container_cpu_percent > 95  # Increase threshold
  for: 5m  # Wait longer before alerting
```

### Changing Data Retention

Edit `docker-compose.yml`:

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # Keep data for 30 days
    - '--storage.tsdb.retention.size=10GB' # Limit storage size
```

## Troubleshooting

### Metrics Not Appearing

**Check Metrics Exporter**
```bash
# View logs
docker compose logs metrics

# Verify endpoint is accessible
curl http://localhost:9090/metrics | grep hemostat_

# Check Redis connection
docker compose exec metrics python -c "import redis; redis.Redis(host='redis').ping()"
```

### Prometheus Not Scraping

**Verify Targets**
```bash
# Check target status
curl http://localhost:9091/api/v1/targets

# View in browser
open http://localhost:9091/targets
```

**Check Connectivity**
```bash
# Test from Prometheus container
docker compose exec prometheus wget -O- http://metrics:9090/metrics
```

### Grafana Shows "No Data"

1. **Verify time range** - Use "Last 15 minutes" or "Last 1 hour"
2. **Test data source** - Go to Configuration → Data Sources → Test
3. **Check Prometheus** - Query metrics directly in Prometheus UI
4. **Generate activity** - Start agents to create events

**Test Prometheus Connection**
```bash
# From Grafana container
docker compose exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up
```

### High Resource Usage

**Reduce Scrape Frequency**
```yaml
scrape_interval: 30s  # From 10s to 30s
```

**Lower Retention Period**
```yaml
--storage.tsdb.retention.time=7d  # From 15d to 7d
```

**Add Recording Rules** for expensive queries:
```yaml
# Create recording rules for frequently used queries
- record: job:hemostat_cpu_avg:5m
  expr: avg(hemostat_container_cpu_percent)
```

## Integration with Existing Dashboard

HemoStat provides two complementary dashboards:

### Streamlit Dashboard (Port 8501)
- **Real-time event streaming**
- **Live container status grid**
- **Event timeline and details**
- **Active issues feed**

### Grafana Dashboard (Port 3000)
- **Historical metrics analysis**
- **Performance trends over time**
- **Alert visualization**
- **Custom query exploration**

**Use Cases:**
- **Streamlit**: Real-time incident response and live monitoring
- **Grafana**: Performance analysis, capacity planning, trend identification

## Best Practices

### Dashboard Design

1. **Use appropriate time ranges** - Last 1 hour for real-time, 24 hours for trends
2. **Set meaningful thresholds** - Based on SLAs and baseline performance
3. **Add annotations** - Mark deployments and incidents on graphs
4. **Create variables** - For dynamic container/service filtering

### Alerting Strategy

1. **Set alert thresholds conservatively** - Avoid alert fatigue
2. **Use multi-condition alerts** - Combine metrics for context
3. **Configure notification channels** - Slack, email, PagerDuty
4. **Test alert rules** - Verify alerts trigger appropriately

### Performance Optimization

1. **Use recording rules** - Pre-compute expensive queries
2. **Limit cardinality** - Avoid high-cardinality labels
3. **Set appropriate retention** - Balance storage and query needs
4. **Monitor Prometheus itself** - Track ingestion rate and query performance

### Security

1. **Change default passwords** - Especially Grafana admin password
2. **Enable authentication** - For Prometheus and Grafana
3. **Use HTTPS** - In production deployments
4. **Restrict network access** - Limit to authorized networks

## Advanced Topics

### Adding Custom Metrics

Extend the Metrics Exporter in `agents/hemostat_metrics/metrics.py`:

```python
from prometheus_client import Counter

# Define new metric
self.custom_metric = Counter(
    "hemostat_custom_total",
    "Description of custom metric",
    ["label1", "label2"]
)

# Update metric in event handler
self.custom_metric.labels(label1="value1", label2="value2").inc()
```

### Creating Custom Dashboards

1. Design dashboard in Grafana UI
2. Export as JSON: Dashboard Settings → JSON Model
3. Save to `monitoring/grafana/provisioning/dashboards/`
4. Restart Grafana to load

### Setting Up Alertmanager

For advanced alert routing and aggregation:

```yaml
# In prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Remote Write Configuration

For long-term storage:

```yaml
# In prometheus.yml
remote_write:
  - url: "https://prometheus-remote-storage.example.com/api/v1/write"
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Visualization dashboards |
| **Prometheus** | http://localhost:9091 | Query UI and alerts |
| **Metrics Exporter** | http://localhost:9090/metrics | Raw metrics endpoint |
| **Streamlit Dashboard** | http://localhost:8501 | Real-time monitoring |

## References

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Metrics Exporter Source**: `agents/hemostat_metrics/`
- **Configuration Files**: `monitoring/prometheus/` and `monitoring/grafana/`

## See Also

- [Architecture](architecture.md) - System design and agent communication
- [Deployment](deployment.md) - Production deployment strategies
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [API Reference](api/agents.rst) - Metrics Exporter API documentation

# HemoStat Monitoring with Prometheus & Grafana

This directory contains the monitoring stack configuration for HemoStat using Prometheus and Grafana.

## Architecture

```
┌──────────────┐
│   Monitor    │──┐
│   Analyzer   │  │
│   Responder  │  ├─► Publish events to Redis
│   Alert      │  │
└──────────────┘──┘
        │
        ▼
┌──────────────────┐
│ Metrics Exporter │ Subscribe & convert to Prometheus metrics
│   (Port 9090)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Prometheus     │ Scrape & store time-series data
│   (Port 9091)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Grafana      │ Visualize metrics in dashboards
│   (Port 3000)    │
└──────────────────┘
```

## Quick Start

### 1. Start All Services

```bash
# Start the full stack
docker compose up -d

# Verify services are running
docker compose ps
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin` (change on first login)
  
- **Prometheus**: http://localhost:9091
  - Query interface and metrics browser
  
- **Metrics Endpoint**: http://localhost:9090/metrics
  - Raw Prometheus metrics from HemoStat

### 3. View HemoStat Dashboard

1. Login to Grafana at http://localhost:3000
2. Navigate to **Dashboards** → **HemoStat** folder
3. Click **HemoStat Overview**

The dashboard shows:
- Container health metrics (CPU, memory)
- Health alerts and anomalies
- Analysis performance and confidence scores
- Remediation attempts and success rates
- System performance metrics

## Directory Structure

```
monitoring/
├── prometheus/
│   ├── prometheus.yml           # Prometheus config (scrape targets)
│   ├── rules/
│   │   └── hemostat_alerts.yml  # Alert rules
│   └── README.md                # Prometheus documentation
│
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml   # Auto-provision Prometheus datasource
│   │   └── dashboards/
│   │       ├── dashboard.yml    # Auto-load dashboards
│   │       └── hemostat_overview.json  # Main dashboard
│   └── README.md                # Grafana documentation
│
└── README.md                    # This file
```

## Key Metrics

### Container Health
- `hemostat_container_cpu_percent` - CPU usage per container
- `hemostat_container_memory_percent` - Memory usage per container
- `hemostat_container_restart_count` - Container restart count

### System Performance
- `hemostat_health_alerts_total` - Total health alerts by severity
- `hemostat_analysis_duration_seconds` - Analysis response time
- `hemostat_remediation_attempts_total` - Remediation attempts by status
- `hemostat_analysis_confidence` - AI confidence scores

### Agent Health
- `hemostat_agent_uptime_seconds` - Agent uptime tracking
- `hemostat_redis_operations_total` - Redis operations

## Common Tasks

### Query Metrics in Prometheus

```bash
# Open Prometheus UI
open http://localhost:9091

# Example queries:
# - Average CPU across all containers: avg(hemostat_container_cpu_percent)
# - Remediation success rate: rate(hemostat_remediation_attempts_total{status="success"}[5m])
# - Analysis p95 latency: histogram_quantile(0.95, rate(hemostat_analysis_duration_seconds_bucket[5m]))
```

### Create Custom Grafana Dashboard

1. In Grafana, click **+** → **Dashboard**
2. Add panel with Prometheus query
3. Customize visualization
4. Save dashboard to HemoStat folder

### View Active Alerts

```bash
# Check Prometheus alerts
curl http://localhost:9091/api/v1/alerts | jq

# Check alert rules
curl http://localhost:9091/api/v1/rules | jq
```

### Export Metrics for Analysis

```bash
# Export current metrics
curl http://localhost:9090/metrics > hemostat_metrics.txt

# Query specific metric
curl 'http://localhost:9091/api/v1/query?query=hemostat_container_cpu_percent'
```

## Troubleshooting

### Metrics Exporter Not Running

```bash
# Check logs
docker compose logs metrics

# Verify Redis connection
docker compose exec metrics python -c "import redis; redis.Redis(host='redis').ping()"

# Check metrics endpoint
curl http://localhost:9090/metrics
```

### Prometheus Not Scraping

```bash
# Check Prometheus targets
curl http://localhost:9091/api/v1/targets

# View Prometheus logs
docker compose logs prometheus

# Verify metrics service is accessible from Prometheus
docker compose exec prometheus wget -O- http://metrics:9090/metrics
```

### Grafana Not Showing Data

```bash
# Check Grafana logs
docker compose logs grafana

# Verify Prometheus datasource
curl -u admin:admin http://localhost:3000/api/datasources

# Test Prometheus connection from Grafana
docker compose exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up
```

### No Data in Dashboard

1. Verify HemoStat agents are running: `docker compose ps`
2. Check if metrics are being exported: `curl http://localhost:9090/metrics | grep hemostat_`
3. Verify Prometheus is scraping: Visit http://localhost:9091/targets
4. Check Grafana time range includes recent data
5. Ensure containers are generating activity (health alerts)

## Configuration

### Change Prometheus Retention

Edit `docker-compose.yml`:
```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # Change from 15d to 30d
```

### Adjust Scrape Intervals

Edit `monitoring/prometheus/prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'hemostat-metrics'
    scrape_interval: 5s  # Scrape more frequently
```

### Customize Alert Rules

Edit `monitoring/prometheus/rules/hemostat_alerts.yml`:
```yaml
- alert: HighContainerCPU
  expr: hemostat_container_cpu_percent > 95  # Increase threshold
  for: 5m  # Increase duration before alerting
```

### Change Grafana Admin Password

Edit `.env` or `docker-compose.yml`:
```yaml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=your_secure_password
```

## Integration with Existing Dashboard

HemoStat includes both:
- **Streamlit Dashboard** (http://localhost:8501) - Real-time event streaming
- **Grafana Dashboard** (http://localhost:3000) - Historical metrics and trends

Both provide complementary views:
- Use **Streamlit** for live monitoring and event details
- Use **Grafana** for historical analysis and performance trends

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## Next Steps

1. **Customize Dashboards**: Create team-specific views in Grafana
2. **Set Up Alerting**: Configure Grafana alerts to Slack/email
3. **Add More Metrics**: Extend metrics exporter for custom metrics
4. **Long-term Storage**: Configure Prometheus remote write for data retention
5. **Federation**: Set up Prometheus federation for multi-cluster monitoring

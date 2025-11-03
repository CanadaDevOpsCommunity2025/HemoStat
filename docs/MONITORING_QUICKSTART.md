# Monitoring Quick Start Guide

Get up and running with HemoStat's Prometheus & Grafana monitoring stack in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- HemoStat project cloned
- `.env` file configured (copy from `.env.example`)

## Step 1: Start the Stack

```powershell
# Windows PowerShell
docker compose up -d

# Or start just the monitoring stack
docker compose up -d redis metrics prometheus grafana
```

## Step 2: Verify Services

```powershell
# Check all services are running
docker compose ps

# Expected output should show:
# - hemostat-redis (port 6379)
# - hemostat-metrics (port 9090)
# - hemostat-prometheus (port 9091)
# - hemostat-grafana (port 3000)
```

## Step 3: Access Dashboards

Open in your browser:

### Grafana Dashboard
- **URL**: http://localhost:3000
- **Username**: `admin`
- **Password**: `admin` (change on first login)

### Prometheus Query UI
- **URL**: http://localhost:9091
- Query and explore metrics directly

### Metrics Endpoint
- **URL**: http://localhost:9090/metrics
- Raw Prometheus metrics from HemoStat

## Step 4: View HemoStat Overview Dashboard

1. Login to Grafana at http://localhost:3000
2. Navigate to **Dashboards** → **Browse**
3. Click **HemoStat** folder
4. Select **HemoStat Overview**

You should see:
- ✅ Container CPU and Memory usage graphs
- ✅ Health alerts metrics
- ✅ Analysis performance metrics
- ✅ Remediation attempt statistics

## Step 5: Generate Some Activity

Start the HemoStat agents to generate metrics:

```powershell
# Start all agents
docker compose up -d monitor analyzer responder alert

# Or start demo test services to trigger health alerts
docker compose up -d test-api test-worker
```

## Verify Metrics Are Flowing

### Check Metrics Exporter
```powershell
# View raw metrics
curl http://localhost:9090/metrics | Select-String "hemostat_"

# Should see metrics like:
# - hemostat_container_cpu_percent
# - hemostat_health_alerts_total
# - hemostat_analysis_requests_total
```

### Check Prometheus Is Scraping
```powershell
# Open Prometheus UI
Start-Process http://localhost:9091

# Go to Status → Targets
# Verify "hemostat-metrics" target is UP
```

### Query Metrics in Prometheus
Try these queries in the Prometheus UI (http://localhost:9091):

```promql
# Average CPU across all containers
avg(hemostat_container_cpu_percent)

# Health alerts in last 5 minutes
rate(hemostat_health_alerts_total[5m]) * 60

# Analysis p95 latency
histogram_quantile(0.95, rate(hemostat_analysis_duration_seconds_bucket[5m]))

# Remediation success rate
sum(rate(hemostat_remediation_attempts_total{status="success"}[5m])) /
sum(rate(hemostat_remediation_attempts_total[5m]))
```

## Troubleshooting

### No Metrics Showing Up?

**Check Metrics Exporter Logs:**
```powershell
docker compose logs metrics
```

**Verify Redis Connection:**
```powershell
docker compose exec metrics python -c "import redis; r = redis.Redis(host='redis'); print(r.ping())"
```

### Prometheus Not Scraping?

**Check Prometheus Targets:**
```powershell
# View targets status
curl http://localhost:9091/api/v1/targets | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Or open in browser
Start-Process http://localhost:9091/targets
```

**Check Prometheus Logs:**
```powershell
docker compose logs prometheus
```

### Grafana Shows "No Data"?

1. **Check time range** - Use "Last 15 minutes" or "Last 1 hour"
2. **Verify data source** - Go to Configuration → Data Sources → Test connection
3. **Generate activity** - Start agents and test services
4. **Check Prometheus** - Query metrics directly in Prometheus UI first

### Port Conflicts?

If ports are already in use, edit `docker-compose.yml`:

```yaml
# Change Grafana port
grafana:
  ports:
    - "3001:3000"  # Changed from 3000:3000

# Change Prometheus port
prometheus:
  ports:
    - "9092:9090"  # Changed from 9091:9090

# Change Metrics port
metrics:
  ports:
    - "9093:9090"  # Changed from 9090:9090
```

## Next Steps

### Customize Grafana Dashboard

1. Click panel title → **Edit**
2. Modify query or visualization
3. **Save** dashboard

### Set Up Alerts in Grafana

1. Edit a panel
2. Go to **Alert** tab
3. Define condition (e.g., CPU > 90%)
4. Add notification channel (Slack, email, etc.)

### Create Custom Metrics

Extend `agents/hemostat_metrics/metrics.py`:

```python
# Add new metric
self.my_custom_metric = Counter(
    "hemostat_my_custom_total",
    "Description of my metric",
    ["label1", "label2"]
)

# Update metric
self.my_custom_metric.labels(label1="value1", label2="value2").inc()
```

### Export Dashboards

```powershell
# Export dashboard as JSON
# In Grafana: Dashboard settings → JSON Model → Copy
# Save to: monitoring/grafana/provisioning/dashboards/my_dashboard.json
```

## Common Commands

```powershell
# Stop all services
docker compose down

# Restart specific service
docker compose restart metrics

# View logs
docker compose logs -f grafana prometheus metrics

# Rebuild metrics exporter after code changes
docker compose build metrics
docker compose up -d metrics

# Clean up volumes (WARNING: deletes all data)
docker compose down -v
```

## Service URLs Reference

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Visualization dashboards |
| **Prometheus** | http://localhost:9091 | Time-series database & query UI |
| **Metrics Exporter** | http://localhost:9090/metrics | Raw metrics endpoint |
| **Streamlit Dashboard** | http://localhost:8501 | Real-time event monitoring |
| **Redis** | localhost:6379 | Message bus |

## Architecture Overview

```
Container Events → Monitor Agent → Redis → Metrics Exporter → Prometheus → Grafana
                                      ↓
                              Analyzer Agent
                                      ↓
                             Responder Agent
                                      ↓
                               Alert Agent
```

## Documentation Links

- **Full Monitoring Guide**: [monitoring/README.md](monitoring/README.md)
- **Prometheus Config**: [monitoring/prometheus/README.md](monitoring/prometheus/README.md)
- **Grafana Setup**: [monitoring/grafana/README.md](monitoring/grafana/README.md)
- **Metrics Exporter**: [agents/hemostat_metrics/README.md](agents/hemostat_metrics/README.md)

## Support

For issues or questions:
1. Check logs: `docker compose logs <service-name>`
2. Verify network connectivity between services
3. Review [monitoring/README.md](monitoring/README.md) for detailed troubleshooting
4. Check Prometheus targets at http://localhost:9091/targets

## Success Indicators

✅ **Everything is working if:**
- Grafana dashboard shows data in panels
- Prometheus targets page shows "hemostat-metrics" as UP
- Metrics endpoint returns data: `curl http://localhost:9090/metrics`
- Grafana datasource test succeeds
- Dashboards auto-refresh with new data every 10 seconds

# Prometheus Configuration for HemoStat

This directory contains Prometheus configuration for monitoring HemoStat system metrics.

## Files

- **`prometheus.yml`** - Main Prometheus configuration
- **`rules/hemostat_alerts.yml`** - Alert rules for HemoStat metrics

## Configuration Overview

### Scrape Targets

1. **hemostat-metrics** (port 9090)
   - HemoStat Metrics Exporter agent
   - Scrapes every 10 seconds
   - Exposes all HemoStat system metrics

2. **prometheus** (port 9090)
   - Prometheus self-monitoring
   - Scrapes every 30 seconds

### Alert Rules

The `rules/hemostat_alerts.yml` file defines alerting rules across several categories:

#### Health Alerts
- **HighContainerCPU** - CPU usage > 90% for 2+ minutes
- **HighContainerMemory** - Memory usage > 90% for 2+ minutes
- **ExcessiveContainerRestarts** - Frequent container restarts

#### Analysis Alerts
- **SlowAnalysisResponse** - Analysis taking > 10 seconds
- **LowAnalysisConfidence** - Low confidence scores

#### Remediation Alerts
- **HighRemediationFailureRate** - Failure rate > 30%
- **SlowRemediationExecution** - Execution time > 60 seconds

#### Alert System Alerts
- **HighAlertFailureRate** - Alert notification failures > 20%
- **HighAlertDeduplicationRate** - Excessive duplicate alerts

#### System Alerts
- **MetricsExporterDown** - Metrics exporter unavailable
- **NoHealthAlertsDetected** - No alerts for 30+ minutes (possible monitor issue)

## Usage

### Start Prometheus
```bash
# Via Docker Compose
docker compose up -d prometheus

# Access UI
open http://localhost:9090
```

### Query Metrics
```promql
# Container CPU usage
hemostat_container_cpu_percent

# Analysis duration (95th percentile)
histogram_quantile(0.95, rate(hemostat_analysis_duration_seconds_bucket[5m]))

# Remediation success rate
rate(hemostat_remediation_attempts_total{status="success"}[5m])

# Total health alerts by severity
sum by (severity) (hemostat_health_alerts_total)
```

### View Alerts
```bash
# Check active alerts
curl http://localhost:9090/api/v1/alerts

# Check alert rules
curl http://localhost:9090/api/v1/rules
```

## Integration with Grafana

Prometheus serves as the data source for Grafana dashboards. To connect:

1. Open Grafana (http://localhost:3000)
2. Go to **Configuration** > **Data Sources**
3. Add Prometheus data source
4. Set URL: `http://prometheus:9090`
5. Click **Save & Test**

## Customization

### Adjust Scrape Intervals

Edit `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'hemostat-metrics'
    scrape_interval: 5s  # Change from 10s to 5s for more frequent scraping
```

### Add Alert Rules

Create new rule files in `rules/` directory:
```yaml
# rules/custom_alerts.yml
groups:
  - name: custom
    rules:
      - alert: MyCustomAlert
        expr: my_metric > threshold
        labels:
          severity: warning
        annotations:
          summary: "Custom alert triggered"
```

Update `prometheus.yml` to load custom rules:
```yaml
rule_files:
  - '/etc/prometheus/rules/*.yml'
```

### Add More Scrape Targets

To monitor additional services, add to `scrape_configs`:
```yaml
scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

## Retention and Storage

Default retention: 15 days. To customize:
```bash
# In docker-compose.yml
command:
  - '--storage.tsdb.retention.time=30d'
  - '--storage.tsdb.retention.size=10GB'
```

## Troubleshooting

### Prometheus not scraping metrics
```bash
# Check targets status
curl http://localhost:9090/api/v1/targets

# Check if metrics exporter is accessible
curl http://metrics:9090/metrics
```

### Alerts not firing
```bash
# Verify alert rules are loaded
curl http://localhost:9090/api/v1/rules

# Check alert rule evaluation
curl http://localhost:9090/api/v1/alerts
```

### High resource usage
- Increase scrape intervals
- Reduce retention period
- Add recording rules for expensive queries

## Best Practices

1. **Scrape Intervals**: Balance between data granularity and resource usage
2. **Alert Thresholds**: Adjust based on your environment and SLAs
3. **Retention**: Set appropriate retention based on storage capacity
4. **Recording Rules**: Create recording rules for frequently used complex queries
5. **Relabeling**: Use relabeling to clean up metric labels

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

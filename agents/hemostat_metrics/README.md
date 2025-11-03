# HemoStat Metrics Exporter Agent

The Metrics Exporter agent exposes HemoStat system metrics in Prometheus format for monitoring and observability.

## Purpose

- **Metrics Collection**: Subscribe to all HemoStat events and convert them to Prometheus metrics
- **HTTP Endpoint**: Serves metrics at `http://localhost:9090/metrics` for Prometheus scraping
- **Observability**: Provides insights into system performance, container health, and agent operations

## Metrics Exposed

### Container Health Metrics
- `hemostat_container_cpu_percent` - CPU usage percentage per container
- `hemostat_container_memory_percent` - Memory usage percentage per container
- `hemostat_container_memory_bytes` - Memory usage in bytes per container
- `hemostat_container_network_rx_bytes_total` - Network bytes received (counter)
- `hemostat_container_network_tx_bytes_total` - Network bytes transmitted (counter)
- `hemostat_container_blkio_read_bytes_total` - Block I/O read bytes (counter)
- `hemostat_container_blkio_write_bytes_total` - Block I/O write bytes (counter)
- `hemostat_container_restart_count` - Container restart count

### Health Alert Metrics
- `hemostat_health_alerts_total` - Total health alerts by severity
- `hemostat_anomalies_detected_total` - Total anomalies by type

### Analysis Metrics
- `hemostat_analysis_requests_total` - Total analysis requests
- `hemostat_analysis_duration_seconds` - Analysis duration histogram
- `hemostat_analysis_confidence` - Analysis confidence score distribution

### Remediation Metrics
- `hemostat_remediation_attempts_total` - Total remediation attempts by action and status
- `hemostat_remediation_duration_seconds` - Remediation duration histogram
- `hemostat_remediation_cooldown_active` - Cooldown status per container

### Alert Metrics
- `hemostat_alerts_sent_total` - Total alerts sent by channel
- `hemostat_alerts_deduped_total` - Total deduplicated alerts

### System Metrics
- `hemostat_agent_uptime_seconds` - Agent uptime
- `hemostat_redis_operations_total` - Redis operations by type
- `hemostat_time_to_detection_seconds` - Time to detect issues
- `hemostat_time_to_remediation_seconds` - Time to remediate issues

## Configuration

Environment variables:
- `METRICS_PORT` - HTTP server port for metrics endpoint (default: 9090)
- `REDIS_HOST` - Redis server hostname (default: redis)
- `REDIS_PORT` - Redis server port (default: 6379)
- `LOG_LEVEL` - Logging level (default: INFO)

## Running

### Standalone
```bash
python -m agents.hemostat_metrics.main
```

### Docker Compose
```bash
docker compose up -d metrics
```

### Access Metrics
```bash
# View metrics
curl http://localhost:9090/metrics

# Check if Prometheus is scraping
curl http://localhost:9090/metrics | grep hemostat_
```

## Integration with Prometheus

Prometheus configuration (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'hemostat-metrics'
    static_configs:
      - targets: ['metrics:9090']
    scrape_interval: 15s
```

## Architecture

```
┌─────────────┐
│   Monitor   │──┐
└─────────────┘  │
┌─────────────┐  │
│  Analyzer   │──┤ Publish events to Redis
└─────────────┘  │
┌─────────────┐  │
│  Responder  │──┤
└─────────────┘  │
┌─────────────┐  │
│    Alert    │──┘
└─────────────┘
       │
       ▼
┌─────────────────┐
│ Metrics Exporter│ Subscribe to events
└────────┬────────┘ Convert to Prometheus metrics
         │
         ▼
  HTTP :9090/metrics
         │
         ▼
  ┌─────────────┐
  │ Prometheus  │ Scrape metrics
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   Grafana   │ Visualize
  └─────────────┘
```

## Development

The Metrics Exporter inherits from `HemoStatAgent` base class, providing:
- Redis pub/sub communication
- Shared state management
- Graceful shutdown handling
- Connection retry logic

All metrics are exposed via the `prometheus_client` library's HTTP server.

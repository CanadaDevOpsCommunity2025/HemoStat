# HemoStat Vulnerability Scanner Agent

The Vulnerability Scanner Agent integrates with OWASP ZAP to perform automated security vulnerability scans of web applications and publishes findings to the HemoStat ecosystem.

## Features

- **Automated Scanning**: Periodically scans configured web application targets
- **OWASP ZAP Integration**: Uses industry-standard ZAP proxy for vulnerability detection
- **Risk Categorization**: Categorizes vulnerabilities by risk level (High, Medium, Low, Informational)
- **Real-time Alerts**: Publishes critical vulnerability alerts to the HemoStat alert system
- **Comprehensive Reporting**: Generates detailed vulnerability reports with remediation guidance

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZAP_HOST` | `zap` | OWASP ZAP container hostname |
| `ZAP_PORT` | `8080` | OWASP ZAP API port |
| `VULNSCANNER_INTERVAL` | `3600` | Scan interval in seconds (1 hour) |
| `VULNSCANNER_TIMEOUT` | `1800` | Individual scan timeout (30 minutes) |
| `VULNSCANNER_MAX_TIME` | `3600` | Maximum scan time (1 hour) |
| `VULNSCANNER_TARGETS` | `""` | Comma-separated list of additional targets to scan |

### Default Targets

- `http://juice-shop:3000` - OWASP Juice Shop vulnerable application

## Usage

### Standalone Execution
```bash
python -m agents.hemostat_vulnscanner.main
```

### Docker Execution
```bash
docker-compose up vulnscanner
```

## Integration with HemoStat Ecosystem

### Published Events

#### Vulnerability Scan Completed
- **Channel**: `hemostat:vulnerabilities`
- **Event Type**: `vulnerability_scan_completed`
- **Data**: Complete vulnerability report with risk categorization

#### Critical Vulnerabilities Found
- **Channel**: `hemostat:alerts`
- **Event Type**: `critical_vulnerabilities_found`
- **Severity**: `high`
- **Data**: Critical vulnerability details and counts

### Shared State

Scan results are stored in Redis shared state with keys:
- `vuln_scan_{timestamp}` - Complete scan reports (24-hour TTL)

## Vulnerability Report Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "target_url": "http://juice-shop:3000",
  "total_vulnerabilities": 15,
  "risk_summary": {
    "High": 3,
    "Medium": 5,
    "Low": 4,
    "Informational": 3
  },
  "critical_vulnerabilities": [
    {
      "name": "SQL Injection",
      "url": "http://juice-shop:3000/api/users",
      "param": "email",
      "description": "SQL injection vulnerability detected",
      "solution": "Use parameterized queries",
      "reference": "https://owasp.org/www-community/attacks/SQL_Injection"
    }
  ],
  "scan_agent": "hemostat-vulnscanner",
  "scan_tool": "OWASP ZAP"
}
```

## ZAP API Integration

The agent uses the following ZAP API endpoints:

- `GET /JSON/core/view/version/` - Check ZAP readiness
- `GET /JSON/ascan/action/scan/` - Start active scan
- `GET /JSON/ascan/view/status/` - Check scan progress
- `GET /JSON/core/view/alerts/` - Retrieve vulnerability results

## Security Considerations

- The agent runs as a non-root user in the container
- ZAP API access is restricted to the internal Docker network
- Scan results include sensitive security information and should be handled appropriately
- Consider rate limiting and resource constraints for production deployments

## Troubleshooting

### Common Issues

1. **ZAP Connection Failed**
   - Ensure ZAP container is running and healthy
   - Check network connectivity between containers
   - Verify ZAP API is accessible on configured port

2. **Scan Timeouts**
   - Increase `VULNSCANNER_MAX_TIME` for large applications
   - Check target application responsiveness
   - Monitor ZAP container resources

3. **No Vulnerabilities Found**
   - Verify target application is accessible from ZAP
   - Check ZAP scan configuration and scope
   - Review ZAP logs for scan issues

### Logs

The agent provides detailed logging at multiple levels:
- `INFO`: Scan progress and results
- `DEBUG`: ZAP API interactions
- `ERROR`: Connection and processing errors

## Development

### Testing

Test the agent with the included Juice Shop target:

```bash
# Start the services
docker-compose up -d juice-shop zap

# Run a single scan cycle
python -c "
from agents.hemostat_vulnscanner import VulnerabilityScanner
scanner = VulnerabilityScanner()
scanner.run_scan_cycle()
"
```

### Adding New Targets

Add targets via environment variable:
```bash
export VULNSCANNER_TARGETS="http://app1:8080,http://app2:9090"
```

Or modify the `default_targets` list in the `VulnerabilityScanner` class.

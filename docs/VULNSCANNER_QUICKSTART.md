# HemoStat Vulnerability Scanner Quick Start Guide

This guide walks you through setting up and using the OWASP ZAP vulnerability scanner integration with HemoStat.

## 🚀 Quick Start

### 1. Start the Services

```bash
# Start Juice Shop and ZAP services
docker-compose up -d juice-shop zap

# Wait for services to be healthy (may take 1-2 minutes)
docker-compose ps

# Check service logs if needed
docker-compose logs zap
docker-compose logs juice-shop
```

### 2. Run the Demo

```bash
# Run the interactive demo
python demo_vulnscanner.py
```

This will:
- Connect to ZAP API
- Scan Juice Shop for vulnerabilities  
- Display results with risk categorization
- Save detailed results to `zap_scan_results.json`

### 3. Start the Full System

```bash
# Start all HemoStat services including vulnerability scanner
docker-compose up -d

# Monitor vulnerability scanner logs
docker-compose logs -f vulnscanner
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Vulnerability Scanner Configuration
VULNSCANNER_INTERVAL=3600        # Scan every hour (3600 seconds)
VULNSCANNER_TIMEOUT=1800         # 30 minute timeout per scan
VULNSCANNER_MAX_TIME=3600        # 1 hour maximum scan time
VULNSCANNER_TARGETS=             # Additional targets (comma-separated)

# Example with additional targets:
# VULNSCANNER_TARGETS=http://app1:8080,http://app2:9090
```

### Adding Custom Targets

1. **Via Environment Variable:**
   ```bash
   export VULNSCANNER_TARGETS="http://myapp:8080,http://api:3000"
   docker-compose up -d vulnscanner
   ```

2. **Via Docker Compose Override:**
   ```yaml
   # docker-compose.override.yml
   services:
     vulnscanner:
       environment:
         VULNSCANNER_TARGETS: "http://myapp:8080,http://api:3000"
   ```

## 📊 Monitoring Results

### 1. Dashboard Integration

Access the HemoStat dashboard at http://localhost:8501 to view:
- Real-time vulnerability alerts
- Scan history and trends
- Risk level summaries

### 2. Redis Channels

Monitor vulnerability events directly:

```bash
# Subscribe to vulnerability events
redis-cli -h localhost -p 6379 subscribe hemostat:vulnerabilities

# Subscribe to critical alerts
redis-cli -h localhost -p 6379 subscribe hemostat:alerts
```

### 3. Log Analysis

```bash
# View vulnerability scanner logs
docker-compose logs vulnscanner

# Follow logs in real-time
docker-compose logs -f vulnscanner

# Filter for specific events
docker-compose logs vulnscanner | grep "vulnerability_scan_completed"
```

## 🔍 Understanding Results

### Risk Levels

- **🔴 High**: Critical vulnerabilities requiring immediate attention
- **🟡 Medium**: Important vulnerabilities to address soon
- **🟢 Low**: Minor issues for future consideration
- **ℹ️ Informational**: General security observations

### Common Vulnerabilities in Juice Shop

The OWASP Juice Shop intentionally contains vulnerabilities for testing with ZAP (zaproxy/zap-stable):

- **SQL Injection**: Database query manipulation
- **XSS (Cross-Site Scripting)**: Client-side code injection
- **Broken Authentication**: Login bypass techniques
- **Sensitive Data Exposure**: Information leakage
- **Security Misconfiguration**: Improper security settings

## 🛠️ Troubleshooting

### ZAP Connection Issues

```bash
# Check if ZAP is running
curl http://localhost:8080/JSON/core/view/version/

# Restart ZAP if needed
docker-compose restart zap

# Check ZAP logs
docker-compose logs zap
```

### Juice Shop Connection Issues

```bash
# Check if Juice Shop is accessible
curl http://localhost:3000

# Restart Juice Shop if needed
docker-compose restart juice-shop

# Check Juice Shop logs
docker-compose logs juice-shop
```

### Scan Timeouts

If scans are timing out:

1. **Increase timeout values:**
   ```bash
   export VULNSCANNER_MAX_TIME=7200  # 2 hours
   export VULNSCANNER_TIMEOUT=3600   # 1 hour
   ```

2. **Check target application performance:**
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:3000
   ```

3. **Monitor ZAP resource usage:**
   ```bash
   docker stats hemostat-zap
   ```

### No Vulnerabilities Found

If no vulnerabilities are detected:

1. **Verify target is accessible from ZAP container:**
   ```bash
   docker exec hemostat-zap curl http://juice-shop:3000
   ```

2. **Check ZAP scan configuration:**
   ```bash
   # View active scans
   curl "http://localhost:8080/JSON/ascan/view/scans/"
   ```

3. **Review ZAP spider results:**
   ```bash
   # Check if ZAP discovered URLs
   curl "http://localhost:8080/JSON/core/view/urls/"
   ```

## 🔒 Security Considerations

### Production Deployment

1. **Network Security:**
   - Restrict ZAP API access to internal networks only
   - Use firewall rules to limit exposure

2. **Resource Limits:**
   ```yaml
   services:
     zap:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '1.0'
   ```

3. **Scan Scheduling:**
   - Run scans during off-peak hours
   - Implement rate limiting for production targets

4. **Data Handling:**
   - Vulnerability data contains sensitive information
   - Implement proper access controls
   - Consider data retention policies

### Ethical Scanning

- Only scan applications you own or have permission to test
- Be mindful of scan intensity on production systems
- Follow responsible disclosure practices for findings

## 📚 Additional Resources

- [OWASP ZAP Documentation](https://www.zaproxy.org/docs/)
- [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/)
- [HemoStat Architecture Documentation](docs/architecture.md)
- [ZAP API Reference](https://www.zaproxy.org/docs/api/)

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs`
3. Verify service health: `docker-compose ps`
4. Test individual components with the demo script
5. Check network connectivity between containers

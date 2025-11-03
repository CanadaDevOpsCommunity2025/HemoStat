# Troubleshooting Guide

Solutions for common issues and debugging techniques.

## Common Issues

### Services Won't Start

**Problem:** `docker-compose up` fails or services crash

**Solutions:**

```bash
# Check Docker is running
docker ps

# View service logs
docker-compose logs hemostat-redis
docker-compose logs hemostat-monitor

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Check for port conflicts
lsof -i :8501  # Streamlit
lsof -i :3000  # Arcane
lsof -i :6379  # Redis
```

### Monitor Not Detecting Issues

**Problem:** Container anomalies not appearing in logs

**Check:**

```bash
# View Monitor logs
docker-compose logs -f hemostat-monitor

# Verify Redis connection
docker exec hemostat-redis redis-cli ping

# Check test-api is running
docker-compose ps | grep test-api

# Manually trigger issue
docker exec hemostat-test-api apk add stress
docker exec hemostat-test-api stress --cpu 4 --timeout 10
```

**Solutions:**

- Increase memory/CPU stress to exceed thresholds (80% memory, 85% CPU)
- Check Monitor polling interval (default 30 seconds)
- Verify Redis is healthy: `docker-compose logs hemostat-redis`

### Analyzer Errors

**Problem:** Analyzer crashes or doesn't process alerts

**Check:**

```bash
# View Analyzer logs
docker-compose logs -f hemostat-analyzer

# Check if OpenAI API key is set
echo $OPENAI_API_KEY

# Verify Redis connection
docker exec hemostat-redis redis-cli KEYS "hemostat:*"
```

**Solutions:**

- Without API key, system uses fallback rule-based analysis (normal!)
- Check API key is valid: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
- Check rate limits on OpenAI account
- Review Analyzer logs for error details

### Analyzer - Anthropic API Authentication Error (401)

**Problem:** `Error code: 401 - invalid x-api-key` when using Claude models

**Root Causes:**

1. Wrong environment file being loaded - Docker Compose uses `.env` by default, not `.env.docker.{platform}`
2. Incorrect ChatAnthropic parameter - Using `model_name` instead of `model`
3. API key not in the correct .env file - Key is in `.env.docker.windows` but not in `.env`

**Check:**

```bash
# Verify API key is in the container
docker exec hemostat-analyzer printenv | grep ANTHROPIC_API_KEY

# Check which env file Docker Compose is using
docker inspect hemostat-analyzer | grep -A 20 "Env"

# Verify the API key format (should start with sk-ant-)
docker exec hemostat-analyzer printenv ANTHROPIC_API_KEY
```

**Solutions:**

**Option 1: Use correct env file with Docker Compose (Recommended)**

Always use the platform-specific env file when building/running:

```bash
# Windows
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows build analyzer --no-cache
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d analyzer

# Linux
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux build analyzer --no-cache
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d analyzer

# macOS
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos build analyzer --no-cache
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d analyzer
```

**Option 2: Add API key to default .env file**

Copy your Anthropic API key from `.env.docker.windows` to `.env`:

```bash
# Edit .env and set:
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
AI_MODEL=claude-haiku-4-5-20251001
```

Then rebuild normally:

```bash
docker compose build analyzer --no-cache
docker compose up -d analyzer
```

See README.md section "Building & Rebuilding Services" for complete platform-specific commands.

### Responder Not Fixing Issues

**Problem:** Remediation not executing

**Check:**

```bash
# View Responder logs
docker-compose logs -f hemostat-responder

# Check Docker socket permissions
ls -la /var/run/docker.sock

# Verify container can be restarted
docker exec hemostat-responder docker restart hemostat-test-api
```

**Solutions:**

- Check cooldown not active: `docker exec hemostat-redis redis-cli GET "hemostat:remediation:*"`
- Verify Docker socket is mounted correctly in docker-compose.yml
- Check safety mechanisms (cooldown, max retries) aren't triggered
- Review Responder logs for error details

### Dashboard Not Updating

**Problem:** Streamlit shows no data

**Check:**

```bash
# View Streamlit logs
docker-compose logs -f hemostat-dashboard

# Verify Redis has data
docker exec hemostat-redis redis-cli GET "hemostat:stats:hemostat-test-api"

# Check dashboard can connect to Redis
docker exec hemostat-dashboard ping redis

# Refresh browser
# Streamlit auto-refreshes every 5 seconds
```

**Solutions:**

- Wait 30+ seconds for Monitor to collect first stats
- Manually refresh Streamlit page
- Check Redis is healthy and storing data
- Verify dashboard/app.py is reading correct Redis keys

### Alert Not Sending Slack

**Problem:** No Slack notifications despite fixes

**Check:**

```bash
# View Alert logs
docker-compose logs -f hemostat-alert

# Check Slack webhook URL is set
echo $SLACK_WEBHOOK_URL

# Test webhook manually
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{
    "attachments": [{
      "color": "good",
      "title": "HemoStat Test",
      "text": "This is a test notification"
    }]
  }'
```

**Solutions:**

- Without Slack webhook, system still works (just no notifications)
- Verify webhook URL is correct and active
- Check Slack workspace permissions
- Review Alert logs for HTTP errors

### Performance Issues

**Problem:** System slow or laggy

**Check:**

```bash
# View system resources
docker stats

# Check individual service performance
docker-compose logs hemostat-monitor | grep "published"
docker-compose logs hemostat-analyzer | grep "Published"

# Monitor Redis performance
docker exec hemostat-redis redis-cli --stat
```

**Solutions:**

- Reduce Monitor polling interval (edit hemostat_monitor.py)
- Increase Docker resource limits (edit docker-compose.yml)
- Check Redis is not full: `docker exec hemostat-redis redis-cli INFO memory`
- Clear old events: `docker exec hemostat-redis redis-cli KEYS "hemostat:events:*" | xargs redis-cli DEL`

### Docker Permissions

**Problem:** Permission denied errors

**Check:**

```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Check if user is in docker group
groups $USER
```

**Solutions:**

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Restart Docker service
sudo systemctl restart docker

# Or run docker-compose with sudo
sudo docker-compose up -d
```

## Debug Mode

### Enable Verbose Logging

Edit each agent to add more logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # Change from INFO to DEBUG
```

### Monitor Redis Activity

```bash
# Watch all Redis events in real-time
docker exec hemostat-redis redis-cli SUBSCRIBE "hemostat:*"

# List all Redis keys
docker exec hemostat-redis redis-cli KEYS "*"

# View specific key value
docker exec hemostat-redis redis-cli GET "hemostat:stats:hemostat-test-api"

# Monitor Redis traffic
docker exec hemostat-redis redis-cli MONITOR
```

### Test Individual Components

```bash
# Test Monitor independently
docker run -it hemostat-agents-hemostat-monitor bash
python hemostat_monitor.py

# Test Docker SDK
docker run -it python:3.11 bash
pip install docker
python -c "import docker; c = docker.from_env(); print(c.containers.list())"

# Test Redis connection
docker run -it redis:7-alpine redis-cli -h redis ping
```

## Getting Help

1. **Check logs first:** Most issues show up in Docker logs
2. **Search TROUBLESHOOTING.md:** Common issues documented here
3. **Review docker-compose logs:** Full system trace
4. **Check GitHub issues:** If this was forked from a repo
5. **Ask AI/LLM:** Paste logs into Claude/ChatGPT for analysis

## Performance Tuning

### Monitor Polling Interval

```python
# In agents/hemostat_monitor/monitor.py
time.sleep(30)  # Change to 10 for faster detection, 60 for less CPU
```

### Analyzer Thresholds

```python
# In agents/hemostat_analyzer/analyzer.py
if memory_pct > 90:  # Lower for earlier alerts
if cpu_pct > 90:     # Lower for earlier alerts
```

### Responder Cooldown

```python
# In agents/hemostat_responder/responder.py
self.cooldown_period = 3600  # 1 hour, lower for more restarts
self.max_actions_per_hour = 3  # Increase for more remediation attempts
```

### Dashboard Refresh Rate

```python
# In dashboard/app.py - Streamlit auto-refreshes every 5 seconds
# To change, add to Streamlit config
```

## Advanced Debugging

### Network Inspection

```bash
# Check if agents can communicate
docker exec hemostat-monitor ping hemostat-redis
docker exec hemostat-analyzer ping hemostat-redis

# Test inter-container connectivity
docker network inspect hemostat-agents_default
```

### Resource Limits

```bash
# View resource usage
docker stats hemostat-monitor
docker stats hemostat-analyzer
docker stats hemostat-responder

# Set resource limits in docker-compose.yml
# See docker-compose.yml for examples
```

## Collecting Debug Information

If you're still stuck, capture the output of:

```bash
docker-compose logs > hemostat-debug.log
docker ps > containers.log
docker-compose ps > services.log
```

Review the logs carefully for error messages!

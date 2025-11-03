# HemoStat Deployment Guide

## Production Deployment Checklist

- [ ] All credentials in environment variables (.env file)
- [ ] Redis password configured
- [ ] TLS enabled for all network traffic
- [ ] Logs shipped to centralized logging (ELK, DataDog, etc.)
- [ ] Monitoring and alerting configured
- [ ] Backup strategy for Redis data
- [ ] Disaster recovery plan
- [ ] Security audit completed
- [ ] Performance testing done
- [ ] Load testing done

## Kubernetes Deployment

### Helm Chart Structure

```
hemostat-chart/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── monitor-deployment.yaml
│   ├── analyzer-deployment.yaml
│   ├── responder-deployment.yaml
│   ├── alert-deployment.yaml
│   ├── dashboard-deployment.yaml
│   ├── redis-statefulset.yaml
│   └── configmap.yaml
```

### Deploy to Kubernetes

```bash
helm install hemostat ./hemostat-chart
helm upgrade hemostat ./hemostat-chart
helm uninstall hemostat
```

## Docker Registry

### Push Images

```bash
docker tag hemostat-agents-hemostat-monitor:latest myregistry/hemostat-monitor:v1.0
docker push myregistry/hemostat-monitor:v1.0
```

### Use Private Registry

```yaml
# In docker-compose.yml
hemostat-monitor:
  image: myregistry/hemostat-monitor:v1.0
  imagePullPolicy: IfNotPresent
```

## Cloud Deployments

### AWS ECS

1. Create ECS cluster
2. Push images to ECR
3. Create ECS task definitions
4. Create ECS services
5. Configure auto-scaling

### Azure Container Instances

1. Push images to ACR
2. Create container groups
3. Configure network
4. Set up monitoring

### Google Cloud Run

1. Push images to GCR
2. Deploy services
3. Configure ingress
4. Set up monitoring

## High Availability Setup

### Redis Cluster

```bash
# Multi-node Redis cluster
redis-cli --cluster create node1:6379 node2:6379 node3:6379 ...
```

### Agent Replicas

```yaml
hemostat-analyzer-1:
  build: ./agents/hemostat_analyzer

hemostat-analyzer-2:
  build: ./agents/hemostat_analyzer

hemostat-analyzer-3:
  build: ./agents/hemostat_analyzer
```

### Load Balancing

- Use Redis for load distribution
- Agents pull work from queues
- Automatic failover on agent crash

## Monitoring

### Prometheus Metrics

- Agent cycle times
- Redis latency
- Docker API latency
- Remediation success rate
- False alarm rate

### Grafana Dashboards

1. System overview (all agents)
2. Per-agent metrics
3. Redis performance
4. Historical trends

### Alerting Rules

```yaml
- alert: MonitorHighLatency
  expr: avg(monitor_cycle_time) > 60
  for: 5m

- alert: AnalyzerHighErrorRate
  expr: rate(analyzer_errors[5m]) > 0.1
  for: 5m
```

## Scaling Strategy

### Vertical Scaling

- Increase CPU/memory per agent
- Increase container limits
- Better for single-machine deployments

### Horizontal Scaling

- Run multiple agent instances
- Redis handles message distribution
- Better for production

### Auto-Scaling Rules

```yaml
minReplicas: 1
maxReplicas: 10
targetCPUUtilizationPercentage: 70
```

## Backup and Recovery

### Redis Backup

```bash
# Enable RDB snapshots
redis-cli BGSAVE
docker cp hemostat-redis:/data/dump.rdb ./backup/

# Enable AOF (append-only file)
redis-cli CONFIG SET appendonly yes
```

### Restore Redis

```bash
docker cp ./backup/dump.rdb hemostat-redis:/data/
docker-compose restart hemostat-redis
```

## Security Hardening

### Network

- Use private networks only
- Whitelist allowed IPs
- Disable unnecessary ports

### Secrets Management

```bash
# Use Docker secrets
docker secret create openai_key <(echo "sk-...")
docker secret create slack_webhook <(echo "https://...")
```

### RBAC

```bash
# Kubernetes RBAC
kubectl create role hemostat-reader --verb=get --verb=list --resource=pods
kubectl create rolebinding hemostat-reader-binding --role=hemostat-reader
```

### Audit Logging

- All container operations logged
- All remediation actions logged
- Centralized log aggregation
- Regular audit reviews

## Performance Tuning

### Redis Optimization

```redis
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Agent Optimization

```python
# Tune polling intervals
Monitor: time.sleep(10)      # Faster detection
Analyzer: parallel_analysis  # Process multiple alerts
Responder: batch_execution   # Execute multiple fixes
```

### Docker Optimization

```yaml
# In docker-compose.yml
hemostat-monitor:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

## Disaster Recovery

### Failure Scenarios

**Scenario 1: Redis down**

- Agents queue messages in memory
- Messages lost if multiple agents crash
- Recovery: Restart Redis, restart agents

**Scenario 2: Monitor down**

- No new metrics collected
- Stale data in Redis
- Recovery: Restart Monitor

**Scenario 3: Analyzer down**

- Alerts accumulate in Redis
- Recovery: Restart Analyzer, process queue

**Scenario 4: Responder down**

- Remediation requests queue up
- Issues not fixed
- Recovery: Restart Responder, execute queue

**Scenario 5: Alert down**

- Notifications not sent
- Events still recorded in Redis
- Recovery: Restart Alert, send backlog

### RTO/RPO Goals

- RTO (Recovery Time Objective): < 5 minutes
- RPO (Recovery Point Objective): < 1 minute

---

For detailed deployment steps, consult your cloud provider's documentation.

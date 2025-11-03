# HemoStat Analyzer Agent

## Overview

The Analyzer Agent consumes health alerts from the Monitor Agent, performs AI-powered root cause analysis using LangChain with GPT-4 or Claude, distinguishes real issues from transient spikes, and publishes remediation recommendations or false alarm notifications.

**Key Responsibilities:**
- Subscribe to `hemostat:health_alert` channel for container health events
- Analyze container health issues using AI (GPT-4 or Claude)
- Fall back to rule-based logic if AI fails or is unavailable
- Calculate confidence scores for analysis results
- Publish to `hemostat:remediation_needed` (high confidence) or `hemostat:false_alarm` (low confidence)
- Track alert history for pattern detection and trend analysis

## Architecture

The Analyzer Agent inherits from `HemoStatAgent` base class and implements:

- **LangChain Integration**: Unified interface for OpenAI GPT-4 and Anthropic Claude models
- **Rule-Based Fallback**: Deterministic decision tree for reliability when AI services are unavailable
- **Alert History Tracking**: Redis-backed history for pattern detection and metric trend analysis
- **Structured Event Publishing**: Publishes analysis results to Redis channels for consumption by downstream agents

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODEL` | `gpt-4` | AI model to use: `gpt-4`, `claude-3-opus`, `claude-3-sonnet` |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for GPT-4 (required if using GPT-4) |
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key for Claude (required if using Claude) |
| `AI_FALLBACK_ENABLED` | `false` | Force rule-based analysis (disable AI): set to `true` to skip AI entirely |
| `ANALYZER_CONFIDENCE_THRESHOLD` | `0.7` | Confidence threshold for remediation (0.0-1.0) |
| `ANALYZER_HISTORY_SIZE` | `10` | Maximum alerts to keep in history per container |
| `ANALYZER_HISTORY_TTL` | `3600` | History TTL in seconds (default: 1 hour) |
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | `json` | Log format: json or text |

### AI Model Selection

- **GPT-4**: Best overall accuracy, higher cost, requires OpenAI API key
- **Claude-3-Opus**: Excellent reasoning, comparable to GPT-4, requires Anthropic API key
- **Claude-3-Sonnet**: Faster and cheaper, good for most scenarios

### Confidence Threshold

The `ANALYZER_CONFIDENCE_THRESHOLD` determines when to trigger remediation:

- **Lower threshold (0.5-0.6)**: More aggressive remediation, higher false positive rate
- **Default (0.7)**: Good balance for most scenarios
- **Higher threshold (0.8-0.9)**: More conservative, may miss real issues

## Usage

### Docker Compose (Recommended)

```bash
# Ensure API keys are set in .env
docker-compose up -d analyzer

# View logs
docker-compose logs -f analyzer
```

### Local Development

```bash
# Install dependencies with UV
uv sync --extra agents

# Set API keys in .env
export OPENAI_API_KEY=sk-...
# OR
export ANTHROPIC_API_KEY=sk-ant-...

# Run analyzer
uv run python -m agents.hemostat_analyzer.main
```

### Testing Event Flow

```bash
# Terminal 1: Subscribe to remediation events
redis-cli SUBSCRIBE hemostat:remediation_needed

# Terminal 2: Subscribe to false alarms
redis-cli SUBSCRIBE hemostat:false_alarm

# Terminal 3: Monitor Agent will detect issues and publish to hemostat:health_alert
# (Requires Monitor Agent running)
```

## AI Analysis

### How It Works

1. **Receive Alert**: Analyzer receives health alert with container metrics, anomalies, and health status
2. **Retrieve History**: Fetches historical alerts from Redis for pattern detection
3. **Build Prompt**: Constructs structured prompt with context and asks for root cause analysis
4. **LLM Response**: LLM responds with root cause, remediation action, confidence score, and false alarm assessment
5. **Parse Response**: Extracts structured response and routes to appropriate channel

### Confidence Scoring

- **AI Analysis**: Provides confidence 0.0-1.0 based on analysis certainty
- **Rule-Based Analysis**: Uses fixed confidence levels (0.6-0.9) based on rule type
- **Threshold**: Default 0.7 determines remediation vs. false alarm

### Example Prompt Structure

```
You are an expert DevOps engineer analyzing container health issues.

Container: web-app-1
Health Status: unhealthy

Current Metrics:
- CPU: 95%
- Memory: 88%
- Network I/O: 1.2GB/s
- Exit Code: 0
- Restart Count: 2

Detected Anomalies (3):
- high_cpu (severity: critical)
- high_memory (severity: high)
- excessive_restarts (severity: medium)

Recent alert history (2 alerts):
  Alert 1: CPU=85%, Memory=75%, Anomalies=2
  Alert 2: CPU=95%, Memory=88%, Anomalies=3

Provide your analysis in JSON format with: root_cause, action, reason, confidence, is_false_alarm
```

## Rule-Based Fallback

Used when:
- `AI_FALLBACK_ENABLED=true` (hard switch to disable AI entirely)
- AI API key is not configured (OPENAI_API_KEY or ANTHROPIC_API_KEY missing)
- AI service is unavailable (API errors, rate limits, timeouts)
- AI response parsing fails

### Decision Rules

| Rule | Condition | Action | Confidence | Notes |
|------|-----------|--------|-----------|-------|
| Non-Zero Exit | `exit_code != 0` | restart | 0.9 | Container crashed |
| Excessive Restarts | `restart_count > 5` | none | 0.6 | Circuit breaker (false alarm) |
| Critical Anomaly | Any critical severity | restart | 0.85 | Immediate action needed |
| Unhealthy Status | `health_status == "unhealthy"` | restart | 0.7 | Health check failed |
| Sustained High CPU | `cpu > 90%` for 2+ alerts | restart | 0.75 | Escalating issue |
| Memory Leak | Memory increasing trend | restart | 0.8 | Pattern detected |
| Transient Spike | Single medium anomaly, no history | none | 0.65 | Likely false alarm |
| Default | No rules match | none | 0.5 | Insufficient evidence |

**Note**: Rule-based logic is deterministic and reliable but less nuanced than AI analysis.

## Event Schema

### Input Events

**Channel**: `hemostat:health_alert`  
**Event Type**: `container_unhealthy`

```json
{
  "event_type": "container_unhealthy",
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "agent": "monitor",
  "data": {
    "container_id": "abc123def456",
    "container_name": "web-app-1",
    "image": "myapp:latest",
    "status": "running",
    "health_status": "unhealthy",
    "exit_code": 0,
    "restart_count": 2,
    "metrics": {
      "cpu_percent": 95.5,
      "memory_percent": 88.2,
      "memory_bytes": 1879048192,
      "network_io": "1.2GB/s",
      "disk_io": "50MB/s"
    },
    "anomalies": [
      {
        "type": "high_cpu",
        "severity": "critical",
        "value": 95.5,
        "threshold": 85
      },
      {
        "type": "high_memory",
        "severity": "high",
        "value": 88.2,
        "threshold": 80
      }
    ]
  }
}
```

### Output Events

#### Remediation Needed

**Channel**: `hemostat:remediation_needed`  
**Event Type**: `remediation_needed`

```json
{
  "event_type": "remediation_needed",
  "timestamp": "2024-01-15T10:30:46.234567+00:00",
  "agent": "analyzer",
  "data": {
    "container": "web-app-1",
    "action": "restart",
    "reason": "Sustained high CPU usage (95%) with increasing memory trend; likely resource leak",
    "confidence": 0.85,
    "metrics": {
      "cpu_percent": 95.5,
      "memory_percent": 88.2
    },
    "analysis_method": "ai"
  }
}
```

#### False Alarm

**Channel**: `hemostat:false_alarm`  
**Event Type**: `false_alarm`

```json
{
  "event_type": "false_alarm",
  "timestamp": "2024-01-15T10:30:46.234567+00:00",
  "agent": "analyzer",
  "data": {
    "container": "web-app-1",
    "reason": "Transient CPU spike; no historical pattern detected",
    "confidence": 0.65,
    "analysis_method": "rule_based"
  }
}
```

## Pattern Detection

### Alert History

The Analyzer maintains a history of recent alerts per container in Redis:

- **Storage**: `hemostat:state:alert_history:{container_name}`
- **Size**: Last N alerts (configurable via `ANALYZER_HISTORY_SIZE`, default: 10)
- **TTL**: Configurable via `ANALYZER_HISTORY_TTL` (default: 3600 seconds)

### Trend Detection

Analyzes metric trends over historical alerts to distinguish:

- **Recurring Issues**: Same anomaly type appearing multiple times
- **Escalating Metrics**: CPU/memory increasing over time (potential leak)
- **Transient Spikes**: Single anomaly with no historical pattern

### Examples

| Pattern | Interpretation | Action |
|---------|-----------------|--------|
| Single high CPU spike | Transient load | False alarm |
| Three consecutive high CPU alerts | Sustained issue | Restart |
| Memory 60% → 70% → 80% | Memory leak | Restart |
| Recurring "unhealthy" status | Persistent problem | Restart |

## Troubleshooting

### "AI analysis not working"

**Check**:
- API keys are set correctly in `.env`
- API key is valid and has sufficient quota
- Check logs for API errors: `docker-compose logs analyzer | grep -i error`

**Solution**:
```bash
# Verify API key
echo $OPENAI_API_KEY

# Check logs
docker-compose logs -f analyzer
```

### "Always using rule-based fallback"

**Check**:
- `AI_FALLBACK_ENABLED` is not set to `true`
- LangChain and AI SDK imports are available
- Check for import errors in logs

**Solution**:
```bash
# Verify dependencies
uv sync --extra agents

# Check import
python -c "from langchain_openai import ChatOpenAI; print('OK')"
```

### "Too many false alarms"

**Adjust**:
- Lower `ANALYZER_CONFIDENCE_THRESHOLD` (e.g., 0.6)
- Increase Monitor Agent thresholds to reduce noise
- Review rule-based logic for overly aggressive rules

### "Missing real issues"

**Adjust**:
- Raise `ANALYZER_CONFIDENCE_THRESHOLD` (e.g., 0.8)
- Review rule-based logic for insufficient coverage
- Check alert history is being tracked: `redis-cli GET hemostat:state:alert_history:*`

### "Redis connection failed"

**Check**:
- Redis service is running: `docker-compose ps redis`
- `REDIS_HOST` and `REDIS_PORT` are correct
- Network connectivity: `docker-compose exec analyzer ping redis`

### "LangChain import errors"

**Solution**:
```bash
# Ensure agents extra is installed
uv sync --extra agents

# Verify LangChain version
python -c "import langchain; print(langchain.__version__)"
```

### "API rate limits"

**Solutions**:
- Implement request throttling
- Use Claude-3-Sonnet (faster, cheaper)
- Increase retry delays: `AGENT_RETRY_DELAY=2`

## Development

### Running Tests

```bash
# Unit tests (Phase 4)
pytest tests/analyzer/

# Integration tests
pytest tests/integration/
```

### Adding New AI Models

Extend `_initialize_llm()` method:

```python
elif self.ai_model.startswith("gpt-3.5"):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=self.ai_model, temperature=0.3, api_key=api_key)
```

### Customizing Rule-Based Logic

Modify `_rule_based_analyze()` method to add new rules or adjust thresholds.

### Adjusting Prompt Templates

Modify the prompt text in `_ai_analyze()` method to change analysis focus.

## Dependencies

All dependencies are managed via UV and `pyproject.toml`:

- `langchain==0.1.0` - LLM orchestration
- `openai==1.10.0` - GPT-4 integration
- `anthropic==0.8.0` - Claude integration
- `redis==5.0.1` - Redis client (from base dependencies)
- `python-dotenv==1.0.0` - Environment loading (from base dependencies)
- `python-json-logger==2.0.7` - Structured logging (from base dependencies)

**Installation**:
```bash
uv sync --extra agents
```

## Next Steps

- **Phase 2c - Responder Agent**: Consumes `hemostat:remediation_needed` events and safely executes container remediation actions
- **Phase 2d - Alert Agent**: Logs false alarms and publishes notifications to external channels (Slack, email, etc.)
- **Phase 3 - Dashboard**: Real-time monitoring UI with event history and metrics visualization
- **Phase 4 - Testing**: Comprehensive test suite with unit and integration tests

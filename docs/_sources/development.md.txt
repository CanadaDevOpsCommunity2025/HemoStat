# Development Guide

Guide for contributing to HemoStat and setting up your development environment.

## Development Setup

### Install uv

HemoStat uses `uv` for fast Python package management:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or on Windows with PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Set Up Virtual Environment

```bash
# Install all dependencies including dev tools
uv sync --all-extras

# Or just core dependencies
uv sync
```

### Load Environment Configuration

```bash
# Copy from template
cp .env.example .env

# Edit .env with your API keys:
# - OPENAI_API_KEY (for GPT-4 analysis)
# - ANTHROPIC_API_KEY (for Claude analysis)
# - SLACK_WEBHOOK_URL (for notifications)
```

## Code Quality Tools

HemoStat uses modern, fast tools from Astral (creators of uv):

### Ruff (Linting & Formatting)

Fast Python linter and formatter (written in Rust):

```bash
# Format code
ruff format

# Lint and auto-fix
ruff check --fix
```

### ty (Type Checking)

Modern type checker (written in Rust):

```bash
# Run type checker
ty check
```

### Run All Quality Checks

```bash
# Using make (recommended)
make quality

# Or manually
ruff format && ruff check --fix && ty check
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Development Workflow

### Running Agents Locally

Start Redis first (required for all agents):

```bash
docker compose up -d redis
```

Then run individual agents:

```bash
# Using make
make monitor
make analyzer
make responder
make alert

# Or directly
python -m agents.hemostat_monitor.main
python -m agents.hemostat_analyzer.main
python -m agents.hemostat_responder.main
python -m agents.hemostat_alert.main
```

### Running the Dashboard

```bash
streamlit run dashboard/app.py
# Access at http://localhost:8501
```

### Testing Changes

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_monitor.py -v

# Run single test
pytest tests/test_monitor.py::TestMonitorAgent::test_cpu_threshold -v

# Run with coverage report
pytest --cov=agents --cov-report=html
# View report at htmlcov/index.html
```

### Running Quality Checks

```bash
# Format code
make format

# Lint with auto-fix
make lint

# Type check
make typecheck

# Run all checks
make quality
```

## Understanding the Architecture

### Multi-Agent Message Flow

HemoStat uses a **pub/sub architecture** with four specialized agents communicating via Redis:

1. **Monitor Agent** - Continuously polls container metrics (CPU, memory, disk, process status)
2. **Analyzer Agent** - Receives health events, performs AI-powered root cause analysis using GPT-4 or Claude
3. **Responder Agent** - Receives remediation recommendations, executes safe container actions (restart, scale, cleanup)
4. **Alert Agent** - Receives remediation events, sends Slack notifications and stores event history

All agents inherit from `HemoStatAgent` base class which provides:

- Redis pub/sub communication primitives
- Shared state management
- Graceful shutdown handling and connection retry logic

See the [Architecture documentation](architecture.md) for detailed information.

### Redis Channel Schema

```text
hemostat:health_alert           (Monitor → Analyzer)
hemostat:remediation_needed     (Analyzer → Responder)
hemostat:remediation_complete   (Responder → Alert)
hemostat:false_alarm            (Analyzer → Alert)
```

See the [API Protocol documentation](api_protocol.md) for message formats.

## Writing Docstrings

All code should include Google-style docstrings. These are automatically extracted and included in the [API Reference documentation](api/index.rst).

### Example: Function Docstring

```python
def analyze_container_health(container_name: str, metrics: Dict) -> Dict:
    """Analyze container health and determine if remediation is needed.
    
    Performs AI-powered root cause analysis on container metrics to determine
    if the issue is real or a false alarm. Returns analysis results with
    confidence scoring.
    
    Args:
        container_name: Name of the container to analyze
        metrics: Dictionary of container metrics (cpu_pct, memory_pct, etc.)
    
    Returns:
        Dictionary containing:
            - action: Recommended remediation action (restart, scale, etc.)
            - confidence: Confidence score (0.0-1.0)
            - reason: Human-readable explanation
    
    Raises:
        ValueError: If metrics are invalid or incomplete
        ConnectionError: If AI service is unavailable
    """
    # Implementation here
    pass
```

### Example: Class Docstring

```python
class ContainerMonitor(HemoStatAgent):
    """Monitors Docker container health and publishes alerts.
    
    Continuously polls container metrics and detects anomalies. When issues
    are detected, publishes health_alert events to Redis for the Analyzer
    to process.
    
    Attributes:
        polling_interval: Seconds between health checks (default: 30)
        thresholds: Dict of metric thresholds (cpu_pct, memory_pct, etc.)
    """
    
    def __init__(self, agent_name: str = "Monitor", **kwargs):
        """Initialize the Monitor Agent.
        
        Args:
            agent_name: Name for this agent instance
            **kwargs: Additional arguments passed to HemoStatAgent
        """
        super().__init__(agent_name=agent_name, **kwargs)
```

## Adding Features

### Adding a New Agent

1. Create `agents/my_agent/my_agent.py`
2. Import `HemoStatAgent` from `agents.agent_base`
3. Override `run()` method
4. Subscribe to relevant Redis channels
5. Publish events to specific channels
6. Add Dockerfile and update docker-compose.yml
7. Write comprehensive docstrings (they'll appear in API docs!)

See the [API Reference](api/agents.rst) for the `HemoStatAgent` base class documentation.

### Adding New Remediation Actions

1. Edit `agents/hemostat_responder/responder.py`
2. Add new method (e.g., `scale_container()`)
3. Update `_handle_remediation_request()` to call new method
4. Update Analyzer to suggest new action
5. Document the new action with docstrings

### Customizing Monitor Thresholds

Edit `agents/hemostat_monitor/monitor.py`:

```python
self.thresholds = {
    'memory_pct': 80,   # Change to 70 for earlier alerts
    'cpu_pct': 85       # Change to 75 for earlier alerts
}
```

## Testing with Dry-Run Mode

Test remediation actions without modifying containers:

```bash
# Set dry-run mode
export RESPONDER_DRY_RUN=true

# Run responder
python -m agents.hemostat_responder.main

# Actions will be logged but not executed
```

## Contributing Guidelines

### Code Style

- Follow Google-style docstrings (they're auto-documented!)
- Use type hints for all function parameters and returns
- Line length: 100 characters (enforced by ruff)
- Use double quotes for strings (enforced by ruff)

### Testing Requirements

- Write tests for new features
- Run `make test` before committing
- Aim for >80% code coverage

### Documentation Requirements

- Write comprehensive docstrings (they appear in API docs!)
- Update relevant markdown files in `docs/`
- Update README.md if adding major features

### Making Commits

```bash
# Run quality checks before committing
make quality

# Run tests
make test

# Commit with descriptive message
git commit -m "Add feature: description"
```

## Project Phases

### Phase 1: Core Architecture ✅

- Multi-agent system with Redis pub/sub
- Base agent class with communication primitives
- Logging and error handling

### Phase 2: Agent Implementations ✅

- Monitor Agent - Container health polling
- Analyzer Agent - AI-powered analysis
- Responder Agent - Safe remediation
- Alert Agent - Slack notifications

### Phase 3: Dashboard ✅

- Streamlit-based monitoring interface
- Real-time metrics and event visualization
- Historical data and trends

### Phase 4: Testing & Monitoring 🔄

- Unit tests for all agents
- Integration tests
- Performance monitoring
- CI/CD pipeline

## Useful Commands

```bash
# View logs for a specific service
docker-compose logs -f monitor

# Rebuild a service after code changes
docker-compose build analyzer --no-cache
docker-compose up -d analyzer

# Run agents locally (requires Redis)
make monitor

# Run quality checks
make quality

# Run tests with coverage
make test-cov

# View test coverage report
open htmlcov/index.html

# Clean up build artifacts
make clean
```

## Getting Help

- **Architecture questions**: See [Architecture documentation](architecture.md)
- **API questions**: See [API Reference](api/index.rst) (auto-generated from docstrings!)
- **Common issues**: See [Troubleshooting guide](troubleshooting.md)
- **Deployment**: See [Deployment guide](deployment.md)

## Documentation

Your docstrings are automatically included in the [API Reference documentation](api/index.rst)! Write clear, comprehensive docstrings and they'll be visible to all users.

To build and view documentation locally:

```bash
# Install docs dependencies
make docs-install

# Build documentation
make docs-build

# Serve locally
make docs-serve
# View at http://localhost:8000
```

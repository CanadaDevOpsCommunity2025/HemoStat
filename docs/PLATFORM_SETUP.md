# HemoStat Platform Setup Guide

This guide explains how HemoStat automatically detects your operating system and configures Docker socket access for Windows, Linux, and macOS.

## Quick Start

### For Local Development

```bash
# Copy the local environment file
cp .env.local .env

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# In separate terminals, run each agent:
uv run python -m agents.hemostat_monitor.main
uv run python -m agents.hemostat_analyzer.main
uv run python -m agents.hemostat_responder.main
uv run python -m agents.hemostat_alert.main
uv run streamlit run dashboard/app.py
```

The system will automatically detect your OS and use the correct Docker socket!

### For Docker Compose

**Windows:**

```bash
docker compose -f docker-compose.yml -f docker-compose.windows.yml --env-file .env.docker.windows up -d
```

**Linux:**

```bash
docker compose -f docker-compose.yml -f docker-compose.linux.yml --env-file .env.docker.linux up -d
```

**macOS:**

```bash
docker compose -f docker-compose.yml -f docker-compose.macos.yml --env-file .env.docker.macos up -d
```

## How It Works

### Platform Detection

HemoStat uses `agents/platform_utils.py` to automatically detect:

1. **Operating System**: Windows, Linux, or macOS
2. **Execution Environment**: Local or inside Docker container
3. **Docker Socket Path**: Appropriate for the platform

### Docker Socket Paths

| Platform | Local | In Docker |
|----------|-------|-----------|
| Windows | `npipe:////./pipe/docker_engine` | `unix:///var/run/docker.sock` |
| Linux | `unix:///var/run/docker.sock` | `unix:///var/run/docker.sock` |
| macOS | `unix:///var/run/docker.sock` | `unix:///var/run/docker.sock` |

**Note**: When running inside Docker containers on Windows, Docker Desktop automatically maps the named pipe to `/var/run/docker.sock`, so all containers use the Unix socket path.

### Environment Files

- **`.env.local`**: Auto-detected platform (for local development)
- **`.env.docker.windows`**: Explicit Windows Docker Compose config
- **`.env.docker.linux`**: Explicit Linux Docker Compose config
- **`.env.docker.macos`**: Explicit macOS Docker Compose config

### Agent Logging

Each agent logs its detected platform on startup:

```text
Agent 'monitor' initialized successfully on Windows (local)
Agent 'responder' initialized successfully on Linux (in Docker)
Agent 'analyzer' initialized successfully on macOS (local)
```

## Troubleshooting

### Docker Connection Fails

If agents can't connect to Docker:

1. **Windows**: Ensure Docker Desktop is running
2. **Linux**: Ensure Docker daemon is running (`sudo systemctl start docker`)
3. **macOS**: Ensure Docker Desktop is running

### Override Auto-Detection

You can override the auto-detected socket by setting `DOCKER_HOST`:

```bash
# Force a specific Docker socket
export DOCKER_HOST=unix:///var/run/docker.sock
uv run python -m agents.hemostat_monitor.main
```

### Check Detected Platform

Add debug logging to see what platform was detected:

```bash
export LOG_LEVEL=DEBUG
uv run python -m agents.hemostat_monitor.main
```

## For Team Development

1. Each team member clones the repo
2. Copy `.env.local` to `.env`
3. Run agents locally - platform is auto-detected!
4. Or use Docker Compose with the appropriate `.env.docker.*` file

No manual configuration needed - HemoStat handles it automatically!

## Implementation Details

### Platform Detection Code

Located in `agents/platform_utils.py`:

- `get_platform()`: Returns OS name (Windows, Linux, Darwin)
- `is_in_docker()`: Checks for `/.dockerenv` file
- `get_docker_host()`: Returns appropriate socket path
- `get_platform_display()`: Human-readable platform info for logging

### Agent Integration

All agents inherit platform detection through `HemoStatAgent` base class:

- Logs platform on initialization
- Responder and Monitor use `get_docker_host()` for Docker connection
- Environment variable `DOCKER_HOST` can override auto-detection

## Questions?

Check the logs to see what platform was detected:

```bash
docker compose logs monitor | grep "initialized successfully"
```

The output will show the detected platform and whether it's running locally or in Docker.

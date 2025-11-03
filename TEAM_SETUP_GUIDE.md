# HemoStat Team Setup Guide

Quick setup guide for new team members to get HemoStat running with optimal build performance.

## Prerequisites

Before you start, ensure you have:

- ✅ **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
  - Windows: https://www.docker.com/products/docker-desktop
  - macOS: https://www.docker.com/products/docker-desktop
  - Linux: https://docs.docker.com/engine/install/
  
- ✅ **Python 3.11+**
  - Download: https://www.python.org/downloads/

- ✅ **UV Package Manager**
  - Install: https://docs.astral.sh/uv/getting-started/installation/

- ✅ **Git**
  - Download: https://git-scm.com/downloads

## Step 1: Clone Repository

```bash
git clone https://github.com/jondmarien/HemoStat.git
cd HemoStat
```

## Step 2: Enable BuildKit (IMPORTANT!)

**This makes builds 95% faster on rebuilds!**

Choose your platform:

### 🪟 Windows

```powershell
.\scripts\windows\enable_buildkit.ps1
```

### 🐧 Linux

```bash
chmod +x scripts/linux/enable_buildkit.sh
./scripts/linux/enable_buildkit.sh
```

### 🍎 macOS

```zsh
chmod +x scripts/macos/enable_buildkit.zsh
./scripts/macos/enable_buildkit.zsh
```

**Important:** Restart your terminal after running the script!

See [scripts/BUILDKIT_SETUP.md](scripts/BUILDKIT_SETUP.md) for troubleshooting.

## Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# Required:
#   - ANTHROPIC_API_KEY or OPENAI_API_KEY (for AI analysis)
#   - HUGGINGFACE_API_KEY (optional, for HF models)
# Optional:
#   - SLACK_WEBHOOK_URL (for Slack notifications)
```

**Get API Keys:**
- **Anthropic (Claude)**: https://console.anthropic.com/ (Recommended)
- **OpenAI (GPT-4)**: https://platform.openai.com/api-keys
- **HuggingFace**: https://huggingface.co/settings/tokens
- **Slack Webhook**: https://api.slack.com/messaging/webhooks

## Step 4: Build Project

### First Build (Will Take ~10 minutes)

This is normal! BuildKit is downloading and caching all dependencies.

**Windows:**
```powershell
make windows-build
```

**Linux:**
```bash
make linux-build
```

**macOS:**
```bash
make macos-build
```

**What's happening:**
- Downloading Python packages (langchain, huggingface, etc.)
- Building Docker images
- Caching everything for future builds

☕ Go grab a coffee! This only happens once.

### Subsequent Builds (~30 seconds!)

After the first build, rebuilds are **95% faster** thanks to BuildKit cache!

```bash
# Make a code change, then:
make windows-build  # or linux-build or macos-build
```

⚡ Should complete in ~30 seconds!

## Step 5: Start Services

```bash
# Windows
make windows-up

# Linux
make linux-up

# macOS
make macos-up
```

**Verify services are running:**
```bash
docker compose ps
```

You should see:
- ✅ hemostat-redis
- ✅ hemostat-monitor
- ✅ hemostat-analyzer
- ✅ hemostat-responder
- ✅ hemostat-alert
- ✅ hemostat-metrics
- ✅ hemostat-prometheus
- ✅ hemostat-grafana
- ✅ hemostat-dashboard

## Step 6: Access Dashboards

Open in your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Streamlit Dashboard** | http://localhost:8501 | None |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9091 | None |
| **Metrics** | http://localhost:9090/metrics | None |

## Step 7: Test the System

Run a demo scenario:

**Windows:**
```powershell
.\scripts\windows\demo_trigger_cpu_spike.ps1
```

**Linux:**
```bash
./scripts/linux/demo_trigger_cpu_spike.sh
```

**macOS:**
```zsh
./scripts/macos/demo_trigger_cpu_spike.zsh
```

**Watch the magic happen:**
1. Open Streamlit dashboard: http://localhost:8501
2. Run the demo script
3. See the system detect, analyze, and remediate the issue!

## Common Commands

```bash
# View logs
docker compose logs -f

# View specific service
docker compose logs -f analyzer

# Restart a service
docker compose restart analyzer

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v

# Run quality checks
make quality

# Run tests
make test
```

## Troubleshooting

### Build Timing Out?

If you see timeout errors downloading packages:

1. **Increase timeout** - Already set to 1000s (16 minutes)
2. **Check internet connection** - Large packages like `hf-xet` are slow
3. **Try again** - Sometimes package registries are slow
4. **Use different time** - Try building during off-peak hours

### BuildKit Not Working?

```bash
# Verify BuildKit is enabled
# Linux/macOS:
echo $DOCKER_BUILDKIT  # Should show: 1

# Windows PowerShell:
$env:DOCKER_BUILDKIT   # Should show: 1
```

If not enabled:
1. Run the enable script again
2. Restart your terminal
3. Try building again

### Docker Not Running?

**Windows/macOS:**
- Open Docker Desktop
- Wait for Docker to start (whale icon in system tray)
- Try again

**Linux:**
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Permission Denied?

**Linux/macOS:**
```bash
# Add yourself to docker group
sudo usermod -aG docker $USER

# Log out and back in for changes to take effect
```

### Services Not Starting?

```bash
# Check logs for errors
docker compose logs

# Check specific service
docker compose logs monitor

# Restart all services
docker compose restart

# Nuclear option: clean rebuild
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Performance Tips

### 1. Use BuildKit (Already Enabled!)
- First build: 10 minutes
- Rebuilds: 30 seconds ⚡

### 2. Don't Clean Too Often
```bash
# This removes cache (avoid unless necessary)
docker compose down -v
docker buildx prune --all
```

### 3. Selective Rebuilds
```bash
# Only rebuild what changed
docker compose build analyzer
docker compose up -d analyzer
```

### 4. Cache Management
```bash
# View cache size
docker buildx du

# Clean old cache (safe, keeps recent)
docker buildx prune

# Only if you need space:
docker buildx prune --all --force
```

## Project Structure

```
HemoStat/
├── agents/               # HemoStat agents
│   ├── hemostat_monitor/
│   ├── hemostat_analyzer/
│   ├── hemostat_responder/
│   ├── hemostat_alert/
│   └── hemostat_metrics/
├── dashboard/           # Streamlit UI
├── monitoring/          # Prometheus & Grafana configs
├── scripts/            # Demo and utility scripts
├── docs/               # Documentation
├── .env                # Your environment config
├── docker-compose.yml  # Service orchestration
└── pyproject.toml      # Python dependencies
```

## Next Steps

1. **Read the docs**: https://quartz.chron0.tech/HemoStat/
2. **Explore agents**: Check out `agents/` directory
3. **Try demos**: Run scripts in `scripts/`
4. **Check monitoring**: View Grafana dashboards
5. **Make changes**: Edit code and rebuild (fast!)

## Getting Help

1. **Check logs**: `docker compose logs <service>`
2. **View docs**: See `docs/` directory
3. **Ask team**: Reach out in team chat
4. **GitHub Issues**: https://github.com/jondmarien/HemoStat/issues

## Team Collaboration

### Branch Strategy
- `main` - Stable production code
- `develop` - Integration branch
- `feature/*` - New features
- `fix/*` - Bug fixes

### Before Committing
```bash
# Run quality checks
make quality

# Run tests
make test

# Format code
make format
```

### Pull Request Process
1. Create feature branch
2. Make changes
3. Run quality checks
4. Commit with descriptive message
5. Push and create PR
6. Wait for review
7. Address feedback
8. Merge!

## Welcome to HemoStat! 🎉

You're all set! Start building, testing, and iterating on HemoStat.

**Remember:**
- ⚡ BuildKit makes rebuilds super fast
- 📊 Check Grafana for metrics
- 🔍 Check logs when things go wrong
- 🤝 Ask questions in team chat

Happy coding! 🚀

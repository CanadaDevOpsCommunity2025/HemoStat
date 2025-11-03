# Docker BuildKit Quick Reference

## 🚀 One-Time Setup

```powershell
# Enable BuildKit permanently
.\scripts\windows\enable_buildkit.ps1

# Restart your terminal after running
```

## ✅ Verify It's Working

```powershell
# Check environment
$env:DOCKER_BUILDKIT
# Should show: 1

# Check buildx
docker buildx version
```

## 🔨 Build Commands

```powershell
# Full stack build (with cache)
make windows-build

# Individual service
docker compose build analyzer

# Force rebuild (no cache)
docker compose build --no-cache analyzer

# Build and start
make windows
```

## 📊 Cache Management

```powershell
# View cache usage
docker buildx du

# Clean old cache (safe)
docker buildx prune

# Clean all cache (nuclear)
docker buildx prune --all --force
```

## ⚡ Speed Benefits

| Build | Without BuildKit | With BuildKit |
|-------|-----------------|---------------|
| **First** | 10 minutes | 10 minutes |
| **Second** | 10 minutes | 30 seconds ⚡ |
| **Third** | 10 minutes | 30 seconds ⚡ |

**Time Saved:** ~95% on rebuilds!

## 🎯 What BuildKit Does

✅ **Caches downloaded packages** (hf-xet, langchain, etc.)  
✅ **Builds stages in parallel**  
✅ **Shows better progress**  
✅ **Skips unused stages**  

## 📝 Cache Locations in Dockerfiles

```dockerfile
# UV cache (analyzer, monitor, responder, alert, dashboard)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra agents

# Pip cache (metrics)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install packages
```

## 🔧 Troubleshooting

**BuildKit not enabled?**
```powershell
$env:DOCKER_BUILDKIT=1
$env:COMPOSE_DOCKER_CLI_BUILD=1
```

**Still slow?**
- First build is always slow (downloading packages)
- Second+ builds use cache and are MUCH faster
- Check: `docker buildx du` to see cache

**Cache not working?**
- Verify Docker version: `docker version` (need 18.09+)
- Check Dockerfile has `RUN --mount=type=cache,...`

## 📖 More Info

See [BUILDKIT_GUIDE.md](BUILDKIT_GUIDE.md) for complete documentation.

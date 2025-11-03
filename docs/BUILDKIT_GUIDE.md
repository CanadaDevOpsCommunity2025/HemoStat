# Docker BuildKit Setup & Usage Guide

## What is Docker BuildKit?

**Docker BuildKit** is Docker's next-generation build engine that provides significant improvements over the legacy builder.

### Key Features

#### 1. **Cache Mounts** (Most Important for HemoStat!)
Persist package manager caches (pip, uv, npm, apt) between builds:
```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra agents
```

**Before BuildKit:**
- Every build downloads ALL packages (including slow hf-xet)
- Build #1: Download 200MB of packages ⏱️ 10 minutes
- Build #2: Download 200MB AGAIN ⏱️ 10 minutes
- Build #3: Download 200MB AGAIN ⏱️ 10 minutes

**With BuildKit Cache:**
- First build downloads packages ⏱️ 10 minutes
- Subsequent builds reuse cache ⏱️ 30 seconds
- Only NEW packages are downloaded

#### 2. **Parallel Builds**
- Build independent stages simultaneously
- Multi-agent builds run in parallel

#### 3. **Better Progress Output**
- Live build progress with real-time stats
- Colored output
- Time estimates

#### 4. **Skip Unused Stages**
- Only builds stages you actually need
- Multi-stage builds are more efficient

#### 5. **Build Secrets**
- Inject secrets without leaving them in layers
- Safer than environment variables

## Setup Instructions

### Method 1: Enable Permanently (Recommended)

Choose your platform and run the setup script:

**🪟 Windows (PowerShell):**
```powershell
.\scripts\windows\enable_buildkit.ps1
```

**🐧 Linux (Bash):**
```bash
chmod +x scripts/linux/enable_buildkit.sh
./scripts/linux/enable_buildkit.sh
```

**🍎 macOS (Zsh):**
```zsh
chmod +x scripts/macos/enable_buildkit.zsh
./scripts/macos/enable_buildkit.zsh
```

**Then restart your terminal!**

See [scripts/BUILDKIT_SETUP.md](scripts/BUILDKIT_SETUP.md) for detailed platform-specific instructions.

**Manual Setup (if script fails):**

Windows PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable('DOCKER_BUILDKIT', '1', 'User')
[System.Environment]::SetEnvironmentVariable('COMPOSE_DOCKER_CLI_BUILD', '1', 'User')
```

Linux/macOS - Add to `~/.bashrc` or `~/.zshrc`:
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

Then: `source ~/.bashrc` (or `~/.zshrc`)

### Method 2: Enable Per-Session

**Windows PowerShell:**
```powershell
$env:DOCKER_BUILDKIT=1
$env:COMPOSE_DOCKER_CLI_BUILD=1
```

**Windows CMD:**
```cmd
set DOCKER_BUILDKIT=1
set COMPOSE_DOCKER_CLI_BUILD=1
```

**Linux/macOS:**
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### Method 3: Enable Per-Command

```powershell
# Single build
$env:DOCKER_BUILDKIT=1; docker compose build

# Or
docker buildx build -t myimage .
```

## Verify BuildKit is Enabled

**Check environment variables:**
```bash
# Linux/macOS
echo $DOCKER_BUILDKIT
echo $COMPOSE_DOCKER_CLI_BUILD

# Windows PowerShell
$env:DOCKER_BUILDKIT
$env:COMPOSE_DOCKER_CLI_BUILD

# All should show: 1
```

**Check BuildKit availability:**
```bash
# All platforms
docker buildx version

# Build with BuildKit (you should see new progress format)
docker compose build monitor
```

**BuildKit Enabled Output:**
```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.23kB
 => [internal] load .dockerignore
 => [builder 1/5] FROM docker.io/library/python:3.11-slim
 => [builder 2/5] WORKDIR /build
 => [builder 3/5] RUN pip install uv
 => [builder 4/5] COPY pyproject.toml ./
 => [builder 5/5] RUN --mount=type=cache,target=/root/.cache/uv uv sync
```

**Legacy Builder Output (no BuildKit):**
```
Step 1/10 : FROM python:3.11-slim
 ---> abc123def456
Step 2/10 : WORKDIR /build
 ---> Running in xyz789
```

## Build Commands with Cache

### Full Stack Build
```powershell
# Windows with BuildKit cache
make windows-build

# Equivalent manual command
docker compose -f docker-compose.yml -f docker-compose.windows.yml build
```

### Individual Service Build
```powershell
# Rebuild analyzer with cache
docker compose build analyzer

# Rebuild without cache (fresh start)
docker compose build --no-cache analyzer
```

### View Cache Usage
```powershell
# List BuildKit cache
docker buildx du

# Clean old cache (keeps recent)
docker buildx prune

# Clean all cache (nuclear option)
docker buildx prune --all
```

## How Cache Mounts Work in HemoStat

### Example: Analyzer Agent

**Dockerfile with Cache Mount:**
```dockerfile
# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /build
COPY pyproject.toml uv.lock* ./
COPY agents/ ./agents/

# Cache mount persists between builds!
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra agents --no-dev
```

**What Happens:**

**First Build:**
1. UV downloads `langchain`, `langchain-huggingface`, `hf-xet`, etc.
2. Files saved to `/root/.cache/uv` IN THE CACHE (not the image)
3. Build completes in ~10 minutes

**Second Build (code change):**
1. UV checks `/root/.cache/uv` (CACHE IS STILL THERE!)
2. Packages already downloaded, skip download
3. Build completes in ~30 seconds ⚡

**Third Build (new dependency):**
1. UV checks `/root/.cache/uv`
2. Most packages cached, only downloads NEW package
3. Build completes in ~1-2 minutes

## Cache Mount Locations

All HemoStat Dockerfiles now use cache mounts:

| Service | Cache Location | Purpose |
|---------|---------------|---------|
| **monitor** | `/root/.cache/uv` | UV package cache |
| **analyzer** | `/root/.cache/uv` | UV package cache (HuggingFace!) |
| **responder** | `/root/.cache/uv` | UV package cache |
| **alert** | `/root/.cache/uv` | UV package cache |
| **metrics** | `/root/.cache/pip` | Pip package cache |
| **dashboard** | `/root/.cache/uv` | UV package cache |

## Performance Comparison

### Without BuildKit Cache

```
Build #1: ████████████████████ 600s (10 min)
Build #2: ████████████████████ 600s (10 min)
Build #3: ████████████████████ 600s (10 min)
```

### With BuildKit Cache

```
Build #1: ████████████████████ 600s (10 min) - Initial download
Build #2: ███░░░░░░░░░░░░░░░░░  30s (0.5 min) - Cache hit! ⚡
Build #3: ███░░░░░░░░░░░░░░░░░  30s (0.5 min) - Cache hit! ⚡
```

**Time Saved:** ~95% reduction in rebuild time!

## Advanced BuildKit Features

### 1. Inline Cache (for CI/CD)

Export cache with image:
```powershell
docker buildx build \
  --cache-to type=inline \
  --tag myimage:latest \
  .
```

### 2. Registry Cache (share with team)

```powershell
# Build and push cache to registry
docker buildx build \
  --cache-to type=registry,ref=myregistry/myapp:buildcache \
  --cache-from type=registry,ref=myregistry/myapp:buildcache \
  --tag myimage:latest \
  .
```

### 3. Local Cache Export

```powershell
docker buildx build \
  --cache-to type=local,dest=./buildcache \
  --cache-from type=local,src=./buildcache \
  .
```

### 4. Multi-Platform Builds

```powershell
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myimage:latest \
  .
```

## Troubleshooting

### BuildKit Not Working?

**Check if enabled:**
```powershell
$env:DOCKER_BUILDKIT
# Should output: 1
```

**Enable for session:**
```powershell
$env:DOCKER_BUILDKIT=1
$env:COMPOSE_DOCKER_CLI_BUILD=1
```

### Cache Not Persisting?

**Check Docker version:**
```powershell
docker version
# BuildKit requires Docker 18.09+
```

**Verify cache mount syntax:**
```dockerfile
# Correct
RUN --mount=type=cache,target=/root/.cache/uv uv sync

# Wrong (no --mount)
RUN uv sync
```

### Slow First Build?

- This is normal! Cache mounts only help on SECOND+ builds
- First build must download everything
- Set `UV_HTTP_TIMEOUT=1000` for slow networks

### Cache Taking Too Much Space?

```powershell
# Check cache size
docker buildx du

# Clean old cache (keeps recent)
docker buildx prune

# Clean all cache (fresh start)
docker buildx prune --all --force
```

## Best Practices

### 1. Order Dockerfile Commands

**Bad (cache invalidates often):**
```dockerfile
COPY . .                    # Changes invalidate cache
RUN uv sync                 # Has to rerun every time
```

**Good (cache persists longer):**
```dockerfile
COPY pyproject.toml ./      # Rarely changes
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync                 # Cache persists!
COPY . .                    # Changes don't affect uv sync
```

### 2. Use Specific Cache Targets

```dockerfile
# UV cache
RUN --mount=type=cache,target=/root/.cache/uv

# Pip cache
RUN --mount=type=cache,target=/root/.cache/pip

# Apt cache
RUN --mount=type=cache,target=/var/cache/apt
```

### 3. Combine with Multi-Stage Builds

```dockerfile
# Stage 1: Builder (with cache)
FROM python:3.11-slim AS builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Stage 2: Runtime (minimal, no cache needed)
FROM python:3.11-slim
COPY --from=builder /app/.venv /app/.venv
```

### 4. Use .dockerignore

Prevent unnecessary cache invalidation:
```
__pycache__/
*.pyc
.venv/
.git/
```

## Resources

- **BuildKit Documentation**: https://docs.docker.com/build/buildkit/
- **Cache Mounts**: https://docs.docker.com/build/cache/
- **Docker Buildx**: https://docs.docker.com/buildx/working-with-buildx/

## Summary

✅ **Enable BuildKit** → Run `.\scripts\windows\enable_buildkit.ps1`  
✅ **All Dockerfiles Updated** → Cache mounts added  
✅ **Timeout Increased** → 1000s for slow HuggingFace downloads  
✅ **Build Faster** → 95% reduction in rebuild time  

**Next Step:** Run `make windows-build` and enjoy faster builds! 🚀

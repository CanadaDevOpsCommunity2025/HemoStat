# Docker BuildKit Setup Instructions

Enable Docker BuildKit for faster builds with cached dependencies (95% faster rebuilds!).

## Choose Your Platform

### 🪟 Windows

**PowerShell:**
```powershell
.\scripts\windows\enable_buildkit.ps1
```

**What it does:**
- Sets `DOCKER_BUILDKIT=1` permanently (User environment variable)
- Sets `COMPOSE_DOCKER_CLI_BUILD=1` permanently
- Applies to current session immediately

**Requirements:**
- Windows 10/11
- Docker Desktop for Windows
- PowerShell 5.1+

---

### 🐧 Linux

**Bash:**
```bash
chmod +x scripts/linux/enable_buildkit.sh
./scripts/linux/enable_buildkit.sh
```

**What it does:**
- Detects your shell (bash, zsh, fish)
- Adds environment variables to shell config (~/.bashrc, ~/.zshrc, etc.)
- Applies to current session immediately

**Requirements:**
- Docker Engine 19.03+ or Docker Desktop for Linux
- Bash, Zsh, or Fish shell

**Manual Setup (if script fails):**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

---

### 🍎 macOS

**Zsh (default on macOS):**
```zsh
chmod +x scripts/macos/enable_buildkit.zsh
./scripts/macos/enable_buildkit.zsh
```

**What it does:**
- Detects your shell (zsh is default on macOS 10.15+)
- Adds environment variables to shell config (~/.zshrc or ~/.bash_profile)
- Applies to current session immediately
- Verifies Docker Desktop is running

**Requirements:**
- macOS 10.14+
- Docker Desktop for Mac
- Zsh (default) or Bash

**Manual Setup (if script fails):**

Add to `~/.zshrc`:
```zsh
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

Then reload:
```zsh
source ~/.zshrc
```

---

## Verify Setup

All platforms:
```bash
# Check environment variables
echo $DOCKER_BUILDKIT
# Should output: 1

echo $COMPOSE_DOCKER_CLI_BUILD
# Should output: 1

# Check BuildKit is available
docker buildx version
```

## Build Your Project

After enabling BuildKit:

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

## Performance Comparison

| Build | Without BuildKit | With BuildKit | Time Saved |
|-------|-----------------|---------------|------------|
| **First build** | 10 minutes | 10 minutes | 0% |
| **Rebuild (code change)** | 10 minutes | 30 seconds | **95%** ⚡ |
| **Rebuild (deps change)** | 10 minutes | 1-2 minutes | **80-90%** |

## What BuildKit Does

✅ **Caches downloaded packages** - UV/pip downloads persist between builds  
✅ **Parallel execution** - Multiple build stages run simultaneously  
✅ **Smart caching** - Only rebuild changed layers  
✅ **Better output** - Live progress bars and colored logs  

## Cache Management

View cache size:
```bash
docker buildx du
```

Clean old cache:
```bash
docker buildx prune
```

Clean all cache (fresh start):
```bash
docker buildx prune --all --force
```

## Troubleshooting

### BuildKit Not Enabled?

**Check variables:**
```bash
# Linux/macOS
echo $DOCKER_BUILDKIT
echo $COMPOSE_DOCKER_CLI_BUILD

# Windows PowerShell
$env:DOCKER_BUILDKIT
$env:COMPOSE_DOCKER_CLI_BUILD
```

Both should show `1`.

**Fix:**
- Restart your terminal after running the setup script
- Or manually source your shell config:
  - Linux/macOS: `source ~/.bashrc` or `source ~/.zshrc`
  - Windows: Close and reopen PowerShell

### Docker Version Too Old?

BuildKit requires Docker 18.09+. Update Docker:
- **Windows/macOS:** Update Docker Desktop
- **Linux:** Update Docker Engine

Check version:
```bash
docker version
```

### Script Permission Denied? (Linux/macOS)

Make script executable:
```bash
chmod +x scripts/linux/enable_buildkit.sh
# or
chmod +x scripts/macos/enable_buildkit.zsh
```

### Docker Not Running? (macOS)

Start Docker Desktop:
1. Open Docker Desktop from Applications
2. Wait for Docker to start (whale icon in menu bar)
3. Run the script again

### Still Having Issues?

1. Check Docker is installed: `docker --version`
2. Check Docker is running: `docker info`
3. Check BuildKit availability: `docker buildx version`
4. See [BUILDKIT_GUIDE.md](../BUILDKIT_GUIDE.md) for detailed troubleshooting

## More Information

- **Complete Guide:** [BUILDKIT_GUIDE.md](../BUILDKIT_GUIDE.md)
- **Quick Reference:** [BUILDKIT_QUICKREF.md](../BUILDKIT_QUICKREF.md)
- **Docker BuildKit Docs:** https://docs.docker.com/build/buildkit/

## Team Setup Instructions

Share this with your teammates:

1. **Clone the repository**
2. **Run the setup script for your OS** (see above)
3. **Restart your terminal**
4. **Build the project** - first build will be slow (normal!)
5. **Make a change and rebuild** - second build will be fast! ⚡

That's it! Everyone on the team will benefit from 95% faster rebuilds.

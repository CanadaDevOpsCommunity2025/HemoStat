#
# HemoStat Demo: Cleanup Scenario (PowerShell)
#
# This script demonstrates the cleanup remediation action by creating stopped
# containers and triggering a cleanup remediation request.
#
# Usage: .\demo_trigger_cleanup.ps1
#

$ErrorActionPreference = "Stop"

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# Check if Docker is running
try {
    docker ps | Out-Null
} catch {
    Write-Host "Error: Docker is not running" -ForegroundColor Red
    exit 1
}

# Check if HemoStat agents are running
$redisRunning = docker ps | Select-String "hemostat-redis"
if (-not $redisRunning) {
    Write-Host "Error: HemoStat services not running. Start with: docker-compose up -d" -ForegroundColor Red
    exit 1
}

# Create cleanup scenario
Write-Host ""
Write-Host "=== HemoStat Demo: Cleanup Scenario ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Creating stopped containers to trigger cleanup..." -ForegroundColor Cyan
Write-Host ""

# Create stopped containers
try {
    docker run --name hemostat-test-stopped-1 --network hemostat-network alpine:latest echo "test" 2>$null | Out-Null
    docker run --name hemostat-test-stopped-2 --network hemostat-network alpine:latest echo "test" 2>$null | Out-Null
    docker run --name hemostat-test-stopped-3 --network hemostat-network alpine:latest echo "test" 2>$null | Out-Null
    Write-Host "✓ Created 3 stopped containers" -ForegroundColor Green
} catch {
    # Containers may already exist, ignore errors
}

# Get current timestamp in ISO 8601 format
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# Trigger cleanup via Redis
Write-Host ""
Write-Host "Manually publishing cleanup remediation request to Redis..." -ForegroundColor Cyan
Write-Host "Note: This demonstrates direct Redis interaction (alternative to waiting for Analyzer)" -ForegroundColor Gray
Write-Host ""

# Publish event to remediation_needed channel
$payload = @{
    timestamp = $timestamp
    agent = "demo-script"
    type = "remediation_needed"
    data = @{
        container = "hemostat-test-stopped-1"
        action = "cleanup"
        reason = "Demo cleanup scenario"
        confidence = 0.9
    }
} | ConvertTo-Json -Compress

try {
    docker exec hemostat-redis redis-cli PUBLISH "hemostat:remediation_needed" $payload 2>$null | Out-Null
    Write-Host "✓ Published cleanup remediation request to Redis" -ForegroundColor Green
} catch {
    Write-Host "⚠ Could not publish to Redis: $_" -ForegroundColor Yellow
}

# Monitor Responder action
Write-Host ""
Write-Host "Monitoring Responder Agent cleanup action..." -ForegroundColor Cyan
Write-Host "Expected: Responder removes stopped containers and prunes resources"
Write-Host ""

# Wait for Responder to process
Start-Sleep -Seconds 10

# Check if stopped containers were removed
Write-Host "Checking if stopped containers were removed..." -ForegroundColor Cyan
$remaining = (docker ps -a | Select-String "hemostat-test-stopped" | Measure-Object).Count

if ($remaining -eq 0) {
    Write-Host "✓ All test containers removed by Responder" -ForegroundColor Green
} else {
    Write-Host "⚠ $remaining test containers still present (manual cleanup may be needed)" -ForegroundColor Yellow
}

# Verify completion
Write-Host ""
Write-Host "Checking for remediation_complete events..." -ForegroundColor Cyan
try {
    $eventCount = docker exec hemostat-redis redis-cli LLEN "hemostat:events:remediation_complete" 2>$null
    if (-not $eventCount) { $eventCount = 0 }

    if ([int]$eventCount -gt 0) {
        Write-Host "✓ Remediation events detected ($eventCount total)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Recent events:" -ForegroundColor Cyan
        docker exec hemostat-redis redis-cli LRANGE "hemostat:events:remediation_complete" 0 3 2>$null
    } else {
        Write-Host "⚠ No remediation completion events detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not check Redis events: $_" -ForegroundColor Yellow
}

# Cleanup any remaining test containers
Write-Host ""
Write-Host "Cleaning up any remaining test containers..." -ForegroundColor Cyan
try {
    docker rm -f hemostat-test-stopped-1 hemostat-test-stopped-2 hemostat-test-stopped-3 2>$null | Out-Null
} catch {
    # Ignore errors if containers don't exist
}

# Completion message
Write-Host ""
Write-Host "=== Demo Complete ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "This demo showed how to:"
Write-Host "  1. Create a cleanup scenario (stopped containers)"
Write-Host "  2. Manually publish remediation requests to Redis"
Write-Host "  3. Trigger specific remediation actions"
Write-Host "  4. Verify Responder execution"
Write-Host ""
Write-Host "To view agent logs:"
Write-Host "  docker-compose logs -f responder alert"
Write-Host ""
Write-Host "To monitor Redis events:"
Write-Host "  docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'"
Write-Host ""

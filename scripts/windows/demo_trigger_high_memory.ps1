#
# HemoStat Demo: High Memory Scenario (PowerShell)
#
# This script triggers high memory usage in the test-api service to demonstrate
# memory leak detection and remediation workflow.
#
# Usage: .\demo_trigger_high_memory.ps1 [duration] [size_mb]
#   duration: Spike duration in seconds (default: 60)
#   size_mb: Memory to allocate in MB (default: 500)
#

param(
    [int]$Duration = 60,
    [int]$SizeMB = 500
)

$ErrorActionPreference = "Stop"

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# Check if test-api service is running
$testApiRunning = docker ps | Select-String "hemostat-test-api"
if (-not $testApiRunning) {
    Write-Host "Error: test-api service not running. Start with: docker-compose up -d test-api" -ForegroundColor Red
    exit 1
}

# Trigger memory spike
Write-Host ""
Write-Host "=== HemoStat Demo: High Memory Scenario ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Triggering memory allocation on test-api (duration: ${Duration}s, size: ${SizeMB}MB)" -ForegroundColor Cyan
Write-Host ""

# Execute curl command
try {
    $body = @{
        duration = $Duration
        size_mb = $SizeMB
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "http://localhost:5000/stress/memory" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing `
        -ErrorAction Stop

    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Memory spike triggered successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to trigger memory spike (HTTP $($response.StatusCode))" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Failed to trigger memory spike: $_" -ForegroundColor Red
    exit 1
}

# Monitor HemoStat response
Write-Host ""
Write-Host "Monitoring HemoStat agent responses..." -ForegroundColor Cyan
Write-Host "Expected flow: Monitor → Analyzer → Responder → Alert → Dashboard"
Write-Host "Expected detection: Memory usage >80% threshold"
Write-Host "Expected action: Container restart to free memory"
Write-Host ""
Write-Host "You can monitor Redis events in separate terminals:"
Write-Host "  Terminal 1: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert"
Write-Host "  Terminal 2: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_needed"
Write-Host "  Terminal 3: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_complete"
Write-Host "  Dashboard: http://localhost:8501"
Write-Host ""

# Wait for Monitor to detect
Write-Host "Waiting for Monitor Agent to detect high memory (polls every 30s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 35

# Check if health alert was published
Write-Host "Checking if health alert was published..." -ForegroundColor Cyan
try {
    $eventCount = docker exec hemostat-redis redis-cli LLEN "hemostat:events:all" 2>$null
    if (-not $eventCount) { $eventCount = 0 }

    if ([int]$eventCount -gt 0) {
        Write-Host "✓ Health events detected in Redis ($eventCount total events)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Recent events:" -ForegroundColor Cyan
        docker exec hemostat-redis redis-cli LRANGE "hemostat:events:all" 0 5 2>$null
    } else {
        Write-Host "⚠ No events detected yet (Monitor may need more time)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not check Redis events: $_" -ForegroundColor Yellow
}

# Cleanup message
Write-Host ""
Write-Host "=== Demo Complete ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Memory spike will end in $Duration seconds from trigger time."
Write-Host ""
Write-Host "To stop immediately:"
Write-Host "  curl -X POST http://localhost:5000/stress/stop"
Write-Host ""
Write-Host "To view agent logs:"
Write-Host "  docker-compose logs -f monitor analyzer responder alert"
Write-Host ""
Write-Host "To check current metrics:"
Write-Host "  curl http://localhost:5000/metrics"
Write-Host ""

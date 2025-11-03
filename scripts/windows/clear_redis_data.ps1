#!/usr/bin/env pwsh
#
# Clear HemoStat Redis Data
#
# Removes all HemoStat events and state from Redis for a fresh start.
# Use this between test runs to clear old data.
#

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  HemoStat - Clear Redis Data" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Redis container is running
$redisRunning = docker ps --filter "name=hemostat-redis" --format "{{.Names}}" | Select-String -Pattern "hemostat-redis" -Quiet

if (-not $redisRunning) {
    Write-Host "✗ Redis container is not running" -ForegroundColor Red
    Write-Host "  Start with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "⚠ WARNING: This will delete all HemoStat data from Redis:" -ForegroundColor Yellow
Write-Host "  - All events (timeline, history)" -ForegroundColor Yellow
Write-Host "  - Remediation state and cooldowns" -ForegroundColor Yellow
Write-Host "  - Circuit breaker state" -ForegroundColor Yellow
Write-Host "  - Alert history" -ForegroundColor Yellow
Write-Host "  - Audit logs" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Are you sure you want to continue? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Clearing Redis data..." -ForegroundColor Cyan

# Get all HemoStat keys
$keys = docker exec hemostat-redis redis-cli KEYS 'hemostat:*'

if ($null -eq $keys -or $keys.Count -eq 0) {
    Write-Host "✓ No HemoStat data found in Redis (already clean)" -ForegroundColor Green
    exit 0
}

Write-Host "Found $($keys.Count) keys to delete" -ForegroundColor Cyan

# Delete all HemoStat keys
$result = docker exec hemostat-redis redis-cli --raw EVAL "return redis.call('del', unpack(redis.call('keys', 'hemostat:*')))" 0

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Successfully cleared $result keys from Redis" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to clear Redis data" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Redis data cleared successfully!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Refresh the Dashboard to see clean state" -ForegroundColor White
Write-Host "  2. Run demo scripts to generate new events" -ForegroundColor White
Write-Host ""

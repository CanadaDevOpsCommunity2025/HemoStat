#!/usr/bin/env pwsh
#
# Backup HemoStat Redis Data
#
# Exports all HemoStat events and state to a JSON file for later analysis.
# Useful for saving test runs, demos, or debugging.
#

param(
    [string]$OutputFile = "hemostat_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
)

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  HemoStat - Backup Redis Data" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Redis container is running
$redisRunning = docker ps --filter "name=hemostat-redis" --format "{{.Names}}" | Select-String -Pattern "hemostat-redis" -Quiet

if (-not $redisRunning) {
    Write-Host "✗ Redis container is not running" -ForegroundColor Red
    Write-Host "  Start with: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "Backing up HemoStat data to: $OutputFile" -ForegroundColor Cyan
Write-Host ""

# Get all HemoStat keys
$keys = docker exec hemostat-redis redis-cli KEYS 'hemostat:*'

if ($null -eq $keys -or $keys.Count -eq 0) {
    Write-Host "⚠ No HemoStat data found in Redis (nothing to backup)" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($keys.Count) keys to backup" -ForegroundColor Cyan

# Create backup object
$backup = @{
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    version = "1.0"
    keys = @{}
}

# Export each key
foreach ($key in $keys) {
    if ([string]::IsNullOrWhiteSpace($key)) { continue }
    
    # Get key type
    $keyType = docker exec hemostat-redis redis-cli TYPE $key
    
    switch ($keyType.Trim()) {
        "string" {
            $value = docker exec hemostat-redis redis-cli GET $key
            $backup.keys[$key] = @{
                type = "string"
                value = $value
            }
        }
        "list" {
            $value = docker exec hemostat-redis redis-cli LRANGE $key 0 -1
            $backup.keys[$key] = @{
                type = "list"
                value = $value
            }
        }
        "set" {
            $value = docker exec hemostat-redis redis-cli SMEMBERS $key
            $backup.keys[$key] = @{
                type = "set"
                value = $value
            }
        }
        "hash" {
            $value = docker exec hemostat-redis redis-cli HGETALL $key
            $backup.keys[$key] = @{
                type = "hash"
                value = $value
            }
        }
        default {
            Write-Host "⚠ Skipping unsupported key type: $keyType for $key" -ForegroundColor Yellow
        }
    }
}

# Write to file
$backup | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputFile -Encoding UTF8

$fileSize = (Get-Item $OutputFile).Length
$fileSizeKB = [math]::Round($fileSize / 1KB, 2)

Write-Host ""
Write-Host "✓ Successfully backed up $($backup.keys.Count) keys" -ForegroundColor Green
Write-Host "✓ Backup saved to: $OutputFile ($fileSizeKB KB)" -ForegroundColor Green
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Backup complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

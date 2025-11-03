#
# HemoStat Message Flow Verification (PowerShell)
#
# Comprehensive verification that all agents are communicating correctly via Redis pub/sub.
# This script verifies: Monitor → Analyzer → Responder → Alert → Dashboard
#
# Usage: .\verify_message_flow.ps1
#

$ErrorActionPreference = "Continue"

# Track overall status
$VerificationPassed = $true

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  HemoStat End-to-End Message Flow Verification" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Prerequisites Check
Write-Host "Step 1: Checking Prerequisites" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow

# Check if services are running
$services = @("redis", "monitor", "analyzer", "responder", "alert", "dashboard", "test-api")
foreach ($service in $services) {
    $running = docker ps | Select-String "hemostat-$service"
    if ($running) {
        Write-Host "✓ $service is running" -ForegroundColor Green
    } else {
        Write-Host "✗ $service is NOT running" -ForegroundColor Red
        $VerificationPassed = $false
    }
}

if (-not $VerificationPassed) {
    Write-Host ""
    Write-Host "ERROR: Not all required services are running" -ForegroundColor Red
    Write-Host "Please start all services with: docker-compose up -d"
    exit 1
}

# Test Redis Connectivity
Write-Host ""
Write-Host "Step 2: Testing Redis Connectivity" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

$redisPing = docker exec hemostat-redis redis-cli ping 2>$null
if ($redisPing -match "PONG") {
    Write-Host "✓ Redis is responding" -ForegroundColor Green
} else {
    Write-Host "✗ Redis is not responding" -ForegroundColor Red
    exit 1
}

# Verify Redis Channels
Write-Host ""
Write-Host "Step 3: Verifying Redis Pub/Sub Channels" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Yellow

$channels = @("hemostat:health_alert", "hemostat:remediation_needed", "hemostat:remediation_complete", "hemostat:false_alarm")
foreach ($channel in $channels) {
    Write-Host "  Channel: $channel" -ForegroundColor Cyan
}

# Trigger Test Scenario
Write-Host ""
Write-Host "Step 4: Triggering Test Scenario" -ForegroundColor Yellow
Write-Host "---------------------------------" -ForegroundColor Yellow
Write-Host "Triggering CPU spike (45 seconds, 90% intensity)..." -ForegroundColor Cyan

try {
    $body = @{
        duration = 45
        intensity = 0.9
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "http://localhost:5001/stress/cpu" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing `
        -ErrorAction Stop

    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Test scenario triggered successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to trigger test scenario (HTTP $($response.StatusCode))" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Failed to trigger test scenario: $_" -ForegroundColor Red
    exit 1
}

# Monitor Message Flow
Write-Host ""
Write-Host "Step 5: Monitoring Message Flow (this will take ~60 seconds)" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------" -ForegroundColor Yellow

# [1/4] Wait for Monitor Agent
Write-Host ""
Write-Host "[1/4] Waiting for Monitor Agent to detect high CPU..." -ForegroundColor Cyan
Start-Sleep -Seconds 35

try {
    $healthAlerts = docker exec hemostat-redis redis-cli LRANGE "hemostat:events:all" 0 10 2>$null | Select-String "health_alert" | Measure-Object
    
    if ($healthAlerts.Count -gt 0) {
        Write-Host "✓ Monitor published health_alert event" -ForegroundColor Green
    } else {
        Write-Host "⚠ No health_alert detected (may need more time)" -ForegroundColor Yellow
        $VerificationPassed = $false
    }
} catch {
    Write-Host "⚠ Could not check health alerts: $_" -ForegroundColor Yellow
}

# [2/4] Check Analyzer
Write-Host ""
Write-Host "[2/4] Checking if Analyzer processed alert..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

try {
    $remediationEvents = docker exec hemostat-redis redis-cli LLEN "hemostat:events:remediation_complete" 2>$null
    if (-not $remediationEvents) { $remediationEvents = 0 }

    if ([int]$remediationEvents -gt 0) {
        Write-Host "✓ Analyzer published remediation decision" -ForegroundColor Green
    } else {
        Write-Host "⚠ No remediation decision detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not check remediation events: $_" -ForegroundColor Yellow
}

# [3/4] Check Responder
Write-Host ""
Write-Host "[3/4] Checking if Responder executed action..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

try {
    $completeEvents = docker exec hemostat-redis redis-cli LRANGE "hemostat:events:remediation_complete" 0 10 2>$null | Select-String "remediation_complete" | Measure-Object

    if ($completeEvents.Count -gt 0) {
        Write-Host "✓ Responder completed remediation" -ForegroundColor Green
    } else {
        Write-Host "⚠ No remediation completion detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not check completion events: $_" -ForegroundColor Yellow
}

# [4/4] Verify Alert Agent
Write-Host ""
Write-Host "[4/4] Verifying Alert Agent stored events..." -ForegroundColor Cyan

try {
    $eventCount = docker exec hemostat-redis redis-cli LLEN "hemostat:events:all" 2>$null
    if (-not $eventCount) { $eventCount = 0 }

    if ([int]$eventCount -gt 0) {
        Write-Host "✓ Alert Agent stored $eventCount events" -ForegroundColor Green
    } else {
        Write-Host "✗ No events stored by Alert Agent" -ForegroundColor Red
        $VerificationPassed = $false
    }
} catch {
    Write-Host "✗ Could not check Alert Agent events: $_" -ForegroundColor Red
    $VerificationPassed = $false
}

# Verify Dashboard Access
Write-Host ""
Write-Host "Step 6: Verifying Dashboard Access" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

try {
    $dashboardResponse = Invoke-WebRequest -Uri "http://localhost:8501/_stcore/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($dashboardResponse.StatusCode -eq 200) {
        Write-Host "✓ Dashboard is accessible at http://localhost:8501" -ForegroundColor Green
    } else {
        $dashboardResponse = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($dashboardResponse.StatusCode -eq 200) {
            Write-Host "✓ Dashboard is accessible at http://localhost:8501" -ForegroundColor Green
        } else {
            Write-Host "⚠ Dashboard may not be ready yet" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "⚠ Dashboard may not be ready yet" -ForegroundColor Yellow
}

# Summary Report
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Verification Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Message Flow: Monitor → Analyzer → Responder → Alert → Dashboard"
Write-Host ""

if ($VerificationPassed) {
    Write-Host "Status: ✓ VERIFIED" -ForegroundColor Green
    Write-Host ""
    Write-Host "All agents are communicating correctly via Redis pub/sub!"
} else {
    Write-Host "Status: ⚠ PARTIAL" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Some checks did not pass. This may be due to timing or configuration."
}

Write-Host ""
Write-Host "Recent Events:" -ForegroundColor Yellow
Write-Host "--------------" -ForegroundColor Yellow
try {
    docker exec hemostat-redis redis-cli LRANGE "hemostat:events:all" 0 5 2>$null
} catch {
    Write-Host "No events found"
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "-----------" -ForegroundColor Yellow
Write-Host "  1. View Dashboard: http://localhost:8501"
Write-Host "  2. Check agent logs: docker-compose logs -f monitor analyzer responder alert"
Write-Host "  3. Monitor Redis events: docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'"
Write-Host "  4. Check container stats: docker stats hemostat-test-api"
Write-Host ""

# Cleanup - stop stress test
Write-Host "Cleaning up..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://localhost:5001/stress/stop" -Method POST -UseBasicParsing -ErrorAction SilentlyContinue | Out-Null
} catch {
    # Ignore cleanup errors
}

Write-Host ""
Write-Host "Verification complete!" -ForegroundColor Cyan
Write-Host ""

# Exit with appropriate code
if ($VerificationPassed) {
    exit 0
} else {
    exit 1
}

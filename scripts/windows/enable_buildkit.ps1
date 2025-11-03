# Enable Docker BuildKit for Windows
# Run this script once to enable BuildKit permanently

Write-Host "Enabling Docker BuildKit..." -ForegroundColor Cyan

# Set environment variables for current user (persistent)
[System.Environment]::SetEnvironmentVariable('DOCKER_BUILDKIT', '1', 'User')
[System.Environment]::SetEnvironmentVariable('COMPOSE_DOCKER_CLI_BUILD', '1', 'User')

# Set for current session
$env:DOCKER_BUILDKIT = '1'
$env:COMPOSE_DOCKER_CLI_BUILD = '1'

Write-Host "✓ BuildKit enabled for current session" -ForegroundColor Green
Write-Host "✓ BuildKit enabled permanently (restart terminal to apply)" -ForegroundColor Green

Write-Host ""
Write-Host "Benefits:" -ForegroundColor Yellow
Write-Host "  - Faster builds with parallel execution"
Write-Host "  - Cached pip/uv downloads between builds"
Write-Host "  - Better build output and progress"
Write-Host ""
Write-Host "Verify BuildKit is enabled:" -ForegroundColor Cyan
Write-Host "  docker buildx version"
Write-Host ""
Write-Host "Build with cache:" -ForegroundColor Cyan
Write-Host "  make windows-build"

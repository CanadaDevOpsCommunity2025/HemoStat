#!/bin/zsh
#
# HemoStat Demo: High Memory Scenario (Zsh)
#
# This script triggers high memory usage in the test-api service to demonstrate
# memory leak detection and remediation workflow.
#
# Usage: ./demo_trigger_high_memory.zsh [duration] [size_mb]
#   duration: Spike duration in seconds (default: 60)
#   size_mb: Memory to allocate in MB (default: 500)
#

setopt ERR_EXIT  # Exit on error

# Default parameters
DURATION=${1:-60}
SIZE_MB=${2:-500}

# Check prerequisites
echo "Checking prerequisites..."

# Check if test-api service is running
if ! docker ps | grep -q hemostat-test-api; then
    echo "Error: test-api service not running. Start with: docker-compose up -d test-api"
    exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not found"
    exit 1
fi

# Trigger memory spike
echo ""
echo "=== HemoStat Demo: High Memory Scenario ==="
echo ""
echo "Triggering memory allocation on test-api (duration: ${DURATION}s, size: ${SIZE_MB}MB)"
echo ""

# Execute curl command
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:5000/stress/memory \
    -H "Content-Type: application/json" \
    -d "{\"duration\": ${DURATION}, \"size_mb\": ${SIZE_MB}}")

if [[ "$HTTP_CODE" = "200" ]]; then
    echo "✓ Memory spike triggered successfully"
else
    echo "✗ Failed to trigger memory spike (HTTP $HTTP_CODE)"
    exit 1
fi

# Monitor HemoStat response
echo ""
echo "Monitoring HemoStat agent responses..."
echo "Expected flow: Monitor → Analyzer → Responder → Alert → Dashboard"
echo "Expected detection: Memory usage >80% threshold"
echo "Expected action: Container restart to free memory"
echo ""
echo "You can monitor Redis events in separate terminals:"
echo "  Terminal 1: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert"
echo "  Terminal 2: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_needed"
echo "  Terminal 3: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_complete"
echo "  Dashboard: http://localhost:8501"
echo ""

# Wait for Monitor to detect
echo "Waiting for Monitor Agent to detect high memory (polls every 30s)..."
sleep 35

# Check if health alert was published
echo "Checking if health alert was published..."
EVENT_COUNT=$(docker exec hemostat-redis redis-cli LLEN hemostat:events:all 2>/dev/null || echo "0")

if [[ "$EVENT_COUNT" -gt 0 ]]; then
    echo "✓ Health events detected in Redis ($EVENT_COUNT total events)"
    echo ""
    echo "Recent events:"
    docker exec hemostat-redis redis-cli LRANGE hemostat:events:all 0 5 2>/dev/null || true
else
    echo "⚠ No events detected yet (Monitor may need more time)"
fi

# Cleanup message
echo ""
echo "=== Demo Complete ==="
echo ""
echo "Memory spike will end in ${DURATION} seconds from trigger time."
echo ""
echo "To stop immediately:"
echo "  curl -X POST http://localhost:5000/stress/stop"
echo ""
echo "To view agent logs:"
echo "  docker-compose logs -f monitor analyzer responder alert"
echo ""
echo "To check current metrics:"
echo "  curl http://localhost:5000/metrics"
echo ""

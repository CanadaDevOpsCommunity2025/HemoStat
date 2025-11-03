#!/bin/zsh
#
# HemoStat Demo: CPU Spike Scenario (Zsh)
#
# This script triggers a CPU spike in the test-api service to demonstrate
# the end-to-end HemoStat workflow:
# Monitor detects high CPU → Analyzer recommends restart → Responder executes restart → Alert sends notification
#
# Usage: ./demo_trigger_cpu_spike.zsh [duration] [intensity]
#   duration: Spike duration in seconds (default: 60)
#   intensity: CPU intensity 0.0-1.0 (default: 0.9 = 90%)
#

setopt ERR_EXIT  # Exit on error

# Default parameters
DURATION=${1:-60}
INTENSITY=${2:-0.9}

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

# Trigger CPU spike
echo ""
echo "=== HemoStat Demo: CPU Spike Scenario ==="
echo ""
echo "Triggering CPU spike on test-api (duration: ${DURATION}s, intensity: ${INTENSITY})"
echo ""

# Execute curl command
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:5000/stress/cpu \
    -H "Content-Type: application/json" \
    -d "{\"duration\": ${DURATION}, \"intensity\": ${INTENSITY}}")

if [[ "$HTTP_CODE" = "200" ]]; then
    echo "✓ CPU spike triggered successfully"
else
    echo "✗ Failed to trigger CPU spike (HTTP $HTTP_CODE)"
    exit 1
fi

# Monitor HemoStat response
echo ""
echo "Monitoring HemoStat agent responses..."
echo "Expected flow: Monitor → Analyzer → Responder → Alert → Dashboard"
echo ""
echo "You can monitor Redis events in separate terminals:"
echo "  Terminal 1: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:health_alert"
echo "  Terminal 2: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_needed"
echo "  Terminal 3: docker exec hemostat-redis redis-cli SUBSCRIBE hemostat:remediation_complete"
echo "  Dashboard: http://localhost:8501"
echo ""

# Wait for Monitor to detect
echo "Waiting for Monitor Agent to detect high CPU (polls every 30s)..."
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
echo "CPU spike will end in ${DURATION} seconds from trigger time."
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

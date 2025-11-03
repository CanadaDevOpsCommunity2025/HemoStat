#!/bin/bash
#
# HemoStat Demo: Cleanup Scenario
#
# This script demonstrates the cleanup remediation action by creating stopped
# containers and triggering a cleanup remediation request.
#
# Usage: ./demo_trigger_cleanup.sh
#

set -e  # Exit on error

# Check prerequisites
echo "Checking prerequisites..."

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "Error: Docker is not running"
    exit 1
fi

# Check if HemoStat agents are running
if ! docker ps | grep -q hemostat-redis; then
    echo "Error: HemoStat services not running. Start with: docker-compose up -d"
    exit 1
fi

# Create cleanup scenario
echo ""
echo "=== HemoStat Demo: Cleanup Scenario ==="
echo ""
echo "Creating stopped containers to trigger cleanup..."
echo ""

# Create stopped containers
docker run --name hemostat-test-stopped-1 --network hemostat-network alpine:latest echo "test" 2>/dev/null || true
docker run --name hemostat-test-stopped-2 --network hemostat-network alpine:latest echo "test" 2>/dev/null || true
docker run --name hemostat-test-stopped-3 --network hemostat-network alpine:latest echo "test" 2>/dev/null || true

echo "✓ Created 3 stopped containers"

# Get current timestamp in ISO 8601 format
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z")

# Trigger cleanup via Redis
echo ""
echo "Manually publishing cleanup remediation request to Redis..."
echo "Note: This demonstrates direct Redis interaction (alternative to waiting for Analyzer)"
echo ""

# Publish event to remediation_needed channel
PAYLOAD="{\"timestamp\": \"${TIMESTAMP}\", \"agent\": \"demo-script\", \"type\": \"remediation_needed\", \"data\": {\"container\": \"hemostat-test-stopped-1\", \"action\": \"cleanup\", \"reason\": \"Demo cleanup scenario\", \"confidence\": 0.9}}"

docker exec hemostat-redis redis-cli PUBLISH hemostat:remediation_needed "$PAYLOAD" > /dev/null 2>&1

echo "✓ Published cleanup remediation request to Redis"

# Monitor Responder action
echo ""
echo "Monitoring Responder Agent cleanup action..."
echo "Expected: Responder removes stopped containers and prunes resources"
echo ""

# Wait for Responder to process
sleep 10

# Check if stopped containers were removed
echo "Checking if stopped containers were removed..."
REMAINING=$(docker ps -a | grep -c hemostat-test-stopped || echo "0")

if [ "$REMAINING" -eq 0 ]; then
    echo "✓ All test containers removed by Responder"
else
    echo "⚠ $REMAINING test containers still present (manual cleanup may be needed)"
fi

# Verify completion
echo ""
echo "Checking for remediation_complete events..."
EVENT_COUNT=$(docker exec hemostat-redis redis-cli LLEN hemostat:events:remediation_complete 2>/dev/null || echo "0")

if [ "$EVENT_COUNT" -gt 0 ]; then
    echo "✓ Remediation events detected ($EVENT_COUNT total)"
    echo ""
    echo "Recent events:"
    docker exec hemostat-redis redis-cli LRANGE hemostat:events:remediation_complete 0 3 2>/dev/null || true
else
    echo "⚠ No remediation completion events detected"
fi

# Cleanup any remaining test containers
echo ""
echo "Cleaning up any remaining test containers..."
docker rm -f hemostat-test-stopped-1 hemostat-test-stopped-2 hemostat-test-stopped-3 2>/dev/null || true

# Completion message
echo ""
echo "=== Demo Complete ==="
echo ""
echo "This demo showed how to:"
echo "  1. Create a cleanup scenario (stopped containers)"
echo "  2. Manually publish remediation requests to Redis"
echo "  3. Trigger specific remediation actions"
echo "  4. Verify Responder execution"
echo ""
echo "To view agent logs:"
echo "  docker-compose logs -f responder alert"
echo ""
echo "To monitor Redis events:"
echo "  docker exec hemostat-redis redis-cli SUBSCRIBE 'hemostat:*'"
echo ""

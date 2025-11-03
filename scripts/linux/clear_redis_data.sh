#!/bin/bash
#
# Clear HemoStat Redis Data
#
# Removes all HemoStat events and state from Redis for a fresh start.
# Use this between test runs to clear old data.
#

set -e

echo ""
echo "================================================================"
echo "  HemoStat - Clear Redis Data"
echo "================================================================"
echo ""

# Check if Redis container is running
if ! docker ps | grep -q hemostat-redis; then
    echo "✗ Redis container is not running"
    echo "  Start with: docker-compose up -d"
    exit 1
fi

echo "⚠ WARNING: This will delete all HemoStat data from Redis:"
echo "  - All events (timeline, history)"
echo "  - Remediation state and cooldowns"
echo "  - Circuit breaker state"
echo "  - Alert history"
echo "  - Audit logs"
echo ""

read -p "Are you sure you want to continue? (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Clearing Redis data..."

# Get count of keys
key_count=$(docker exec hemostat-redis redis-cli KEYS 'hemostat:*' | wc -l)

if [ "$key_count" -eq 0 ]; then
    echo "✓ No HemoStat data found in Redis (already clean)"
    exit 0
fi

echo "Found $key_count keys to delete"

# Delete all HemoStat keys
deleted=$(docker exec hemostat-redis redis-cli --raw EVAL "return redis.call('del', unpack(redis.call('keys', 'hemostat:*')))" 0)

echo "✓ Successfully cleared $deleted keys from Redis"

echo ""
echo "================================================================"
echo "  Redis data cleared successfully!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "  1. Refresh the Dashboard to see clean state"
echo "  2. Run demo scripts to generate new events"
echo ""

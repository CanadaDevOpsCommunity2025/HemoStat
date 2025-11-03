#!/bin/zsh
#
# Backup HemoStat Redis Data
#
# Exports all HemoStat events and state to a JSON file for later analysis.
# Useful for saving test runs, demos, or debugging.
#

setopt ERR_EXIT

OUTPUT_FILE="${1:-hemostat_backup_$(date +%Y%m%d_%H%M%S).json}"

echo ""
echo "================================================================"
echo "  HemoStat - Backup Redis Data"
echo "================================================================"
echo ""

# Check if Redis container is running
if ! docker ps | grep -q hemostat-redis; then
    echo "✗ Redis container is not running"
    echo "  Start with: docker-compose up -d"
    exit 1
fi

echo "Backing up HemoStat data to: $OUTPUT_FILE"
echo ""

# Get all HemoStat keys
keys=$(docker exec hemostat-redis redis-cli KEYS 'hemostat:*')

if [[ -z "$keys" ]]; then
    echo "⚠ No HemoStat data found in Redis (nothing to backup)"
    exit 0
fi

key_count=$(echo "$keys" | wc -l | tr -d ' ')
echo "Found $key_count keys to backup"

# Start JSON file
echo "{" > "$OUTPUT_FILE"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$OUTPUT_FILE"
echo "  \"version\": \"1.0\"," >> "$OUTPUT_FILE"
echo "  \"keys\": {" >> "$OUTPUT_FILE"

first=true
echo "$keys" | while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    
    # Get key type
    key_type=$(docker exec hemostat-redis redis-cli TYPE "$key" | tr -d '\r')
    
    # Add comma if not first entry
    if [[ "$first" = "false" ]]; then
        echo "," >> "$OUTPUT_FILE"
    fi
    first=false
    
    echo -n "    \"$key\": {" >> "$OUTPUT_FILE"
    echo -n "\"type\": \"$key_type\", \"value\": " >> "$OUTPUT_FILE"
    
    case "$key_type" in
        string)
            value=$(docker exec hemostat-redis redis-cli GET "$key")
            echo -n "\"$value\"" >> "$OUTPUT_FILE"
            ;;
        list)
            docker exec hemostat-redis redis-cli --raw LRANGE "$key" 0 -1 | jq -Rs 'split("\n") | map(select(length > 0))' >> "$OUTPUT_FILE"
            ;;
        set)
            docker exec hemostat-redis redis-cli --raw SMEMBERS "$key" | jq -Rs 'split("\n") | map(select(length > 0))' >> "$OUTPUT_FILE"
            ;;
        hash)
            docker exec hemostat-redis redis-cli --raw HGETALL "$key" | jq -Rs 'split("\n") | map(select(length > 0))' >> "$OUTPUT_FILE"
            ;;
        *)
            echo -n "null" >> "$OUTPUT_FILE"
            ;;
    esac
    
    echo -n "}" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "  }" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

file_size=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
file_size_kb=$((file_size / 1024))

echo ""
echo "✓ Successfully backed up $key_count keys"
echo "✓ Backup saved to: $OUTPUT_FILE (${file_size_kb} KB)"
echo ""
echo "================================================================"
echo "  Backup complete!"
echo "================================================================"
echo ""

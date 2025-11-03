#!/usr/bin/env python3
"""
HemoStat Redis Cleanup Script

Clears old events and state from Redis to free up memory and improve performance.
Useful for cleaning up after demos or testing sessions.

Usage:
    python scripts/cleanup_redis.py [--all] [--events] [--state] [--dry-run]

Options:
    --all       Clear all HemoStat data (default)
    --events    Clear only event data
    --state     Clear only state data
    --dry-run   Show what would be deleted without actually deleting
"""

import os
import sys
from typing import Optional

import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_redis_client() -> redis.Redis:
    """Get Redis client from environment variables."""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")

    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )


def cleanup_events(client: redis.Redis, dry_run: bool = False) -> int:
    """
    Clear all event data from Redis.

    Args:
        client: Redis client
        dry_run: If True, only show what would be deleted

    Returns:
        Number of keys deleted
    """
    deleted_count = 0
    cursor = 0

    print("🧹 Cleaning up event data...")

    while True:
        cursor, keys = client.scan(cursor, match="hemostat:events:*", count=100)

        for key in keys:
            if not dry_run:
                client.delete(key)
            deleted_count += 1
            print(f"  {'[DRY RUN] ' if dry_run else ''}Deleted: {key}")

        if cursor == 0:
            break

    return deleted_count


def cleanup_state(client: redis.Redis, dry_run: bool = False) -> int:
    """
    Clear all state data from Redis.

    Args:
        client: Redis client
        dry_run: If True, only show what would be deleted

    Returns:
        Number of keys deleted
    """
    deleted_count = 0
    cursor = 0

    print("🧹 Cleaning up state data...")

    while True:
        cursor, keys = client.scan(cursor, match="hemostat:state:*", count=100)

        for key in keys:
            if not dry_run:
                client.delete(key)
            deleted_count += 1
            print(f"  {'[DRY RUN] ' if dry_run else ''}Deleted: {key}")

        if cursor == 0:
            break

    return deleted_count


def cleanup_audit(client: redis.Redis, dry_run: bool = False) -> int:
    """
    Clear all audit data from Redis.

    Args:
        client: Redis client
        dry_run: If True, only show what would be deleted

    Returns:
        Number of keys deleted
    """
    deleted_count = 0
    cursor = 0

    print("🧹 Cleaning up audit data...")

    while True:
        cursor, keys = client.scan(cursor, match="hemostat:audit:*", count=100)

        for key in keys:
            if not dry_run:
                client.delete(key)
            deleted_count += 1
            print(f"  {'[DRY RUN] ' if dry_run else ''}Deleted: {key}")

        if cursor == 0:
            break

    return deleted_count


def cleanup_all(client: redis.Redis, dry_run: bool = False) -> int:
    """
    Clear all HemoStat data from Redis.

    Args:
        client: Redis client
        dry_run: If True, only show what would be deleted

    Returns:
        Total number of keys deleted
    """
    total = 0
    total += cleanup_events(client, dry_run)
    total += cleanup_state(client, dry_run)
    total += cleanup_audit(client, dry_run)
    return total


def main() -> None:
    """Main entry point."""
    try:
        # Parse arguments
        dry_run = "--dry-run" in sys.argv
        all_data = "--all" in sys.argv or (
            "--events" not in sys.argv and "--state" not in sys.argv
        )
        events_only = "--events" in sys.argv
        state_only = "--state" in sys.argv

        # Connect to Redis
        print("🔗 Connecting to Redis...")
        client = get_redis_client()
        client.ping()
        print("✓ Connected to Redis\n")

        # Show dry-run warning
        if dry_run:
            print("⚠️  DRY RUN MODE - No data will be deleted\n")

        # Perform cleanup
        total_deleted = 0
        if all_data:
            total_deleted = cleanup_all(client, dry_run)
        elif events_only:
            total_deleted = cleanup_events(client, dry_run)
        elif state_only:
            total_deleted = cleanup_state(client, dry_run)

        # Summary
        print(f"\n{'[DRY RUN] ' if dry_run else ''}✓ Cleanup complete!")
        print(f"  Total keys {'would be ' if dry_run else ''}deleted: {total_deleted}")

        if dry_run:
            print("\n💡 Run without --dry-run to actually delete the data:")
            print("   python scripts/cleanup_redis.py")

    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

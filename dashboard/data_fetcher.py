"""
Dashboard Data Fetcher Module

Provides Redis data access layer with efficient caching for dashboard operations.
Uses Streamlit caching decorators to minimize Redis polling and improve performance.
"""

import json
import os
from typing import Any

import redis
import streamlit as st

from agents.logger import HemoStatLogger


@st.cache_resource
def get_redis_client() -> redis.Redis:
    """
    Get or create a cached Redis client for long-lived connections.

    Loads Redis configuration from environment variables and establishes
    a connection with string response decoding enabled. Tests connection
    on first initialization.

    Returns:
        redis.Redis: Connected Redis client instance with decode_responses=True

    Raises:
        redis.ConnectionError: If Redis connection cannot be established
    """
    logger = HemoStatLogger.get_logger("dashboard")

    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")

    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        client.ping()
        logger.info(f"Redis connection established: {redis_host}:{redis_port}/{redis_db}")
        return client
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


@st.cache_data(ttl=5)
def get_all_events(limit: int = 100) -> list[dict]:
    """
    Fetch all events from Redis with 5-second cache.

    Retrieves events from the `hemostat:events:all` list, parses JSON,
    and returns sorted by timestamp (newest first). Handles missing keys
    and malformed JSON gracefully.

    Args:
        limit: Maximum number of events to retrieve (default: 100)

    Returns:
        list[dict]: List of event dictionaries sorted by timestamp (newest first)
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        client = get_redis_client()
        events_raw = client.lrange("hemostat:events:all", 0, limit - 1)

        events: list[dict] = []
        for event_str in events_raw:  # type: ignore[union-attr]
            try:
                event = json.loads(event_str)
                events.append(event)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed event JSON: {e}")
                continue

        # Sort by timestamp, newest first
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events
    except Exception as e:
        logger.error(f"Error fetching all events: {e}")
        return []


@st.cache_data(ttl=5)
def get_events_by_type(event_type: str, limit: int = 100) -> list[dict]:
    """
    Fetch events of a specific type from Redis with 5-second cache.

    Retrieves events from `hemostat:events:{event_type}` list, parses JSON,
    and returns as list. Handles missing keys gracefully.

    Args:
        event_type: Type of events to fetch (e.g., 'remediation_complete', 'false_alarm')
        limit: Maximum number of events to retrieve (default: 100)

    Returns:
        list[dict]: List of event dictionaries of the specified type
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        client = get_redis_client()
        key = f"hemostat:events:{event_type}"
        events_raw = client.lrange(key, 0, limit - 1)

        events: list[dict] = []
        for event_str in events_raw:  # type: ignore[union-attr]
            try:
                event = json.loads(event_str)
                events.append(event)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed event JSON in {key}: {e}")
                continue

        return events
    except Exception as e:
        logger.error(f"Error fetching events by type '{event_type}': {e}")
        return []


@st.cache_data(ttl=5)
def get_container_stats(container_id: str) -> dict[str, Any] | None:
    """
    Fetch container statistics from Redis with 5-second cache.

    Retrieves stats from `hemostat:state:container:{container_id}` key,
    parses JSON, and returns as dictionary. Returns None if key doesn't
    exist or has expired.

    Args:
        container_id: Container ID to fetch stats for

    Returns:
        dict[str, Any] | None: Container stats dictionary or None if not found
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        client = get_redis_client()
        key = f"hemostat:state:container:{container_id}"
        stats_str = client.get(key)

        if not stats_str:
            return None

        try:
            return json.loads(stats_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed stats JSON for {container_id}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error fetching container stats for {container_id}: {e}")
        return None


@st.cache_data(ttl=5)
def get_active_containers() -> list[str]:
    """
    Fetch list of active container IDs from Redis with 5-second cache.

    Scans Redis for keys matching `hemostat:state:container:*` pattern
    and extracts container IDs. Uses SCAN instead of KEYS for production safety.

    Returns:
        list[str]: List of active container IDs
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        client = get_redis_client()
        container_ids = []

        # Use SCAN for production safety (doesn't block Redis)
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor, match="hemostat:state:container:*", count=100)
            for key in keys:
                # Extract container ID from key format: hemostat:state:container:{id}
                container_id = key.replace("hemostat:state:container:", "")
                container_ids.append(container_id)

            if cursor == 0:
                break

        return container_ids
    except Exception as e:
        logger.error(f"Error fetching active containers: {e}")
        return []


@st.cache_data(ttl=5)
def get_remediation_stats() -> dict[str, Any]:
    """
    Aggregate remediation statistics from Redis with 5-second cache.

    Fetches events from `hemostat:events:remediation_complete` and calculates:
    - Total remediations
    - Success count
    - Failure count
    - Rejection count (cooldown/circuit breaker)
    - Success rate percentage

    Returns:
        dict[str, Any]: Dictionary with aggregated remediation statistics
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        remediation_events = get_events_by_type("remediation_complete", limit=1000)

        total = len(remediation_events)
        success_count = sum(1 for e in remediation_events if e.get("status") == "success")
        failure_count = sum(1 for e in remediation_events if e.get("status") == "failed")
        rejection_count = sum(1 for e in remediation_events if e.get("status") == "rejected")

        success_rate = (success_count / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "success": success_count,
            "failed": failure_count,
            "rejected": rejection_count,
            "success_rate": round(success_rate, 1),
        }
    except Exception as e:
        logger.error(f"Error calculating remediation stats: {e}")
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "rejected": 0,
            "success_rate": 0.0,
        }


@st.cache_data(ttl=5)
def get_false_alarm_count() -> int:
    """
    Count false alarm events from Redis with 5-second cache.

    Uses LLEN to efficiently count events in `hemostat:events:false_alarm` list
    without fetching all events.

    Returns:
        int: Number of false alarm events
    """
    logger = HemoStatLogger.get_logger("dashboard")

    try:
        client = get_redis_client()
        count = client.llen("hemostat:events:false_alarm")
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"Error fetching false alarm count: {e}")
        return 0

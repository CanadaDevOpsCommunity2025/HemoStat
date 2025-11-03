"""
Dashboard Entry Point Module

Provides startup configuration and pre-flight checks for the dashboard.
This module can be run directly for validation before starting Streamlit.
"""

import os
import sys

import redis
from dotenv import load_dotenv

from agents.logger import HemoStatLogger


def main() -> None:
    """
    Main entry point for dashboard startup.

    Loads environment variables, initializes logging, performs pre-flight
    checks (Redis connection, environment variables), and provides startup
    instructions.

    Exits with code 1 if critical configuration is missing.
    """
    # Load environment variables
    load_dotenv()

    # Initialize logger
    logger = HemoStatLogger.get_logger("dashboard")

    # Log startup banner
    logger.info("=" * 70)
    logger.info("HemoStat Dashboard - Phase 3 Visualization")
    logger.info("=" * 70)

    # Log configuration summary
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    dashboard_port = os.getenv("DASHBOARD_PORT", "8501")
    refresh_interval = os.getenv("DASHBOARD_REFRESH_INTERVAL", "5")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    logger.info(f"Redis Host: {redis_host}")
    logger.info(f"Redis Port: {redis_port}")
    logger.info(f"Dashboard Port: {dashboard_port}")
    logger.info(f"Refresh Interval: {refresh_interval}s")
    logger.info(f"Log Level: {log_level}")

    # Pre-flight checks
    logger.info("Running pre-flight checks...")

    # Check Redis connection
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            db=0,
            socket_connect_timeout=5,
        )
        redis_client.ping()
        logger.info("✓ Redis connection successful")
    except redis.ConnectionError as e:
        logger.error(f"✗ Redis connection failed: {e}")
        logger.error("Cannot proceed without Redis. Please ensure Redis is running.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Unexpected error during Redis check: {e}")
        sys.exit(1)

    # Check optional configuration
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook:
        logger.warning("⚠ SLACK_WEBHOOK_URL not configured (optional)")

    logger.info("=" * 70)
    logger.info("Pre-flight checks passed!")
    logger.info("=" * 70)
    logger.info("")
    logger.info("To start the dashboard, run:")
    logger.info("  streamlit run dashboard/app.py")
    logger.info("")
    logger.info("Or with Docker Compose:")
    logger.info("  docker-compose up -d dashboard")
    logger.info("")
    logger.info("Dashboard will be available at:")
    logger.info(f"  http://localhost:{dashboard_port}")
    logger.info("")


if __name__ == "__main__":
    main()

"""
HemoStat Alert Agent Entry Point

Runs the Alert Agent as a standalone module.
Usage: python -m agents.hemostat_alert.main

Import paths supported:
- from agents.hemostat_alert import AlertNotifier (package-level)
- from agents.hemostat_alert.hemostat_alert import AlertNotifier (primary module)
- from agents.hemostat_alert.alert import AlertNotifier (implementation module)
"""

import logging
import os
import sys
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_alert import AlertNotifier

if TYPE_CHECKING:
    pass


def main():
    """Main entry point for Alert Agent."""
    load_dotenv()

    # Set up logging
    log_level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("hemostat.alert")

    logger.info("=" * 80)
    logger.info("HemoStat Alert Agent Starting")
    logger.info("=" * 80)

    alert = None
    try:
        # Log configuration
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        slack_status = "enabled" if slack_webhook else "disabled"
        alert_enabled = os.getenv("ALERT_ENABLED", "true").lower() == "true"
        event_ttl = os.getenv("ALERT_EVENT_TTL", "3600")
        max_events = os.getenv("ALERT_MAX_EVENTS", "100")

        logger.info("Configuration Summary:")
        logger.info(f"  - Slack Notifications: {slack_status}")
        logger.info(f"  - Alert Enabled: {alert_enabled}")
        logger.info(f"  - Event TTL: {event_ttl}s")
        logger.info(f"  - Max Events: {max_events}")

        # Instantiate Alert Agent
        alert = AlertNotifier()
        logger.info("Alert Agent initialized successfully")

        # Log subscription info
        logger.info("Subscribed to channels:")
        logger.info("  - hemostat:remediation_complete")
        logger.info("  - hemostat:false_alarm")

        # Start listening loop
        logger.info("Starting message listening loop...")
        alert.run()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully...")
        if alert:
            alert.stop()
        sys.exit(0)

    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        if alert:
            alert.stop()
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if alert:
            alert.stop()
        sys.exit(1)

    finally:
        if alert:
            alert.stop()
        logger.info("Alert Agent shutdown complete")


if __name__ == "__main__":
    main()

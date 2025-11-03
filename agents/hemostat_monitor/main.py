"""
HemoStat Monitor Agent Entry Point

Runs the Monitor Agent as a standalone module.
Usage: python -m agents.hemostat_monitor.main

Import paths supported:
- from agents.hemostat_monitor import ContainerMonitor (package-level)
- from agents.hemostat_monitor.hemostat_monitor import ContainerMonitor (primary module)
- from agents.hemostat_monitor.monitor import ContainerMonitor (implementation module)
"""

import logging
import sys

from docker.errors import DockerException
from dotenv import load_dotenv

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_monitor import ContainerMonitor


def main() -> None:
    """
    Main entry point for the Monitor Agent.

    Initializes the agent and starts the monitoring loop with graceful shutdown handling.
    """
    # Load environment variables
    load_dotenv()

    # Set up logging
    logger = logging.getLogger("hemostat.monitor")
    logger.info("=" * 60)
    logger.info("HemoStat Monitor Agent Starting")
    logger.info("=" * 60)

    monitor = None
    try:
        # Instantiate and run the monitor
        monitor = ContainerMonitor()
        logger.info("Monitor Agent initialized successfully")
        logger.info("Starting container polling...")
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user (SIGINT)")
    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    except DockerException as e:
        logger.error(f"Docker connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if monitor:
            monitor.stop()
        logger.info("=" * 60)
        logger.info("HemoStat Monitor Agent Stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

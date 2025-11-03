"""
HemoStat Metrics Exporter Entry Point

Runs the Metrics Exporter as a standalone module.
Usage: python -m agents.hemostat_metrics.main
"""

import sys

from dotenv import load_dotenv

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_metrics import MetricsExporter
from agents.logger import HemoStatLogger


def main() -> None:
    """
    Main entry point for the Metrics Exporter.

    Initializes the agent and starts the metrics server with graceful shutdown handling.
    """
    # Load environment variables
    load_dotenv()

    # Configure root logger and get logger for this module
    HemoStatLogger.configure_root_logger()
    logger = HemoStatLogger.get_logger("metrics")

    logger.info("=" * 60)
    logger.info("HemoStat Metrics Exporter Starting")
    logger.info("=" * 60)

    exporter = None
    try:
        # Instantiate and run the exporter
        exporter = MetricsExporter()
        logger.info("Metrics Exporter initialized successfully")
        logger.info("Starting metrics server...")
        exporter.run()
    except KeyboardInterrupt:
        logger.info("Metrics Exporter interrupted by user (SIGINT)")
    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if exporter:
            exporter.stop()
        logger.info("=" * 60)
        logger.info("HemoStat Metrics Exporter Stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

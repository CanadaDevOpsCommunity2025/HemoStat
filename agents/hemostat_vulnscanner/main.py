"""
HemoStat Vulnerability Scanner Agent Entry Point

Runs the Vulnerability Scanner Agent as a standalone module.
Usage: python -m agents.hemostat_vulnscanner.main

Import paths supported:
- from agents.hemostat_vulnscanner import VulnerabilityScanner (package-level)
- from agents.hemostat_vulnscanner.vulnscanner import VulnerabilityScanner (implementation module)
"""

import sys

from dotenv import load_dotenv
from requests.exceptions import RequestException

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_vulnscanner import VulnerabilityScanner
from agents.logger import HemoStatLogger


def main() -> None:
    """
    Main entry point for the Vulnerability Scanner Agent.

    Initializes the agent and starts the scanning loop with graceful shutdown handling.
    """
    # Load environment variables
    load_dotenv()

    # Configure root logger and get logger for this module
    HemoStatLogger.configure_root_logger()
    logger = HemoStatLogger.get_logger("vulnscanner")

    logger.info("=" * 60)
    logger.info("HemoStat Vulnerability Scanner Agent Starting")
    logger.info("=" * 60)

    scanner = None
    try:
        # Instantiate and run the scanner
        scanner = VulnerabilityScanner()
        logger.info("Vulnerability Scanner Agent initialized successfully")
        logger.info("Starting vulnerability scanning...")
        scanner.run()
    except KeyboardInterrupt:
        logger.info("Scanner interrupted by user (SIGINT)")
    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    except RequestException as e:
        logger.error(f"ZAP API connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if scanner:
            scanner.stop()
        logger.info("=" * 60)
        logger.info("HemoStat Vulnerability Scanner Agent Stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

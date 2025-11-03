"""
HemoStat Analyzer Agent Entry Point

Runs the Analyzer Agent as a standalone module.
Usage: python -m agents.hemostat_analyzer.main

Import paths supported:
- from agents.hemostat_analyzer import HealthAnalyzer (package-level)
- from agents.hemostat_analyzer.analyzer import HealthAnalyzer (implementation module)
"""

import logging
import sys

from dotenv import load_dotenv

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_analyzer import HealthAnalyzer


def main() -> None:
    """
    Main entry point for the Analyzer Agent.

    Initializes the agent and starts the analysis loop with graceful shutdown handling.
    """
    # Load environment variables
    load_dotenv()

    # Set up logging
    logger = logging.getLogger("hemostat.analyzer")
    logger.info("=" * 60)
    logger.info("HemoStat Analyzer Agent Starting")
    logger.info("=" * 60)

    analyzer = None
    try:
        # Instantiate and run the analyzer
        analyzer = HealthAnalyzer()
        logger.info("Analyzer Agent initialized successfully")
        logger.info("Starting analysis loop...")
        analyzer.run()
    except KeyboardInterrupt:
        logger.info("Analyzer interrupted by user (SIGINT)")
    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    except ImportError as e:
        logger.error(
            f"Missing required dependencies: {e}. "
            "Install with: uv sync --extra agents"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if analyzer:
            analyzer.stop()
        logger.info("=" * 60)
        logger.info("HemoStat Analyzer Agent Stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

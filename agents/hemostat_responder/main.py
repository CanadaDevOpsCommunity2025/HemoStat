"""
HemoStat Responder Agent Entry Point

Runs the Responder Agent as a standalone module.
Usage: python -m agents.hemostat_responder.main

Import paths supported:
- from agents.hemostat_responder import ContainerResponder (package-level)
- from agents.hemostat_responder.hemostat_responder import ContainerResponder (primary module)
- from agents.hemostat_responder.responder import ContainerResponder (implementation module)
"""

import logging
import sys

from docker.errors import DockerException
from dotenv import load_dotenv

from agents.agent_base import HemoStatConnectionError
from agents.hemostat_responder import ContainerResponder


def main():
    """Main entry point for the Responder Agent."""
    # Load environment variables
    load_dotenv()

    # Set up logging
    log_level = logging.INFO
    logger = logging.getLogger("hemostat.responder")
    logger.setLevel(log_level)

    responder = None
    try:
        # Log startup banner
        logger.info("=" * 60)
        logger.info("HemoStat Responder Agent - Starting")
        logger.info("=" * 60)

        # Instantiate responder
        responder = ContainerResponder()

        logger.info("Responder Agent initialized successfully")
        logger.info("Listening for remediation requests on hemostat:remediation_needed")

        # Start listening loop
        responder.run()

    except HemoStatConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    except DockerException as e:
        logger.error(f"Docker connection failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Gracefully stop responder and close connections
        if responder:
            try:
                responder.stop()
            except Exception as e:
                logger.warning(f"Error stopping responder: {e}")
        logger.info("Responder Agent stopped")


if __name__ == "__main__":
    main()

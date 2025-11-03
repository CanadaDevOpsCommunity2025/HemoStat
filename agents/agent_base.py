"""
HemoStat Base Agent Module

Provides the foundational HemoStatAgent base class that all specialized agents inherit from.
Encapsulates Redis pub/sub communication patterns and shared state management.
"""

import json
import os
import signal
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import redis
from dotenv import load_dotenv

from agents.logger import HemoStatLogger
from agents.platform_utils import get_platform_display

# Load environment variables from .env file
load_dotenv()

# Get logger for this module
logger = HemoStatLogger.get_logger("agent_base")


class HemoStatConnectionError(Exception):
    """Custom exception for Redis connection failures."""

    pass


class HemoStatAgent:
    """
    Base class for all HemoStat agents.

    Encapsulates Redis pub/sub communication and shared state management.
    All specialized agents (Monitor, Analyzer, Responder, Alert) inherit from this class.
    """

    def __init__(
        self,
        agent_name: str,
        redis_host: str | None = None,
        redis_port: int | None = None,
        redis_db: int = 0,
    ):
        """
        Initialize the HemoStat agent.

        Args:
            agent_name: Unique identifier for this agent (e.g., 'monitor', 'analyzer')
            redis_host: Redis server hostname (defaults to env REDIS_HOST or 'redis')
            redis_port: Redis server port (defaults to env REDIS_PORT or 6379)
            redis_db: Redis database number (default: 0)

        Raises:
            HemoStatConnectionError: If Redis connection fails after retries
        """
        self.agent_name = agent_name
        self._running = False
        self._subscriptions: dict[str, Callable] = {}

        # Load Redis config from environment or use defaults
        if redis_host is None:
            redis_host = os.getenv("REDIS_HOST", "redis")
        if redis_port is None:
            redis_port = int(os.getenv("REDIS_PORT", 6379))

        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db

        # Initialize logger using custom HemoStatLogger
        self.logger = HemoStatLogger.get_logger(agent_name)

        # Initialize Redis connection with retry logic
        self.redis = self._connect_redis()

        # Set up pub/sub
        self.pubsub = self.redis.pubsub()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        self.logger.info(
            f"Agent '{self.agent_name}' initialized successfully on {get_platform_display()}",
            extra={"agent": self.agent_name},
        )

    def _connect_redis(self) -> redis.Redis:
        """
        Connect to Redis with exponential backoff retry logic.

        Returns:
            Connected Redis client instance

        Raises:
            HemoStatConnectionError: If connection fails after configured attempts
        """
        max_retries = int(os.getenv("AGENT_RETRY_MAX", 3))
        initial_delay = float(os.getenv("AGENT_RETRY_DELAY", 1))

        # Build exponential backoff list
        retry_delays = [initial_delay * (2**i) for i in range(max_retries)]

        redis_password = os.getenv("REDIS_PASSWORD", "").strip()

        for attempt in range(max_retries):
            try:
                redis_kwargs: dict[str, Any] = {
                    "host": self.redis_host,
                    "port": self.redis_port,
                    "db": self.redis_db,
                    "decode_responses": True,
                    "socket_connect_timeout": 5,
                    "socket_keepalive": True,
                }
                if redis_password:
                    redis_kwargs["password"] = redis_password

                client = redis.Redis(**redis_kwargs)  # type: ignore[arg-type]
                # Test connection
                client.ping()
                self.logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
                return client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    self.logger.warning(
                        f"Redis connection failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e!s}"
                    )
                    time.sleep(wait_time)
                else:
                    error_msg = (
                        f"Failed to connect to Redis after {max_retries} attempts. "
                        f"Last error: {e!s}"
                    )
                    self.logger.error(error_msg)
                    raise HemoStatConnectionError(error_msg) from e

        # This should never be reached, but satisfies type checker
        msg = f"Failed to connect to Redis after {max_retries} attempts"
        raise HemoStatConnectionError(msg)

    def publish_event(self, channel: str, event_type: str, data: dict[str, Any]) -> bool:
        """
        Publish a structured event to a Redis channel.

        Args:
            channel: Redis channel name (e.g., 'hemostat:events:health')
            event_type: Type of event (e.g., 'container_unhealthy')
            data: Event payload data

        Returns:
            True if publish succeeded, False otherwise
        """
        max_retries = int(os.getenv("AGENT_RETRY_MAX", 3))
        initial_delay = float(os.getenv("AGENT_RETRY_DELAY", 1))

        # Build exponential backoff list
        retry_delays = [initial_delay * (2**i) for i in range(max_retries)]

        event_payload = {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "agent": self.agent_name,
            "data": data,
        }

        for attempt in range(max_retries):
            try:
                json_payload = json.dumps(event_payload)
                num_subscribers = self.redis.publish(channel, json_payload)
                self.logger.info(
                    f"Published event '{event_type}' to channel '{channel}' "
                    f"({num_subscribers} subscribers)"
                )
                return True
            except (TypeError, ValueError) as e:
                self.logger.error(f"Failed to serialize event payload: {e!s}")
                return False
            except redis.RedisError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    self.logger.warning(
                        f"Failed to publish event (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e!s}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        f"Failed to publish event after {max_retries} attempts. Last error: {e!s}"
                    )
                    return False

        # This should never be reached, but satisfies type checker
        return False

    def subscribe_to_channel(
        self, channel: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """
        Subscribe to a Redis channel and register a message handler.

        Args:
            channel: Redis channel name to subscribe to
            callback: Callable that will be invoked for each message
                     (receives deserialized message dict)
        """
        try:
            self.pubsub.subscribe(channel)
            self._subscriptions[channel] = callback
            self.logger.info(f"Subscribed to channel '{channel}'")
        except redis.RedisError as e:
            self.logger.error(f"Failed to subscribe to channel '{channel}': {e!s}")

    def start_listening(self) -> None:
        """
        Start the pub/sub message listening loop.

        Blocks until stop() is called. Handles messages and exceptions gracefully.
        """
        self._running = True
        self.logger.info("Starting message listening loop")

        try:
            for message in self.pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        self.logger.debug(
                            f"Received message on channel '{message['channel']}': "
                            f"{payload.get('event_type', 'unknown')}"
                        )
                        # Invoke registered callback if it exists
                        callback = self._subscriptions.get(message["channel"])
                        if callback:
                            callback(payload)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to deserialize message: {e!s}")
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e!s}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Listening loop error: {e!s}", exc_info=True)
        finally:
            self.logger.info("Message listening loop stopped")

    def get_shared_state(self, key: str) -> dict[str, Any] | None:
        """
        Retrieve shared state from Redis.

        Args:
            key: State key (will be prefixed with 'hemostat:state:')

        Returns:
            Deserialized state dict, or None if key doesn't exist or error occurs
        """
        try:
            full_key = f"hemostat:state:{key}"
            value = self.redis.get(full_key)

            if value is None:
                return None

            # Check TTL and warn if expiring soon
            ttl = self.redis.ttl(full_key)
            if ttl > 0 and ttl < 300:  # Less than 5 minutes
                self.logger.warning(f"Shared state '{key}' expiring soon (TTL: {ttl}s)")

            return json.loads(value)
        except redis.RedisError as e:
            self.logger.error(f"Failed to get shared state '{key}': {e!s}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to deserialize shared state '{key}': {e!s}")
            return None

    def set_shared_state(self, key: str, value: dict[str, Any], ttl: int | None = None) -> bool:
        """
        Store shared state in Redis with optional TTL.

        Args:
            key: State key (will be prefixed with 'hemostat:state:')
            value: State data to store
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = f"hemostat:state:{key}"
            json_value = json.dumps(value)
            self.redis.set(full_key, json_value)

            if ttl is not None:
                self.redis.expire(full_key, ttl)

            self.logger.debug(f"Set shared state '{key}'" + (f" with TTL {ttl}s" if ttl else ""))
            return True
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to serialize shared state '{key}': {e!s}")
            return False
        except redis.RedisError as e:
            self.logger.error(f"Failed to set shared state '{key}': {e!s}")
            return False

    def stop(self) -> None:
        """
        Gracefully shut down the agent.

        Stops the listening loop, unsubscribes from channels, and closes connections.
        """
        self.logger.info("Stopping agent")
        self._running = False

        try:
            self.pubsub.unsubscribe()
            self.logger.debug("Unsubscribed from all channels")
        except Exception as e:
            self.logger.error(f"Error unsubscribing: {e!s}")

        try:
            self.redis.close()
            self.logger.debug("Closed Redis connection")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {e!s}")

        self.logger.info("Agent stopped successfully")

    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """
        Handle OS shutdown signals (SIGTERM, SIGINT).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop()

    @classmethod
    def from_env(cls, agent_name: str) -> "HemoStatAgent":
        """
        Create an agent instance from environment variables.

        Reads REDIS_HOST, REDIS_PORT, and REDIS_DB from environment.

        Args:
            agent_name: Name of the agent

        Returns:
            Initialized HemoStatAgent instance
        """
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))

        return cls(
            agent_name=agent_name,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
        )

    @property
    def is_running(self) -> bool:
        """
        Check if the agent is currently running.

        Returns:
            True if the agent is running, False otherwise
        """
        return self._running

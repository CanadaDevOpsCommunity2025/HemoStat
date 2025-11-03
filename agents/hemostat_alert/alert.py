"""
HemoStat Alert Agent - Event Storage and Notifications

Consumes remediation completion and false alarm events from the Responder and Analyzer agents.
Sends formatted notifications to Slack webhooks, stores events in Redis for dashboard consumption,
and implements event deduplication to prevent notification spam.
"""

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import requests
from requests import exceptions as requests_exceptions

from agents.agent_base import HemoStatAgent


class AlertNotifier(HemoStatAgent):
    """Alert Agent for sending notifications and storing events.

    Subscribes to remediation completion and false alarm events,
    sends Slack notifications, and stores events in Redis for dashboard consumption.
    Implements event deduplication using minute-level timestamps and event type hashing
    to prevent duplicate notifications within configurable TTL windows.
    """

    def __init__(self):
        """
        Initialize the Alert Agent.

        Loads configuration from environment variables, subscribes to remediation
        completion and false alarm channels, and validates Slack webhook URL if provided.

        Raises:
            HemoStatConnectionError: If Redis connection fails
        """
        super().__init__(agent_name="alert")

        # Load configuration from environment
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        self.alert_enabled = os.getenv("ALERT_ENABLED", "true").lower() == "true"
        self.event_ttl = int(os.getenv("ALERT_EVENT_TTL", "3600"))
        self.max_events = int(os.getenv("ALERT_MAX_EVENTS", "100"))
        self.dedupe_ttl = int(os.getenv("ALERT_DEDUPE_TTL", "60"))

        # Validate Slack webhook URL if provided
        if self.slack_webhook_url and not self.slack_webhook_url.startswith(
            "https://hooks.slack.com/"
        ):
            self.logger.warning(
                f"Invalid Slack webhook URL format: {self.slack_webhook_url[:50]}..."
            )

        # Subscribe to both channels
        self.subscribe_to_channel(
            "hemostat:remediation_complete", self._handle_remediation_complete
        )
        self.subscribe_to_channel("hemostat:false_alarm", self._handle_false_alarm)

        # Log initialization
        slack_status = "enabled" if (self.alert_enabled and self.slack_webhook_url) else "disabled"
        self.logger.info(
            f"Alert Agent initialized - Slack: {slack_status}, "
            f"Event TTL: {self.event_ttl}s, Max Events: {self.max_events}, "
            f"Dedup TTL: {self.dedupe_ttl}s"
        )

    def run(self) -> None:
        """
        Start the message listening loop.

        Blocks until stop() is called. Handles exceptions gracefully and logs errors.
        """
        try:
            self.logger.info("Alert Agent starting listening loop")
            self.start_listening()
        except Exception as e:
            self.logger.error(f"Error in listening loop: {e}", exc_info=True)
            raise

    def _handle_remediation_complete(self, message: dict[str, Any]) -> None:
        """
        Handle remediation completion event from Responder Agent.

        Extracts payload and timestamp from message envelope, stores event in Redis,
        and sends Slack notification if enabled.

        Args:
            message: Full message wrapper with event_type, timestamp, agent, and data fields
        """
        try:
            # Extract the inner payload from the envelope
            payload = message.get("data", {})
            source_timestamp = message.get("timestamp")

            self.logger.info(
                f"Received remediation_complete event for container: {payload.get('container', 'unknown')}"
            )

            # Store event in Redis
            self._store_event("remediation_complete", payload, source_timestamp)

            # Send Slack notification if enabled
            if self.alert_enabled:
                self._send_slack_notification(
                    payload, event_type="remediation_complete", event_timestamp=source_timestamp
                )

        except Exception as e:
            self.logger.error(f"Error handling remediation_complete event: {e}", exc_info=True)

    def _handle_false_alarm(self, message: dict[str, Any]) -> None:
        """
        Handle false alarm event from Analyzer Agent.

        Extracts payload and timestamp from message envelope, stores event in Redis,
        and sends Slack notification if enabled.

        Args:
            message: Full message wrapper with event_type, timestamp, agent, and data fields
        """
        try:
            # Extract the inner payload from the envelope
            payload = message.get("data", {})
            source_timestamp = message.get("timestamp")

            self.logger.info(
                f"Received false_alarm event for container: {payload.get('container', 'unknown')}"
            )

            # Store event in Redis
            self._store_event("false_alarm", payload, source_timestamp)

            # Send Slack notification if enabled
            if self.alert_enabled:
                self._send_slack_notification(
                    payload, event_type="false_alarm", event_timestamp=source_timestamp
                )

        except Exception as e:
            self.logger.error(f"Error handling false_alarm event: {e}", exc_info=True)

    def _store_event(
        self, event_type: str, payload: dict[str, Any], source_timestamp: str | None = None
    ) -> None:
        """
        Store event in Redis list for dashboard consumption.

        Stores events in both type-specific lists and a unified timeline list.
        Uses source timestamp if available, otherwise uses current time.
        Maintains max event count and TTL per list.

        Args:
            event_type: Type of event (e.g., 'remediation_complete', 'false_alarm')
            payload: Event data payload
            source_timestamp: Optional timestamp from event source (ISO format string)
        """
        try:
            # Use source timestamp if available, otherwise use current time
            timestamp = source_timestamp or datetime.now(UTC).isoformat()

            # Build event entry with metadata
            event_entry = {
                "timestamp": timestamp,
                "agent": "alert",
                "event_type": event_type,
                "data": payload,
            }

            event_json = json.dumps(event_entry)

            # Store in type-specific list (newest first)
            self.redis.lpush(f"hemostat:events:{event_type}", event_json)
            self.redis.ltrim(f"hemostat:events:{event_type}", 0, self.max_events - 1)
            self.redis.expire(f"hemostat:events:{event_type}", self.event_ttl)

            # Store in unified timeline
            self.redis.lpush("hemostat:events:all", event_json)
            self.redis.ltrim("hemostat:events:all", 0, self.max_events - 1)
            self.redis.expire("hemostat:events:all", self.event_ttl)

            self.logger.debug(
                f"Event stored: {event_type} for {payload.get('container', 'unknown')}"
            )

        except Exception as e:
            self.logger.error(f"Error storing event in Redis: {e}", exc_info=True)

    def _send_slack_notification(
        self, message: dict[str, Any], event_type: str, event_timestamp: str | None = None
    ) -> None:
        """
        Send formatted notification to Slack webhook.

        Checks if Slack is configured, performs deduplication, formats message
        based on event type, and sends via webhook with retry logic.

        Args:
            message: Event message data to format and send
            event_type: Type of event ('remediation_complete' or 'false_alarm')
            event_timestamp: Optional timestamp for deduplication (ISO format string)
        """
        try:
            # Check if Slack is configured
            if not self.slack_webhook_url:
                self.logger.debug("Slack webhook not configured, skipping notification")
                return

            # Check for duplicate events
            if self._is_duplicate_event(event_type, event_timestamp):
                self.logger.debug("Duplicate event detected, skipping Slack notification")
                return

            # Format message based on event type
            if event_type == "remediation_complete":
                payload = self._format_remediation_notification(message)
            elif event_type == "false_alarm":
                payload = self._format_false_alarm_notification(message)
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
                return

            # Send with retry logic (only if payload was successfully formatted)
            if payload:
                self._send_webhook_with_retry(payload, message, event_type)

        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}", exc_info=True)

    def _send_webhook_with_retry(
        self, payload: dict[str, Any], message: dict[str, Any], event_type: str | None = None
    ) -> None:
        """
        Send webhook with exponential backoff retry logic.

        Implements retry logic with exponential backoff for transient failures.
        Handles rate limiting (429) with longer backoff. Marks successfully sent
        events in deduplication cache.

        Args:
            payload: Formatted Slack message payload
            message: Original event message
            event_type: Type of event for deduplication cache
        """
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                response = requests.post(self.slack_webhook_url, json=payload, timeout=10)

                if response.status_code == 200:
                    # Mark as sent in deduplication cache
                    if event_type:
                        event_hash = self._get_event_hash(event_type, event_timestamp=None)
                        self.redis.setex(f"hemostat:alert_sent:{event_hash}", self.dedupe_ttl, "1")
                    self.logger.info(f"Slack notification sent successfully for {event_type}")
                    return

                elif response.status_code == 429:
                    # Rate limit - use longer backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt) * 2  # Longer backoff for rate limits
                        self.logger.warning(
                            f"Slack rate limit (429), retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        self.logger.warning("Slack rate limit (429) - max retries exceeded")
                        return

                else:
                    self.logger.warning(
                        f"Slack webhook error {response.status_code}: {response.text}"
                    )
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        self.logger.warning(
                            f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)

            except requests_exceptions.Timeout:
                self.logger.warning(f"Slack webhook timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)

            except requests_exceptions.RequestException as e:
                self.logger.warning(
                    f"Slack webhook request error: {e} (attempt {attempt + 1}/{max_retries})"
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)

    def _format_remediation_notification(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """
        Format remediation completion event as Slack message.

        Creates a formatted Slack attachment with color coding based on status:
        - Green (#36a64f) for success
        - Red (#ff0000) for failed
        - Orange (#ff9900) for rejected
        - Gray (#cccccc) for not applicable

        Args:
            message: Remediation event data with container, action, result, etc.

        Returns:
            Dictionary with Slack attachment format, or None if formatting fails
        """
        container = message.get("container", "unknown")
        action = message.get("action", "unknown")
        dry_run = message.get("dry_run", False)
        reason = message.get("reason", "")
        confidence = message.get("confidence", 0)

        # Extract result object and get status
        result_obj = message.get("result", {})
        status = (
            result_obj.get("status", "unknown") if isinstance(result_obj, dict) else str(result_obj)
        )
        error_details = result_obj.get("error", "") if isinstance(result_obj, dict) else ""
        rejection_reason = result_obj.get("reason", "") if isinstance(result_obj, dict) else ""

        # Determine color and emoji based on status
        if status == "success":
            color = "#36a64f"
            emoji = "✅"
            status_text = "Success"
        elif status == "failed":
            color = "#ff0000"
            emoji = "❌"
            status_text = "Failed"
        elif status == "rejected":
            color = "#ff9900"
            emoji = "⏸️"
            status_text = "Rejected"
        else:
            color = "#cccccc"
            emoji = "i"
            status_text = "Not Applicable"

        # Build fields
        fields = [
            {"title": "Container", "value": container, "short": True},
            {"title": "Action", "value": action, "short": True},
            {"title": "Status", "value": status_text, "short": True},
        ]

        if reason:
            fields.append({"title": "Reason", "value": reason, "short": False})

        if rejection_reason and status == "rejected":
            fields.append({"title": "Rejection Reason", "value": rejection_reason, "short": False})

        if confidence > 0:
            fields.append({"title": "Confidence", "value": f"{confidence:.1%}", "short": True})

        if dry_run:
            fields.append({"title": "Dry Run", "value": "Yes", "short": True})

        if error_details and status == "failed":
            fields.append({"title": "Error", "value": error_details, "short": False})

        # Build attachment
        attachment = {
            "fallback": f"{emoji} Container Remediation: {status_text}",
            "color": color,
            "title": f"{emoji} Container Remediation: {status_text}",
            "fields": fields,
            "footer": "HemoStat Alert Agent",
            "ts": int(datetime.now(UTC).timestamp()),
        }

        return {"attachments": [attachment]}

    def _format_false_alarm_notification(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """
        Format false alarm event as Slack message.

        Creates a formatted Slack attachment for false alarm events with yellow color (#ffcc00).
        Includes container name, analysis method, reason, and confidence score.

        Args:
            message: False alarm event data with container, reason, confidence, etc.

        Returns:
            Dictionary with Slack attachment format, or None if formatting fails
        """
        container = message.get("container", "unknown")
        reason = message.get("reason", "")
        confidence = message.get("confidence", 0)
        analysis_method = message.get("analysis_method", "unknown")

        # Build fields
        fields = [
            {"title": "Container", "value": container, "short": True},
            {"title": "Analysis Method", "value": analysis_method, "short": True},
        ]

        if reason:
            fields.append({"title": "Reason", "value": reason, "short": False})

        if confidence > 0:
            fields.append({"title": "Confidence", "value": f"{confidence:.1%}", "short": True})

        # Build attachment
        attachment = {
            "fallback": "⚠️ False Alarm Detected",
            "color": "#ffcc00",
            "title": "⚠️ False Alarm Detected",
            "fields": fields,
            "footer": "HemoStat Alert Agent",
            "ts": int(datetime.now(UTC).timestamp()),
        }

        return {"attachments": [attachment]}

    def _is_duplicate_event(self, event_type: str, event_timestamp: str | None = None) -> bool:
        """
        Check if event was recently sent to avoid duplicate notifications.

        Uses minute-level timestamp granularity and event type to generate hash.
        Checks Redis cache for recent sends within dedupe_ttl window.

        Args:
            event_type: Type of event ('remediation_complete' or 'false_alarm')
            event_timestamp: Optional timestamp for deduplication (ISO format string)

        Returns:
            True if event was recently sent, False otherwise
        """
        event_hash = self._get_event_hash(event_type, event_timestamp)
        cache_key = f"hemostat:alert_sent:{event_hash}"
        return bool(self.redis.get(cache_key))

    def _get_event_hash(self, event_type: str, event_timestamp: str | None = None) -> str:
        """
        Generate deterministic hash for event deduplication.

        Creates hash from event type and minute-level timestamp to allow
        deduplication of duplicate events within the same minute.

        Args:
            event_type: Type of event
            event_timestamp: Optional timestamp (ISO format string)

        Returns:
            MD5 hash string for deduplication cache key
        """
        # Use provided timestamp or current time, rounded to minute
        timestamp = event_timestamp or datetime.now(UTC).isoformat()
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                minute_timestamp = dt.replace(second=0, microsecond=0).isoformat()
            except (ValueError, AttributeError):
                minute_timestamp = datetime.now(UTC).replace(second=0, microsecond=0).isoformat()
        else:
            minute_timestamp = datetime.now(UTC).replace(second=0, microsecond=0).isoformat()

        # Create hash from event_type and timestamp
        hash_input = f"{event_type}:{minute_timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()

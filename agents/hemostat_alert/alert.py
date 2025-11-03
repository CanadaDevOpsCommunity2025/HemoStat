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
from zoneinfo import ZoneInfo

import requests
from requests import exceptions as requests_exceptions

from agents.agent_base import HemoStatAgent
from agents.platform_utils import get_platform_display


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

        # Subscribe to all channels
        self.subscribe_to_channel(
            "hemostat:remediation_complete", self._handle_remediation_complete
        )
        self.subscribe_to_channel("hemostat:false_alarm", self._handle_false_alarm)
        self.subscribe_to_channel("hemostat:alerts", self._handle_vulnerability_alert)

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

    def _handle_vulnerability_alert(self, message: dict[str, Any]) -> None:
        """
        Handle vulnerability alert event from Vulnerability Scanner Agent.

        Extracts payload and timestamp from message envelope, stores event in Redis,
        and sends Slack notification if enabled.

        Args:
            message: Full message wrapper with event_type, timestamp, agent, and data fields
        """
        try:
            # Extract the inner payload from the envelope
            payload = message.get("data", {})
            source_timestamp = message.get("timestamp")
            event_type = message.get("event_type", "unknown")

            target_url = payload.get("target_url", "unknown")
            critical_count = payload.get("critical_count", 0)
            
            self.logger.info(
                f"Received vulnerability alert for {target_url}: {critical_count} critical vulnerabilities"
            )

            # Store event in Redis
            self._store_event("vulnerability_alert", payload, source_timestamp)

            # Send Slack notification if enabled
            if self.alert_enabled:
                self._send_slack_notification(
                    payload, event_type="vulnerability_alert", event_timestamp=source_timestamp
                )

        except Exception as e:
            self.logger.error(f"Error handling vulnerability_alert event: {e}", exc_info=True)

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
            elif event_type == "vulnerability_alert":
                payload = self._format_vulnerability_notification(message)
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
        analysis_method = message.get("analysis_method", "unknown")

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

        # Format analysis method with indicator
        if analysis_method == "ai":
            ai_indicator = "🤖 AI-Powered"
        elif analysis_method == "rule_based":
            ai_indicator = "📋 Rule-Based"
        else:
            ai_indicator = analysis_method

        # Build fields
        fields = [
            {"title": "Event Type", "value": "Remediation Complete", "short": True},
            {"title": "Source Agent", "value": "Responder", "short": True},
            {"title": "Container", "value": container, "short": True},
            {"title": "Action", "value": action, "short": True},
            {"title": "Status", "value": status_text, "short": True},
            {"title": "Analysis", "value": ai_indicator, "short": True},
            {"title": "Environment", "value": get_platform_display(), "short": True},
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

        # Get timestamp from message or use current time
        timestamp_str = message.get("timestamp", datetime.now(UTC).isoformat())
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            ts = int(timestamp.timestamp())
            # Convert to Eastern Time for display
            eastern = ZoneInfo("America/New_York")
            timestamp_et = timestamp.astimezone(eastern)
            tz_abbr = timestamp_et.strftime("%Z")  # EST or EDT
            time_display = timestamp_et.strftime(f"%I:%M:%S %p {tz_abbr}")
        except (ValueError, AttributeError):
            ts = int(datetime.now(UTC).timestamp())
            now_et = datetime.now(ZoneInfo("America/New_York"))
            tz_abbr = now_et.strftime("%Z")
            time_display = now_et.strftime(f"%I:%M:%S %p {tz_abbr}")

        # Add timestamp field
        fields.append({"title": "Timestamp", "value": time_display, "short": True})

        # Build attachment with enhanced metadata
        attachment = {
            "fallback": f"{emoji} Container Remediation: {status_text} - {container}",
            "color": color,
            "pretext": "🤖 *Responder Agent* → Remediation Complete",
            "title": f"{emoji} Container Remediation: {status_text}",
            "fields": fields,
            "footer": "HemoStat • Alert Agent • Remediation Event",
            "ts": ts,
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

        # Format analysis method with indicator
        if analysis_method == "ai":
            ai_indicator = "🤖 AI-Powered"
        elif analysis_method == "rule_based":
            ai_indicator = "📋 Rule-Based"
        else:
            ai_indicator = analysis_method

        # Build fields
        fields = [
            {"title": "Event Type", "value": "False Alarm", "short": True},
            {"title": "Source Agent", "value": "Analyzer", "short": True},
            {"title": "Container", "value": container, "short": True},
            {"title": "Analysis", "value": ai_indicator, "short": True},
            {"title": "Environment", "value": get_platform_display(), "short": True},
        ]

        if reason:
            fields.append({"title": "Reason", "value": reason, "short": False})

        if confidence > 0:
            fields.append({"title": "Confidence", "value": f"{confidence:.1%}", "short": True})

        # Get timestamp from message or use current time
        timestamp_str = message.get("timestamp", datetime.now(UTC).isoformat())
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            ts = int(timestamp.timestamp())
            # Convert to Eastern Time for display
            eastern = ZoneInfo("America/New_York")
            timestamp_et = timestamp.astimezone(eastern)
            tz_abbr = timestamp_et.strftime("%Z")  # EST or EDT
            time_display = timestamp_et.strftime(f"%I:%M:%S %p {tz_abbr}")
        except (ValueError, AttributeError):
            ts = int(datetime.now(UTC).timestamp())
            now_et = datetime.now(ZoneInfo("America/New_York"))
            tz_abbr = now_et.strftime("%Z")
            time_display = now_et.strftime(f"%I:%M:%S %p {tz_abbr}")

        # Add timestamp field
        fields.append({"title": "Timestamp", "value": time_display, "short": True})

        # Build attachment with enhanced metadata
        attachment = {
            "fallback": f"⚠️ False Alarm: {container} - No action needed",
            "color": "#ffcc00",
            "pretext": "🔍 *Analyzer Agent* → False Alarm",
            "title": "⚠️ False Alarm: No Remediation Required",
            "fields": fields,
            "footer": "HemoStat • Alert Agent • Analysis Event",
            "ts": ts,
        }

        return {"attachments": [attachment]}

    def _format_vulnerability_notification(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """
        Format vulnerability alert event as Slack message.

        Creates a formatted Slack attachment with red color coding for critical vulnerabilities.
        Includes vulnerability counts, target information, and critical vulnerability details.

        Args:
            message: Vulnerability alert data with target_url, critical_count, critical_vulns, etc.

        Returns:
            Dictionary with Slack attachment format, or None if formatting fails
        """
        target_url = message.get("target_url", "unknown")
        critical_count = message.get("critical_count", 0)
        total_count = message.get("total_count", 0)
        critical_vulns = message.get("critical_vulns", [])

        # Build fields
        fields = [
            {"title": "Event Type", "value": "🚨 Critical Vulnerabilities Found", "short": True},
            {"title": "Target", "value": target_url, "short": True},
            {"title": "Critical Vulnerabilities", "value": str(critical_count), "short": True},
            {"title": "Total Vulnerabilities", "value": str(total_count), "short": True},
        ]

        # Add critical vulnerability details (limit to top 3 for Slack readability)
        if critical_vulns:
            vuln_details = []
            for i, vuln in enumerate(critical_vulns[:3], 1):
                vuln_name = vuln.get("name", "Unknown")
                vuln_url = vuln.get("url", "")
                vuln_param = vuln.get("param", "")
                
                detail = f"{i}. **{vuln_name}**"
                if vuln_url:
                    detail += f"\n   URL: `{vuln_url}`"
                if vuln_param:
                    detail += f"\n   Parameter: `{vuln_param}`"
                
                vuln_details.append(detail)
            
            if len(critical_vulns) > 3:
                vuln_details.append(f"... and {len(critical_vulns) - 3} more critical vulnerabilities")
            
            fields.append({
                "title": "Critical Vulnerability Details",
                "value": "\n\n".join(vuln_details),
                "short": False
            })

        # Add timestamp field
        timestamp_str = message.get("timestamp")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            ts = int(timestamp.timestamp())
            # Convert to Eastern Time for display
            eastern = ZoneInfo("America/New_York")
            timestamp_et = timestamp.astimezone(eastern)
            tz_abbr = timestamp_et.strftime("%Z")  # EST or EDT
            time_display = timestamp_et.strftime(f"%I:%M:%S %p {tz_abbr}")
        except (ValueError, AttributeError):
            ts = int(datetime.now(UTC).timestamp())
            now_et = datetime.now(ZoneInfo("America/New_York"))
            tz_abbr = now_et.strftime("%Z")
            time_display = now_et.strftime(f"%I:%M:%S %p {tz_abbr}")

        fields.append({"title": "Scan Time", "value": time_display, "short": True})

        # Build attachment with critical vulnerability styling
        attachment = {
            "fallback": f"🚨 CRITICAL: {critical_count} vulnerabilities found in {target_url}",
            "color": "#ff0000",  # Red for critical security alerts
            "pretext": "🔒 *Vulnerability Scanner* → Critical Security Alert",
            "title": f"🚨 {critical_count} Critical Vulnerabilities Detected",
            "title_link": target_url if target_url.startswith("http") else None,
            "fields": fields,
            "footer": "HemoStat • Alert Agent • Security Scan",
            "ts": ts,
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

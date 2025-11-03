"""
HemoStat Metrics Exporter Agent

Subscribes to HemoStat events and exposes metrics in Prometheus format.
Provides observability into system performance, container health, and agent operations.
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from agents.agent_base import HemoStatAgent


class MetricsExporter(HemoStatAgent):
    """
    Metrics Exporter for HemoStat.

    Subscribes to all HemoStat events and exposes metrics for Prometheus scraping.
    Runs an HTTP server on port 9090 to serve metrics endpoint.
    """

    def __init__(self):
        """
        Initialize the Metrics Exporter agent.

        Raises:
            HemoStatConnectionError: If Redis connection fails
        """
        # Initialize base agent
        super().__init__(agent_name="metrics")

        # Prometheus metrics port
        self.metrics_port = int(os.getenv("METRICS_PORT", 9090))

        # Container health metrics
        self.container_cpu_usage = Gauge(
            "hemostat_container_cpu_percent",
            "Container CPU usage percentage",
            ["container_id", "container_name"],
        )
        self.container_memory_usage = Gauge(
            "hemostat_container_memory_percent",
            "Container memory usage percentage",
            ["container_id", "container_name"],
        )
        self.container_memory_bytes = Gauge(
            "hemostat_container_memory_bytes",
            "Container memory usage in bytes",
            ["container_id", "container_name"],
        )
        self.container_network_rx_bytes = Counter(
            "hemostat_container_network_rx_bytes_total",
            "Container network received bytes",
            ["container_id", "container_name"],
        )
        self.container_network_tx_bytes = Counter(
            "hemostat_container_network_tx_bytes_total",
            "Container network transmitted bytes",
            ["container_id", "container_name"],
        )
        self.container_blkio_read_bytes = Counter(
            "hemostat_container_blkio_read_bytes_total",
            "Container block I/O read bytes",
            ["container_id", "container_name"],
        )
        self.container_blkio_write_bytes = Counter(
            "hemostat_container_blkio_write_bytes_total",
            "Container block I/O write bytes",
            ["container_id", "container_name"],
        )
        self.container_restart_count = Gauge(
            "hemostat_container_restart_count",
            "Container restart count",
            ["container_id", "container_name"],
        )

        # Health alert metrics
        self.health_alerts_total = Counter(
            "hemostat_health_alerts_total",
            "Total number of health alerts",
            ["container_name", "severity"],
        )
        self.anomalies_detected = Counter(
            "hemostat_anomalies_detected_total",
            "Total number of anomalies detected",
            ["container_name", "anomaly_type"],
        )

        # Analysis metrics
        self.analysis_requests_total = Counter(
            "hemostat_analysis_requests_total",
            "Total number of analysis requests",
            ["result_type"],
        )
        self.analysis_duration_seconds = Histogram(
            "hemostat_analysis_duration_seconds",
            "Analysis duration in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )
        self.analysis_confidence = Histogram(
            "hemostat_analysis_confidence",
            "Analysis confidence score",
            ["result_type"],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        # Remediation metrics
        self.remediation_attempts_total = Counter(
            "hemostat_remediation_attempts_total",
            "Total number of remediation attempts",
            ["container_name", "action", "status"],
        )
        self.remediation_duration_seconds = Histogram(
            "hemostat_remediation_duration_seconds",
            "Remediation duration in seconds",
            ["action"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )
        self.remediation_cooldown_active = Gauge(
            "hemostat_remediation_cooldown_active",
            "Whether cooldown is active for container (1 = active, 0 = inactive)",
            ["container_id"],
        )

        # Alert metrics
        self.alerts_sent_total = Counter(
            "hemostat_alerts_sent_total",
            "Total number of alerts sent",
            ["channel", "status"],
        )
        self.alerts_deduped_total = Counter(
            "hemostat_alerts_deduped_total",
            "Total number of deduplicated alerts",
        )

        # System health metrics
        self.agent_uptime_seconds = Gauge(
            "hemostat_agent_uptime_seconds",
            "Agent uptime in seconds",
            ["agent_name"],
        )
        self.redis_operations_total = Counter(
            "hemostat_redis_operations_total",
            "Total Redis operations",
            ["operation", "status"],
        )

        # Time-to-X metrics
        self.time_to_detection_seconds = Histogram(
            "hemostat_time_to_detection_seconds",
            "Time from issue occurrence to detection",
            buckets=[5, 10, 15, 30, 60, 120, 300],
        )
        self.time_to_remediation_seconds = Histogram(
            "hemostat_time_to_remediation_seconds",
            "Time from detection to remediation completion",
            buckets=[5, 10, 15, 30, 60, 120, 300, 600],
        )

        self.logger.info(f"Metrics Exporter initialized on port {self.metrics_port}")

    def run(self) -> None:
        """
        Main metrics exporter loop.

        Starts HTTP server for Prometheus scraping and subscribes to HemoStat events.
        """
        self._running = True

        # Start Prometheus HTTP server
        try:
            start_http_server(self.metrics_port)
            self.logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
            self.logger.info(f"Metrics endpoint: http://localhost:{self.metrics_port}/metrics")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}", exc_info=True)
            return

        # Subscribe to all HemoStat channels
        self.subscribe_to_channel("hemostat:health_alert", self._handle_health_alert)
        self.subscribe_to_channel("hemostat:events:analysis", self._handle_analysis_result)
        self.subscribe_to_channel("hemostat:events:remediation", self._handle_remediation_event)
        self.subscribe_to_channel("hemostat:events:alert", self._handle_alert_event)

        self.logger.info("Metrics exporter started, listening for events...")

        # Track agent uptime
        start_time = time.time()

        try:
            while self._running:
                # Update uptime metric
                uptime = time.time() - start_time
                self.agent_uptime_seconds.labels(agent_name="metrics").set(uptime)

                # Process messages from Redis pub/sub
                message = self.pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    # Message already handled by registered callback
                    pass

                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Metrics exporter interrupted by user")
        finally:
            self.stop()

    def _handle_health_alert(self, message: dict[str, Any]) -> None:
        """
        Handle health alert events from Monitor agent.

        Args:
            message: Health alert message payload
        """
        try:
            data = message.get("data", {})
            container_id = data.get("container_id", "unknown")
            container_name = data.get("container_name", "unknown")
            metrics = data.get("metrics", {})
            anomalies = data.get("anomalies", [])

            # Update container metrics
            if metrics:
                cpu = metrics.get("cpu_percent", 0)
                memory_pct = metrics.get("memory_percent", 0)
                memory_bytes = metrics.get("memory_usage", 0)

                self.container_cpu_usage.labels(
                    container_id=container_id, container_name=container_name
                ).set(cpu)
                self.container_memory_usage.labels(
                    container_id=container_id, container_name=container_name
                ).set(memory_pct)
                self.container_memory_bytes.labels(
                    container_id=container_id, container_name=container_name
                ).set(memory_bytes)

            # Track anomalies
            for anomaly in anomalies:
                anomaly_type = anomaly.get("type", "unknown")
                severity = anomaly.get("severity", "unknown")

                self.anomalies_detected.labels(
                    container_name=container_name, anomaly_type=anomaly_type
                ).inc()
                self.health_alerts_total.labels(
                    container_name=container_name, severity=severity
                ).inc()

            self.logger.debug(
                f"Processed health alert for {container_name}: {len(anomalies)} anomalies"
            )
        except Exception as e:
            self.logger.error(f"Error processing health alert: {e}", exc_info=False)

    def _handle_analysis_result(self, message: dict[str, Any]) -> None:
        """
        Handle analysis result events from Analyzer agent.

        Args:
            message: Analysis result message payload
        """
        try:
            data = message.get("data", {})
            result_type = data.get("result_type", "unknown")
            confidence = data.get("confidence", 0.0)
            duration = data.get("analysis_duration", 0.0)

            # Track analysis metrics
            self.analysis_requests_total.labels(result_type=result_type).inc()
            self.analysis_duration_seconds.observe(duration)
            self.analysis_confidence.labels(result_type=result_type).observe(confidence)

            self.logger.debug(
                f"Processed analysis result: {result_type}, confidence={confidence:.2f}"
            )
        except Exception as e:
            self.logger.error(f"Error processing analysis result: {e}", exc_info=False)

    def _handle_remediation_event(self, message: dict[str, Any]) -> None:
        """
        Handle remediation events from Responder agent.

        Args:
            message: Remediation event message payload
        """
        try:
            data = message.get("data", {})
            container_name = data.get("container_name", "unknown")
            action = data.get("action", "unknown")
            status = data.get("status", "unknown")
            duration = data.get("duration", 0.0)

            # Track remediation metrics
            self.remediation_attempts_total.labels(
                container_name=container_name, action=action, status=status
            ).inc()

            if duration > 0:
                self.remediation_duration_seconds.labels(action=action).observe(duration)

            self.logger.debug(
                f"Processed remediation event: {container_name}, action={action}, status={status}"
            )
        except Exception as e:
            self.logger.error(f"Error processing remediation event: {e}", exc_info=False)

    def _handle_alert_event(self, message: dict[str, Any]) -> None:
        """
        Handle alert events from Alert agent.

        Args:
            message: Alert event message payload
        """
        try:
            data = message.get("data", {})
            channel = data.get("channel", "unknown")
            status = data.get("status", "unknown")
            deduped = data.get("deduped", False)

            # Track alert metrics
            self.alerts_sent_total.labels(channel=channel, status=status).inc()

            if deduped:
                self.alerts_deduped_total.inc()

            self.logger.debug(f"Processed alert event: channel={channel}, status={status}")
        except Exception as e:
            self.logger.error(f"Error processing alert event: {e}", exc_info=False)

    def stop(self) -> None:
        """Stop the metrics exporter agent gracefully."""
        self._running = False
        self.logger.info("Metrics exporter stopped")

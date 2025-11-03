"""
HemoStat Monitor Agent

Continuously polls Docker containers to detect health issues, resource anomalies, and failures.
Publishes structured health alerts to Redis for consumption by the Analyzer Agent.
"""

import os
import time
from datetime import datetime, UTC
from typing import Any

import docker
from docker.errors import APIError, DockerException

from agents.agent_base import HemoStatAgent
from agents.platform_utils import get_docker_host


class ContainerMonitor(HemoStatAgent):
    """
    Monitor Agent for HemoStat.

    Polls Docker containers at regular intervals, collects metrics (CPU, memory, network, disk I/O),
    detects anomalies against configurable thresholds, and publishes health alerts to Redis.
    """

    def __init__(self):
        """
        Initialize the Container Monitor agent.

        Raises:
            DockerException: If Docker connection fails
            HemoStatConnectionError: If Redis connection fails
        """
        # Initialize base agent
        super().__init__(agent_name="monitor")

        # Initialize Docker client with platform-aware socket detection
        try:
            docker_host = os.getenv("DOCKER_HOST") or get_docker_host()
            self.docker_client = docker.from_env()
            self.logger.info(f"Docker client initialized successfully: {docker_host}")
            self.docker_available = True
        except DockerException as e:
            self.logger.warning(
                f"Docker client unavailable (running in Docker without socket mount): {e}. "
                f"Monitor will continue via Redis events only."
            )
            self.docker_client = None
            self.docker_available = False

        # Load configuration from environment
        self.poll_interval = int(os.getenv("AGENT_POLL_INTERVAL", 30))
        self.threshold_cpu = int(os.getenv("THRESHOLD_CPU_PERCENT", 85))
        self.threshold_memory = int(os.getenv("THRESHOLD_MEMORY_PERCENT", 80))

        self.logger.info(
            f"Monitor Agent initialized with thresholds: "
            f"CPU={self.threshold_cpu}%, Memory={self.threshold_memory}%"
        )

    def run(self) -> None:
        """
        Main monitoring loop that runs continuously until stopped.

        Polls containers at regular intervals and detects anomalies.
        """
        self._running = True
        self.logger.info("Starting monitor loop")

        try:
            while self._running:
                try:
                    self._poll_containers()
                except Exception as e:
                    self.logger.error(f"Error during container polling: {e}", exc_info=True)

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.logger.info("Monitor interrupted by user")
        finally:
            self.stop()

    def _poll_containers(self) -> None:
        """
        Fetch all containers (running and exited) and check their health status.

        Includes both running and exited containers to detect non-zero exit codes.
        Handles Docker API errors gracefully without breaking the loop.
        Skips polling if Docker is unavailable.
        """
        if not self.docker_available:
            return

        try:
            containers = self.docker_client.containers.list(
                all=True, filters={"status": ["running", "exited"]}
            )
            self.logger.debug(f"Polling {len(containers)} containers")

            for container in containers:
                try:
                    # Refresh container state to avoid stale status
                    container.reload()
                    self._check_container_health(container)
                except Exception as e:
                    self.logger.error(
                        f"Error checking container {container.short_id}: {e}", exc_info=False
                    )
        except APIError as e:
            self.logger.error(f"Docker API error during container listing: {e}")
        except DockerException as e:
            self.logger.error(f"Docker error during polling: {e}")

    def _check_container_health(self, container) -> None:
        """
        Check the health status of a single container.

        Collects metrics, detects anomalies, and publishes alerts if needed.

        Args:
            container: Docker container object
        """
        container_name = container.name

        try:
            # Collect container metadata
            stats = self._get_container_stats(container)
            if stats is None:
                return

            # Get health status
            health_info = self._check_health_status(container)

            # Detect anomalies
            anomalies = self._detect_anomalies(container, stats, health_info)

            # Store container state to Redis (for dashboard health grid)
            # This stores data for ALL containers, not just unhealthy ones
            container_id = container.short_id
            container_state = {
                "container_id": container_id,
                "container_name": container_name,
                "status": container.status,
                "cpu_percent": stats.get("cpu_percent", 0),
                "memory_percent": stats.get("memory_percent", 0),
                "memory_usage": stats.get("memory_usage", 0),
                "memory_limit": stats.get("memory_limit", 0),
                "health_status": health_info["health_status"],
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self.set_shared_state(f"container:{container_id}", container_state, ttl=300)

            # Publish alert if anomalies detected
            if anomalies:
                self._publish_health_alert(container, stats, anomalies, health_info)
            else:
                self.logger.debug(f"Container {container_name} is healthy")
        except Exception as e:
            self.logger.error(f"Error checking health of {container_name}: {e}", exc_info=False)

    def _get_container_stats(self, container) -> dict[str, Any] | None:
        """
        Fetch container metrics using non-streaming stats call.

        Uses precpu_stats and cpu_stats for CPU calculation without maintaining open streams.
        This method retrieves a single snapshot of container statistics and calculates
        CPU percentage using Docker's official formula with precpu_stats to avoid
        connection leaks from streaming calls.

        Args:
            container: Docker container object to fetch stats for

        Returns:
            Dictionary with keys: cpu_percent, memory_percent, memory_usage, memory_limit,
            network_rx_bytes, network_tx_bytes, blkio_read_bytes, blkio_write_bytes.
            Returns None if stats retrieval fails.
        """
        try:
            # Use non-streaming call to get stats with precpu_stats for CPU calculation
            stats = container.stats(stream=False)

            # Calculate CPU percentage using Docker's formula with precpu_stats
            cpu_percent = self._calculate_cpu_percent(stats)

            # Calculate memory percentage
            memory_stats = stats.get("memory_stats", {})
            memory_percent = self._calculate_memory_percent(memory_stats)

            # Extract network I/O stats
            networks = stats.get("networks") or {}
            network_rx_bytes = 0
            network_tx_bytes = 0
            for net_data in networks.values() if networks else []:
                network_rx_bytes += net_data.get("rx_bytes", 0)
                network_tx_bytes += net_data.get("tx_bytes", 0)

            # Extract block I/O stats
            blkio_stats = stats.get("blkio_stats") or {}
            blkio_read_bytes = 0
            blkio_write_bytes = 0
            for stat in (blkio_stats.get("io_service_bytes_recursive") or []):
                if stat.get("op") == "Read":
                    blkio_read_bytes += stat.get("value", 0)
                elif stat.get("op") == "Write":
                    blkio_write_bytes += stat.get("value", 0)

            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_usage": memory_stats.get("usage", 0),
                "memory_limit": memory_stats.get("limit", 0),
                "network_rx_bytes": network_rx_bytes,
                "network_tx_bytes": network_tx_bytes,
                "blkio_read_bytes": blkio_read_bytes,
                "blkio_write_bytes": blkio_write_bytes,
            }

            return metrics
        except Exception as e:
            self.logger.error(f"Error getting stats for {container.name}: {e}")
            return None

    def _check_health_status(self, container) -> dict[str, Any]:
        """
        Extract health status, exit code, and restart count from container.

        Returns:
            Dictionary with health_status, exit_code, and restart_count
        """
        try:
            attrs = container.attrs
            state = attrs.get("State", {})

            # Get health status
            health = state.get("Health", {})
            health_status = health.get("Status", "unknown")

            # Get exit code
            exit_code = state.get("ExitCode", 0)

            # Get restart count
            restart_count = attrs.get("RestartCount", 0)

            return {
                "health_status": health_status,
                "exit_code": exit_code,
                "restart_count": restart_count,
            }
        except Exception as e:
            self.logger.error(f"Error checking health status: {e}")
            return {
                "health_status": "unknown",
                "exit_code": 0,
                "restart_count": 0,
            }

    def _detect_anomalies(
        self, container, stats: dict[str, Any], health_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies in container metrics against configured thresholds.

        Severity levels:
        - critical: metric > 95% or immediate action required
        - high: metric > threshold
        - medium: metric > 80% of threshold

        Args:
            container: Docker container object
            stats: Container metrics dictionary
            health_info: Health status information

        Returns:
            List of detected anomalies with type, severity, and details
        """
        anomalies = []

        # CPU anomaly with granular severity
        cpu_percent = stats["cpu_percent"]
        if cpu_percent > self.threshold_cpu:
            severity = "critical" if cpu_percent > 95 else "high"
            anomalies.append(
                {
                    "type": "high_cpu",
                    "severity": severity,
                    "threshold": self.threshold_cpu,
                    "actual": round(cpu_percent, 2),
                }
            )
        elif cpu_percent > 0.8 * self.threshold_cpu:
            anomalies.append(
                {
                    "type": "high_cpu",
                    "severity": "medium",
                    "threshold": self.threshold_cpu,
                    "actual": round(cpu_percent, 2),
                }
            )

        # Memory anomaly with granular severity
        memory_percent = stats["memory_percent"]
        if memory_percent > self.threshold_memory:
            severity = "critical" if memory_percent > 95 else "high"
            anomalies.append(
                {
                    "type": "high_memory",
                    "severity": severity,
                    "threshold": self.threshold_memory,
                    "actual": round(memory_percent, 2),
                }
            )
        elif memory_percent > 0.8 * self.threshold_memory:
            anomalies.append(
                {
                    "type": "high_memory",
                    "severity": "medium",
                    "threshold": self.threshold_memory,
                    "actual": round(memory_percent, 2),
                }
            )

        # Health status anomaly
        if health_info["health_status"] not in ["healthy", "unknown"]:
            anomalies.append(
                {
                    "type": "unhealthy_status",
                    "severity": "high",
                    "status": health_info["health_status"],
                }
            )

        # Exit code anomaly (for stopped containers)
        if health_info["exit_code"] != 0 and container.status == "exited":
            anomalies.append(
                {
                    "type": "non_zero_exit",
                    "severity": "high",
                    "exit_code": health_info["exit_code"],
                }
            )

        # Excessive restarts
        if health_info["restart_count"] > 5:
            anomalies.append(
                {
                    "type": "excessive_restarts",
                    "severity": "medium",
                    "restart_count": health_info["restart_count"],
                }
            )

        return anomalies

    def _publish_health_alert(
        self,
        container,
        stats: dict[str, Any],
        anomalies: list[dict[str, Any]],
        health_info: dict[str, Any],
    ) -> None:
        """
        Publish a health alert to Redis for consumption by the Analyzer Agent.

        Args:
            container: Docker container object
            stats: Container metrics
            anomalies: List of detected anomalies
            health_info: Health status information
        """
        try:
            container_id = container.short_id
            container_name = container.name

            # Build event payload
            payload = {
                "container_id": container_id,
                "container_name": container_name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "metrics": stats,
                "anomalies": anomalies,
                "health_status": health_info["health_status"],
                "exit_code": health_info["exit_code"],
                "restart_count": health_info["restart_count"],
            }

            # Publish event
            self.publish_event("hemostat:health_alert", "container_unhealthy", payload)

            # Update shared state with TTL
            self.set_shared_state(f"container:{container_id}", stats, ttl=300)

            self.logger.warning(
                f"Health alert published for {container_name}: {len(anomalies)} anomalies detected"
            )
        except Exception as e:
            self.logger.error(f"Error publishing health alert: {e}", exc_info=False)

    def _calculate_cpu_percent(self, stats: dict[str, Any]) -> float:
        """
        Calculate CPU percentage using Docker's official formula.

        Formula: (delta_cpu / delta_system) x online_cpus x 100

        Uses precpu_stats and cpu_stats from a single stats snapshot.
        Allows CPU percent > 100% on multi-core systems.

        Args:
            stats: Container stats dictionary with cpu_stats and precpu_stats

        Returns:
            CPU percentage as float (0.0 if calculation fails, can exceed 100% on multi-core)
        """
        try:
            # Extract current and previous CPU values
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            precpu_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)

            system_usage = cpu_stats.get("system_cpu_usage", 0)
            presystem_usage = precpu_stats.get("system_cpu_usage", 0)

            online_cpus = cpu_stats.get("online_cpus", 1)

            # Calculate deltas
            cpu_delta = cpu_usage - precpu_usage
            system_delta = system_usage - presystem_usage

            # Avoid division by zero
            if system_delta == 0:
                return 0.0

            # Apply Docker formula
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

            # Return without upper clamp to allow >100% on multi-core systems
            return max(0.0, cpu_percent)
        except Exception as e:
            self.logger.debug(f"Error calculating CPU percent: {e}")
            return 0.0

    def _calculate_memory_percent(self, mem_stats: dict[str, Any]) -> float:
        """
        Calculate memory percentage, excluding cache (matches docker stats behavior).

        Args:
            mem_stats: Memory stats from container stats

        Returns:
            Memory percentage as float (0.0 if calculation fails)
        """
        try:
            usage = mem_stats.get("usage", 0)
            limit = mem_stats.get("limit", 0)

            # Subtract cache (handle both cgroup v1 and v2)
            stats = mem_stats.get("stats", {})
            cache = stats.get("inactive_file", 0) or stats.get("total_inactive_file", 0)

            actual_usage = usage - cache

            # Avoid division by zero
            if limit == 0:
                return 0.0

            memory_percent = (actual_usage / limit) * 100.0

            return max(0.0, min(memory_percent, 100.0))  # Clamp to 0-100
        except Exception as e:
            self.logger.debug(f"Error calculating memory percent: {e}")
            return 0.0

    def stop(self) -> None:
        """Stop the monitor agent gracefully."""
        self._running = False
        self.logger.info("Monitor agent stopped")

"""
HemoStat Responder Agent - Safe Container Remediation

Executes remediation actions recommended by the Analyzer Agent with comprehensive
safety constraints including cooldown periods, circuit breakers, and audit logging.
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import docker
from docker.errors import APIError, DockerException, NotFound

from agents.agent_base import HemoStatAgent
from agents.platform_utils import get_docker_host


class ContainerResponder(HemoStatAgent):
    """
    Executes safe container remediation with multi-layered safety mechanisms.

    Subscribes to hemostat:remediation_needed channel and executes Docker operations
    (restart, scale, cleanup, exec) while enforcing cooldown periods, circuit breakers,
    and maintaining comprehensive audit logs.
    """

    def __init__(self):
        """
        Initialize the Responder Agent.

        Connects to Docker daemon with retry logic, loads safety configuration from
        environment variables, and subscribes to remediation_needed channel.

        Raises:
            HemoStatConnectionError: If Redis connection fails
        """
        super().__init__(agent_name="responder")

        # Initialize Docker client with exponential backoff retry logic
        try:
            self.docker_client = self._connect_docker()
            self.docker_available = True
        except DockerException as e:
            self.logger.warning(
                f"Docker client unavailable (running in Docker without socket mount): {e}. "
                f"Responder will continue via Redis events only."
            )
            self.docker_client = None
            self.docker_available = False

        # Load safety configuration from environment
        self.cooldown_seconds = int(os.getenv("RESPONDER_COOLDOWN_SECONDS", "3600"))
        self.max_retries_per_hour = int(os.getenv("RESPONDER_MAX_RETRIES_PER_HOUR", "3"))
        self.dry_run = os.getenv("RESPONDER_DRY_RUN", "false").lower() == "true"
        self.enforce_exec_allowlist = (
            os.getenv("RESPONDER_ENFORCE_EXEC_ALLOWLIST", "false").lower() == "true"
        )

        # Subscribe to remediation channel
        self.subscribe_to_channel("hemostat:remediation_needed", self._handle_remediation_request)

        self.logger.info(
            f"Responder Agent initialized - "
            f"cooldown={self.cooldown_seconds}s, "
            f"max_retries={self.max_retries_per_hour}/hour, "
            f"dry_run={self.dry_run}, "
            f"enforce_exec_allowlist={self.enforce_exec_allowlist}"
        )

    def _connect_docker(self) -> docker.DockerClient:
        """
        Connect to Docker daemon with exponential backoff retry logic.

        Uses platform-aware Docker socket detection. Automatically selects the
        appropriate socket path for Windows (npipe), Linux, or macOS (unix socket).

        Returns:
            Connected Docker client instance

        Raises:
            DockerException: If connection fails after configured attempts
        """
        max_retries = int(os.getenv("RESPONDER_RETRY_MAX", "3"))
        initial_delay = float(os.getenv("RESPONDER_RETRY_DELAY", "1"))
        docker_host = os.getenv("DOCKER_HOST") or get_docker_host()

        retry_delays = [initial_delay * (2**i) for i in range(max_retries)]
        last_error: DockerException | None = None

        for attempt in range(max_retries):
            try:
                client = docker.from_env()
                self.logger.info(f"Docker client initialized: {docker_host}")
                return client
            except DockerException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    self.logger.warning(
                        f"Failed to connect to Docker (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e!s}"
                    )
                    time.sleep(wait_time)

        # All retries exhausted - raise the error
        msg = f"Failed to connect to Docker after {max_retries} attempts. Last error: {last_error!s}"
        raise DockerException(msg) from last_error

    def run(self) -> None:
        """
        Start the message listening loop.

        Blocks until stop() is called. Listens for remediation requests on
        hemostat:remediation_needed channel and processes them.
        """
        try:
            self.logger.info("Starting Responder Agent listening loop")
            self.start_listening()
        except Exception as e:
            self.logger.error(f"Error in listening loop: {e}", exc_info=True)
            raise

    def _handle_remediation_request(self, message: dict[str, Any]) -> None:
        """
        Callback invoked when remediation request is received from Analyzer Agent.

        Args:
            message: Full message wrapper with event_type, timestamp, agent, data
        """
        try:
            # Extract request payload from message wrapper
            request_data = message.get("data", {})
            self.logger.info(f"Received remediation request: {json.dumps(request_data)}")
            self._execute_remediation(request_data)
        except Exception as e:
            self.logger.error(f"Error handling remediation request: {e}", exc_info=True)

    def _execute_remediation(self, request_data: dict[str, Any]) -> None:
        """
        Main remediation orchestration method.

        Performs safety checks (cooldown, circuit breaker) and routes to appropriate
        action handler. Updates state and publishes completion event.

        Args:
            request_data: Remediation request with container, action, and metadata
        """
        container = request_data.get("container")
        action = request_data.get("action")

        if not container or not action:
            self.logger.error("Invalid remediation request: missing container or action")
            return

        # Safety Check 1: Cooldown period
        if not self._check_cooldown(container):
            remaining = self._get_cooldown_remaining(container)
            self.logger.info(f"Cooldown active for {container}: {remaining}s remaining")
            self._publish_cooldown_active(container, action, remaining)
            self._log_audit_trail(
                container,
                action,
                {"status": "rejected", "reason": "cooldown_active"},
                request_data,
            )
            return

        # Safety Check 2: Circuit breaker
        if not self._check_circuit_breaker(container):
            cb_state = self.get_shared_state(f"circuit_breaker:{container}") or {}
            retry_count = cb_state.get("retry_count", 0)
            self.logger.warning(f"Circuit breaker open for {container}: {retry_count} retries")
            self._publish_circuit_breaker_active(container, action, retry_count)
            self._log_audit_trail(
                container,
                action,
                {"status": "rejected", "reason": "circuit_breaker_open"},
                request_data,
            )
            return

        # Safety Check 3: Dry-run mode
        if self.dry_run:
            self._dry_run_action(container, action, request_data)
            return

        # Route to appropriate action handler
        result = None
        try:
            if action == "restart":
                result = self._restart_container(container)
            elif action == "scale_up":
                result = self._scale_container(container)
            elif action == "cleanup":
                result = self._cleanup_container(container)
            elif action == "exec":
                command = request_data.get("command")
                result = self._exec_container(container, command)
            else:
                result = {"status": "failed", "error": f"Unknown action: {action}"}
                self.logger.error(f"Unknown remediation action: {action}")
        except Exception as e:
            result = {"status": "failed", "error": str(e)}
            self.logger.error(f"Error executing {action} on {container}: {e}", exc_info=True)

        # Update state based on result (treat not_applicable as non-failure)
        success = result.get("status") in ("success", "not_applicable")
        if result.get("status") != "not_applicable":
            self._update_remediation_history(container, action, result)
            self._update_circuit_breaker(container, success)
        else:
            # Log not_applicable but don't trigger cooldown or circuit breaker
            self.logger.info(f"Action {action} not applicable for {container}")

        # Publish completion event
        self._publish_remediation_complete(request_data, result)

        # Log audit trail
        self._log_audit_trail(container, action, result, request_data)

    def _check_cooldown(self, container: str) -> bool:
        """
        Check if cooldown period has elapsed since last remediation action.

        Args:
            container: Container name

        Returns:
            True if cooldown expired or no previous action, False if within cooldown
        """
        history = self.get_shared_state(f"remediation_history:{container}")

        if not history:
            self.logger.debug(f"No remediation history for {container}")
            return True

        last_timestamp = history.get("last_action_timestamp")
        if not last_timestamp:
            return True

        try:
            last_time = datetime.fromisoformat(last_timestamp)
            elapsed = (datetime.now(UTC) - last_time).total_seconds()

            if elapsed < self.cooldown_seconds:
                self.logger.debug(
                    f"Cooldown active for {container}: {elapsed}s elapsed, "
                    f"{self.cooldown_seconds}s required"
                )
                return False

            self.logger.debug(f"Cooldown expired for {container}: {elapsed}s elapsed")
            return True
        except Exception as e:
            self.logger.error(f"Error checking cooldown for {container}: {e}")
            return True

    def _get_cooldown_remaining(self, container: str) -> int:
        """
        Get remaining cooldown time in seconds.

        Calculates how many seconds remain in the cooldown period for a container.

        Args:
            container: Container name

        Returns:
            Remaining cooldown time in seconds (0 if no cooldown active)
        """
        history = self.get_shared_state(f"remediation_history:{container}") or {}
        last_timestamp = history.get("last_action_timestamp")

        if not last_timestamp:
            return 0

        try:
            last_time = datetime.fromisoformat(last_timestamp)
            elapsed = (datetime.now(UTC) - last_time).total_seconds()
            remaining = max(0, int(self.cooldown_seconds - elapsed))
            return remaining
        except Exception:
            return 0

    def _check_circuit_breaker(self, container: str) -> bool:
        """
        Check if circuit breaker is open (max retries exceeded).

        Args:
            container: Container name

        Returns:
            True if circuit closed (safe to proceed), False if circuit open
        """
        cb_state = self.get_shared_state(f"circuit_breaker:{container}")

        if not cb_state:
            self.logger.debug(f"No circuit breaker state for {container}")
            return True

        # Check if hour window has elapsed (reset circuit)
        opened_timestamp = cb_state.get("opened_timestamp")
        if opened_timestamp:
            try:
                opened_time = datetime.fromisoformat(opened_timestamp)
                elapsed = (datetime.now(UTC) - opened_time).total_seconds()

                if elapsed >= 3600:  # 1 hour
                    self.logger.info(f"Circuit breaker hour window elapsed for {container}")
                    return True
            except Exception as e:
                self.logger.error(f"Error checking circuit breaker window: {e}")

        # Check if circuit is open
        is_open = cb_state.get("is_open", False)
        if is_open:
            self.logger.warning(
                f"Circuit breaker open for {container}: {cb_state.get('retry_count', 0)} retries"
            )
            return False

        self.logger.debug(f"Circuit breaker closed for {container}")
        return True

    def _restart_container(self, container: str) -> dict[str, Any]:
        """
        Restart a container gracefully.

        Args:
            container: Container name or ID

        Returns:
            Result dict with status and details
        """
        try:
            self.logger.warning(f"Restarting container: {container}")

            container_obj = self.docker_client.containers.get(container)
            container_obj.restart(timeout=10)

            # Wait for container to reach running state
            max_wait = 30
            start_time = time.time()
            while time.time() - start_time < max_wait:
                container_obj.reload()
                if container_obj.status == "running":
                    self.logger.warning(f"Container restarted successfully: {container}")
                    return {
                        "status": "success",
                        "action": "restart",
                        "container": container,
                        "details": "Container restarted and running",
                    }
                time.sleep(1)

            # Timeout waiting for running state
            return {
                "status": "failed",
                "error": f"Container did not reach running state within {max_wait}s",
            }
        except NotFound:
            error_msg = f"Container not found: {container}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}
        except APIError as e:
            error_msg = f"Docker API error restarting {container}: {e}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

    def _scale_container(self, container: str) -> dict[str, Any]:
        """
        Scale container replicas (Docker Swarm services).

        Args:
            container: Container or service name

        Returns:
            Result dict with status and details
        """
        try:
            self.logger.info(f"Scaling container: {container}")

            # Get container to check for Swarm service labels
            try:
                container_obj = self.docker_client.containers.get(container)
                labels = container_obj.labels or {}
            except NotFound:
                error_msg = f"Container not found: {container}"
                self.logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            # Check if container is part of a Swarm service
            service_name = labels.get("com.docker.swarm.service.name")
            if not service_name:
                self.logger.warning(
                    f"Scale operation not applicable for standalone containers. "
                    f"Container {container} is not part of a Docker Swarm service."
                )
                return {
                    "status": "not_applicable",
                    "action": "scale_up",
                    "container": container,
                    "details": "Scale operation not applicable - requires Docker Swarm service",
                }

            # Find and scale the Swarm service
            services = self.docker_client.services.list(filters={"name": service_name})
            if not services:
                self.logger.warning(f"Swarm service not found: {service_name}")
                return {
                    "status": "not_applicable",
                    "action": "scale_up",
                    "container": container,
                    "details": f"Swarm service {service_name} not found",
                }

            service = services[0]
            current_spec = service.attrs.get("Spec", {})
            current_mode = current_spec.get("Mode", {})
            current_replicas = current_mode.get("Replicated", {}).get("Replicas", 1)
            new_replicas = current_replicas + 1

            # Update service replicas
            current_mode["Replicated"] = {"Replicas": new_replicas}
            current_spec["Mode"] = current_mode
            service.update(mode=current_mode)

            self.logger.warning(
                f"Scaled service {service_name} from {current_replicas} to {new_replicas} replicas"
            )

            return {
                "status": "success",
                "action": "scale_up",
                "container": container,
                "details": {
                    "service": service_name,
                    "previous_replicas": current_replicas,
                    "new_replicas": new_replicas,
                },
            }
        except APIError as e:
            error_msg = f"Docker API error scaling {container}: {e}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

    def _cleanup_container(self, container: str) -> dict[str, Any]:
        """
        Clean up stopped containers and prune unused resources strictly scoped to target container.

        Args:
            container: Container name or ID (used for filtering)

        Returns:
            Result dict with cleanup statistics
        """
        try:
            self.logger.info(f"Cleaning up resources for container: {container}")

            # Get target container info for scoped cleanup
            try:
                target_container = self.docker_client.containers.get(container)
                image_id = target_container.image.id
                labels = target_container.labels or {}
            except NotFound:
                error_msg = f"Container not found: {container}"
                self.logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            cleanup_stats: dict[str, int | list[str]] = {
                "containers_removed": 0,
                "volumes_removed": 0,
                "space_reclaimed_bytes": 0,
                "notes": [],
            }

            # Build container filters combining constraints
            filters = {"status": ["exited"]}
            compose_project = labels.get("com.docker.compose.project")
            compose_service = labels.get("com.docker.compose.service")

            if compose_project:
                # Build label filters for Compose project and optionally service
                label_filters = [f"com.docker.compose.project={compose_project}"]
                if compose_service:
                    label_filters.append(f"com.docker.compose.service={compose_service}")
                filters["label"] = label_filters
                self.logger.debug(
                    f"Using Compose filters: project={compose_project}, service={compose_service}"
                )
            else:
                # Filter by ancestor image to match containers from same image
                filters["ancestor"] = [image_id]
                self.logger.debug(f"Using image filter: ancestor={image_id}")

            # List and remove scoped stopped containers
            stopped_containers = self.docker_client.containers.list(all=True, filters=filters)
            removed_container_ids = []

            for stopped_container in stopped_containers:
                try:
                    # Double-check status before removal
                    stopped_container.reload()
                    if stopped_container.status == "running":
                        self.logger.warning(f"Skipping running container: {stopped_container.name}")
                        continue

                    self.logger.info(f"Removing stopped container: {stopped_container.name}")
                    stopped_container.remove(v=True)  # Remove with volumes
                    if isinstance(cleanup_stats["containers_removed"], int):
                        cleanup_stats["containers_removed"] += 1
                    removed_container_ids.append(stopped_container.id)
                except APIError as e:
                    self.logger.warning(f"Failed to remove container {stopped_container.name}: {e}")

            # Prune volumes strictly scoped
            try:
                volumes_removed_count = 0
                space_reclaimed = 0

                if compose_project:
                    # Prune volumes with Compose project label filter
                    volume_filters = {"label": [f"com.docker.compose.project={compose_project}"]}
                    if compose_service:
                        volume_filters["label"].append(
                            f"com.docker.compose.service={compose_service}"
                        )

                    self.logger.debug(f"Pruning volumes with filters: {volume_filters}")
                    volumes_result = self.docker_client.volumes.prune(filters=volume_filters)
                    volumes_removed_count = len(volumes_result.get("VolumesDeleted", []))
                    space_reclaimed = volumes_result.get("SpaceReclaimed", 0)
                    self.logger.info(f"Pruned {volumes_removed_count} Compose-scoped volumes")
                else:
                    # No Compose labels: enumerate dangling volumes and match to removed containers
                    if removed_container_ids:
                        dangling_volumes = self.docker_client.volumes.list(
                            filters={"dangling": True}
                        )
                        for vol in dangling_volumes:
                            try:
                                # Check if volume is referenced by removed containers or has matching labels
                                vol_labels = vol.attrs.get("Labels", {})
                                if vol_labels.get("com.docker.compose.project") or any(
                                    cid in str(vol.attrs) for cid in removed_container_ids
                                ):
                                    self.logger.info(f"Removing dangling volume: {vol.name}")
                                    vol.remove()
                                    volumes_removed_count += 1
                            except APIError as e:
                                self.logger.warning(f"Failed to remove volume {vol.name}: {e}")
                    else:
                        if isinstance(cleanup_stats["notes"], list):
                            cleanup_stats["notes"].append(
                                "No containers removed; skipping volume pruning"
                            )
                        self.logger.info("No containers removed; skipping volume pruning")

                if isinstance(cleanup_stats["volumes_removed"], int):
                    cleanup_stats["volumes_removed"] = volumes_removed_count
                if isinstance(cleanup_stats["space_reclaimed_bytes"], int):
                    cleanup_stats["space_reclaimed_bytes"] = space_reclaimed
            except APIError as e:
                self.logger.warning(f"Failed to prune volumes: {e}")
                if isinstance(cleanup_stats["notes"], list):
                    cleanup_stats["notes"].append(f"Volume pruning failed: {e}")

            self.logger.info(
                f"Cleanup complete: {cleanup_stats['containers_removed']} containers removed, "
                f"{cleanup_stats['volumes_removed']} volumes removed, "
                f"{cleanup_stats['space_reclaimed_bytes']} bytes reclaimed"
            )

            return {
                "status": "success",
                "action": "cleanup",
                "container": container,
                "details": cleanup_stats,
            }
        except APIError as e:
            error_msg = f"Docker API error during cleanup: {e}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

    def _exec_container(self, container: str, command: str | None) -> dict[str, Any]:
        """
        Execute diagnostic command inside container.

        Args:
            container: Container name or ID
            command: Command to execute (default: ps aux)

        Returns:
            Result dict with command output and exit code
        """
        try:
            if not command:
                command = "ps aux"

            self.logger.info(f"Executing command in {container}: {command}")

            # Security: Validate command against whitelist of safe diagnostic commands
            safe_commands = [
                "ps aux",
                "ps",
                "top",
                "df",
                "free",
                "netstat",
                "ss",
                "env",
                "pwd",
                "whoami",
                "date",
                "uptime",
                "uname",
            ]

            command_allowed = any(command.startswith(safe_cmd) for safe_cmd in safe_commands)

            if not command_allowed:
                if self.enforce_exec_allowlist:
                    error_msg = f"Command not in allowlist (enforce_exec_allowlist=true): {command}"
                    self.logger.error(error_msg)
                    return {"status": "rejected", "error": error_msg}
                else:
                    self.logger.warning(f"Command not in whitelist, executing anyway: {command}")

            container_obj = self.docker_client.containers.get(container)

            # Check if container is running
            container_obj.reload()
            if container_obj.status != "running":
                error_msg = f"Container not running: {container} (status: {container_obj.status})"
                self.logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            # Execute command
            exit_code, output = container_obj.exec_run(command)

            # Decode output if bytes
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")

            self.logger.info(f"Command executed in {container}: exit_code={exit_code}")

            return {
                "status": "success",
                "action": "exec",
                "container": container,
                "command": command,
                "exit_code": exit_code,
                "output": output[:1000],  # Limit output to 1000 chars
            }
        except NotFound:
            error_msg = f"Container not found: {container}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}
        except APIError as e:
            error_msg = f"Docker API error executing command: {e}"
            self.logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

    def _dry_run_action(self, container: str, action: str, request_data: dict[str, Any]) -> None:
        """
        Simulate remediation action without executing.

        Args:
            container: Container name
            action: Remediation action
            request_data: Original request data
        """
        self.logger.info(f"DRY RUN: Would execute {action} on {container}")

        # Simulate operation time
        time.sleep(0.5)

        result = {
            "status": "success",
            "action": action,
            "container": container,
            "details": f"Dry-run simulation of {action}",
        }

        # Publish success event with dry_run flag
        self._publish_remediation_complete(request_data, result, dry_run=True)

        # Log audit trail
        self._log_audit_trail(container, action, result, request_data, dry_run=True)

    def _update_remediation_history(
        self, container: str, action: str, result: dict[str, Any]
    ) -> None:
        """
        Update remediation history in Redis.

        Args:
            container: Container name
            action: Remediation action
            result: Action result
        """
        try:
            history = self.get_shared_state(f"remediation_history:{container}") or {}

            # Update last action timestamp
            history["last_action_timestamp"] = datetime.now(UTC).isoformat()
            history["last_action"] = action
            history["last_result_status"] = result.get("status")

            # Update retry count (increment if within same hour, reset if new hour)
            if result.get("status") == "success":
                history["retry_count"] = 0
            else:
                last_retry_hour = history.get("last_retry_hour")
                current_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

                if last_retry_hour:
                    try:
                        last_hour = datetime.fromisoformat(last_retry_hour)
                        if last_hour == current_hour:
                            history["retry_count"] = history.get("retry_count", 0) + 1
                        else:
                            history["retry_count"] = 1
                    except Exception:
                        history["retry_count"] = 1
                else:
                    history["retry_count"] = 1

                history["last_retry_hour"] = current_hour.isoformat()

            self.set_shared_state(
                f"remediation_history:{container}",
                history,
                ttl=7200,  # 2 hours
            )

            self.logger.debug(f"Updated remediation history for {container}")
        except Exception as e:
            self.logger.error(f"Error updating remediation history: {e}")

    def _update_circuit_breaker(self, container: str, success: bool) -> None:
        """
        Update circuit breaker state in Redis with rolling 1-hour window.

        Args:
            container: Container name
            success: Whether remediation was successful
        """
        try:
            cb_state = self.get_shared_state(f"circuit_breaker:{container}") or {}
            current_time = datetime.now(UTC)

            # Check if 1-hour window has elapsed and reset if needed
            opened_timestamp_str = cb_state.get("opened_timestamp")
            if opened_timestamp_str:
                try:
                    opened_time = datetime.fromisoformat(opened_timestamp_str)
                    elapsed = (current_time - opened_time).total_seconds()
                    if elapsed >= 3600:  # 1 hour
                        # Reset circuit breaker after 1-hour window
                        cb_state["is_open"] = False
                        cb_state["failure_count"] = 0
                        cb_state["retry_count"] = 0
                        cb_state["opened_timestamp"] = None
                        self.logger.info(
                            f"Circuit breaker window elapsed for {container}, resetting"
                        )
                except Exception as e:
                    self.logger.error(f"Error checking circuit breaker window: {e}")

            if success:
                # Reset on success
                cb_state["is_open"] = False
                cb_state["retry_count"] = 0
                cb_state["failure_count"] = 0
                self.logger.debug(f"Circuit breaker closed for {container}")
            else:
                # Increment failure count
                failure_count = cb_state.get("failure_count", 0) + 1
                cb_state["failure_count"] = failure_count

                # Check if we should open circuit
                if failure_count >= self.max_retries_per_hour:
                    cb_state["is_open"] = True
                    cb_state["opened_timestamp"] = current_time.isoformat()
                    self.logger.warning(
                        f"Circuit breaker opened for {container}: {failure_count} failures"
                    )
                else:
                    cb_state["retry_count"] = failure_count

            self.set_shared_state(
                f"circuit_breaker:{container}",
                cb_state,
                ttl=7200,  # 2 hours
            )
        except Exception as e:
            self.logger.error(f"Error updating circuit breaker: {e}")

    def _publish_remediation_complete(
        self,
        request_data: dict[str, Any],
        result: dict[str, Any],
        dry_run: bool = False,
    ) -> None:
        """
        Publish remediation completion event.

        Args:
            request_data: Original remediation request
            result: Action result
            dry_run: Whether this was a dry-run
        """
        try:
            # Build data without event_type or timestamp
            data = {
                "container": request_data.get("container"),
                "action": request_data.get("action"),
                "result": result,
                "dry_run": dry_run,
                "reason": request_data.get("reason"),
                "confidence": request_data.get("confidence"),
            }

            self.publish_event("hemostat:remediation_complete", "remediation_complete", data)

            if result.get("status") == "success":
                self.logger.info(
                    f"Published remediation_complete: {data['container']} - {result.get('status')}"
                )
            else:
                self.logger.error(
                    f"Published remediation_complete: {data['container']} - {result.get('status')}"
                )
        except Exception as e:
            self.logger.error(f"Error publishing remediation_complete: {e}")

    def _log_audit_trail(
        self,
        container: str,
        action: str,
        result: dict[str, Any],
        request_data: dict[str, Any],
        dry_run: bool = False,
    ) -> None:
        """
        Log comprehensive audit trail to Redis.

        Args:
            container: Container name
            action: Remediation action
            result: Action result
            request_data: Original request data
            dry_run: Whether this was a dry-run
        """
        try:
            audit_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "container": container,
                "action": action,
                "result_status": result.get("status"),
                "error": result.get("error"),
                "confidence": request_data.get("confidence"),
                "reason": request_data.get("reason"),
                "metrics": request_data.get("metrics"),
                "dry_run": dry_run,
            }

            # Store in Redis list (LPUSH for newest first)
            audit_key = f"hemostat:audit:{container}"
            self.redis.lpush(audit_key, json.dumps(audit_entry))

            # Keep only last 100 entries
            self.redis.ltrim(audit_key, 0, 99)

            # Set TTL (7 days)
            self.redis.expire(audit_key, 604800)

            self.logger.debug(f"Logged audit trail for {container}")
        except Exception as e:
            self.logger.error(f"Error logging audit trail: {e}")

    def _publish_cooldown_active(self, container: str, action: str, remaining_seconds: int) -> None:
        """
        Publish cooldown active event.

        Args:
            container: Container name
            action: Original remediation action
            remaining_seconds: Seconds remaining in cooldown
        """
        try:
            # Structure rejection events with result object
            data = {
                "container": container,
                "action": action,
                "result": {
                    "status": "rejected",
                    "reason": "cooldown_active",
                    "remaining_seconds": remaining_seconds,
                },
            }

            self.publish_event("hemostat:remediation_complete", "remediation_complete", data)
            self.logger.info(f"Cooldown active for {container}: {remaining_seconds}s remaining")
        except Exception as e:
            self.logger.error(f"Error publishing cooldown_active: {e}")

    def _publish_circuit_breaker_active(
        self, container: str, action: str, retry_count: int
    ) -> None:
        """
        Publish circuit breaker open event.

        Args:
            container: Container name
            action: Original remediation action
            retry_count: Current retry count
        """
        try:
            # Structure rejection events with result object
            data = {
                "container": container,
                "action": action,
                "result": {
                    "status": "rejected",
                    "reason": "circuit_breaker_open",
                    "retry_count": retry_count,
                },
            }

            self.publish_event("hemostat:remediation_complete", "remediation_complete", data)
            self.logger.warning(f"Circuit breaker open for {container}: {retry_count} retries")
        except Exception as e:
            self.logger.error(f"Error publishing circuit_breaker_active: {e}")

"""
HemoStat Analyzer Agent - Core Implementation

Performs AI-powered root cause analysis of container health issues using LangChain with
Claude/GPT-4, distinguishes real issues from false alarms, calculates confidence scores,
and publishes remediation recommendations or false alarm notifications.
"""

import json
import os
import re
import time
from typing import Any

from agents.agent_base import HemoStatAgent


class HealthAnalyzer(HemoStatAgent):
    """
    AI-powered health analyzer for container health issues.

    Inherits from HemoStatAgent and implements intelligent analysis of container health
    alerts using LangChain with Claude/GPT-4, with rule-based fallback for reliability.
    """

    def __init__(self):
        """
        Initialize the Health Analyzer.

        Loads configuration from environment variables, initializes LangChain LLM,
        and subscribes to health alert channel.

        Raises:
            HemoStatConnectionError: If Redis connection fails
        """
        super().__init__(agent_name="analyzer")

        # Load AI configuration
        self.ai_model = os.getenv("AI_MODEL", "gpt-4")
        # AI_FALLBACK_ENABLED: if true, use AI with fallback to rule-based; if false, force rule-based only
        self.ai_enabled = os.getenv("AI_FALLBACK_ENABLED", "true").lower() == "true"
        self.confidence_threshold = float(os.getenv("ANALYZER_CONFIDENCE_THRESHOLD", 0.7))
        self.history_size = int(os.getenv("ANALYZER_HISTORY_SIZE", 10))
        self.history_ttl = int(os.getenv("ANALYZER_HISTORY_TTL", 3600))

        # Initialize LLM (skip if AI is disabled)
        self.llm = None if not self.ai_enabled else self._initialize_llm()

        # Subscribe to health alerts
        self.subscribe_to_channel("hemostat:health_alert", self._handle_health_alert)

        self.logger.info(
            f"Analyzer Agent initialized with AI model: {self.ai_model if self.llm else 'DISABLED - using rule-based analysis only'}",
            extra={"agent": self.agent_name},
        )

    def _initialize_llm(self) -> Any | None:
        """
        Initialize LangChain LLM based on AI_MODEL configuration.

        Returns:
            Initialized LLM instance (ChatOpenAI or ChatAnthropic), or None if initialization fails

        Raises:
            ImportError: If required LangChain libraries are not installed
        """
        try:
            if self.ai_model.startswith("gpt"):
                from langchain_openai import ChatOpenAI

                if not os.getenv("OPENAI_API_KEY", "").strip():
                    self.logger.warning(
                        "OPENAI_API_KEY not set; AI analysis disabled (using rule-based fallback)"
                    )
                    return None

                self.logger.info(f"Initializing ChatOpenAI with model: {self.ai_model}")
                return ChatOpenAI(
                    model=self.ai_model,  # type: ignore[arg-type]
                    temperature=0.3,
                )

            elif self.ai_model.startswith("claude"):
                from langchain_anthropic import ChatAnthropic

                if not os.getenv("ANTHROPIC_API_KEY", "").strip():
                    self.logger.warning(
                        "ANTHROPIC_API_KEY not set; AI analysis disabled (using rule-based fallback)"
                    )
                    return None

                self.logger.info(f"Initializing ChatAnthropic with model: {self.ai_model}")
                return ChatAnthropic(  
                    model=self.ai_model,
                    temperature=0.3,
                )

            elif "/" in self.ai_model:  # Hugging Face model (e.g., "openai/gpt-oss-120b")
                from langchain_huggingface import HuggingFaceEndpoint

                hf_token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN", "")
                if not hf_token.strip():
                    self.logger.warning(
                        "HUGGINGFACE_API_KEY or HF_TOKEN not set; AI analysis disabled (using rule-based fallback)"
                    )
                    return None

                self.logger.info(f"Initializing HuggingFaceEndpoint with model: {self.ai_model}")
                return HuggingFaceEndpoint(
                    repo_id=self.ai_model,
                    temperature=0.3,
                    max_new_tokens=512,
                    huggingfacehub_api_token=hf_token,
                )

            else:
                self.logger.warning(f"Unknown AI model: {self.ai_model}; using rule-based fallback")
                return None

        except ImportError as e:
            self.logger.error(
                f"Failed to import LangChain libraries: {e}. Install with: uv sync --extra agents"
            )
            return None
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            return None

    def run(self) -> None:
        """
        Start the analyzer listening loop.

        Blocks until stop() is called. Handles exceptions gracefully.
        """
        try:
            self.start_listening()
        except Exception as e:
            self.logger.error(f"Error in listening loop: {e}", exc_info=True)

    def _handle_health_alert(self, message: dict[str, Any]) -> None:
        """
        Callback invoked when a health alert is received from Monitor Agent.

        Args:
            message: Deserialized health alert message from Redis
        """
        try:
            # Extract alert data
            alert_data = message.get("data", {})
            container_name = alert_data.get("container_name", "unknown")

            self.logger.info(
                f"Received health alert for container: {container_name}",
                extra={"agent": self.agent_name},
            )

            # Perform analysis
            self._analyze_health_issue(alert_data)

        except Exception as e:
            self.logger.error(f"Error handling health alert: {e}", exc_info=True)

    def _analyze_health_issue(self, alert_data: dict[str, Any]) -> None:
        """
        Main analysis orchestration method.

        Retrieves historical context, attempts AI analysis, falls back to rule-based
        if needed, and routes to appropriate channel based on confidence.

        Args:
            alert_data: Health alert data from Monitor Agent
        """
        container_name = alert_data.get("container_name", "unknown")

        try:
            # Retrieve historical context
            history = self.get_shared_state(f"alert_history:{container_name}")
            history_list = history.get("alerts", []) if history else []

            # Attempt AI analysis if LLM is available
            analysis = None
            if self.llm:
                analysis = self._ai_analyze(alert_data, history_list)

            # Fall back to rule-based if AI failed or not available
            if analysis is None:
                analysis = self._rule_based_analyze(alert_data, history_list)

            # Update alert history
            self._update_alert_history(container_name, alert_data)

            # Route to appropriate channel based on confidence and action
            if analysis.get("is_false_alarm"):
                self._publish_false_alarm(alert_data, analysis)
            elif analysis.get("confidence", 0) >= self.confidence_threshold:
                # Guard: only publish remediation if action is actionable (not "none")
                if analysis.get("action") != "none":
                    self._publish_remediation_needed(alert_data, analysis)
                else:
                    # Action is "none" even with high confidence; treat as false alarm
                    self._publish_false_alarm(alert_data, analysis)
            else:
                self._publish_false_alarm(alert_data, analysis)

        except Exception as e:
            self.logger.error(
                f"Error analyzing health issue for {container_name}: {e}", exc_info=True
            )

    def _ai_analyze(self, alert_data: dict[str, Any], history: list[dict]) -> dict[str, Any] | None:
        """
        Perform AI-powered analysis using LangChain.

        Args:
            alert_data: Current health alert data
            history: List of historical alerts for pattern detection

        Returns:
            Analysis dict with keys: action, reason, confidence, is_false_alarm, analysis_method
            Returns None if AI analysis fails (triggers fallback)
        """
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            container_name = alert_data.get("container_name", "unknown")
            metrics = alert_data.get("metrics", {})
            anomalies = alert_data.get("anomalies", [])
            health_status = alert_data.get("health_status", "unknown")

            # Build context for the prompt
            history_summary = ""
            if history:
                history_summary = f"\n\nRecent alert history ({len(history)} alerts):\n"
                for i, h in enumerate(history[-3:], 1):  # Last 3 alerts
                    h_metrics = h.get("metrics", {})
                    h_anomalies = h.get("anomalies", [])
                    history_summary += f"  Alert {i}: CPU={h_metrics.get('cpu_percent', 'N/A')}%, Memory={h_metrics.get('memory_percent', 'N/A')}%, Anomalies={len(h_anomalies)}\n"

            # Build structured prompt
            prompt_text = f"""You are an expert DevOps engineer analyzing container health issues.

Container: {container_name}
Health Status: {health_status}

Current Metrics:
- CPU: {metrics.get("cpu_percent", "N/A")}%
- Memory: {metrics.get("memory_percent", "N/A")}%
- Network I/O: {metrics.get("network_io", "N/A")}
- Disk I/O: {metrics.get("disk_io", "N/A")}
- Exit Code: {alert_data.get("exit_code", "N/A")}
- Restart Count: {alert_data.get("restart_count", 0)}

Detected Anomalies ({len(anomalies)}):
{json.dumps(anomalies, indent=2) if anomalies else "None"}
{history_summary}

Respond with valid JSON only, no code fences or commentary. Provide your analysis in this format:
{{
  "root_cause": "Brief description of the root cause",
  "action": "restart|scale_up|cleanup|none",
  "reason": "Explanation for the recommended action",
  "confidence": 0.0-1.0,
  "is_false_alarm": true|false
}}

Be concise and focus on actionable insights."""

            # Invoke LLM with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    messages = [
                        SystemMessage(
                            content="You are an expert DevOps engineer analyzing container health issues."
                        ),
                        HumanMessage(content=prompt_text),
                    ]

                    if not self.llm:
                        self.logger.error("LLM not initialized")
                        return None

                    response = self.llm.invoke(messages)
                    response_text = response.content

                    # Parse JSON response - strip code fences first
                    json_str = response_text.strip()
                    # Remove markdown code fences if present
                    json_str = re.sub(r"^```(?:json)?\s*", "", json_str)
                    json_str = re.sub(r"\s*```$", "", json_str)

                    # Try to extract JSON from response
                    json_start = json_str.find("{")
                    json_end = json_str.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = json_str[json_start:json_end]

                    # Parse JSON
                    analysis_result = json.loads(json_str)

                    # Validate required fields
                    if all(
                        k in analysis_result
                        for k in [
                            "root_cause",
                            "action",
                            "reason",
                            "confidence",
                            "is_false_alarm",
                        ]
                    ):
                        analysis_result["analysis_method"] = "ai"
                        self.logger.info(
                            f"AI analysis successful for {container_name}: "
                            f"action={analysis_result['action']}, confidence={analysis_result['confidence']}"
                        )
                        return analysis_result

                    self.logger.warning(
                        f"Invalid AI response format for {container_name}, retrying..."
                    )

                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Failed to parse AI response (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        # Sleep between retries for non-JSON formats
                        time.sleep(0.5 * (2**attempt))
                    continue

            self.logger.warning(
                f"AI analysis failed for {container_name} after {max_retries} attempts; falling back to rule-based"
            )
            return None

        except Exception as e:
            self.logger.error(
                f"AI analysis error for {alert_data.get('container_name', 'unknown')}: {e}",
                exc_info=True,
            )
            return None

    def _rule_based_analyze(
        self, alert_data: dict[str, Any], history: list[dict]
    ) -> dict[str, Any]:
        """
        Fallback analysis using deterministic rules.

        Args:
            alert_data: Current health alert data
            history: List of historical alerts for pattern detection

        Returns:
            Analysis dict with keys: action, reason, confidence, is_false_alarm, analysis_method
        """
        metrics = alert_data.get("metrics", {})
        anomalies = alert_data.get("anomalies", [])
        health_status = alert_data.get("health_status", "unknown")
        exit_code = alert_data.get("exit_code", 0)
        restart_count = alert_data.get("restart_count", 0)

        cpu_percent = metrics.get("cpu_percent", 0)
        memory_percent = metrics.get("memory_percent", 0)

        # Rule 1: Non-zero exit code (high confidence)
        if exit_code != 0:
            return {
                "action": "restart",
                "reason": f"Container exited with non-zero code: {exit_code}",
                "confidence": 0.9,
                "is_false_alarm": False,
                "analysis_method": "rule_based",
            }

        # Rule 2: Excessive restarts (circuit breaker - false alarm)
        if restart_count > 5:
            return {
                "action": "none",
                "reason": f"Excessive restarts detected ({restart_count}); circuit breaker activated",
                "confidence": 0.6,
                "is_false_alarm": True,
                "analysis_method": "rule_based",
            }

        # Rule 3: Critical severity anomaly
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        if critical_anomalies:
            return {
                "action": "restart",
                "reason": f"Critical anomalies detected: {', '.join(a.get('type', 'unknown') for a in critical_anomalies)}",
                "confidence": 0.85,
                "is_false_alarm": False,
                "analysis_method": "rule_based",
            }

        # Rule 4: Unhealthy status
        if health_status == "unhealthy":
            return {
                "action": "restart",
                "reason": "Container health check failed",
                "confidence": 0.7,
                "is_false_alarm": False,
                "analysis_method": "rule_based",
            }

        # Rule 5: Sustained high CPU (2+ consecutive alerts)
        cpu_trend = self._detect_metric_trend(history, "cpu_percent")
        if cpu_percent > 90 and cpu_trend in ["increasing", "stable"]:
            return {
                "action": "restart",
                "reason": f"Sustained high CPU usage: {cpu_percent}%",
                "confidence": 0.75,
                "is_false_alarm": False,
                "analysis_method": "rule_based",
            }

        # Rule 6: Memory leak pattern (increasing trend)
        memory_trend = self._detect_metric_trend(history, "memory_percent")
        if memory_trend == "increasing" and memory_percent > 70:
            return {
                "action": "restart",
                "reason": f"Memory leak pattern detected; memory increasing to {memory_percent}%",
                "confidence": 0.8,
                "is_false_alarm": False,
                "analysis_method": "rule_based",
            }

        # Rule 7: Transient spike (single medium anomaly, no history)
        medium_anomalies = [a for a in anomalies if a.get("severity") == "medium"]
        if len(anomalies) == 1 and len(medium_anomalies) == 1 and not history:
            return {
                "action": "none",
                "reason": "Transient spike detected; likely false alarm",
                "confidence": 0.65,
                "is_false_alarm": True,
                "analysis_method": "rule_based",
            }

        # Default: Low confidence false alarm
        return {
            "action": "none",
            "reason": "Insufficient evidence for remediation",
            "confidence": 0.5,
            "is_false_alarm": True,
            "analysis_method": "rule_based",
        }

    def _detect_metric_trend(self, history: list[dict], metric_key: str) -> str:
        """
        Helper method to detect trends in historical metrics.

        Args:
            history: List of historical alert dicts
            metric_key: Metric key to analyze (e.g., "cpu_percent", "memory_percent")

        Returns:
            Trend string: "increasing", "decreasing", "stable", or "unknown"
        """
        try:
            if len(history) < 2:
                return "unknown"

            # Extract metric values from last 3-5 alerts
            values = []
            for alert in history[-5:]:
                metrics = alert.get("metrics", {})
                value = metrics.get(metric_key)
                if value is not None:
                    values.append(float(value))

            if len(values) < 2:
                return "unknown"

            # Calculate trend
            diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
            avg_diff = sum(diffs) / len(diffs)

            if avg_diff > 5:  # Threshold for "increasing"
                return "increasing"
            elif avg_diff < -5:  # Threshold for "decreasing"
                return "decreasing"
            else:
                return "stable"

        except Exception as e:
            self.logger.debug(f"Error detecting metric trend: {e}")
            return "unknown"

    def _publish_remediation_needed(
        self, alert_data: dict[str, Any], analysis: dict[str, Any]
    ) -> None:
        """
        Publish a remediation needed event.

        Args:
            alert_data: Original health alert data
            analysis: Analysis result from AI or rule-based logic
        """
        container_name = alert_data.get("container_name", "unknown")

        payload = {
            "container": container_name,
            "action": analysis.get("action", "none"),
            "reason": analysis.get("reason", ""),
            "confidence": analysis.get("confidence", 0.0),
            "metrics": alert_data.get("metrics", {}),
            "analysis_method": analysis.get("analysis_method", "unknown"),
        }

        self.publish_event("hemostat:remediation_needed", "remediation_needed", payload)

        self.logger.warning(
            f"Remediation needed for {container_name}: "
            f"action={analysis.get('action')}, confidence={analysis.get('confidence'):.2f}",
            extra={"agent": self.agent_name},
        )

    def _publish_false_alarm(self, alert_data: dict[str, Any], analysis: dict[str, Any]) -> None:
        """
        Publish a false alarm event.

        Args:
            alert_data: Original health alert data
            analysis: Analysis result from AI or rule-based logic
        """
        container_name = alert_data.get("container_name", "unknown")

        payload = {
            "container": container_name,
            "reason": analysis.get("reason", ""),
            "confidence": analysis.get("confidence", 0.0),
            "analysis_method": analysis.get("analysis_method", "unknown"),
        }

        self.publish_event("hemostat:false_alarm", "false_alarm", payload)

        self.logger.info(
            f"False alarm for {container_name}: {analysis.get('reason')} "
            f"(confidence={analysis.get('confidence'):.2f})",
            extra={"agent": self.agent_name},
        )

    def _update_alert_history(self, container_name: str, alert_data: dict[str, Any]) -> None:
        """
        Update alert history in Redis for pattern detection.

        Args:
            container_name: Name of the container
            alert_data: Current alert data to append to history
        """
        try:
            # Retrieve existing history
            history_key = f"alert_history:{container_name}"
            existing = self.get_shared_state(history_key)
            alerts = existing.get("alerts", []) if existing else []

            # Append current alert
            alerts.append(alert_data)

            # Keep only last N alerts
            alerts = alerts[-self.history_size :]

            # Store updated history
            history_data = {"alerts": alerts, "container": container_name}
            self.set_shared_state(history_key, history_data, ttl=self.history_ttl)

            self.logger.debug(f"Updated alert history for {container_name} ({len(alerts)} alerts)")

        except Exception as e:
            self.logger.error(f"Error updating alert history for {container_name}: {e}")

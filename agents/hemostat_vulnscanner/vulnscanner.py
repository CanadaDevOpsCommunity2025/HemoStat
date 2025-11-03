"""
HemoStat Vulnerability Scanner Agent

Integrates with OWASP ZAP to perform automated security vulnerability scans
of web applications and publishes findings to the HemoStat ecosystem.
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from agents.agent_base import HemoStatAgent
from agents.logger import HemoStatLogger


class VulnerabilityScanner(HemoStatAgent):
    """
    Vulnerability Scanner Agent that uses OWASP ZAP to scan web applications
    for security vulnerabilities and publishes findings to Redis.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Vulnerability Scanner Agent.
        
        Args:
            **kwargs: Additional arguments passed to HemoStatAgent
        """
        super().__init__("vulnscanner", **kwargs)
        
        # ZAP configuration
        self.zap_host = os.getenv("ZAP_HOST", "zap")
        self.zap_port = int(os.getenv("ZAP_PORT", "8080"))
        self.zap_api_url = f"http://{self.zap_host}:{self.zap_port}"
        
        # Scanner configuration
        self.scan_interval = int(os.getenv("VULNSCANNER_INTERVAL", "3600"))  # 1 hour default
        self.scan_timeout = int(os.getenv("VULNSCANNER_TIMEOUT", "1800"))  # 30 minutes default
        self.max_scan_time = int(os.getenv("VULNSCANNER_MAX_TIME", "3600"))  # 1 hour max
        
        # Target configuration
        self.default_targets = [
            "http://juice-shop:3000",  # Default Juice Shop target
        ]
        
        # Parse additional targets from environment
        targets_env = os.getenv("VULNSCANNER_TARGETS", "")
        if targets_env:
            additional_targets = [t.strip() for t in targets_env.split(",") if t.strip()]
            self.default_targets.extend(additional_targets)
        
        self.logger.info(f"Vulnerability Scanner initialized with targets: {self.default_targets}")
        self.logger.info(f"ZAP API URL: {self.zap_api_url}")
        self.logger.info(f"Scan interval: {self.scan_interval}s")

    def _wait_for_zap(self, max_wait: int = 120) -> bool:
        """
        Wait for ZAP to be ready and responsive.
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if ZAP is ready, False if timeout
        """
        self.logger.info("Waiting for ZAP to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.zap_api_url}/JSON/core/view/version/",
                    timeout=5
                )
                if response.status_code == 200:
                    version_info = response.json()
                    self.logger.info(f"ZAP is ready. Version: {version_info.get('version', 'unknown')}")
                    return True
            except (ConnectionError, Timeout, RequestException) as e:
                self.logger.debug(f"ZAP not ready yet: {e}")
            
            time.sleep(5)
        
        self.logger.error(f"ZAP did not become ready within {max_wait} seconds")
        return False

    def _start_scan(self, target_url: str) -> str | None:
        """
        Start a ZAP scan for the given target URL.
        
        Args:
            target_url: URL to scan
            
        Returns:
            Scan ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Starting ZAP scan for: {target_url}")
            
            # Start active scan
            response = requests.get(
                f"{self.zap_api_url}/JSON/ascan/action/scan/",
                params={
                    "url": target_url,
                    "recurse": "true",
                    "inScopeOnly": "false"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                scan_id = result.get("scan")
                if scan_id:
                    self.logger.info(f"ZAP scan started successfully. Scan ID: {scan_id}")
                    return scan_id
                else:
                    self.logger.error(f"Failed to get scan ID from ZAP response: {result}")
            else:
                self.logger.error(f"ZAP scan request failed with status {response.status_code}: {response.text}")
                
        except (ConnectionError, Timeout, RequestException) as e:
            self.logger.error(f"Failed to start ZAP scan: {e}")
        
        return None

    def _get_scan_status(self, scan_id: str) -> int:
        """
        Get the progress status of a ZAP scan.
        
        Args:
            scan_id: ZAP scan ID
            
        Returns:
            Progress percentage (0-100), or -1 if error
        """
        try:
            response = requests.get(
                f"{self.zap_api_url}/JSON/ascan/view/status/",
                params={"scanId": scan_id},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return int(result.get("status", -1))
            else:
                self.logger.error(f"Failed to get scan status: {response.status_code}")
                
        except (ConnectionError, Timeout, RequestException, ValueError) as e:
            self.logger.error(f"Error getting scan status: {e}")
        
        return -1

    def _get_scan_results(self) -> list[dict[str, Any]]:
        """
        Retrieve vulnerability findings from ZAP.
        
        Returns:
            List of vulnerability alert dictionaries
        """
        try:
            response = requests.get(
                f"{self.zap_api_url}/JSON/core/view/alerts/",
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                alerts = result.get("alerts", [])
                self.logger.info(f"Retrieved {len(alerts)} vulnerability alerts from ZAP")
                return alerts
            else:
                self.logger.error(f"Failed to get scan results: {response.status_code}")
                
        except (ConnectionError, Timeout, RequestException) as e:
            self.logger.error(f"Error getting scan results: {e}")
        
        return []

    def _wait_for_scan_completion(self, scan_id: str) -> bool:
        """
        Wait for a ZAP scan to complete.
        
        Args:
            scan_id: ZAP scan ID
            
        Returns:
            True if scan completed successfully, False if timeout or error
        """
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < self.max_scan_time:
            progress = self._get_scan_status(scan_id)
            
            if progress == -1:
                self.logger.error("Failed to get scan progress")
                return False
            
            if progress != last_progress:
                self.logger.info(f"Scan progress: {progress}%")
                last_progress = progress
            
            if progress >= 100:
                self.logger.info("Scan completed successfully")
                return True
            
            time.sleep(10)  # Check every 10 seconds
        
        self.logger.error(f"Scan timed out after {self.max_scan_time} seconds")
        return False

    def _process_vulnerabilities(self, alerts: list[dict[str, Any]], target_url: str) -> dict[str, Any]:
        """
        Process and categorize vulnerability alerts.
        
        Args:
            alerts: List of ZAP alert dictionaries
            target_url: Target URL that was scanned
            
        Returns:
            Processed vulnerability report
        """
        # Categorize by risk level
        risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
        critical_vulns = []
        
        for alert in alerts:
            risk = alert.get("risk", "Informational")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            # Collect critical vulnerabilities (High risk)
            if risk == "High":
                critical_vulns.append({
                    "name": alert.get("alert", "Unknown"),
                    "url": alert.get("url", ""),
                    "param": alert.get("param", ""),
                    "description": alert.get("description", ""),
                    "solution": alert.get("solution", ""),
                    "reference": alert.get("reference", "")
                })
        
        # Create summary report
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "target_url": target_url,
            "total_vulnerabilities": len(alerts),
            "risk_summary": risk_counts,
            "critical_vulnerabilities": critical_vulns,
            "scan_agent": "hemostat-vulnscanner",
            "scan_tool": "OWASP ZAP"
        }
        
        return report

    def _publish_scan_results(self, report: dict[str, Any]) -> None:
        """
        Publish vulnerability scan results to Redis channels.
        
        Args:
            report: Vulnerability scan report
        """
        try:
            # Publish to vulnerability channel
            self.publish_event("hemostat:vulnerabilities", {
                "event_type": "vulnerability_scan_completed",
                "agent": self.agent_name,
                "timestamp": report["timestamp"],
                "data": report
            })
            
            # If critical vulnerabilities found, publish alert
            if report["risk_summary"].get("High", 0) > 0:
                self.publish_event("hemostat:alerts", {
                    "event_type": "critical_vulnerabilities_found",
                    "agent": self.agent_name,
                    "timestamp": report["timestamp"],
                    "severity": "high",
                    "message": f"Found {report['risk_summary']['High']} critical vulnerabilities in {report['target_url']}",
                    "data": {
                        "target_url": report["target_url"],
                        "critical_count": report["risk_summary"]["High"],
                        "total_count": report["total_vulnerabilities"],
                        "critical_vulns": report["critical_vulnerabilities"]
                    }
                })
            
            # Store scan results in shared state
            state_key = f"vuln_scan_{int(time.time())}"
            self.set_shared_state(state_key, report, ttl=86400)  # 24 hours TTL
            
            self.logger.info(f"Published vulnerability scan results for {report['target_url']}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish scan results: {e}", exc_info=True)

    def scan_target(self, target_url: str) -> bool:
        """
        Perform a complete vulnerability scan of a target URL.
        
        Args:
            target_url: URL to scan
            
        Returns:
            True if scan completed successfully, False otherwise
        """
        self.logger.info(f"Starting vulnerability scan for: {target_url}")
        
        # Start the scan
        scan_id = self._start_scan(target_url)
        if not scan_id:
            return False
        
        # Wait for completion
        if not self._wait_for_scan_completion(scan_id):
            return False
        
        # Get results
        alerts = self._get_scan_results()
        
        # Process and publish results
        report = self._process_vulnerabilities(alerts, target_url)
        self._publish_scan_results(report)
        
        return True

    def run_scan_cycle(self) -> None:
        """
        Run a complete scan cycle for all configured targets.
        """
        self.logger.info("Starting vulnerability scan cycle")
        
        # Wait for ZAP to be ready
        if not self._wait_for_zap():
            self.logger.error("ZAP is not ready, skipping scan cycle")
            return
        
        # Scan each target
        for target_url in self.default_targets:
            try:
                self.logger.info(f"Scanning target: {target_url}")
                success = self.scan_target(target_url)
                if success:
                    self.logger.info(f"Successfully completed scan for {target_url}")
                else:
                    self.logger.error(f"Failed to complete scan for {target_url}")
                
                # Brief pause between targets
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error scanning {target_url}: {e}", exc_info=True)
        
        self.logger.info("Vulnerability scan cycle completed")

    def run(self) -> None:
        """
        Main execution loop for the vulnerability scanner agent.
        """
        self.logger.info("Vulnerability Scanner Agent starting...")
        
        try:
            while self._running:
                # Run scan cycle
                self.run_scan_cycle()
                
                # Wait for next scan interval
                self.logger.info(f"Waiting {self.scan_interval} seconds until next scan cycle")
                time.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self) -> None:
        """
        Stop the vulnerability scanner agent.
        """
        self.logger.info("Stopping Vulnerability Scanner Agent")
        self._running = False
        
        # Close pub/sub connection
        if hasattr(self, 'pubsub'):
            try:
                self.pubsub.close()
            except Exception as e:
                self.logger.error(f"Error closing pubsub connection: {e}")

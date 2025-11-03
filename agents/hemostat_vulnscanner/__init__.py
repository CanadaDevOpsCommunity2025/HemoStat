"""
HemoStat Vulnerability Scanner Agent Package

Provides vulnerability scanning capabilities using OWASP ZAP integration.
Scans web applications for security vulnerabilities and publishes findings to the HemoStat ecosystem.
"""

from agents.hemostat_vulnscanner.vulnscanner import VulnerabilityScanner

__all__ = ["VulnerabilityScanner"]

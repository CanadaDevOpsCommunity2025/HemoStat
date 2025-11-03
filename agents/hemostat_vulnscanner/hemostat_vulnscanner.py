"""
HemoStat Vulnerability Scanner Agent Module

Re-exports the VulnerabilityScanner class for consistent import patterns.
This module follows the same pattern as other HemoStat agents.
"""

from agents.hemostat_vulnscanner.vulnscanner import VulnerabilityScanner

__all__ = ["VulnerabilityScanner"]

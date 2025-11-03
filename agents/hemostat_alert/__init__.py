"""
HemoStat Alert Agent Package

Provides the AlertNotifier class for sending notifications and storing events for dashboard consumption.
"""

from .hemostat_alert import AlertNotifier

__all__ = ["AlertNotifier"]

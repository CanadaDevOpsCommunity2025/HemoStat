"""
HemoStat Monitor Agent - Primary module

Re-exports ContainerMonitor from monitor.py to provide the hemostat_monitor module path.
This module satisfies the requested path: agents/hemostat_monitor/hemostat_monitor.py
"""

from .monitor import ContainerMonitor

__all__ = ["ContainerMonitor"]

"""
HemoStat Responder Agent - Primary module

Re-exports ContainerResponder from responder.py to provide the hemostat_responder module path.
This module satisfies the requested path: agents/hemostat_responder/hemostat_responder.py
"""

from .responder import ContainerResponder

__all__ = ["ContainerResponder"]

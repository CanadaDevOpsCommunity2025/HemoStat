"""
HemoStat Platform Detection Utilities

Provides OS detection and platform-specific configuration for Docker socket handling.
Supports Windows, Linux, and macOS with automatic detection of running environment.
"""

import os
import platform
from pathlib import Path


def get_platform() -> str:
    """
    Get the current operating system name.

    Returns:
        'Windows', 'Linux', or 'Darwin' (macOS)
    """
    return platform.system()


def is_in_docker() -> bool:
    """
    Detect if the current process is running inside a Docker container.

    Returns:
        True if running in Docker, False otherwise
    """
    return Path("/.dockerenv").exists()


def get_docker_host() -> str:
    """
    Get the appropriate Docker daemon socket path for the current platform.

    Logic:

    - If running in Docker container: always use unix:///var/run/docker.sock
      (Docker Desktop on Windows maps the named pipe to this path inside containers)
    - If running locally on Windows: use npipe:////./pipe/docker_engine
    - If running locally on Linux/macOS: use unix:///var/run/docker.sock

    Returns:
        Docker daemon socket path appropriate for the platform
    """
    # Inside Docker containers, always use Unix socket (Docker Desktop handles mapping)
    if is_in_docker():
        return "unix:///var/run/docker.sock"

    # Running locally - check OS
    system = get_platform()

    if system == "Windows":
        return "npipe:////./pipe/docker_engine"
    else:
        # Linux and macOS both use Unix sockets
        return "unix:///var/run/docker.sock"


def get_platform_display() -> str:
    """
    Get a human-readable platform description for logging.

    Returns:
        Platform description string
    """
    system = get_platform()
    in_docker = is_in_docker()

    docker_status = " (in Docker)" if in_docker else " (local)"

    if system == "Windows":
        return f"Windows{docker_status}"
    elif system == "Darwin":
        return f"macOS{docker_status}"
    else:
        return f"Linux{docker_status}"

"""
HemoStat Custom Logger Module

Provides a centralized, comprehensive logging system for the HemoStat project.
Supports multiple output formats (text, JSON), configurable log levels, and
structured logging with contextual information.
"""

import logging
import os
import sys
from typing import ClassVar


class HemoStatLogger:
    """
    Centralized logger factory for HemoStat agents.

    Provides consistent logging configuration across all agents with support for:
    - Multiple output formats (text, JSON)
    - Configurable log levels via environment variables
    - Structured logging with contextual information
    - Consistent formatting and naming conventions
    """

    _loggers: ClassVar[dict[str, logging.Logger]] = {}
    _configured: ClassVar[bool] = False

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger with the given name.

        Creates a new logger if it doesn't exist, or returns the cached instance.
        All loggers are configured with consistent formatting and handlers.

        Args:
            name: Logger name (typically agent name like 'monitor', 'analyzer', etc.)

        Returns:
            Configured logging.Logger instance
        """
        full_name = f"hemostat.{name}"

        if full_name not in cls._loggers:
            logger = logging.getLogger(full_name)
            cls._configure_logger(logger, name)
            cls._loggers[full_name] = logger

        return cls._loggers[full_name]

    @classmethod
    def _configure_logger(cls, logger: logging.Logger, agent_name: str) -> None:
        """
        Configure a logger with appropriate handlers and formatters.

        Args:
            logger: Logger instance to configure
            agent_name: Name of the agent (for formatting)
        """
        # Prevent duplicate handlers if logger already has them
        if logger.handlers:
            return

        # Get configuration from environment
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_format_type = os.getenv("LOG_FORMAT", "text").lower()

        # Set log level
        try:
            log_level = getattr(logging, log_level_str)
        except AttributeError:
            log_level = logging.INFO
            logger.warning(f"Invalid LOG_LEVEL '{log_level_str}', using INFO")

        logger.setLevel(log_level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        # Create formatter based on format type
        if log_format_type == "json":
            formatter = cls._get_json_formatter(agent_name)
        else:
            formatter = cls._get_text_formatter(agent_name)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    @staticmethod
    def _get_text_formatter(agent_name: str) -> logging.Formatter:
        """
        Create a text format formatter.

        Args:
            agent_name: Name of the agent for formatting

        Returns:
            Configured logging.Formatter for text output
        """
        fmt = f"[{agent_name.upper()}] %(asctime)s - %(levelname)s - %(message)s"
        return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _get_json_formatter(agent_name: str) -> logging.Formatter:
        """
        Create a JSON format formatter.

        Falls back to text format if python-json-logger is not installed.

        Args:
            agent_name: Name of the agent for formatting

        Returns:
            Configured logging.Formatter for JSON output (or text if unavailable)
        """
        try:
            from pythonjsonlogger import jsonlogger

            fmt = "%(timestamp)s %(level)s %(agent)s %(message)s"
            formatter = jsonlogger.JsonFormatter(
                fmt=fmt,
                rename_fields={"levelname": "level", "name": "logger"},
                timestamp=True,
            )
            # Add agent name to all log records
            original_make_record = logging.Logger.makeRecord

            def make_record_with_agent(
                self,
                name,
                level,
                fn,
                lno,
                msg,
                args,
                exc_info,
                func=None,
                extra=None,
                sinfo=None,
            ):
                if extra is None:
                    extra = {}
                extra["agent"] = agent_name
                return original_make_record(
                    self, name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
                )

            logging.Logger.makeRecord = make_record_with_agent  # type: ignore[assignment]
            return formatter
        except ImportError:
            # Fall back to text format if python-json-logger not available
            fmt = f"[{agent_name.upper()}] %(asctime)s - %(levelname)s - %(message)s"
            return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    @classmethod
    def configure_root_logger(cls) -> None:
        """
        Configure the root logger with basic settings.

        Called once at application startup to set up root logger configuration.
        """
        if cls._configured:
            return

        root_logger = logging.getLogger()
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

        try:
            log_level = getattr(logging, log_level_str)
        except AttributeError:
            log_level = logging.INFO

        root_logger.setLevel(log_level)

        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        cls._configured = True

    @classmethod
    def reset(cls) -> None:
        """
        Reset all cached loggers and configuration.

        Useful for testing or reconfiguration.
        """
        cls._loggers.clear()
        cls._configured = False

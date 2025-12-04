"""
Structured logging setup using structlog.

This module configures structured logging for the application with JSON output
in production and human-readable format in development.
"""

import logging
import sys
from typing import Any, Dict

import structlog


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level and timestamp
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use JSON in production, pretty print in development
            structlog.processors.JSONRenderer() if level.upper() == "INFO" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> Any:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def log_request(method: str, path: str, status_code: int, duration: float, **kwargs) -> None:
    """
    Log an HTTP request with structured data.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional context
    """
    logger = get_logger("http")
    logger.info(
        "HTTP request",
        method=method,
        path=path,
        status_code=status_code,
        duration=duration,
        **kwargs
    )


def log_run_event(run_id: str, event_type: str, cline_run_id: str = None, **kwargs) -> None:
    """
    Log a run-related event with structured data.
    
    Args:
        run_id: Run identifier
        event_type: Type of event
        cline_run_id: Cline Core run identifier (optional)
        **kwargs: Additional context
    """
    logger = get_logger("run")
    logger.info(
        f"Run {event_type}",
        run_id=run_id,
        cline_run_id=cline_run_id,
        event_type=event_type,
        **kwargs
    )


def log_slack_event(event_type: str, channel_id: str = None, user_id: str = None, **kwargs) -> None:
    """
    Log a Slack-related event with structured data.
    
    Args:
        event_type: Type of Slack event
        channel_id: Slack channel ID (optional)
        user_id: Slack user ID (optional)
        **kwargs: Additional context
    """
    logger = get_logger("slack")
    logger.info(
        f"Slack {event_type}",
        event_type=event_type,
        channel_id=channel_id,
        user_id=user_id,
        **kwargs
    )


def log_grpc_event(method: str, success: bool, duration: float = None, **kwargs) -> None:
    """
    Log a gRPC-related event with structured data.
    
    Args:
        method: gRPC method name
        success: Whether the call succeeded
        duration: Call duration in seconds (optional)
        **kwargs: Additional context
    """
    logger = get_logger("grpc")
    logger.info(
        f"gRPC {method}",
        method=method,
        success=success,
        duration=duration,
        **kwargs
    )

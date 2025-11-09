"""
Structured logging configuration with redaction for sensitive data.
"""
import structlog
import logging
import sys
from typing import Any, Dict
import re


# Patterns for redacting sensitive data
REDACTION_PATTERNS = [
    (re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE), '"password": "***REDACTED***"'),
    (re.compile(r'"access_token"\s*:\s*"[^"]*"', re.IGNORECASE), '"access_token": "***REDACTED***"'),
    (re.compile(r'password=[^\s&]+', re.IGNORECASE), 'password=***REDACTED***'),
    (re.compile(r'token=[^\s&]+', re.IGNORECASE), 'token=***REDACTED***'),
]


def redact_sensitive_data(msg: str) -> str:
    """Redact sensitive data from log messages."""
    for pattern, replacement in REDACTION_PATTERNS:
        msg = pattern.sub(replacement, msg)
    return msg


def add_redaction(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """Processor to redact sensitive data from log events."""
    if 'event' in event_dict:
        event_dict['event'] = redact_sensitive_data(str(event_dict['event']))
    
    # Redact from any string values in the event dict
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = redact_sensitive_data(value)
    
    return event_dict


def configure_logging(log_level: str = "INFO"):
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_redaction,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a configured logger instance."""
    return structlog.get_logger(name)


# Configure on module import
configure_logging()

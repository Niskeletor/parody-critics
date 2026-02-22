#!/usr/bin/env python3
"""
🎭 Parody Critics - Centralized Logging System
Enhanced logging with colored output, file rotation, and debugging
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        # Add component identification
        if hasattr(record, 'component'):
            record.component = f"[{record.component}]"
        else:
            record.component = ""

        return super().format(record)


class ParodyCriticsLogger:
    """
    Centralized logging system for Parody Critics
    Features:
    - Multiple log levels with environment-based defaults
    - File rotation to prevent disk space issues
    - Rich terminal output when available
    - Component-based logging for debugging
    - Request ID tracking for API calls
    """

    def __init__(self, name: str = "parody_critics", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Environment-based log level
        env_level = os.getenv('PARODY_CRITICS_LOG_LEVEL', 'INFO').upper()
        self.log_level = getattr(logging, env_level, logging.INFO)

        # Create main logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture everything, filter at handler level

        # Prevent duplicate logs
        if self.logger.handlers:
            self.logger.handlers.clear()

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup file and console handlers"""

        # File handler with rotation (10MB max, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # File formatter with full details
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s() | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        if RICH_AVAILABLE and sys.stdout.isatty():
            # Rich handler for beautiful terminal output
            console_handler = RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=False,
                enable_link_path=False
            )
            console_handler.setLevel(self.log_level)
        else:
            # Standard console handler with colors
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)

            console_formatter = ColoredFormatter(
                fmt='%(asctime)s | %(levelname)s %(component)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Add separate error log for critical issues
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)

    def get_logger(self, component: Optional[str] = None) -> logging.Logger:
        """Get logger for specific component"""
        if component:
            component_logger = logging.getLogger(f"{self.name}.{component}")
            component_logger.setLevel(logging.DEBUG)

            # Add component info to records
            old_factory = logging.getLogRecordFactory()

            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.component = component
                return record

            logging.setLogRecordFactory(record_factory)

            return component_logger

        return self.logger

    def log_request(self, request_id: str, method: str, url: str, status: int = None, duration: float = None):
        """Log HTTP requests with details"""
        message = f"REQUEST {request_id} | {method} {url}"
        if status and duration:
            message += f" | {status} | {duration:.3f}s"

        if status and status >= 400:
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def log_llm_call(self, model: str, prompt_length: int, response_length: int, duration: float):
        """Log LLM API calls"""
        self.logger.info(
            f"LLM_CALL | model={model} | prompt={prompt_length}chars | "
            f"response={response_length}chars | duration={duration:.2f}s"
        )

    def log_db_operation(self, operation: str, table: str, count: int = None, duration: float = None):
        """Log database operations"""
        message = f"DB_{operation.upper()} | table={table}"
        if count is not None:
            message += f" | count={count}"
        if duration:
            message += f" | duration={duration:.3f}s"

        self.logger.debug(message)

    def log_wizard_step(self, step: str, status: str, details: str = None):
        """Log setup wizard progress"""
        message = f"WIZARD | {step} | {status}"
        if details:
            message += f" | {details}"

        if status.upper() in ['ERROR', 'FAILED', 'CRITICAL']:
            self.logger.error(message)
        elif status.upper() in ['WARNING', 'WARN']:
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def setup_request_logging(self):
        """Setup request ID tracking for FastAPI"""
        import uuid

        class RequestIdFilter(logging.Filter):
            def filter(self, record):
                # Add request ID if available in context
                record.request_id = getattr(record, 'request_id', str(uuid.uuid4())[:8])
                return True

        # Add filter to all handlers
        for handler in self.logger.handlers:
            handler.addFilter(RequestIdFilter())

    def get_debug_info(self) -> dict:
        """Get current logging configuration for debugging"""
        return {
            'logger_name': self.name,
            'log_level': logging.getLevelName(self.log_level),
            'log_directory': str(self.log_dir.absolute()),
            'handlers_count': len(self.logger.handlers),
            'rich_available': RICH_AVAILABLE,
            'log_files': list(self.log_dir.glob("*.log"))
        }


# Global logger instance
_global_logger: Optional[ParodyCriticsLogger] = None


def get_logger(component: str = None) -> logging.Logger:
    """
    Get logger instance for component

    Usage:
    logger = get_logger('wizard')
    logger.info("Starting setup wizard")

    logger = get_logger('api')
    logger.error("API endpoint failed", exc_info=True)
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = ParodyCriticsLogger()

    return _global_logger.get_logger(component)


def setup_logging(log_level: str = None, log_dir: str = "logs"):
    """
    Initialize logging system

    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_dir: Directory for log files
    """
    global _global_logger

    if log_level:
        os.environ['PARODY_CRITICS_LOG_LEVEL'] = log_level.upper()

    _global_logger = ParodyCriticsLogger(log_dir=log_dir)

    # Log startup
    logger = _global_logger.get_logger('system')
    logger.info(f"🎭 Parody Critics logging initialized | level={log_level or 'INFO'} | dir={log_dir}")

    return _global_logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = None):
    """
    Enhanced exception logging with context

    Usage:
    try:
        risky_operation()
    except Exception as e:
        log_exception(logger, e, "Processing Jellyfin sync")
        raise
    """
    message = f"Exception in {context or 'operation'}: {str(exc)}"
    logger.error(message, exc_info=True)


# Context manager for operation timing
class LogTimer:
    """Context manager for timing operations"""

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type:
            self.logger.error(f"Failed {self.operation} after {duration:.3f}s: {exc_val}")
        else:
            self.logger.log(self.level, f"Completed {self.operation} in {duration:.3f}s")


if __name__ == "__main__":
    # Test logging system
    setup_logging("DEBUG")

    logger = get_logger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test timer
    with LogTimer(logger, "test operation"):
        import time
        time.sleep(0.1)

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_exception(logger, e, "testing exception handling")
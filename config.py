import logging
from typing import Final
import json
from datetime import datetime

"""
Global configuration and logging utilities for the AI Job Search Agent.

Centralizing these values improves maintainability and makes it easier to tune
timeouts, limits, and logging behavior for production deployments.
"""

# --- Logging -----------------------------------------------------------------

LOG_LEVEL: Final[int] = logging.INFO
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for better parsing and monitoring."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data)


def configure_logging(use_json: bool = False) -> None:
    """
    Configure the root logger for the entire application.

    This function is safe to call multiple times; subsequent calls will have no
    effect if handlers are already configured.

    Args:
        use_json: If True, use JSON formatting for structured logging (production-ready)
    """
    root_logger = logging.getLogger()

    if root_logger.handlers:
        # Logging is already configured by the hosting environment or framework.
        return

    # Create console handler
    console_handler = logging.StreamHandler()

    if use_json:
        # Use JSON formatter for structured logging
        formatter = JsonFormatter()
    else:
        # Use standard text formatter
        formatter = logging.Formatter(LOG_FORMAT)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(LOG_LEVEL)

    # Log startup
    root_logger.info(f"Logging configured. JSON mode: {use_json}")


# --- Job Search & Scraping ---------------------------------------------------

MAX_JOBS_PER_PLATFORM: Final[int] = 10
DEFAULT_HTTP_TIMEOUT_SECONDS: Final[int] = 10

# --- Selenium / Naukri-specific ---------------------------------------------

SELENIUM_DEFAULT_WAIT_SECONDS: Final[int] = 10

# --- Monitoring & Alerts -----------------------------------------------------

# Log aggregation
ENABLE_STRUCTURED_LOGGING: Final[bool] = True
LOG_FAILED_SEARCHES: Final[bool] = True
LOG_RETRY_ATTEMPTS: Final[bool] = True

# Thresholds for alerting
MAX_CONSECUTIVE_FAILURES: Final[int] = 5
FAILURE_RATE_THRESHOLD: Final[float] = 0.3  # 30% failure rate triggers alert

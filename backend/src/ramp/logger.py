"""
RAMP Structured Logging Setup
SIH26080 | Production Structured Logger
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured cloud/observability logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_logs: bool = False) -> logging.Logger:
    """Configures and returns the root RAMP logger."""
    root_logger = logging.getLogger("ramp")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        text_format = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        handler.setFormatter(logging.Formatter(text_format))

    root_logger.addHandler(handler)
    root_logger.propagate = False
    return root_logger


logger = setup_logging()

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import structlog
from dynamic_mcp_skill_hub.config import get_settings


def configure_logging() -> None:
    """Configures centralized logging outputting structured JSON to both stdout and a rotating file."""
    settings = get_settings()
    log_dir = settings.log_dir
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Get the standard root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear pre-existing handlers to prevent duplicate logs
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Clean string formatter for direct output of structlog processed messages
    formatter = logging.Formatter("%(message)s")

    # 1. Stdout Handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # 2. Rotating File Handler (10MB per file, maximum 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Configure structlog to format logs and route them via standard library logging handlers
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Exported central logger namespace
logger = structlog.get_logger("dynamic_mcp_skill_hub")

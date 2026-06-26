"""
core.logging_setup — Structured logging for Stock JSON Clipper.

Provides a pre-configured logger with rotating file output.
Replaces ad-hoc error.log writes with proper leveled logging.

Usage:
    from core.logging_setup import get_logger
    log = get_logger(__name__)
    log.info("Starting fetch for %s", code)
    log.error("Fetch failed", exc_info=True)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_log_initialized = False


def init_logging(log_dir: str = "", level: int = logging.INFO) -> None:
    """Initialize rotating file logging.

    Creates StockJSONClipper.log with rotation (max 1MB, keep 3 backups).

    Args:
        log_dir: Directory for log files (default: current directory).
        level: Minimum log level.
    """
    global _log_initialized
    if _log_initialized:
        return

    log_path = os.path.join(log_dir or os.getcwd(), "StockJSONClipper.log")

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger("stock_clipper")
    root.setLevel(level)
    root.addHandler(handler)

    # Also log to console in debug mode
    if level <= logging.DEBUG:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root.addHandler(console)

    _log_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        Logger instance under the 'stock_clipper' hierarchy.
    """
    return logging.getLogger(f"stock_clipper.{name}")

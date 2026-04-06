"""Logging configuration for the selenium-mcp server."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO", debug: bool = False) -> None:
    """Set up structured console logging for the whole application."""
    log_level = logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO)

    fmt = (
        "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d - %(message)s"
        if debug
        else "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers unless in debug mode
    if not debug:
        for noisy in ("selenium", "urllib3", "asyncio"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger scoped to the selenium-mcp namespace."""
    return logging.getLogger(f"selenium_mcp.{name}")

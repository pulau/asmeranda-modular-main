"""
Bridge module for logging configuration in backend.core.
"""
from __future__ import annotations
import logging
from typing import Dict, Optional

_LOGGERS: Dict[str, logging.Logger] = {}
_CONFIGURED = False


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    force: bool = False,
) -> None:
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except Exception:
            pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=force,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        configure_logging()
    if name not in _LOGGERS:
        _LOGGERS[name] = logging.getLogger(name)
    return _LOGGERS[name]


__all__ = ["configure_logging", "get_logger"]

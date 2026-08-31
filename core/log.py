"""
Centralized logging configuration.

Idempotent: pemanggilan kedua di-skip kecuali ``force=True``.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

_LOGGERS: Dict[str, logging.Logger] = {}
_CONFIGURED = False


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    force: bool = False,
) -> None:
    """
    Konfigurasi root logger. Idempotent - pemanggilan kedua di-skip
    kecuali ``force=True``.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    target_file = log_file or os.environ.get("ASMERANDA_LOG_FILE", "app_errors.log")
    try:
        handlers.append(logging.FileHandler(target_file, encoding="utf-8"))
    except Exception:
        # File handler optional - jangan crash bila folder belum ada
        pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=force,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Kembalikan logger dengan nama tertentu (cached)."""
    if not _CONFIGURED:
        configure_logging()
    if name not in _LOGGERS:
        _LOGGERS[name] = logging.getLogger(name)
    return _LOGGERS[name]

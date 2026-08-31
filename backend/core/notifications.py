"""
Centralized Notification system for Asmeranda Backend.

Provides UI-framework agnostic notification and message bus functionality.
Compatible with WebSocket streaming and structured logging.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from backend.core.log import get_logger

_logger = get_logger("asmeranda.notify")

# Notification level constants
_INFO = "info"
_SUCCESS = "success"
_WARNING = "warning"
_ERROR = "error"
_WRITE = "write"


class Notification:
    """Representation of a single notification message."""

    __slots__ = ("id", "level", "message", "timestamp", "source")

    def __init__(self, level: str, message: Any, source: str = ""):
        self.id = uuid.uuid4().hex
        self.level = level
        self.message = message
        self.timestamp = time.time()
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "source": self.source,
        }


class MessageBus:
    """
    Thread-safe message bus for scoped notification broadcasting.
    """

    def __init__(self, maxlen: int = 1000):
        self._listeners: List[Callable[[Notification], None]] = []
        self._buffer: Deque[Notification] = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def subscribe(self, fn: Callable[[Notification], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(fn)

        def unsubscribe() -> None:
            with self._lock:
                if fn in self._listeners:
                    self._listeners.remove(fn)

        return unsubscribe

    def emit(self, notification: Notification) -> None:
        with self._lock:
            self._buffer.append(notification)
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(notification)
            except Exception as exc:
                _logger.warning("Notification listener error: %s", exc)

    def history(self, limit: Optional[int] = None) -> List[Notification]:
        with self._lock:
            items = list(self._buffer)
        if limit is not None:
            return items[-limit:]
        return items

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# Global MessageBus registry (per scope/session)
_LOCK = threading.RLock()
_BUSES: Dict[str, MessageBus] = {}


def get_bus(scope_id: Optional[str] = None) -> MessageBus:
    """Retrieve MessageBus instance for the specified scope."""
    key = scope_id or "default"
    with _LOCK:
        bus = _BUSES.get(key)
        if bus is None:
            bus = MessageBus()
            _BUSES[key] = bus
        return bus


def _emit(level: str, message: Any, source: str = "") -> None:
    log_fn = {
        _INFO: _logger.info,
        _SUCCESS: _logger.info,
        _WARNING: _logger.warning,
        _ERROR: _logger.error,
        _WRITE: _logger.debug,
    }.get(level, _logger.info)
    log_fn("[%s] %s", level.upper(), message)

    get_bus().emit(Notification(level, message, source))


def info(message: Any, source: str = "") -> None:
    _emit(_INFO, message, source)


def success(message: Any, source: str = "") -> None:
    _emit(_SUCCESS, message, source)


def warning(message: Any, source: str = "") -> None:
    _emit(_WARNING, message, source)


def error(message: Any, source: str = "") -> None:
    _emit(_ERROR, message, source)


def write(message: Any, source: str = "") -> None:
    _emit(_WRITE, message, source)


__all__ = [
    "Notification",
    "MessageBus",
    "get_bus",
    "info",
    "success",
    "warning",
    "error",
    "write",
]

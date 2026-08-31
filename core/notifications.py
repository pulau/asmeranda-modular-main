"""
Notification system - level UI-framework agnostic.

Menggantikan pemanggilan ``st.info``/``success``/``warning``/``error``/
``write`` yang sebelumnya tersebar di modul ML. Default: hanya log ke
logger + emit ke MessageBus. Bila Streamlit ``ScriptRunContext`` aktif,
otomatis diteruskan ke ``st.*`` agar legacy UI tidak kehilangan
tampilan notifikasi.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from .log import get_logger

_logger = get_logger("asmeranda.notify")

# Tipe notifikasi
_INFO = "info"
_SUCCESS = "success"
_WARNING = "warning"
_ERROR = "error"
_WRITE = "write"


def _streamlit_available() -> bool:
    """Best-effort check apakah kita di dalam script Streamlit yang aktif."""
    try:
        import streamlit as st  # type: ignore

        # Mendeteksi apakah ada ScriptRunContext aktif
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore

        return get_script_run_ctx() is not None
    except Exception:
        return False


_ST_ACTIVE = _streamlit_available()


class Notification:
    """Representasi satu pesan notifikasi."""

    __slots__ = ("id", "level", "message", "timestamp", "source")

    def __init__(self, level: str, message: Any, source: str = ""):
        self.id = uuid.uuid4().hex
        self.level = level
        # pesan bisa str, dict, list, atau markdown; simpan apa adanya
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
    Bus notifikasi per-scope (mis. per user / per session).

    Thread-safe. Setiap listener dipanggil dengan ``Notification``.
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
            except Exception as exc:  # pragma: no cover
                _logger.warning("Listener error: %s", exc)

    def history(self, limit: Optional[int] = None) -> List[Notification]:
        with self._lock:
            items = list(self._buffer)
        if limit is not None:
            return items[-limit:]
        return items

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# Registry global MessageBus (per-scope-id)
_LOCK = threading.RLock()
_BUSES: Dict[str, MessageBus] = {}


def get_bus(scope_id: Optional[str] = None) -> MessageBus:
    """Kembalikan MessageBus untuk scope tertentu (default: 'default')."""
    key = scope_id or "default"
    with _LOCK:
        bus = _BUSES.get(key)
        if bus is None:
            bus = MessageBus()
            _BUSES[key] = bus
        return bus


# ---------------------------------------------------------------------------
# Fungsi notifikasi tingkat-modul (pengganti st.info / st.success / dll)
# ---------------------------------------------------------------------------
def _emit(level: str, message: Any, source: str = "") -> None:
    # 1) Log ke logger
    log_fn = {
        _INFO: _logger.info,
        _SUCCESS: _logger.info,
        _WARNING: _logger.warning,
        _ERROR: _logger.error,
        _WRITE: _logger.debug,
    }.get(level, _logger.info)
    log_fn("[%s] %s", level.upper(), message)

    # 2) Emit ke MessageBus (jika ada listener - mis. WebSocket)
    get_bus().emit(Notification(level, message, source))

    # 3) Forward ke Streamlit ``st.*`` bila sedang aktif agar
    #    UI legacy tetap menampilkan notifikasi seperti biasa.
    if _ST_ACTIVE:
        try:
            import streamlit as _st  # type: ignore

            if level == _INFO:
                _st.info(message)
            elif level == _SUCCESS:
                _st.success(message)
            elif level == _WARNING:
                _st.warning(message)
            elif level == _ERROR:
                _st.error(message)
            elif level == _WRITE:
                _st.write(message)
        except Exception:
            # Jangan sampai error notifikasi menghambat alur utama
            pass


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

"""
Workflow state container untuk Asmeranda.

Tujuan:
- Menyimpan state workflow (data, target_column, X_train, dll) per-user
  atau per-session tanpa tergantung pada UI framework apapun.
- Otomatis bridge ke ``st.session_state`` jika dijalankan di legacy
  Streamlit UI (kompatibilitas mundur).
- Thread-safe untuk multi-user di backend FastAPI: setiap request
  membawa ``state_id`` dan state disimpan di registry in-memory
  dengan file-based persistence untuk survive restart.

API publik:
- ``get_state(state_id=None)`` -> dict
- ``set_state(state_id, **kwargs)`` -> None
- ``reset_state(state_id)`` -> None
- ``WorkflowState`` -> wrapper ergonomis
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Optional Streamlit bridge (hanya untuk backward compatibility UI legacy)
# ---------------------------------------------------------------------------
try:
    import streamlit as _st  # type: ignore
    _ST_AVAILABLE = True
except Exception:  # pragma: no cover - di backend FastAPI streamlit absen
    _st = None
    _ST_AVAILABLE = False


# Kunci default workflow (mirror SessionStateManager lama)
DEFAULT_KEYS: Dict[str, Any] = {
    "data": None,
    "processed_data": None,
    "target_column": None,
    "problem_type": None,
    "X_train": None,
    "X_test": None,
    "y_train": None,
    "y_test": None,
    "numerical_columns": [],
    "categorical_columns": [],
    "encoders": {},
    "scaler": None,
    "model_results": [],
    "is_time_series": False,
    "time_column": None,
    "clustering_results": None,
    "eda_insights": {},
    "model": None,
    "model_type": None,
    "forecasting_models": [],
    "forecast_results": None,
}


# ---------------------------------------------------------------------------
# In-memory state registry (digunakan oleh backend FastAPI; thread-safe)
# dengan file-based persistence untuk survive restart
# ---------------------------------------------------------------------------
_LOCK = threading.RLock()
_STATE_REGISTRY: Dict[str, Dict[str, Any]] = {}

# State persistence directory
_STATE_DIR = Path(__file__).resolve().parent.parent / "data" / "states"
_STATE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("asmeranda.core.state")


def _state_file_path(state_id: str) -> Path:
    """Get file path for state persistence."""
    return _STATE_DIR / f"{state_id}.json"


def _save_state_to_disk(state_id: str, state: Dict[str, Any]) -> None:
    """Save state to disk for persistence across restarts."""
    try:
        # Filter out non-serializable objects (DataFrames, models, etc.)
        serializable_state = {}
        for key, value in state.items():
            try:
                # Try to serialize - if it fails, skip this key
                json.dumps({key: value})
                serializable_state[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable objects
                serializable_state[key] = None
        
        state_file = _state_file_path(state_id)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(serializable_state, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning(f"Failed to save state {state_id} to disk: {exc}")


def _load_state_from_disk(state_id: str) -> Optional[Dict[str, Any]]:
    """Load state from disk if available."""
    try:
        state_file = _state_file_path(state_id)
        if not state_file.exists():
            return None
        
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to load state {state_id} from disk: {exc}")
        return None


def _load_all_states_from_disk() -> None:
    """Load all persisted states from disk at startup."""
    try:
        for state_file in _STATE_DIR.glob("*.json"):
            state_id = state_file.stem
            if state_id not in _STATE_REGISTRY:
                persisted_state = _load_state_from_disk(state_id)
                if persisted_state:
                    # Merge with defaults to ensure all keys exist
                    merged_state = dict(DEFAULT_KEYS)
                    merged_state.update(persisted_state)
                    _STATE_REGISTRY[state_id] = merged_state
                    logger.info(f"Loaded persisted state: {state_id}")
    except Exception as exc:
        logger.warning(f"Failed to load states from disk: {exc}")


# Load persisted states at startup
_load_all_states_from_disk()


def _new_state() -> Dict[str, Any]:
    """Buat dict state baru berisi default keys."""
    return dict(DEFAULT_KEYS)


def new_state_id() -> str:
    """Buat ID state baru (UUID4 string)."""
    return uuid.uuid4().hex


def get_state(state_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Ambil state.

    - Jika ``state_id`` None dan Streamlit aktif, kembalikan
      ``st.session_state`` (mode legacy).
    - Jika ``state_id`` None dan Streamlit tidak aktif, buat
      state default temporer (mode singleton - testing/CLI).
    - Jika ``state_id`` diberikan, ambil dari registry; bila belum ada,
      buat entry baru.
    """
    if state_id is None:
        if _ST_AVAILABLE:
            try:
                # Hanya gunakan st.session_state jika context streamlit aktif
                if hasattr(_st, "session_state") and bool(_st.session_state):
                    return _st.session_state  # type: ignore[union-attr]
            except Exception:
                pass
        # Fallback singleton untuk CLI/uji coba/FastAPI
        with _LOCK:
            if "_default" not in _STATE_REGISTRY:
                _STATE_REGISTRY["_default"] = _new_state()
            return _STATE_REGISTRY["_default"]

    with _LOCK:
        if state_id not in _STATE_REGISTRY:
            _STATE_REGISTRY[state_id] = _new_state()
        return _STATE_REGISTRY[state_id]


def set_state(state_id: Optional[str], **kwargs: Any) -> None:
    """Update beberapa key sekaligus pada state."""
    state = get_state(state_id)
    for key, value in kwargs.items():
        state[key] = value
    
    # Persist to disk if state_id is provided (not Streamlit mode)
    if state_id is not None:
        _save_state_to_disk(state_id, state)


def reset_state(state_id: Optional[str] = None) -> None:
    """Reset state ke default. Untuk ``state_id=None`` di legacy,
    hanya workflow keys yang di-reset (key global seperti 'language'
    dipertahankan)."""
    if state_id is None and _ST_AVAILABLE:
        try:
            if hasattr(_st, "session_state"):
                state = _st.session_state  # type: ignore[union-attr]
                for key, default in DEFAULT_KEYS.items():
                    state[key] = default
                return
        except Exception:
            pass

    with _LOCK:
        if state_id is None:
            _STATE_REGISTRY["_default"] = _new_state()
        else:
            _STATE_REGISTRY[state_id] = _new_state()


def delete_state(state_id: str) -> None:
    """Hapus state dari registry dan disk (untuk logout / cleanup)."""
    with _LOCK:
        _STATE_REGISTRY.pop(state_id, None)
    
    # Remove persisted file
    try:
        state_file = _state_file_path(state_id)
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Deleted persisted state file: {state_id}")
    except Exception as exc:
        logger.warning(f"Failed to delete state file {state_id}: {exc}")


def list_states() -> Dict[str, Dict[str, Any]]:
    """Khusus untuk debugging/admin - kembalikan salinan registry."""
    with _LOCK:
        return {k: dict(v) for k, v in _STATE_REGISTRY.items()}


# Alias for test backwards compatibility
_states = _STATE_REGISTRY


# ---------------------------------------------------------------------------
# WorkflowState - thin wrapper untuk API yang lebih ergonomis
# ---------------------------------------------------------------------------
class WorkflowState:
    """
    Wrapper state yang bisa di-inject ke validator/service manapun.
    Mendukung dot-access (``state.target_column``) dan dict-access
    (``state["target_column"]``).
    """

    def __init__(self, state_id: Optional[str] = None):
        self._state_id = state_id
        self._state = get_state(state_id)

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def state_id(self) -> Optional[str]:
        return self._state_id

    def __getitem__(self, key: str) -> Any:
        return self._state.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._state

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, **kwargs: Any) -> "WorkflowState":
        for k, v in kwargs.items():
            self._state[k] = v
        return self

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._state)

    def keys(self):
        return self._state.keys()


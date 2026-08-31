"""
Bridge module for Workflow state container in backend.core.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Ensure root directory is on sys.path so root core can be loaded if present
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("asmeranda.core.state")

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

_LOCK = threading.RLock()
_STATE_REGISTRY: Dict[str, Dict[str, Any]] = {}
_states = _STATE_REGISTRY

_STATE_DIR = _PROJECT_ROOT / "data" / "states"
try:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


def _new_state() -> Dict[str, Any]:
    return dict(DEFAULT_KEYS)


def new_state_id() -> str:
    return uuid.uuid4().hex


def get_state(state_id: Optional[str] = None) -> Dict[str, Any]:
    if state_id is None:
        with _LOCK:
            if "_default" not in _STATE_REGISTRY:
                _STATE_REGISTRY["_default"] = _new_state()
            return _STATE_REGISTRY["_default"]

    with _LOCK:
        if state_id not in _STATE_REGISTRY:
            _STATE_REGISTRY[state_id] = _new_state()
        return _STATE_REGISTRY[state_id]


def set_state(state_id: Optional[str] = None, **kwargs: Any) -> None:
    state = get_state(state_id)
    with _LOCK:
        for key, value in kwargs.items():
            state[key] = value


def reset_state(state_id: Optional[str] = None) -> None:
    with _LOCK:
        if state_id is None:
            _STATE_REGISTRY["_default"] = _new_state()
        else:
            _STATE_REGISTRY[state_id] = _new_state()


def delete_state(state_id: str) -> None:
    with _LOCK:
        _STATE_REGISTRY.pop(state_id, None)


def list_states() -> Dict[str, Dict[str, Any]]:
    with _LOCK:
        return {k: dict(v) for k, v in _STATE_REGISTRY.items()}


def get_all_state_ids() -> List[str]:
    with _LOCK:
        return list(_STATE_REGISTRY.keys())


def cleanup_old_states(max_age_seconds: int = 86400) -> int:
    return 0


class WorkflowState:
    def __init__(self, state_id: Optional[str] = None):
        self._state_id = state_id
        self._state = get_state(state_id)

    @property
    def state_id(self) -> Optional[str]:
        return self._state_id

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def raw(self) -> Dict[str, Any]:
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, **kwargs: Any) -> None:
        set_state(self._state_id, **kwargs)

    def update(self, **kwargs: Any) -> None:
        set_state(self._state_id, **kwargs)

    def reset(self) -> None:
        reset_state(self._state_id)

    def delete(self) -> None:
        if self._state_id:
            delete_state(self._state_id)

    def is_empty(self) -> bool:
        return self._state.get("data") is None

    def has_preprocessed(self) -> bool:
        return self._state.get("processed_data") is not None

    def has_model(self) -> bool:
        return (
            self._state.get("model") is not None
            or bool(self._state.get("model_results"))
            or bool(self._state.get("forecasting_models"))
        )

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        set_state(self._state_id, **{key: value})

    def __contains__(self, key: str) -> bool:
        return key in self._state

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        state = self.__dict__.get("_state")
        if state is not None and name in state:
            return state[name]
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
            return
        state = self.__dict__.get("_state")
        if state is not None and name in DEFAULT_KEYS:
            set_state(self._state_id, **{name: value})
        else:
            super().__setattr__(name, value)


__all__ = [
    "DEFAULT_KEYS",
    "WorkflowState",
    "get_state",
    "set_state",
    "reset_state",
    "delete_state",
    "list_states",
    "new_state_id",
    "get_all_state_ids",
    "cleanup_old_states",
    "_states",
]

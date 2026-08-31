"""Health-check & info endpoint."""
from __future__ import annotations

import platform
import sys
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
def health() -> Dict[str, Any]:
    """Cek bahwa service hidup. Return versi Python & platform juga."""
    return {
        "status": "ok",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }


@router.get("/info", response_model=Dict[str, Any])
def info() -> Dict[str, Any]:
    """Informasi service."""
    return {
        "service": "asmeranda-backend",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/api/v1/datasets",
            "/api/v1/eda/{dataset_id}",
            "/api/v1/preprocessing",
            "/api/v1/training",
        ],
    }

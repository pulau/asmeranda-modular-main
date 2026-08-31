"""
Endpoint /interpretation - SHAP & LIME untuk model yang sudah dilatih.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services import interpretation_service

logger = logging.getLogger("asmeranda.api.interpretation")
router = APIRouter()


class ShapRequest(BaseModel):
    model_id: str
    state_id: Optional[str] = None
    max_samples: int = Field(default=200, ge=10, le=5000)


class LimeRequest(BaseModel):
    model_id: str
    state_id: Optional[str] = None
    sample_index: int = 0
    num_features: int = Field(default=10, ge=1, le=50)


@router.post("/shap")
def run_shap(req: ShapRequest) -> Dict[str, Any]:
    """Hitung SHAP values untuk model."""
    try:
        return interpretation_service.run_shap(
            model_id=req.model_id,
            state_id=req.state_id,
            max_samples=req.max_samples,
        )
    except Exception as exc:
        logger.exception("SHAP gagal")
        return {"success": False, "error": str(exc)}


@router.post("/lime")
def run_lime(req: LimeRequest) -> Dict[str, Any]:
    """Hitung LIME explanation untuk satu instance."""
    try:
        return interpretation_service.run_lime(
            model_id=req.model_id,
            state_id=req.state_id,
            sample_index=req.sample_index,
            num_features=req.num_features,
        )
    except Exception as exc:
        logger.exception("LIME gagal")
        return {"success": False, "error": str(exc)}

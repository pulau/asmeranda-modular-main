"""
Endpoint /timeseries - forecasting & anomaly detection.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services import timeseries_service

logger = logging.getLogger("asmeranda.api.timeseries")
router = APIRouter()


@router.get("/{dataset_id}/detect")
def detect(dataset_id: str, target_column: Optional[str] = None, date_column: Optional[str] = None):
    """Analisis awal: stationarity, anomaly count, summary stats."""
    try:
        return timeseries_service.detect_timeseries(dataset_id, target_column, date_column)
    except Exception as exc:
        logger.exception("Timeseries detect gagal")
        return {"success": False, "error": str(exc)}


@router.get("/{dataset_id}/forecast")
def forecast(
    dataset_id: str,
    target_column: str,
    horizon: int = Query(default=10, ge=1, le=500),
    method: str = Query(default="naive", pattern="^(naive|drift|mean)$"),
    date_column: Optional[str] = None,
):
    """Forecast sederhana (naive / drift / mean)."""
    try:
        return timeseries_service.forecast(
            dataset_id=dataset_id,
            target_column=target_column,
            date_column=date_column,
            horizon=horizon,
            method=method,
        )
    except Exception as exc:
        logger.exception("Timeseries forecast gagal")
        return {"success": False, "error": str(exc)}


@router.get("/{dataset_id}/anomalies")
def anomalies(
    dataset_id: str,
    target_column: str,
    contamination: float = Query(default=0.05, ge=0.001, le=0.5),
):
    """Deteksi anomali dengan IsolationForest."""
    try:
        return timeseries_service.anomaly_detection(
            dataset_id=dataset_id,
            target_column=target_column,
            contamination=contamination,
        )
    except Exception as exc:
        logger.exception("Timeseries anomaly gagal")
        return {"success": False, "error": str(exc)}

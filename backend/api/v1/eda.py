"""
Endpoint /eda - Exploratory Data Analysis (summary, correlation, dll).
"""
from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd
import polars as pl
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.models import EdaCorrelationResponse, EdaSummaryResponse, RecommendationRequest, RecommendationResponse
from backend.services import dataset_service
from backend.services.recommendation_service import RecommendationService

logger = logging.getLogger("asmeranda.api.eda")
router = APIRouter()
recommendation_service = RecommendationService()


@router.get("/{dataset_id}/summary", response_model=EdaSummaryResponse)
def summary(dataset_id: str) -> EdaSummaryResponse:
    """Ringkasan dataset: shape, dtypes, describe, missing values."""
    try:
        result = dataset_service.summary(dataset_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} tidak ditemukan")
        return EdaSummaryResponse(success=True, **result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("EDA summary gagal")
        return EdaSummaryResponse(success=False, error=str(exc))


@router.get("/{dataset_id}/correlation", response_model=EdaCorrelationResponse)
def correlation(
    dataset_id: str,
    columns: str = Query(default="", description="Comma-separated column names; kosong = semua numerik"),
) -> EdaCorrelationResponse:
    """Matriks korelasi Pearson antar kolom numerik."""
    try:
        df = dataset_service.get_dataset_pl(dataset_id)
        if df is None:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} tidak ditemukan")

        if columns.strip():
            cols = [c.strip() for c in columns.split(",") if c.strip()]
            num_df = df.select(cols).select(pl.col(pl.NUMERIC_DTYPES))
        else:
            num_df = df.select(pl.col(pl.NUMERIC_DTYPES))

        if num_df.width < 2:
            return EdaCorrelationResponse(
                success=False,
                error="Butuh minimal 2 kolom numerik untuk korelasi.",
            )

        # Pandas provides a stable Pearson correlation matrix for the active
        # Polars-backed datasets used in this app.
        corr_pd = num_df.to_pandas().corr(method="pearson").fillna(0.0).replace([np.inf, -np.inf], 0.0)
        matrix = corr_pd.round(4).values.tolist()
        return EdaCorrelationResponse(
            success=True,
            columns=corr_pd.columns.tolist(),
            matrix=matrix,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return EdaCorrelationResponse(success=False, error=str(exc))


@router.get("/{dataset_id}/data")
def paginated_data(
    dataset_id: str,
    page: int = Query(1, ge=1, description="Nomor halaman"),
    size: int = Query(50, ge=1, le=1000, description="Jumlah baris per halaman"),
):
    """Ambil sebagian raw data (server-side pagination)"""
    try:
        result = dataset_service.get_paginated_data(dataset_id, page, size)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} tidak ditemukan")
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Paginated data gagal")
        return {"success": False, "error": str(exc)}


# TEMPORARY: Recommendations endpoint added here for immediate functionality
@router.post("/analyze", response_model=RecommendationResponse)
def analyze_dataset(config: RecommendationRequest) -> RecommendationResponse:
    """Analyze dataset and provide AI-powered recommendations."""
    try:
        data = dataset_service.get_dataset(config.dataset_id)
        if data is None:
            logger.warning(
                "Dataset not found for recommendation analysis",
                extra={"dataset_id": config.dataset_id}
            )
            return RecommendationResponse(
                success=False,
                error=f"Dataset {config.dataset_id} not found"
            )

        result = recommendation_service.analyze_dataset(data)

        if not result.get("success"):
            return RecommendationResponse(
                success=False,
                error=result.get("error")
            )

        preprocessing_steps = recommendation_service.recommend_preprocessing(data)

        logger.info(
            "Dataset analysis completed successfully",
            extra={
                "dataset_id": config.dataset_id,
                "n_recommendations": len(result.get("recommendations", [])),
                "detected_problem_type": result.get("detected_problem_type")
            }
        )

        return RecommendationResponse(
            success=True,
            recommendations=result.get("recommendations"),
            dataset_info=result.get("dataset_info"),
            preprocessing_steps=preprocessing_steps
        )

    except Exception as exc:
        logger.error(
            "Dataset analysis failed",
            exc_info=True,
            extra={
                "dataset_id": config.dataset_id,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")

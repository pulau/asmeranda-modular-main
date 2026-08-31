"""
Endpoint /recommendations - AI-powered dataset analysis and recommendations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.schemas.models import RecommendationRequest, RecommendationResponse
from backend.services.recommendation_service import RecommendationService
from backend.services import dataset_service

logger = logging.getLogger("asmeranda.api.recommendations")
router = APIRouter()
recommendation_service = RecommendationService()


@router.post("/analyze", response_model=RecommendationResponse)
def analyze_dataset(config: RecommendationRequest) -> RecommendationResponse:
    """Analyze dataset and provide AI-powered recommendations."""
    try:
        dataset_id = config.dataset_id
        
        # Get dataset
        data = dataset_service.get_dataset(dataset_id)
        if data is None:
            logger.warning(
                "Dataset not found for recommendation analysis",
                extra={"dataset_id": dataset_id}
            )
            return RecommendationResponse(
                success=False,
                error=f"Dataset {dataset_id} not found"
            )

        # Perform analysis
        result = recommendation_service.analyze_dataset(data)

        if not result.get("success"):
            return RecommendationResponse(
                success=False,
                error=result.get("error")
            )

        # Get preprocessing recommendations
        preprocessing_steps = recommendation_service.recommend_preprocessing(data)

        logger.info(
            "Dataset analysis completed successfully",
            extra={
                "dataset_id": dataset_id,
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

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Dataset analysis failed",
            exc_info=True,
            extra={
                "dataset_id": dataset_id,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")
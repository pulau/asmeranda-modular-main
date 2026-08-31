"""
Endpoint /preprocessing - jalankan preprocessing dan simpan ke state.
"""
from __future__ import annotations

import logging
import pandas as pd

from fastapi import APIRouter, HTTPException

from backend.schemas.models import PreprocessingConfig, PreprocessingResponse, ClusteringConfig, ClusteringResponse
from backend.services import preprocessing_service
from backend.services.clustering_service import ClusteringService
from core.state import get_state

logger = logging.getLogger("asmeranda.api.preprocessing")
router = APIRouter()
clustering_service = ClusteringService()


@router.post("/run", response_model=PreprocessingResponse)
def run_preprocessing(config: PreprocessingConfig) -> PreprocessingResponse:
    """Jalankan preprocessing sesuai konfigurasi."""
    try:
        result = preprocessing_service.run(config.dict())
        if not result.get("success"):
            return PreprocessingResponse(success=False, error=result.get("error"))
        return PreprocessingResponse(
            success=True,
            state_id=result["state_id"],
            n_samples_train=result["n_samples_train"],
            n_samples_test=result["n_samples_test"],
            n_features=result["n_features"],
            feature_names=result["feature_names"],
            target_column=result["target_column"],
            problem_type=result["problem_type"],
            preprocessing_steps=result["preprocessing_steps"],
            feature_selection_info=result.get("feature_selection_info"),
            imbalance_handling_info=result.get("imbalance_handling_info"),
        )
    except Exception as exc:
        logger.exception("Preprocessing gagal")
        return PreprocessingResponse(success=False, error=str(exc))


# TEMPORARY: Clustering endpoints added here for immediate functionality
@router.post("/cluster", response_model=ClusteringResponse)
def perform_clustering(config: ClusteringConfig) -> ClusteringResponse:
    """Perform clustering analysis on training data."""
    try:
        state = get_state(config.state_id)
        X_train = state.get("X_train")

        if X_train is None:
            return ClusteringResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        result = clustering_service.perform_clustering(
            X_train, method=config.method, **config.parameters
        )

        if not result.get("success"):
            return ClusteringResponse(
                success=False,
                error=result.get("error"),
                method=config.method
            )

        state["clustering_results"] = {
            "labels": result["labels"],
            "method": result["method"],
            "metrics": result["metrics"],
            "parameters": result["parameters"],
        }

        return ClusteringResponse(
            success=True,
            labels=result["labels"],
            metrics=result["metrics"],
            method=result["method"],
            parameters=result["parameters"]
        )

    except Exception as exc:
        logger.error("Clustering operation failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(exc)}")


@router.post("/optimal-k")
def find_optimal_k(config: ClusteringConfig):
    """Find optimal number of clusters using elbow and silhouette methods."""
    try:
        state = get_state(config.state_id)
        X_train = state.get("X_train")

        if X_train is None:
            return {"success": False, "error": "No training data available"}

        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)

        max_k = config.parameters.get("max_k", 10)
        result = clustering_service.find_optimal_k(X_scaled, max_k=max_k)

        if not result.get("success"):
            return {"success": False, "error": result.get("error")}

        return {"success": True, **result}

    except Exception as exc:
        logger.error("Optimal k calculation failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimal k calculation failed: {str(exc)}")

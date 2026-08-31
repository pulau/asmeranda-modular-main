"""
Endpoint /clustering - unsupervised learning clustering operations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.schemas.models import ClusteringConfig, ClusteringResponse
from backend.services.clustering_service import ClusteringService
from core.state import get_state

logger = logging.getLogger("asmeranda.api.clustering")
router = APIRouter()
clustering_service = ClusteringService()


@router.post("/cluster", response_model=ClusteringResponse)
def perform_clustering(config: ClusteringConfig) -> ClusteringResponse:
    """Perform clustering analysis on training data."""
    try:
        # Get data from state
        state = get_state(config.state_id)
        X_train = state.get("X_train")

        if X_train is None:
            logger.warning(
                "No training data available for clustering",
                extra={"state_id": config.state_id, "method": config.method}
            )
            return ClusteringResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        # Convert to DataFrame if needed
        import pandas as pd
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        # Perform clustering
        result = clustering_service.perform_clustering(
            X_train, method=config.method, **config.parameters
        )

        if not result.get("success"):
            return ClusteringResponse(
                success=False,
                error=result.get("error"),
                method=config.method
            )

        # Store clustering results in state for later use
        state["clustering_results"] = {
            "labels": result["labels"],
            "method": result["method"],
            "metrics": result["metrics"],
            "parameters": result["parameters"],
        }

        logger.info(
            "Clustering completed successfully",
            extra={
                "state_id": config.state_id,
                "method": config.method,
                "n_clusters": result["metrics"].get("n_clusters", 0)
            }
        )

        return ClusteringResponse(
            success=True,
            labels=result["labels"],
            metrics=result["metrics"],
            method=result["method"],
            parameters=result["parameters"]
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Clustering operation failed",
            exc_info=True,
            extra={
                "state_id": config.state_id,
                "method": config.method,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(exc)}")


@router.post("/optimal-k")
def find_optimal_k(config: ClusteringConfig):
    """Find optimal number of clusters using elbow and silhouette methods."""
    try:
        # Get data from state
        state = get_state(config.state_id)
        X_train = state.get("X_train")

        if X_train is None:
            logger.warning(
                "No training data available for optimal k analysis",
                extra={"state_id": config.state_id}
            )
            return {"success": False, "error": "No training data available"}

        # Convert to DataFrame if needed
        import pandas as pd
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        # Scale data for optimal k analysis
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_train)

        # Find optimal k
        max_k = config.parameters.get("max_k", 10)
        result = clustering_service.find_optimal_k(X_scaled, max_k=max_k)

        if not result.get("success"):
            return {"success": False, "error": result.get("error")}

        logger.info(
            "Optimal k analysis completed",
            extra={
                "state_id": config.state_id,
                "optimal_k_elbow": result.get("optimal_k_elbow"),
                "optimal_k_silhouette": result.get("optimal_k_silhouette")
            }
        )

        return {"success": True, **result}

    except Exception as exc:
        logger.error(
            "Optimal k calculation failed",
            exc_info=True,
            extra={
                "state_id": config.state_id,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Optimal k calculation failed: {str(exc)}")
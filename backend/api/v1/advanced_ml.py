"""
Advanced ML API endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.advanced_ml_service import AdvancedMLService
from backend.services.utilities_service import UtilitiesService
from core.state import get_state

logger = logging.getLogger("asmeranda.api.advanced_ml")
router = APIRouter()
advanced_ml_service = AdvancedMLService()
utilities_service = UtilitiesService()


# Request Models
class UMAPRequest(BaseModel):
    state_id: str
    n_components: int = 2
    n_neighbors: int = 15
    min_dist: float = 0.1


class HDBSCANRequest(BaseModel):
    state_id: str
    min_cluster_size: int = 5
    min_samples: Optional[int] = None
    metric: str = 'euclidean'


class AnomalyDetectionRequest(BaseModel):
    state_id: str
    method: str = 'isolation_forest'  # isolation_forest | one_class_svm
    contamination: float = 0.1
    n_estimators: int = 100


class ForecastingRequest(BaseModel):
    state_id: str
    target_column: str
    periods: int = 10
    method: str = 'arima'  # arima | sarima | prophet | lstm | simple | moving_avg | linear


class MissingValueRequest(BaseModel):
    state_id: str
    strategy: str = 'auto'
    numeric_strategy: str = 'mean'
    categorical_strategy: str = 'mode'
    threshold: float = 0.5


class OutlierDetectionRequest(BaseModel):
    state_id: str
    method: str = 'iqr'
    threshold: float = 1.5
    columns: Optional[list] = None


class DataValidationRequest(BaseModel):
    state_id: str
    required_columns: Optional[list] = None
    column_types: Optional[dict] = None
    value_ranges: Optional[dict] = None


# Response Models
class UMAPResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    error: Optional[str] = None


class ClusteringResponse(BaseModel):
    success: bool
    labels: Optional[list] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    n_clusters: Optional[int] = None
    n_noise: Optional[int] = None
    error: Optional[str] = None


class AnomalyDetectionResponse(BaseModel):
    success: bool
    anomaly_labels: Optional[list] = None
    anomaly_scores: Optional[list] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    n_anomalies: Optional[int] = None
    anomaly_rate: Optional[float] = None
    error: Optional[str] = None


class ForecastingResponse(BaseModel):
    success: bool
    forecast: Optional[list] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    last_observed: Optional[float] = None
    error: Optional[str] = None


class DataProcessingResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    original_shape: Optional[tuple] = None
    new_shape: Optional[tuple] = None
    error: Optional[str] = None


# Endpoints
@router.post("/umap", response_model=UMAPResponse)
def umap_dimensionality_reduction(request: UMAPRequest) -> UMAPResponse:
    """Perform UMAP dimensionality reduction."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return UMAPResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = advanced_ml_service.umap_dimensionality_reduction(
            data=data,
            n_components=request.n_components,
            n_neighbors=request.n_neighbors,
            min_dist=request.min_dist
        )
        
        if result["success"]:
            # Convert DataFrame to dict for JSON serialization
            if "data" in result and hasattr(result["data"], "to_dict"):
                result["data"] = result["data"].to_dict(orient="records")
        
        return UMAPResponse(**result)
        
    except Exception as e:
        logger.error(f"UMAP dimensionality reduction failed: {e}")
        return UMAPResponse(success=False, error=str(e))


@router.post("/hdbscan", response_model=ClusteringResponse)
def hdbscan_clustering(request: HDBSCANRequest) -> ClusteringResponse:
    """Perform HDBSCAN clustering."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return ClusteringResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = advanced_ml_service.hdbscan_clustering(
            data=data,
            min_cluster_size=request.min_cluster_size,
            min_samples=request.min_samples,
            metric=request.metric
        )
        
        return ClusteringResponse(**result)
        
    except Exception as e:
        logger.error(f"HDBSCAN clustering failed: {e}")
        return ClusteringResponse(success=False, error=str(e))


@router.post("/anomaly-detection", response_model=AnomalyDetectionResponse)
def anomaly_detection(request: AnomalyDetectionRequest) -> AnomalyDetectionResponse:
    """Perform anomaly detection."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return AnomalyDetectionResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        if request.method == 'isolation_forest':
            result = advanced_ml_service.isolation_forest_anomaly_detection(
                data=data,
                contamination=request.contamination,
                n_estimators=request.n_estimators
            )
        elif request.method == 'one_class_svm':
            result = advanced_ml_service.one_class_svm_anomaly_detection(
                data=data,
                nu=request.contamination,
                kernel='rbf'
            )
        else:
            return AnomalyDetectionResponse(
                success=False,
                error=f"Unknown method: {request.method}"
            )
        
        return AnomalyDetectionResponse(**result)
        
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return AnomalyDetectionResponse(success=False, error=str(e))


@router.post("/forecast", response_model=ForecastingResponse)
def forecast(request: ForecastingRequest) -> ForecastingResponse:
    """Perform time series forecasting."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return ForecastingResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        if request.target_column not in data.columns:
            return ForecastingResponse(
                success=False,
                error=f"Column {request.target_column} not found in data"
            )
        
        result = advanced_ml_service.basic_forecasting(
            data=data,
            target_column=request.target_column,
            periods=request.periods,
            method=request.method
        )
        
        return ForecastingResponse(**result)
        
    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        return ForecastingResponse(success=False, error=str(e))


@router.post("/handle-missing-values", response_model=DataProcessingResponse)
def handle_missing_values(request: MissingValueRequest) -> DataProcessingResponse:
    """Handle missing values in the dataset."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return DataProcessingResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = utilities_service.handle_missing_values(
            data=data,
            strategy=request.strategy,
            numeric_strategy=request.numeric_strategy,
            categorical_strategy=request.categorical_strategy,
            threshold=request.threshold
        )
        
        if result["success"]:
            # Update state with cleaned data
            state["training_data"] = result["data"].to_dict(orient="records")
            # Convert shapes to lists for JSON serialization
            result["original_shape"] = list(result["original_shape"])
            result["new_shape"] = list(result["new_shape"])
            if "data" in result:
                result["data"] = {"shape": result["new_shape"], "processed": True}
        
        return DataProcessingResponse(**result)
        
    except Exception as e:
        logger.error(f"Missing value handling failed: {e}")
        return DataProcessingResponse(success=False, error=str(e))


@router.post("/detect-outliers", response_model=DataProcessingResponse)
def detect_outliers(request: OutlierDetectionRequest) -> DataProcessingResponse:
    """Detect outliers in the dataset."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return DataProcessingResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = utilities_service.detect_outliers(
            data=data,
            method=request.method,
            threshold=request.threshold,
            columns=request.columns
        )
        
        return DataProcessingResponse(data=result)
        
    except Exception as e:
        logger.error(f"Outlier detection failed: {e}")
        return DataProcessingResponse(success=False, error=str(e))


@router.post("/validate-data", response_model=DataProcessingResponse)
def validate_data(request: DataValidationRequest) -> DataProcessingResponse:
    """Validate data against constraints."""
    try:
        state = get_state(request.state_id)
        if not state or "training_data" not in state:
            return DataProcessingResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = utilities_service.validate_data(
            data=data,
            required_columns=request.required_columns,
            column_types=request.column_types,
            value_ranges=request.value_ranges
        )
        
        return DataProcessingResponse(data=result)
        
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        return DataProcessingResponse(success=False, error=str(e))


@router.post("/detect-data-types")
def detect_data_types(state_id: str) -> Dict[str, Any]:
    """Detect data types for all columns."""
    try:
        state = get_state(state_id)
        if not state or "training_data" not in state:
            return {"success": False, "error": "No training data available"}
        
        import pandas as pd
        data = pd.DataFrame(state["training_data"])
        
        result = utilities_service.detect_data_types(data)
        return {"success": True, "data_types": result}
        
    except Exception as e:
        logger.error(f"Data type detection failed: {e}")
        return {"success": False, "error": str(e)}
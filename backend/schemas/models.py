"""
Pydantic schemas untuk request/response API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class DatasetMetadata(BaseModel):
    dataset_id: str
    filename: str
    rows: int
    columns: int
    column_names: List[str]
    numerical_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str] = []
    size_bytes: int
    uploaded_at: str


class DatasetListResponse(BaseModel):
    datasets: List[DatasetMetadata]
    total: int


class DatasetUploadResponse(BaseModel):
    success: bool
    metadata: Optional[DatasetMetadata] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# EDA
# ---------------------------------------------------------------------------
class EdaSummaryResponse(BaseModel):
    success: bool
    metadata: Optional[Dict[str, Any]] = None
    shape: Optional[Dict[str, int]] = None
    dtypes: Optional[Dict[str, str]] = None
    describe_numeric: Optional[Dict[str, Any]] = None
    describe_categorical: Optional[Dict[str, Any]] = None
    missing: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EdaCorrelationResponse(BaseModel):
    success: bool
    columns: Optional[List[str]] = None
    matrix: Optional[List[List[float]]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
class FeatureSelectionConfig(BaseModel):
    method: str = "none"  # none|variance|correlation|kbest|rfe
    max_features: int = 10
    threshold: float = 0.05


class ImbalanceConfig(BaseModel):
    method: str = "none"  # none|oversample|undersample|smote|adasyn
    sampling_strategy: str = "auto"


class PreprocessingConfig(BaseModel):
    dataset_id: str
    target_column: Optional[str] = None
    problem_type: Optional[str] = Field(default=None, pattern="^(Classification|Regression|Forecasting)$")
    numerical_features: Optional[List[str]] = None
    categorical_features: Optional[List[str]] = None
    scaling_method: str = "auto"  # auto|standard|minmax|robust|power|quantile
    imputation_strategy: str = "auto"  # auto|mean|median|most_frequent|drop
    apply_polynomial: bool = False
    apply_binning: bool = False
    apply_encoding: bool = True
    feature_selection: Optional[FeatureSelectionConfig] = None
    imbalance_handling: Optional[ImbalanceConfig] = None
    test_size: float = 0.2
    random_state: int = 42


class PreprocessingResponse(BaseModel):
    success: bool
    state_id: Optional[str] = None
    n_samples_train: Optional[int] = None
    n_samples_test: Optional[int] = None
    n_features: Optional[int] = None
    feature_names: Optional[List[str]] = None
    target_column: Optional[str] = None
    problem_type: Optional[str] = None
    preprocessing_steps: Optional[List[str]] = None
    feature_selection_info: Optional[Dict[str, Any]] = None
    imbalance_handling_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
class TrainingConfig(BaseModel):
    state_id: str
    model_type: str = "RandomForest"
    problem_type: str = "Classification"
    hyperparams: Optional[Dict[str, Any]] = None
    cv_method: str = "kfold"  # none|kfold|stratified|loo|timeseries
    cv_folds: int = 5
    random_state: int = 42


class EvaluationConfig(BaseModel):
    state_id: str
    model_id: str
    generate_plots: bool = True
    plot_types: List[str] = ["confusion_matrix", "roc_curve", "feature_importance"]


class TrainingResponse(BaseModel):
    success: bool
    model_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    cv_scores: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None  # For background task status messages


class EvaluationResponse(BaseModel):
    success: bool
    model_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    plots: Optional[Dict[str, str]] = None  # plot_type -> base64_encoded_image
    error: Optional[str] = None


class PredictionRequest(BaseModel):
    data: List[Dict[str, Any]]  # Input data for prediction


class PredictionResponse(BaseModel):
    success: bool
    predictions: Optional[List[Any]] = None
    probabilities: Optional[List[List[float]]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------
class ClusteringConfig(BaseModel):
    state_id: str
    method: str = "kmeans"  # kmeans, dbscan, hierarchical, spectral
    parameters: Dict[str, Any] = {}


class ClusteringResponse(BaseModel):
    success: bool
    labels: Optional[List[int]] = None
    metrics: Optional[Dict[str, Any]] = None
    method: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Advanced ML
# ---------------------------------------------------------------------------
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


class UMAPResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    error: Optional[str] = None


class AdvancedClusteringResponse(BaseModel):
    success: bool
    labels: Optional[list] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    n_clusters: Optional[int] = None
    n_noise: Optional[int] = None
    error: Optional[str] = None


class AdvancedAnomalyDetectionResponse(BaseModel):
    success: bool
    anomaly_labels: Optional[list] = None
    anomaly_scores: Optional[list] = None
    method: Optional[str] = None
    parameters: Optional[dict] = None
    n_anomalies: Optional[int] = None
    anomaly_rate: Optional[float] = None
    error: Optional[str] = None


class AdvancedForecastingResponse(BaseModel):
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


# ---------------------------------------------------------------------------
# Advanced Supervised ML
# ---------------------------------------------------------------------------
class LearningCurveRequest(BaseModel):
    state_id: str
    model_id: str
    cv: int = 5
    train_sizes: Optional[str] = None  # JSON string of list


class ModelComparisonRequest(BaseModel):
    state_id: str
    model_types: Optional[str] = None  # JSON string of list
    cv_method: str = "kfold"
    cv_folds: int = 5


class LearningCurveResponse(BaseModel):
    success: bool
    model_id: Optional[str] = None
    plot_base64: Optional[str] = None
    train_sizes: Optional[List[float]] = None
    train_scores_mean: Optional[List[float]] = None
    test_scores_mean: Optional[List[float]] = None
    final_train_score: Optional[float] = None
    final_test_score: Optional[float] = None
    score_gap: Optional[float] = None
    diagnosis: Optional[str] = None
    scoring: Optional[str] = None
    cv_folds: Optional[int] = None
    error: Optional[str] = None


class ModelComparisonResponse(BaseModel):
    success: bool
    problem_type: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    ranking: Optional[List[Dict[str, Any]]] = None
    best_model: Optional[Dict[str, Any]] = None
    ranking_metric: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------
class OptimizationConfig(BaseModel):
    state_id: str
    model_type: str = "RandomForest"
    problem_type: str = "Classification"
    method: str = "grid_search"  # grid_search, random_search, bayesian
    cv_folds: int = 5
    n_iter: int = 50  # for random_search and bayesian


class OptimizationResponse(BaseModel):
    success: bool
    best_params: Optional[Dict[str, Any]] = None
    best_score: Optional[float] = None
    method: Optional[str] = None
    cv_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
class RecommendationRequest(BaseModel):
    dataset_id: str


class RecommendationResponse(BaseModel):
    success: bool
    recommendations: Optional[List[Dict[str, Any]]] = None
    dataset_info: Optional[Dict[str, Any]] = None
    preprocessing_steps: Optional[List[str]] = None
    error: Optional[str] = None

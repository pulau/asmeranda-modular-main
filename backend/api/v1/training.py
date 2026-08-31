"""
Endpoint /training - latih model dari state hasil preprocessing.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from pathlib import Path

import pandas as pd

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.schemas.models import (
    TrainingConfig, TrainingResponse, EvaluationConfig, 
    EvaluationResponse, PredictionRequest, PredictionResponse,
    OptimizationConfig, OptimizationResponse,
    LearningCurveRequest, ModelComparisonRequest
)
from backend.services import training_service, evaluation_service
from backend.services.optimization_service import OptimizationService
from backend.core.config import settings
from backend.core.security_audit import audit_logger
from core.state import get_state

logger = logging.getLogger("asmeranda.api.training")
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
optimization_service = OptimizationService()


def _train_model_background(
    state_id: str,
    X_train,
    y_train,
    X_test,
    y_test,
    model_type: str,
    problem_type: str,
    hyperparams: Dict[str, Any],
    cv_method: str,
    cv_folds: int,
) -> Dict[str, Any]:
    """Background task for model training to avoid blocking requests."""
    try:
        result = training_service.train(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            model_type=model_type,
            problem_type=problem_type,
            hyperparams=hyperparams,
            cv_method=cv_method,
            cv_folds=cv_folds,
        )
        
        if result.get("success"):
            logger.info(
                "Background model training completed successfully",
                extra={
                    "model_id": result.get("model_id"),
                    "model_type": model_type,
                    "problem_type": problem_type,
                    "state_id": state_id
                }
            )
        else:
            logger.error(
                "Background model training failed",
                extra={
                    "error": result.get("error"),
                    "model_type": model_type,
                    "problem_type": problem_type,
                    "state_id": state_id
                }
            )
        
        return result
    except Exception as exc:
        logger.error(
            "Background training error",
            exc_info=True,
            extra={
                "state_id": state_id,
                "model_type": model_type,
                "error_type": type(exc).__name__
            }
        )
        return {"success": False, "error": str(exc)}


@router.post("/start", response_model=TrainingResponse)
@limiter.limit("5/minute")  # Limit to 5 training requests per minute per IP
def start_training(request: Request, background_tasks: BackgroundTasks, config: TrainingConfig) -> TrainingResponse:
    """Latih model berdasarkan state hasil preprocessing (async background task)."""
    # Get client IP for audit logging
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        state = get_state(config.state_id)
        X_train = state.get("X_train")
        X_test = state.get("X_test")
        y_train = state.get("y_train")
        y_test = state.get("y_test")

        if X_train is None or y_train is None or X_test is None or y_test is None:
            logger.warning(
                "Invalid preprocessing state",
                extra={
                    "state_id": config.state_id,
                    "model_type": config.model_type,
                    "problem_type": config.problem_type
                }
            )
            audit_logger.log_invalid_input(
                endpoint="/training/start",
                reason="Invalid preprocessing state",
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=400,
                detail="State preprocessing tidak valid (X_train/X_test/y_train/y_test hilang).",
            )

        # Add training as background task to avoid blocking
        background_tasks.add_task(
            _train_model_background,
            config.state_id,
            X_train,
            y_train,
            X_test,
            y_test,
            config.model_type,
            config.problem_type,
            config.hyperparams or {},
            config.cv_method,
            config.cv_folds,
        )
        
        # Log training start
        audit_logger.log_model_training(
            model_type=config.model_type,
            problem_type=config.problem_type,
            ip_address=client_ip,
            success=True
        )
        
        # Return immediate response indicating training started
        logger.info(
            "Model training started in background",
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "problem_type": config.problem_type
            }
        )
        
        return TrainingResponse(
            success=True,
            model_id="pending",  # Will be updated when background task completes
            message="Training started in background. Check /models endpoint for results."
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error during training start",
            exc_info=True,
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "error_type": type(exc).__name__
            }
        )
        audit_logger.log_model_training(
            model_type=config.model_type,
            problem_type=config.problem_type,
            ip_address=client_ip,
            success=False
        )
        raise HTTPException(status_code=500, detail=f"Training start error: {str(exc)}")


@router.get("/models")
def list_models() -> Dict[str, Any]:
    """List semua model yang sudah dilatih."""
    return training_service.list_models()


@router.get("/models/{model_id}")
def get_model(model_id: str) -> Dict[str, Any]:
    meta = training_service.get_metadata(model_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} tidak ditemukan")
    return meta


@router.delete("/models/{model_id}")
def delete_model(model_id: str):
    ok = training_service.delete_model(model_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Model {model_id} tidak ditemukan")
    return {"success": True, "model_id": model_id, "deleted": True}


@router.get("/models/{model_id}/download")
def download_model(model_id: str):
    """Download trained model sebagai .pkl file."""
    model_dir = Path(settings.data_dir) / "models"
    model_path = model_dir / f"{model_id}.pkl"
    
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    
    return FileResponse(
        path=model_path,
        filename=f"model_{model_id}.pkl",
        media_type="application/octet-stream"
    )


# TEMPORARY: Optimization endpoints added here for immediate functionality
@router.post("/optimize", response_model=OptimizationResponse)
def optimize_hyperparameters(
    config: OptimizationConfig, background_tasks: BackgroundTasks
) -> OptimizationResponse:
    """Perform hyperparameter optimization (async background task)."""
    try:
        state = get_state(config.state_id)
        X_train = state.get("X_train")
        y_train = state.get("y_train")

        if X_train is None or y_train is None:
            return OptimizationResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        optimization_params = {
            "cv": config.cv_folds,
        }
        if config.method == "random_search":
            optimization_params["n_iter"] = config.n_iter
        elif config.method == "bayesian":
            optimization_params["n_trials"] = config.n_iter

        background_tasks.add_task(
            _optimization_background,
            config.state_id,
            X_train,
            y_train,
            config.model_type,
            config.problem_type,
            config.method,
            **optimization_params
        )

        return OptimizationResponse(
            success=True,
            method=config.method,
            message="Optimization started in background. Results will be available upon completion."
        )

    except Exception as exc:
        logger.error("Optimization start failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization start failed: {str(exc)}")


@router.post("/optimize-sync", response_model=OptimizationResponse)
def optimize_hyperparameters_sync(config: OptimizationConfig) -> OptimizationResponse:
    """Perform hyperparameter optimization (synchronous, for smaller datasets)."""
    try:
        state = get_state(config.state_id)
        X_train = state.get("X_train")
        y_train = state.get("y_train")

        if X_train is None or y_train is None:
            return OptimizationResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        optimization_params = {
            "cv": config.cv_folds,
        }
        if config.method == "random_search":
            optimization_params["n_iter"] = config.n_iter
        elif config.method == "bayesian":
            optimization_params["n_trials"] = config.n_iter

        result = _optimization_background(
            config.state_id,
            X_train,
            y_train,
            config.model_type,
            config.problem_type,
            config.method,
            **optimization_params
        )

        if not result.get("success"):
            return OptimizationResponse(
                success=False,
                error=result.get("error"),
                method=config.method
            )

        state["optimization_results"] = {
            "best_params": result.get("best_params"),
            "best_score": result.get("best_score"),
            "method": result.get("method"),
            "model_type": config.model_type,
        }

        return OptimizationResponse(
            success=True,
            best_params=result.get("best_params"),
            best_score=result.get("best_score"),
            method=result.get("method"),
            cv_results=result.get("cv_results")
        )

    except Exception as exc:
        logger.error("Synchronous optimization failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(exc)}")


def _optimization_background(
    state_id: str,
    X_train,
    y_train,
    model_type: str,
    problem_type: str,
    method: str,
    **optimization_params
) -> Dict[str, Any]:
    """Background task for hyperparameter optimization."""
    try:
        if method == "grid_search":
            result = optimization_service.grid_search(
                X_train, y_train, model_type, problem_type, **optimization_params
            )
        elif method == "random_search":
            result = optimization_service.random_search(
                X_train, y_train, model_type, problem_type, **optimization_params
            )
        elif method == "bayesian":
            result = optimization_service.bayesian_optimization(
                X_train, y_train, model_type, problem_type, **optimization_params
            )
        else:
            result = {"success": False, "error": f"Unknown optimization method: {method}"}

        if result.get("success"):
            logger.info(
                "Optimization completed successfully",
                extra={
                    "state_id": state_id,
                    "model_type": model_type,
                    "method": method,
                    "best_score": result.get("best_score")
                }
            )
        else:
            logger.error(
                "Optimization failed",
                extra={
                    "state_id": state_id,
                    "model_type": model_type,
                    "method": method,
                    "error": result.get("error")
                }
            )

        return result

    except Exception as exc:
        logger.error(
            "Background optimization error",
            exc_info=True,
            extra={
                "state_id": state_id,
                "model_type": model_type,
                "method": method,
                "error_type": type(exc).__name__
            }
        )
        return {"success": False, "error": str(exc)}


@router.post("/models/{model_id}/predict", response_model=PredictionResponse)
def predict_with_model(model_id: str, request: PredictionRequest):
    """Gunakan trained model untuk prediksi data baru."""
    # Load model
    model_data = training_service.load_model(model_id)
    if model_data is None:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    
    model = model_data["model"]
    feature_names = model_data.get("feature_names", [])
    problem_type = model_data.get("problem_type", "Classification")
    
    try:
        # Convert input data to DataFrame
        input_df = pd.DataFrame(request.data)
        
        # Ensure all required features are present
        missing_features = set(feature_names) - set(input_df.columns)
        if missing_features:
            # Add missing features with zeros
            for feat in missing_features:
                input_df[feat] = 0
        
        # Align columns
        X_new = input_df[feature_names]
        
        # Convert to numeric
        X_new = X_new.apply(pd.to_numeric, errors="coerce").fillna(0.0)
        
        # Make predictions
        predictions = model.predict(X_new)
        
        # Get probabilities if available
        probabilities = None
        if problem_type == "Classification" and hasattr(model, "predict_proba"):
            try:
                probabilities = model.predict_proba(X_new).tolist()
            except Exception:
                pass
        
        return PredictionResponse(
            success=True,
            predictions=predictions.tolist(),
            probabilities=probabilities
        )
        
    except Exception as e:
        logger.error(f"Prediction error for model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/evaluate")
def evaluate_with_state(config: EvaluationConfig):
    """Evaluate model using state data (requires state_id in config)."""
    state_id = getattr(config, 'state_id', None)
    model_id = getattr(config, 'model_id', None)
    
    if not state_id or not model_id:
        raise HTTPException(
            status_code=400, 
            detail="Both state_id and model_id are required for evaluation"
        )
    
    # Get state with test data
    state = get_state(state_id)
    if not state:
        raise HTTPException(status_code=404, detail="State tidak ditemukan")
    
    X_test = state.get("X_test")
    y_test = state.get("y_test")
    problem_type = state.get("problem_type", "Classification")
    
    if X_test is None or y_test is None:
        raise HTTPException(
            status_code=400, 
            detail="Test data tidak tersedia di state"
        )
    
    # Use evaluation service
    try:
        result = evaluation_service.evaluate_model(
            model_id=model_id,
            X_test=X_test,
            y_test=y_test,
            problem_type=problem_type,
            plot_types=config.plot_types
        )
        
        if not result.get("success"):
            return EvaluationResponse(success=False, error=result.get("error"))
        
        return EvaluationResponse(
            success=True,
            model_id=model_id,
            metrics=result.get("metrics"),
            plots=result.get("plots")
        )
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/learning-curve")
def generate_learning_curve(request: LearningCurveRequest):
    """Generate learning curve for a trained model."""
    try:
        state = get_state(request.state_id)
        if not state:
            raise HTTPException(status_code=404, detail="State tidak ditemukan")
        
        X_train = state.get("X_train")
        y_train = state.get("y_train")
        problem_type = state.get("problem_type", "Classification")
        
        if X_train is None or y_train is None:
            raise HTTPException(
                status_code=400, 
                detail="Training data tidak tersedia di state"
            )
        
        # Parse train sizes if provided
        import json
        train_sizes_list = None
        if request.train_sizes:
            try:
                train_sizes_list = json.loads(request.train_sizes)
            except:
                pass
        
        result = evaluation_service.generate_learning_curve(
            model_id=request.model_id,
            X_train=X_train,
            y_train=y_train,
            problem_type=problem_type,
            cv=request.cv,
            train_sizes=train_sizes_list
        )
        
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Learning curve generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Learning curve generation failed: {str(e)}")


@router.post("/compare")
def compare_models(request: ModelComparisonRequest):
    """Compare multiple models and return performance ranking."""
    try:
        state = get_state(request.state_id)
        if not state:
            raise HTTPException(status_code=404, detail="State tidak ditemukan")
        
        X_train = state.get("X_train")
        y_train = state.get("y_train")
        X_test = state.get("X_test")
        y_test = state.get("y_test")
        problem_type = state.get("problem_type", "Classification")
        
        if X_train is None or y_train is None or X_test is None or y_test is None:
            raise HTTPException(
                status_code=400, 
                detail="Training/test data tidak tersedia di state"
            )
        
        # Parse model types if provided
        import json
        model_types_list = None
        if request.model_types:
            try:
                model_types_list = json.loads(request.model_types)
            except:
                pass
        
        result = training_service.compare_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            problem_type=problem_type,
            model_types=model_types_list,
            cv_method=request.cv_method,
            cv_folds=request.cv_folds
        )
        
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model comparison failed: {str(e)}")

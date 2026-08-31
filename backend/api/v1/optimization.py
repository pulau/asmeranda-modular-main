"""
Endpoint /optimization - hyperparameter optimization operations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.schemas.models import OptimizationConfig, OptimizationResponse
from backend.services.optimization_service import OptimizationService
from core.state import get_state

logger = logging.getLogger("asmeranda.api.optimization")
router = APIRouter()
optimization_service = OptimizationService()


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


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_hyperparameters(
    config: OptimizationConfig, background_tasks: BackgroundTasks
) -> OptimizationResponse:
    """Perform hyperparameter optimization (async background task)."""
    try:
        # Get data from state
        state = get_state(config.state_id)
        X_train = state.get("X_train")
        y_train = state.get("y_train")

        if X_train is None or y_train is None:
            logger.warning(
                "No training data available for optimization",
                extra={"state_id": config.state_id, "model_type": config.model_type}
            )
            return OptimizationResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        # Convert to DataFrame if needed
        import pandas as pd
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        # Prepare optimization parameters
        optimization_params = {
            "cv": config.cv_folds,
        }
        if config.method == "random_search":
            optimization_params["n_iter"] = config.n_iter
        elif config.method == "bayesian":
            optimization_params["n_trials"] = config.n_iter

        # Add optimization as background task
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

        logger.info(
            "Hyperparameter optimization started in background",
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "method": config.method
            }
        )

        return OptimizationResponse(
            success=True,
            method=config.method,
            message="Optimization started in background. Results will be available upon completion."
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Optimization start failed",
            exc_info=True,
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Optimization start failed: {str(exc)}")


@router.post("/optimize-sync", response_model=OptimizationResponse)
def optimize_hyperparameters_sync(config: OptimizationConfig) -> OptimizationResponse:
    """Perform hyperparameter optimization (synchronous, for smaller datasets)."""
    try:
        # Get data from state
        state = get_state(config.state_id)
        X_train = state.get("X_train")
        y_train = state.get("y_train")

        if X_train is None or y_train is None:
            logger.warning(
                "No training data available for optimization",
                extra={"state_id": config.state_id, "model_type": config.model_type}
            )
            return OptimizationResponse(
                success=False,
                error="No training data available. Please run preprocessing first."
            )

        # Convert to DataFrame if needed
        import pandas as pd
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)

        # Prepare optimization parameters
        optimization_params = {
            "cv": config.cv_folds,
        }
        if config.method == "random_search":
            optimization_params["n_iter"] = config.n_iter
        elif config.method == "bayesian":
            optimization_params["n_trials"] = config.n_iter

        # Perform optimization synchronously
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

        # Store optimization results in state
        state["optimization_results"] = {
            "best_params": result.get("best_params"),
            "best_score": result.get("best_score"),
            "method": result.get("method"),
            "model_type": config.model_type,
        }

        logger.info(
            "Synchronous optimization completed successfully",
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "method": config.method,
                "best_score": result.get("best_score")
            }
        )

        return OptimizationResponse(
            success=True,
            best_params=result.get("best_params"),
            best_score=result.get("best_score"),
            method=result.get("method"),
            cv_results=result.get("cv_results")
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Synchronous optimization failed",
            exc_info=True,
            extra={
                "state_id": config.state_id,
                "model_type": config.model_type,
                "error_type": type(exc).__name__
            }
        )
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(exc)}")
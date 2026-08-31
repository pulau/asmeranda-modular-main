"""
Hyperparameter optimization service using multiple methods.

This service provides automated hyperparameter tuning using Grid Search,
Randomized Search, and Bayesian Optimization (Optuna).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

logger = logging.getLogger("asmeranda.services.optimization")

# Optional: Optuna for Bayesian optimization
try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


class OptimizationService:
    """Hyperparameter optimization service with multiple methods."""

    def __init__(self):
        self.param_grids = self._get_param_grids()
        self.param_distributions = self._get_param_distributions()

    def _get_param_grids(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter grids for grid search."""
        return {
            "RandomForest": {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            },
            "GradientBoosting": {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.2],
                "max_depth": [3, 5, 7],
                "subsample": [0.8, 0.9, 1.0],
            },
            "LogisticRegression": {
                "C": [0.1, 1.0, 10.0],
                "solver": ["lbfgs", "liblinear"],
                "max_iter": [100, 500, 1000],
            },
            "LinearRegression": {
                "fit_intercept": [True, False],
            },
            "DecisionTree": {
                "max_depth": [None, 10, 20],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            },
            "KNeighbors": {
                "n_neighbors": [3, 5, 7, 9],
                "weights": ["uniform", "distance"],
            },
            "SVM": {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["linear", "rbf"],
                "gamma": ["scale", "auto"],
            },
        }

    def _get_param_distributions(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter distributions for randomized search."""
        return {
            "RandomForest": {
                "n_estimators": [50, 100, 150, 200, 250, 300],
                "max_depth": [None, 5, 10, 15, 20, 25],
                "min_samples_split": [2, 3, 5, 7, 10],
                "min_samples_leaf": [1, 2, 3, 4, 5],
                "max_features": ["sqrt", "log2", None],
            },
            "GradientBoosting": {
                "n_estimators": [50, 100, 150, 200, 250, 300],
                "learning_rate": [0.01, 0.05, 0.1, 0.15, 0.2, 0.25],
                "max_depth": [3, 5, 7, 9, 11],
                "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
            },
            "LogisticRegression": {
                "C": [0.01, 0.1, 1.0, 10.0, 100.0],
                "solver": ["lbfgs", "liblinear", "saga"],
                "max_iter": [100, 200, 500, 1000],
                "penalty": ["l2", "l1"],
            },
            "DecisionTree": {
                "max_depth": [None, 5, 10, 15, 20, 25],
                "min_samples_split": [2, 3, 5, 7, 10],
                "min_samples_leaf": [1, 2, 3, 4, 5],
                "criterion": ["gini", "entropy"],
            },
            "KNeighbors": {
                "n_neighbors": [3, 5, 7, 9, 11, 15],
                "weights": ["uniform", "distance"],
                "algorithm": ["auto", "ball_tree", "kd_tree"],
            },
            "SVM": {
                "C": [0.1, 1.0, 10.0, 100.0],
                "kernel": ["linear", "rbf", "poly"],
                "gamma": ["scale", "auto"],
                "degree": [2, 3, 4],
            },
        }

    def grid_search(
        self,
        X_train,
        y_train,
        model_type: str,
        problem_type: str,
        cv: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform grid search hyperparameter optimization."""
        try:
            param_grid = self.param_grids.get(model_type, {})
            if not param_grid:
                return {
                    "success": False,
                    "error": f"No parameter grid defined for model type: {model_type}",
                }

            # Get base model
            model = self._get_model(model_type, problem_type)
            if model is None:
                return {
                    "success": False,
                    "error": f"Unsupported model type: {model_type}",
                }

            # Determine scoring metric
            scoring = "accuracy" if problem_type == "Classification" else "r2"

            # Perform grid search
            grid_search = GridSearchCV(
                model,
                param_grid,
                cv=cv,
                scoring=scoring,
                n_jobs=-1,
                verbose=0,
            )
            grid_search.fit(X_train, y_train)

            return {
                "success": True,
                "best_params": grid_search.best_params_,
                "best_score": float(grid_search.best_score_),
                "best_model": grid_search.best_estimator_,
                "cv_results": {
                    "mean_test_score": grid_search.cv_results_[
                        "mean_test_score"
                    ].tolist(),
                    "std_test_score": grid_search.cv_results_[
                        "std_test_score"
                    ].tolist(),
                    "params": grid_search.cv_results_["params"],
                },
                "method": "grid_search",
            }

        except Exception as e:
            logger.error(f"Grid search failed: {str(e)}")
            return {"success": False, "error": str(e), "method": "grid_search"}

    def random_search(
        self,
        X_train,
        y_train,
        model_type: str,
        problem_type: str,
        n_iter: int = 50,
        cv: int = 5,
        random_state: int = 42,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform randomized search hyperparameter optimization."""
        try:
            param_distributions = self.param_distributions.get(model_type, {})
            if not param_distributions:
                return {
                    "success": False,
                    "error": f"No parameter distributions defined for model type: {model_type}",
                }

            # Get base model
            model = self._get_model(model_type, problem_type)
            if model is None:
                return {
                    "success": False,
                    "error": f"Unsupported model type: {model_type}",
                }

            # Determine scoring metric
            scoring = "accuracy" if problem_type == "Classification" else "r2"

            # Perform random search
            random_search = RandomizedSearchCV(
                model,
                param_distributions,
                n_iter=n_iter,
                cv=cv,
                scoring=scoring,
                random_state=random_state,
                n_jobs=-1,
                verbose=0,
            )
            random_search.fit(X_train, y_train)

            return {
                "success": True,
                "best_params": random_search.best_params_,
                "best_score": float(random_search.best_score_),
                "best_model": random_search.best_estimator_,
                "cv_results": {
                    "mean_test_score": random_search.cv_results_[
                        "mean_test_score"
                    ].tolist(),
                    "std_test_score": random_search.cv_results_[
                        "std_test_score"
                    ].tolist(),
                    "params": random_search.cv_results_["params"],
                },
                "method": "random_search",
            }

        except Exception as e:
            logger.error(f"Random search failed: {str(e)}")
            return {"success": False, "error": str(e), "method": "random_search"}

    def bayesian_optimization(
        self,
        X_train,
        y_train,
        model_type: str,
        problem_type: str,
        n_trials: int = 50,
        cv: int = 5,
        timeout: int = 300,
        scoring: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform Bayesian optimization using Optuna with adaptive scoring and CV guards."""
        if not OPTUNA_AVAILABLE:
            return {
                "success": False,
                "error": "Optuna not available. Install with: pip install optuna",
                "method": "bayesian",
            }

        try:
            import optuna
            from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold

            # Get parameter distributions
            param_distributions = self.param_distributions.get(model_type, {})
            if not param_distributions:
                # Fallback check for case-insensitive matches
                for k, v in self.param_distributions.items():
                    if k.lower() == model_type.lower():
                        param_distributions = v
                        break
            if not param_distributions:
                return {
                    "success": False,
                    "error": f"No parameter distributions defined for model type: {model_type}",
                }

            # Determine scoring metric
            if scoring is None:
                scoring = "accuracy" if problem_type == "Classification" else "r2"

            # Determine CV strategy
            if problem_type == "Classification" and hasattr(y_train, "value_counts"):
                min_class_count = int(y_train.value_counts().min())
                effective_cv = max(2, min(cv, min_class_count)) if min_class_count >= 2 else KFold(n_splits=cv, shuffle=True, random_state=42)
                if isinstance(effective_cv, int):
                    cv_splitter = StratifiedKFold(n_splits=effective_cv, shuffle=True, random_state=42)
                else:
                    cv_splitter = effective_cv
            else:
                cv_splitter = KFold(n_splits=cv, shuffle=True, random_state=42)

            def objective(trial):
                # Suggest parameters
                params = {}
                for param_name, param_values in param_distributions.items():
                    if isinstance(param_values[0], (int, float)):
                        # Numeric parameter
                        if len(param_values) > 2:
                            if all(isinstance(v, int) for v in param_values):
                                params[param_name] = trial.suggest_int(
                                    param_name, min(param_values), max(param_values)
                                )
                            else:
                                params[param_name] = trial.suggest_float(
                                    param_name, min(param_values), max(param_values)
                                )
                        else:
                            params[param_name] = trial.suggest_categorical(
                                param_name, param_values
                            )
                    else:
                        # Categorical parameter
                        params[param_name] = trial.suggest_categorical(
                            param_name, param_values
                        )

                # Create model with suggested parameters
                model = self._get_model(model_type, problem_type, **params)
                if model is None:
                    return 0.0

                # Perform cross-validation
                scores = cross_val_score(
                    model, X_train, y_train, cv=cv_splitter, scoring=scoring, n_jobs=-1
                )
                return float(scores.mean())

            # Create study with MedianPruner
            pruner = optuna.pruners.MedianPruner() if hasattr(optuna.pruners, "MedianPruner") else None
            study = optuna.create_study(direction="maximize", pruner=pruner)
            study.optimize(objective, n_trials=n_trials, timeout=timeout)

            # Get best parameters
            best_params = study.best_params
            best_score = study.best_value

            # Train final model with best parameters
            best_model = self._get_model(model_type, problem_type, **best_params)
            best_model.fit(X_train, y_train)

            return {
                "success": True,
                "best_params": best_params,
                "best_score": float(best_score),
                "best_model": best_model,
                "n_trials": n_trials,
                "scoring": scoring,
                "method": "bayesian",
            }

        except Exception as e:
            logger.error(f"Bayesian optimization failed: {str(e)}")
            return {"success": False, "error": str(e), "method": "bayesian"}

    def _get_model(
        self, model_type: str, problem_type: str, **params
    ) -> Optional[Any]:
        """Get base model for optimization."""
        try:
            mt = model_type.lower()
            is_clf = problem_type == "Classification"

            if mt in ("random_forst", "randomforest", "rf"):
                return (
                    RandomForestClassifier(random_state=42, **params)
                    if is_clf
                    else RandomForestRegressor(random_state=42, **params)
                )
            elif mt in ("gradient_boosting", "gb", "gbm"):
                return (
                    GradientBoostingClassifier(random_state=42, **params)
                    if is_clf
                    else GradientBoostingRegressor(random_state=42, **params)
                )
            elif mt in ("logistic", "logisticregression"):
                return LogisticRegression(max_iter=1000, **params)
            elif mt in ("linear", "linearregression"):
                return LinearRegression(**params)
            elif mt in ("decision_tree", "dt"):
                return (
                    DecisionTreeClassifier(random_state=42, **params)
                    if is_clf
                    else DecisionTreeRegressor(random_state=42, **params)
                )
            elif mt in ("knn", "kneighbors"):
                return (
                    KNeighborsClassifier(**params)
                    if is_clf
                    else KNeighborsRegressor(**params)
                )
            elif mt in ("svm", "svc", "svr"):
                return (
                    SVC(probability=True, **params) if is_clf else SVR(**params)
                )
            else:
                return None

        except Exception as e:
            logger.error(f"Model creation failed: {str(e)}")
            return None
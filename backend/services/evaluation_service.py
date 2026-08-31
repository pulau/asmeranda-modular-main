"""
Evaluation service - comprehensive model evaluation with visualization.

Service ini menyediakan evaluasi model yang lengkap dengan visualisasi
seperti confusion matrix, ROC curve, precision-recall curve, dll.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
    matthews_corrcoef,
    balanced_accuracy_score,
    cohen_kappa_score,
    explained_variance_score,
)
from sklearn.model_selection import learning_curve
from sklearn.preprocessing import label_binarize

from backend.services.training_service import load_model

logger = logging.getLogger("asmeranda.services.evaluation")


def _plot_to_base64(plt_obj) -> str:
    """Convert matplotlib plot to base64 string."""
    buf = io.BytesIO()
    plt_obj.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt_obj.close()
    return img_base64


def _plot_confusion_matrix(y_true, y_pred, class_names=None) -> str:
    """Generate confusion matrix plot."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def _plot_roc_curve(y_true, y_proba, class_names=None) -> str:
    """Generate ROC curve plot (binary classification)."""
    if len(np.unique(y_true)) != 2:
        # For multiclass, skip ROC curve
        return None
    
    fpr, tpr, _ = roc_curve(y_true, y_proba[:, 1])
    auc_score = roc_auc_score(y_true, y_proba[:, 1])
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {auc_score:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC) Curve')
    plt.legend(loc="lower right")
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def _plot_precision_recall_curve(y_true, y_proba) -> str:
    """Generate precision-recall curve (binary classification)."""
    if len(np.unique(y_true)) != 2:
        return None
    
    precision, recall, _ = precision_recall_curve(y_true, y_proba[:, 1])
    
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def _plot_feature_importance(model, feature_names: List[str], top_n: int = 20) -> str:
    """Generate feature importance plot."""
    if not hasattr(model, 'feature_importances_'):
        return None
    
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]
    
    plt.figure(figsize=(10, 6))
    plt.title(f'Top {top_n} Feature Importances')
    plt.bar(range(len(indices)), importances[indices], align='center')
    plt.xticks(range(len(indices)), [feature_names[i] for i in indices], rotation=45, ha='right')
    plt.xlabel('Feature')
    plt.ylabel('Importance')
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def _plot_residuals(y_true, y_pred) -> str:
    """Generate residual plot for regression."""
    residuals = y_true - y_pred
    
    plt.figure(figsize=(10, 6))
    plt.scatter(y_pred, residuals, alpha=0.5)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('Predicted Values')
    plt.ylabel('Residuals')
    plt.title('Residual Plot')
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def _plot_prediction_vs_actual(y_true, y_pred) -> str:
    """Generate prediction vs actual plot for regression."""
    plt.figure(figsize=(8, 6))
    plt.scatter(y_true, y_pred, alpha=0.5)
    plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
    plt.xlabel('Actual Values')
    plt.ylabel('Predicted Values')
    plt.title('Prediction vs Actual')
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def evaluate_model(
    model_id: str,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    problem_type: str,
    plot_types: List[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate model with comprehensive metrics and visualizations.
    
    Parameters
    ----------
    model_id : str
        ID of the trained model
    X_test : pd.DataFrame
        Test features
    y_test : pd.Series
        Test target
    problem_type : str
        'Classification' or 'Regression'
    plot_types : List[str]
        Types of plots to generate
        
    Returns
    -------
    dict
        Evaluation results with metrics and plots
    """
    if plot_types is None:
        plot_types = ["confusion_matrix", "roc_curve", "feature_importance"]
    
    # Load model
    model_data = load_model(model_id)
    if model_data is None:
        return {"success": False, "error": f"Model {model_id} not found"}
    
    model = model_data["model"]
    feature_names = model_data.get("feature_names", [])
    
    # Ensure X_test has correct features
    if set(feature_names).issubset(set(X_test.columns)):
        X_test_aligned = X_test[feature_names]
    else:
        # Try to align columns
        X_test_aligned = X_test.reindex(columns=feature_names, fill_value=0)
    
    # Convert to numeric
    X_test_aligned = X_test_aligned.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    
    # Make predictions
    try:
        y_pred = model.predict(X_test_aligned)
    except Exception as e:
        return {"success": False, "error": f"Prediction failed: {str(e)}"}
    
    y_proba = None
    if problem_type == "Classification" and hasattr(model, "predict_proba"):
        try:
            y_proba = model.predict_proba(X_test_aligned)
        except Exception:
            y_proba = None
    
    # Calculate metrics
    metrics = {}
    plots = {}
    
    if problem_type == "Classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        metrics["f1_macro"] = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        metrics["classification_report"] = classification_report(
            y_test, y_pred, zero_division=0, output_dict=True
        )
        
        # Advanced metrics
        try:
            metrics["balanced_accuracy"] = float(balanced_accuracy_score(y_test, y_pred))
        except Exception:
            pass
        
        try:
            metrics["matthews_corrcoef"] = float(matthews_corrcoef(y_test, y_pred))
        except Exception:
            pass
        
        try:
            metrics["cohen_kappa"] = float(cohen_kappa_score(y_test, y_pred))
        except Exception:
            pass
        
        if y_proba is not None and len(np.unique(y_test)) == 2:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba[:, 1]))
            except Exception:
                pass
        
        # Generate plots
        if "confusion_matrix" in plot_types:
            class_names = list(np.unique(y_test))
            plots["confusion_matrix"] = _plot_confusion_matrix(y_test, y_pred, class_names)
        
        if "roc_curve" in plot_types and y_proba is not None:
            plots["roc_curve"] = _plot_roc_curve(y_test, y_proba)
        
        if "precision_recall_curve" in plot_types and y_proba is not None:
            plots["precision_recall_curve"] = _plot_precision_recall_curve(y_test, y_proba)
    
    else:  # Regression
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        metrics["mae"] = float(mean_absolute_error(y_test, y_pred))
        metrics["r2"] = float(r2_score(y_test, y_pred))
        
        # Advanced metrics
        try:
            metrics["mape"] = float(mean_absolute_percentage_error(y_test, y_pred))
        except Exception:
            pass
        
        try:
            metrics["medae"] = float(median_absolute_error(y_test, y_pred))
        except Exception:
            pass
        
        try:
            metrics["explained_variance"] = float(explained_variance_score(y_test, y_pred))
        except Exception:
            pass
        
        # Generate plots
        if "residuals" in plot_types:
            plots["residuals"] = _plot_residuals(y_test, y_pred)
        
        if "prediction_vs_actual" in plot_types:
            plots["prediction_vs_actual"] = _plot_prediction_vs_actual(y_test, y_pred)
    
    # Feature importance (both classification and regression)
    if "feature_importance" in plot_types:
        plots["feature_importance"] = _plot_feature_importance(model, feature_names)
    
    return {
        "success": True,
        "model_id": model_id,
        "metrics": metrics,
        "plots": plots,
        "problem_type": problem_type,
    }


def _plot_learning_curve(train_scores, test_scores, train_sizes, scoring: str) -> str:
    """Generate learning curve plot."""
    plt.figure(figsize=(10, 6))
    
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    plt.plot(train_sizes, train_mean, 'o-', color='r', label='Training score')
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color='r')
    plt.plot(train_sizes, test_mean, 'o-', color='g', label='Cross-validation score')
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color='g')
    
    plt.xlabel('Training examples')
    plt.ylabel(f'{scoring.capitalize()} Score')
    plt.title('Learning Curve')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return _plot_to_base64(plt)


def generate_learning_curve(
    model_id: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    problem_type: str,
    cv: int = 5,
    train_sizes: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Generate learning curve to detect overfitting/underfitting.
    
    Parameters
    ----------
    model_id : str
        ID of the trained model
    X_train : pd.DataFrame
        Training features
    y_train : pd.Series
        Training target
    problem_type : str
        'Classification' or 'Regression'
    cv : int
        Number of cross-validation folds
    train_sizes : List[float]
        Training sizes (fractions of total data)
        
    Returns
    -------
    dict
        Learning curve results with plot
    """
    # Load model
    model_data = load_model(model_id)
    if model_data is None:
        return {"success": False, "error": f"Model {model_id} not found"}
    
    model = model_data["model"]
    
    # Ensure X_train has correct features
    feature_names = model_data.get("feature_names", [])
    if set(feature_names).issubset(set(X_train.columns)):
        X_train_aligned = X_train[feature_names]
    else:
        X_train_aligned = X_train.reindex(columns=feature_names, fill_value=0)
    
    # Convert to numeric
    X_train_aligned = X_train_aligned.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    
    # Set default train sizes
    if train_sizes is None:
        train_sizes = np.linspace(0.1, 1.0, 10)
    
    # Set scoring metric
    if problem_type == "Classification":
        scoring = "accuracy"
    else:
        scoring = "r2"
    
    try:
        # Generate learning curve
        train_sizes_abs, train_scores, test_scores = learning_curve(
            model, X_train_aligned, y_train,
            cv=cv,
            scoring=scoring,
            train_sizes=train_sizes,
            n_jobs=-1,
            random_state=42
        )
        
        # Generate plot
        plot_base64 = _plot_learning_curve(train_scores, test_scores, train_sizes_abs, scoring)
        
        # Calculate statistics
        train_mean = np.mean(train_scores, axis=1)
        test_mean = np.mean(test_scores, axis=1)
        final_train_score = float(train_mean[-1])
        final_test_score = float(test_mean[-1])
        gap = final_train_score - final_test_score
        
        # Detect overfitting/underfitting
        diagnosis = "good_fit"
        if gap > 0.1 and final_train_score > 0.9:
            diagnosis = "overfitting"
        elif final_train_score < 0.7 and final_test_score < 0.7:
            diagnosis = "underfitting"
        elif gap > 0.15:
            diagnosis = "high_variance"
        
        return {
            "success": True,
            "model_id": model_id,
            "plot_base64": plot_base64,
            "train_sizes": train_sizes_abs.tolist(),
            "train_scores_mean": train_mean.tolist(),
            "test_scores_mean": test_mean.tolist(),
            "final_train_score": final_train_score,
            "final_test_score": final_test_score,
            "score_gap": float(gap),
            "diagnosis": diagnosis,
            "scoring": scoring,
            "cv_folds": cv
        }
        
    except Exception as e:
        logger.error(f"Learning curve generation failed: {e}")
        return {"success": False, "error": str(e)}
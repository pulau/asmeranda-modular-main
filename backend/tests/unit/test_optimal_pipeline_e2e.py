"""
End-to-end QA Pipeline Optimization Tests for Asmeranda AI.
Validates optimal execution and performance across multiple data science problem archetypes:
1. Standard Tabular Classification (RandomForest, LightGBM/GBM)
2. Imbalanced Dataset with Adaptive SMOTE & Stratified CV
3. Small Dataset (< 100 rows) with regularized models
4. High Dimensional Dataset with Feature Selection
5. Regression with Outliers and Robust Scaling
6. Auto-Configuration Pipeline Engine
"""
import numpy as np
import pandas as pd
import pytest

from backend.services import preprocessing_service, training_service
from backend.services.preprocessing_service import auto_configure_pipeline
from backend.services.optimization_service import OptimizationService
from workflow_validator import WorkflowValidator


def test_auto_configure_pipeline_engine():
    """Verify auto-config pipeline correctly selects preprocessing parameters based on dataset profile."""
    # Create skewed, imbalanced dataset
    np.random.seed(42)
    n = 200
    skewed_num = np.random.exponential(scale=10.0, size=n)
    normal_num = np.random.normal(loc=0, scale=1, size=n)
    cat_col = np.random.choice(["A", "B", "C"], size=n)
    # Imbalanced target (10% minority)
    target = np.array([1] * 20 + [0] * 180)

    df = pd.DataFrame({
        "skewed": skewed_num,
        "normal": normal_num,
        "category": cat_col,
        "target": target,
    })

    config = auto_configure_pipeline(df, target_column="target", problem_type="Classification")
    assert config is not None
    assert config["scaling_method"] in ("robust", "power")
    assert "imbalance_handling" in config
    assert config["imbalance_handling"]["method"] == "smote"


def test_standard_tabular_classification_pipeline():
    """Verify standard binary classification pipeline executes with high accuracy and proper metrics."""
    np.random.seed(42)
    n_samples = 300
    X = pd.DataFrame({
        "f1": np.random.randn(n_samples),
        "f2": np.random.randn(n_samples),
        "f3": np.random.uniform(0, 10, n_samples),
        "cat": np.random.choice(["low", "med", "high"], size=n_samples),
    })
    # Logical target
    y = ((X["f1"] * 2 + X["f2"] > 0)).astype(int)

    # Preprocessing
    X_proc, _ = preprocessing_service._encode(X, ["cat"], apply_encoding=True)
    X_train = X_proc.iloc[:240].copy()
    y_train = y.iloc[:240].copy()
    X_test = X_proc.iloc[240:].copy()
    y_test = y.iloc[240:].copy()

    res = training_service.train(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_type="RandomForest",
        problem_type="Classification",
        cv_method="stratified",
        cv_folds=5,
    )

    assert res["success"] is True
    assert "model_id" in res
    assert res["metrics"]["accuracy"] > 0.70
    assert "f1_macro" in res["metrics"]
    assert "mcc" in res["metrics"]
    assert res["cv_scores"] is not None
    assert res["cv_scores"]["mean"] > 0.70


def test_imbalanced_dataset_adaptive_smote_pipeline():
    """Verify highly imbalanced dataset handles SMOTE adaptively without crashing."""
    np.random.seed(42)
    n_samples = 150
    # Only 6 minority instances
    y = pd.Series([1] * 6 + [0] * 144)
    X = pd.DataFrame(np.random.randn(n_samples, 4), columns=[f"col_{i}" for i in range(4)])

    X_resampled, y_resampled, info = preprocessing_service._handle_imbalance(
        X, y, method="smote", sampling_strategy="auto"
    )

    assert "error" not in info or info["error"] is None
    assert len(X_resampled) > len(X)
    assert y_resampled.value_counts()[1] > 6

    # Training with StratifiedKFold guard
    res = training_service.train(
        X_train=X_resampled,
        y_train=y_resampled,
        X_test=X,
        y_test=y,
        model_type="LogisticRegression",
        problem_type="Classification",
        cv_method="stratified",
        cv_folds=5,
    )
    assert res["success"] is True
    assert res["metrics"]["balanced_accuracy"] is not None


def test_small_dataset_pipeline():
    """Verify small dataset (< 50 rows) trains without crashing on cross validation."""
    np.random.seed(42)
    n_samples = 30
    X = pd.DataFrame(np.random.randn(n_samples, 3), columns=["a", "b", "c"])
    y = pd.Series(np.random.choice([0, 1], size=n_samples))

    res = training_service.train(
        X_train=X.iloc[:24],
        y_train=y.iloc[:24],
        X_test=X.iloc[24:],
        y_test=y.iloc[24:],
        model_type="LogisticRegression",
        problem_type="Classification",
        cv_method="stratified",
        cv_folds=5,
    )
    assert res["success"] is True
    assert "model_id" in res


def test_high_dimensional_feature_selection_pipeline():
    """Verify high-dimensional data is effectively reduced via feature selection."""
    np.random.seed(42)
    n_samples = 100
    n_features = 40
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=[f"feat_{i}" for i in range(n_features)])
    # Add correlated columns
    X["feat_corr"] = X["feat_0"] * 0.999
    y = pd.Series((X["feat_0"] + X["feat_1"] > 0).astype(int))

    X_sel, sel_cols, info = preprocessing_service._feature_selection(
        X, y, method="correlation", max_features=10, threshold=0.90
    )
    assert len(sel_cols) < X.shape[1]
    assert "feat_corr" in info.get("dropped_features", [])


def test_regression_with_outliers_and_robust_scaling():
    """Verify regression pipeline with extreme outliers scales stably."""
    np.random.seed(42)
    n_samples = 120
    X = pd.DataFrame({
        "normal": np.random.randn(n_samples),
        "outlier": np.concatenate([np.random.randn(n_samples - 5), np.array([1000.0, -1000.0, 500.0, -500.0, 800.0])]),
    })
    y = pd.Series(X["normal"] * 3.5 + np.random.normal(0, 0.1, n_samples))

    X_scaled, info = preprocessing_service._scale(X.copy(), ["normal", "outlier"], method="robust")
    assert info["method"] == "robust"
    assert np.isfinite(X_scaled["outlier"]).all()

    res = training_service.train(
        X_train=X_scaled.iloc[:100],
        y_train=y.iloc[:100],
        X_test=X_scaled.iloc[100:],
        y_test=y.iloc[100:],
        model_type="LinearRegression",
        problem_type="Regression",
        cv_method="kfold",
        cv_folds=5,
    )
    assert res["success"] is True
    assert res["metrics"]["r2"] is not None


def test_workflow_validator_end_to_end():
    """Verify workflow state transitions validation across all gates."""
    # Step 1: Upload
    v1 = WorkflowValidator({"dataset_id": "test_id"})
    assert v1.validate("upload_to_eda")["valid"] is True

    # Step 2: EDA to Preprocessing
    v2 = WorkflowValidator({"dataset_id": "test_id", "target_column": "target"})
    assert v2.validate("eda_to_preprocessing")["valid"] is True

    # Step 3: Preprocessing to Training
    v3 = WorkflowValidator({
        "dataset_id": "test_id",
        "target_column": "target",
        "n_samples_train": 100,
        "n_samples_test": 20,
    })
    assert v3.validate("preprocessing_to_training")["valid"] is True

    # Step 4: Training to Evaluation / XAI
    v4 = WorkflowValidator({"model_id": "model_123", "model_type": "RandomForest"})
    assert v4.validate("training_to_evaluation")["valid"] is True
    assert v4.validate("training_to_xai")["valid"] is True

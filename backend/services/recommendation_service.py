"""
AI-powered dataset analysis and recommendation service.

This service provides intelligent recommendations based on dataset characteristics,
mimicking the AI-powered analysis from the legacy system.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger("asmeranda.services.recommendations")


class RecommendationService:
    """AI-powered dataset analysis and recommendation service."""

    def analyze_dataset(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze dataset characteristics and provide recommendations.

        Parameters
        ----------
        data : pd.DataFrame
            Input dataset to analyze

        Returns
        -------
        dict
            Analysis results with recommendations and dataset info
        """
        try:
            recommendations = []

            # Basic dataset characteristics
            n_rows, n_cols = data.shape
            numerical_cols = data.select_dtypes(include=["number"]).columns.tolist()
            categorical_cols = data.select_dtypes(include=["object", "category"]).columns.tolist()

            # Data size recommendations
            if n_rows < 100:
                recommendations.append({
                    "type": "warning",
                    "title": "Small Dataset Size",
                    "description": f"Dataset has only {n_rows} samples. Consider using simpler models to avoid overfitting.",
                    "suggested_models": ["LogisticRegression", "DecisionTree", "KNeighbors"],
                    "priority": "high"
                })
            elif n_rows > 10000:
                recommendations.append({
                    "type": "info",
                    "title": "Large Dataset Size",
                    "description": f"Dataset has {n_rows} samples. Consider using ensemble methods or dimensionality reduction.",
                    "suggested_models": ["RandomForest", "GradientBoosting", "XGBoost"],
                    "priority": "medium"
                })

            # Feature count recommendations
            if n_cols > 50:
                recommendations.append({
                    "type": "warning",
                    "title": "High Dimensionality",
                    "description": f"Dataset has {n_cols} features. Consider feature selection or dimensionality reduction to avoid overfitting.",
                    "suggested_methods": ["PCA", "RFE", "SelectKBest", "UMAP"],
                    "priority": "high"
                })
            elif n_cols > 20:
                recommendations.append({
                    "type": "info",
                    "title": "Many Features",
                    "description": f"Dataset has {n_cols} features. Use feature selection to improve performance.",
                    "suggested_methods": ["Feature Importance", "Recursive Feature Elimination", "Mutual Information"],
                    "priority": "medium"
                })

            # Data type recommendations
            if len(categorical_cols) > len(numerical_cols):
                recommendations.append({
                    "type": "info",
                    "title": "Categorical Dominant Data",
                    "description": f"Dataset has {len(categorical_cols)} categorical columns vs {len(numerical_cols)} numerical. Ensure proper encoding before training.",
                    "suggested_methods": ["One-Hot Encoding", "Target Encoding", "Label Encoding"],
                    "priority": "medium"
                })
            elif len(numerical_cols) > len(categorical_cols):
                recommendations.append({
                    "type": "info",
                    "title": "Numerical Dominant Data",
                    "description": f"Dataset has {len(numerical_cols)} numerical columns vs {len(categorical_cols)} categorical. Scaling may be needed.",
                    "suggested_methods": ["StandardScaler", "MinMaxScaler", "RobustScaler"],
                    "priority": "low"
                })

            # Missing value analysis
            missing_percentage = (data.isnull().sum().sum() / (n_rows * n_cols)) * 100
            if missing_percentage > 20:
                recommendations.append({
                    "type": "warning",
                    "title": "High Missing Value Percentage",
                    "description": f"Dataset has {missing_percentage:.1f}% missing values. Consider imputation strategies.",
                    "suggested_methods": ["Mean/Median Imputation", "KNN Imputation", "Iterative Imputation"],
                    "priority": "high"
                })
            elif missing_percentage > 5:
                recommendations.append({
                    "type": "info",
                    "title": "Moderate Missing Values",
                    "description": f"Dataset has {missing_percentage:.1f}% missing values. Imputation recommended.",
                    "suggested_methods": ["Mean/Median Imputation", "Forward/Backward Fill"],
                    "priority": "medium"
                })

            # Outlier detection recommendation
            for col in numerical_cols:
                if data[col].dtype in ["int64", "float64"]:
                    q1 = data[col].quantile(0.25)
                    q3 = data[col].quantile(0.75)
                    iqr = q3 - q1
                    outliers = ((data[col] < (q1 - 1.5 * iqr)) | (data[col] > (q3 + 1.5 * iqr))).sum()
                    outlier_percentage = (outliers / len(data)) * 100

                    if outlier_percentage > 10:
                        recommendations.append({
                            "type": "warning",
                            "title": f"High Outlier Percentage in {col}",
                            "description": f"Column {col} has {outlier_percentage:.1f}% outliers. Consider outlier handling.",
                            "suggested_methods": ["IQR Method", "Z-Score Method", "Isolation Forest"],
                            "priority": "medium"
                        })
                        break  # Only add one outlier recommendation

            # Problem type detection
            problem_type = self._detect_problem_type(data)
            recommendations.append({
                "type": "success",
                "title": "Detected Problem Type",
                "description": f"Based on data characteristics, this appears to be a {problem_type} problem.",
                "suggested_approach": self._get_approach_recommendation(problem_type),
                "priority": "low"
            })

            return {
                "success": True,
                "recommendations": recommendations,
                "dataset_info": {
                    "n_rows": n_rows,
                    "n_cols": n_cols,
                    "numerical_cols": len(numerical_cols),
                    "categorical_cols": len(categorical_cols),
                    "missing_percentage": missing_percentage,
                    "numerical_column_names": numerical_cols,
                    "categorical_column_names": categorical_cols,
                },
                "detected_problem_type": problem_type
            }

        except Exception as e:
            logger.error(f"Dataset analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "recommendations": [],
                "dataset_info": {}
            }

    def recommend_preprocessing(self, data: pd.DataFrame) -> List[str]:
        """
        Recommend preprocessing steps based on data characteristics.

        Parameters
        ----------
        data : pd.DataFrame
            Input dataset to analyze

        Returns
        -------
        list
            List of recommended preprocessing steps
        """
        steps = []

        # Check for missing values
        if data.isnull().any().any():
            steps.append("imputation")

        # Check for categorical columns
        if data.select_dtypes(include=["object"]).columns.any():
            steps.append("encoding")

        # Check for numerical columns
        if data.select_dtypes(include=["number"]).columns.any():
            steps.append("scaling")

        # Check for imbalanced classification
        object_cols = data.select_dtypes(include=["object"]).columns.tolist()
        if object_cols:
            # Assume last column is target for classification
            target_col = object_cols[-1]
            if data[target_col].nunique() < 10:  # Likely classification
                class_counts = data[target_col].value_counts()
                if class_counts.max() / class_counts.sum() > 0.7:  # 70% in one class
                    steps.append("imbalance_handling")

        # Check for high dimensionality
        if data.shape[1] > 20:
            steps.append("feature_selection")

        # Check for outliers
        numerical_cols = data.select_dtypes(include=["number"]).columns
        if len(numerical_cols) > 0:
            for col in numerical_cols:
                q1 = data[col].quantile(0.25)
                q3 = data[col].quantile(0.75)
                iqr = q3 - q1
                outliers = ((data[col] < (q1 - 1.5 * iqr)) | (data[col] > (q3 + 1.5 * iqr))).sum()
                if (outliers / len(data)) > 0.05:  # More than 5% outliers
                    steps.append("outlier_handling")
                    break

        return steps

    def _detect_problem_type(self, data: pd.DataFrame) -> str:
        """Detect likely problem type based on data characteristics."""
        object_cols = data.select_dtypes(include=["object"]).columns.tolist()

        if not object_cols:
            return "Regression"

        # Check if any column looks like a target (few unique values)
        for col in object_cols:
            unique_count = data[col].nunique()
            if 2 <= unique_count <= 10:  # Likely classification target
                return "Classification"

        return "Unknown"

    def _get_approach_recommendation(self, problem_type: str) -> str:
        """Get recommended approach based on problem type."""
        if problem_type == "Classification":
            return "Start with baseline models (Logistic Regression, Decision Tree), then try ensemble methods (Random Forest, Gradient Boosting). Use cross-validation and handle class imbalance if present."
        elif problem_type == "Regression":
            return "Start with Linear Regression for baseline, then try ensemble methods (Random Forest, Gradient Boosting). Use appropriate regression metrics (R², RMSE, MAE)."
        else:
            return "Perform exploratory data analysis first to understand the data structure and define the problem type."
"""
Clustering service - unsupervised learning with multiple algorithms.

This service provides comprehensive clustering capabilities including KMeans, DBSCAN,
Hierarchical clustering, and various evaluation metrics.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
from sklearn.metrics import (
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
)
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("asmeranda.services.clustering")


class ClusteringService:
    """Comprehensive clustering service with multiple algorithms."""

    def __init__(self):
        self.scaler = StandardScaler()

    def perform_clustering(
        self, data, method: str = "kmeans", **params
    ) -> Dict[str, Any]:
        """
        Perform clustering with specified method.

        Parameters
        ----------
        data : pd.DataFrame or np.ndarray
            Input data for clustering
        method : str
            Clustering method ('kmeans', 'dbscan', 'hierarchical', 'spectral')
        params : dict
            Algorithm-specific parameters

        Returns
        -------
        dict
            Clustering results with labels, metrics, and model information
        """
        try:
            # Convert to DataFrame if needed
            if not isinstance(data, pd.DataFrame):
                data = pd.DataFrame(data)

            # Scale data
            X_scaled = self.scaler.fit_transform(data)

            # Perform clustering based on method
            if method == "kmeans":
                result = self._kmeans_clustering(X_scaled, **params)
            elif method == "dbscan":
                result = self._dbscan_clustering(X_scaled, **params)
            elif method == "hierarchical":
                result = self._hierarchical_clustering(X_scaled, **params)
            elif method == "spectral":
                result = self._spectral_clustering(X_scaled, **params)
            else:
                raise ValueError(f"Unknown clustering method: {method}")

            # Calculate metrics
            metrics = self._calculate_clustering_metrics(X_scaled, result["labels"])

            return {
                "success": True,
                "labels": result["labels"].tolist(),
                "model": result["model"],
                "metrics": metrics,
                "method": method,
                "parameters": params,
            }

        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "method": method,
            }

    def _kmeans_clustering(self, X, n_clusters=3, random_state=42, **kwargs):
        """K-Means clustering."""
        n_clusters = min(n_clusters, X.shape[0] - 1)
        model = KMeans(n_clusters=n_clusters, random_state=random_state, **kwargs)
        labels = model.fit_predict(X)
        return {"labels": labels, "model": model}

    def _dbscan_clustering(self, X, eps=0.5, min_samples=5, **kwargs):
        """DBSCAN clustering."""
        model = DBSCAN(eps=eps, min_samples=min_samples, **kwargs)
        labels = model.fit_predict(X)
        return {"labels": labels, "model": model}

    def _hierarchical_clustering(self, X, n_clusters=3, **kwargs):
        """Hierarchical clustering."""
        n_clusters = min(n_clusters, X.shape[0] - 1)
        model = AgglomerativeClustering(n_clusters=n_clusters, **kwargs)
        labels = model.fit_predict(X)
        return {"labels": labels, "model": model}

    def _spectral_clustering(self, X, n_clusters=3, random_state=42, **kwargs):
        """Spectral clustering."""
        n_clusters = min(n_clusters, X.shape[0] - 1)
        model = SpectralClustering(
            n_clusters=n_clusters, random_state=random_state, **kwargs
        )
        labels = model.fit_predict(X)
        return {"labels": labels, "model": model}

    def _calculate_clustering_metrics(self, X, labels):
        """Calculate comprehensive clustering metrics."""
        if len(set(labels)) <= 1:
            return {
                "error": "Only one cluster or noise found",
                "n_clusters": len(set(labels)),
                "n_noise": (labels == -1).sum() if -1 in labels else 0,
            }

        mask = labels != -1  # Exclude noise for DBSCAN
        if mask.sum() <= 2:
            return {
                "error": "Not enough clustered points for metrics",
                "n_clusters": len(set(labels[mask])),
                "n_noise": (labels == -1).sum() if -1 in labels else 0,
            }

        try:
            metrics = {
                "silhouette_score": float(silhouette_score(X[mask], labels[mask])),
                "calinski_harabasz_score": float(
                    calinski_harabasz_score(X[mask], labels[mask])
                ),
                "davies_bouldin_score": float(
                    davies_bouldin_score(X[mask], labels[mask])
                ),
                "n_clusters": len(set(labels[mask])),
                "n_noise": (labels == -1).sum() if -1 in labels else 0,
            }

            # Cluster size distribution
            unique_labels, counts = np.unique(labels[mask], return_counts=True)
            metrics["cluster_sizes"] = dict(zip(unique_labels.tolist(), counts.tolist()))
            metrics["cluster_size_std"] = float(np.std(counts))
            metrics["cluster_size_mean"] = float(np.mean(counts))

            return metrics

        except Exception as e:
            logger.error(f"Metrics calculation failed: {str(e)}")
            return {
                "error": f"Metrics calculation failed: {str(e)}",
                "n_clusters": len(set(labels[mask])),
                "n_noise": (labels == -1).sum() if -1 in labels else 0,
            }

    def find_optimal_k(self, X, max_k=10, random_state=42):
        """
        Find optimal number of clusters using elbow method and silhouette analysis.

        Parameters
        ----------
        X : array-like
            Input data
        max_k : int
            Maximum number of clusters to try
        random_state : int
            Random state for reproducibility

        Returns
        -------
        dict
            Results with k values, inertias, and silhouette scores
        """
        try:
            max_k = min(max_k, X.shape[0] - 1)
            if max_k < 2:
                return {"error": "Not enough samples for k>1"}

            inertias = []
            silhouette_scores = []

            for k in range(2, max_k + 1):
                kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
                labels = kmeans.fit_predict(X)
                inertias.append(kmeans.inertia_)

                if len(set(labels)) > 1:
                    try:
                        score = silhouette_score(X, labels)
                        silhouette_scores.append(float(score))
                    except Exception:
                        silhouette_scores.append(0.0)
                else:
                    silhouette_scores.append(0.0)

            # Find optimal k using elbow method
            deltas = np.diff(inertias)
            optimal_k_elbow = (
                np.argmax(deltas) + 2 if len(deltas) > 0 else 2
            )

            # Find optimal k using silhouette
            optimal_k_silhouette = (
                np.argmax(silhouette_scores) + 2 if silhouette_scores else 2
            )

            return {
                "success": True,
                "k_values": list(range(2, max_k + 1)),
                "inertias": [float(x) for x in inertias],
                "silhouette_scores": silhouette_scores,
                "optimal_k_elbow": optimal_k_elbow,
                "optimal_k_silhouette": optimal_k_silhouette,
            }

        except Exception as e:
            logger.error(f"Optimal k calculation failed: {str(e)}")
            return {"success": False, "error": str(e)}
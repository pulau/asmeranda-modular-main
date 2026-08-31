"""
Advanced ML Service - Core features including UMAP, HDBSCAN, and basic forecasting.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM

logger = logging.getLogger("asmeranda.services.advanced_ml")


class AdvancedMLService:
    """Service for advanced ML features including dimensionality reduction, clustering, and forecasting."""
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def umap_dimensionality_reduction(
        self, 
        data: pd.DataFrame, 
        n_components: int = 2,
        n_neighbors: int = 15,
        min_dist: float = 0.1
    ) -> Dict[str, Any]:
        """
        Perform UMAP dimensionality reduction.
        
        Args:
            data: Input DataFrame for dimensionality reduction
            n_components: Number of dimensions for output
            n_neighbors: Number of neighbors for UMAP
            min_dist: Minimum distance for UMAP
            
        Returns:
            Dictionary with reduced data and metadata
        """
        try:
            # Check if umap-learn is available
            try:
                import umap
            except ImportError:
                logger.warning("umap-learn not available, falling back to PCA")
                return self.pca_dimensionality_reduction(data, n_components)
            
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply UMAP
            reducer = umap.UMAP(
                n_components=n_components,
                n_neighbors=n_neighbors,
                min_dist=min_dist,
                random_state=42
            )
            embedding = reducer.fit_transform(scaled_data)
            
            # Create result DataFrame
            columns = [f"UMAP_{i+1}" for i in range(n_components)]
            result_df = pd.DataFrame(embedding, columns=columns)
            
            return {
                "success": True,
                "data": result_df,
                "method": "umap",
                "parameters": {
                    "n_components": n_components,
                    "n_neighbors": n_neighbors,
                    "min_dist": min_dist
                },
                "original_shape": data.shape,
                "reduced_shape": embedding.shape
            }
            
        except Exception as e:
            logger.error(f"UMAP dimensionality reduction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "umap"
            }
    
    def pca_dimensionality_reduction(
        self, 
        data: pd.DataFrame, 
        n_components: int = 2
    ) -> Dict[str, Any]:
        """
        Perform PCA dimensionality reduction (fallback for UMAP).
        
        Args:
            data: Input DataFrame for dimensionality reduction
            n_components: Number of dimensions for output
            
        Returns:
            Dictionary with reduced data and metadata
        """
        try:
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply PCA
            pca = PCA(n_components=n_components, random_state=42)
            embedding = pca.fit_transform(scaled_data)
            
            # Create result DataFrame
            columns = [f"PC_{i+1}" for i in range(n_components)]
            result_df = pd.DataFrame(embedding, columns=columns)
            
            return {
                "success": True,
                "data": result_df,
                "method": "pca",
                "parameters": {
                    "n_components": n_components,
                    "explained_variance_ratio": pca.explained_variance_ratio_.tolist()
                },
                "original_shape": data.shape,
                "reduced_shape": embedding.shape
            }
            
        except Exception as e:
            logger.error(f"PCA dimensionality reduction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "pca"
            }
    
    def hdbscan_clustering(
        self,
        data: pd.DataFrame,
        min_cluster_size: int = 5,
        min_samples: int = None,
        metric: str = 'euclidean'
    ) -> Dict[str, Any]:
        """
        Perform HDBSCAN clustering.
        
        Args:
            data: Input DataFrame for clustering
            min_cluster_size: Minimum size of clusters
            min_samples: Number of samples in neighborhood
            metric: Distance metric to use
            
        Returns:
            Dictionary with cluster labels and metadata
        """
        try:
            # Check if hdbscan is available
            try:
                import hdbscan
            except ImportError:
                logger.warning("hdbscan not available, falling back to DBSCAN")
                return self.dbscan_clustering(data, eps=0.5, min_samples=min_cluster_size)
            
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply HDBSCAN
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric=metric,
                prediction_data=True
            )
            labels = clusterer.fit_predict(scaled_data)
            
            # Calculate cluster statistics
            unique_labels = set(labels)
            n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            return {
                "success": True,
                "labels": labels.tolist(),
                "method": "hdbscan",
                "parameters": {
                    "min_cluster_size": min_cluster_size,
                    "min_samples": min_samples,
                    "metric": metric
                },
                "n_clusters": n_clusters,
                "n_noise": n_noise,
                "cluster_probabilities": clusterer.probabilities_.tolist() if hasattr(clusterer, 'probabilities_') else None
            }
            
        except Exception as e:
            logger.error(f"HDBSCAN clustering failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "hdbscan"
            }
    
    def dbscan_clustering(
        self,
        data: pd.DataFrame,
        eps: float = 0.5,
        min_samples: int = 5,
        metric: str = 'euclidean'
    ) -> Dict[str, Any]:
        """
        Perform DBSCAN clustering (fallback for HDBSCAN).
        
        Args:
            data: Input DataFrame for clustering
            eps: Maximum distance between samples
            min_samples: Number of samples in neighborhood
            metric: Distance metric to use
            
        Returns:
            Dictionary with cluster labels and metadata
        """
        try:
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply DBSCAN
            clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
            labels = clusterer.fit_predict(scaled_data)
            
            # Calculate cluster statistics
            unique_labels = set(labels)
            n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            return {
                "success": True,
                "labels": labels.tolist(),
                "method": "dbscan",
                "parameters": {
                    "eps": eps,
                    "min_samples": min_samples,
                    "metric": metric
                },
                "n_clusters": n_clusters,
                "n_noise": n_noise
            }
            
        except Exception as e:
            logger.error(f"DBSCAN clustering failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "dbscan"
            }
    
    def isolation_forest_anomaly_detection(
        self,
        data: pd.DataFrame,
        contamination: float = 0.1,
        n_estimators: int = 100
    ) -> Dict[str, Any]:
        """
        Perform anomaly detection using Isolation Forest.
        
        Args:
            data: Input DataFrame for anomaly detection
            contamination: Expected proportion of outliers
            n_estimators: Number of trees in the forest
            
        Returns:
            Dictionary with anomaly scores and labels
        """
        try:
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply Isolation Forest
            iso_forest = IsolationForest(
                contamination=contamination,
                n_estimators=n_estimators,
                random_state=42
            )
            predictions = iso_forest.fit_predict(scaled_data)
            scores = iso_forest.score_samples(scaled_data)
            
            # Convert predictions: -1 (anomaly) to 1, 1 (normal) to 0
            anomaly_labels = (predictions == -1).astype(int)
            
            return {
                "success": True,
                "anomaly_labels": anomaly_labels.tolist(),
                "anomaly_scores": scores.tolist(),
                "method": "isolation_forest",
                "parameters": {
                    "contamination": contamination,
                    "n_estimators": n_estimators
                },
                "n_anomalies": int(anomaly_labels.sum()),
                "anomaly_rate": float(anomaly_labels.mean())
            }
            
        except Exception as e:
            logger.error(f"Isolation Forest anomaly detection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "isolation_forest"
            }
    
    def one_class_svm_anomaly_detection(
        self,
        data: pd.DataFrame,
        nu: float = 0.1,
        kernel: str = 'rbf'
    ) -> Dict[str, Any]:
        """
        Perform anomaly detection using One-Class SVM.
        
        Args:
            data: Input DataFrame for anomaly detection
            nu: Expected proportion of outliers
            kernel: Kernel type to use
            
        Returns:
            Dictionary with anomaly labels and decision scores
        """
        try:
            # Prepare data
            data_array = data.select_dtypes(include=[np.number]).values
            scaled_data = self.scaler.fit_transform(data_array)
            
            # Apply One-Class SVM
            svm = OneClassSVM(nu=nu, kernel=kernel)
            predictions = svm.fit_predict(scaled_data)
            scores = svm.decision_function(scaled_data)
            
            # Convert predictions: -1 (anomaly) to 1, 1 (normal) to 0
            anomaly_labels = (predictions == -1).astype(int)
            
            return {
                "success": True,
                "anomaly_labels": anomaly_labels.tolist(),
                "decision_scores": scores.tolist(),
                "method": "one_class_svm",
                "parameters": {
                    "nu": nu,
                    "kernel": kernel
                },
                "n_anomalies": int(anomaly_labels.sum()),
                "anomaly_rate": float(anomaly_labels.mean())
            }
            
        except Exception as e:
            logger.error(f"One-Class SVM anomaly detection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "one_class_svm"
            }
    
    def basic_forecasting(
        self,
        data: pd.DataFrame,
        target_column: str,
        periods: int = 10,
        method: str = 'simple'
    ) -> Dict[str, Any]:
        """
        Perform basic time series forecasting.
        
        Args:
            data: Input DataFrame with time series data
            target_column: Column to forecast
            periods: Number of periods to forecast
            method: Forecasting method ('simple', 'moving_avg', 'linear')
            
        Returns:
            Dictionary with forecast results
        """
        try:
            if target_column not in data.columns:
                return {
                    "success": False,
                    "error": f"Column {target_column} not found in data",
                    "method": method
                }
            
            series = data[target_column].values
            last_values = series[-periods:] if len(series) >= periods else series
            
            if method == 'simple':
                # Simple forecasting using last value
                forecast = np.full(periods, series[-1])
                method_name = "Simple (last value)"
                
            elif method == 'moving_avg':
                # Moving average forecasting
                window = min(5, len(series))
                forecast = np.full(periods, np.mean(series[-window:]))
                method_name = "Moving Average"
                
            elif method == 'linear':
                # Linear extrapolation
                from scipy import stats
                x = np.arange(len(series))
                slope, intercept, _, _, _ = stats.linregress(x, series)
                forecast = slope * np.arange(len(series), len(series) + periods) + intercept
                method_name = "Linear Extrapolation"
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown method: {method}",
                    "method": method
                }
            
            return {
                "success": True,
                "forecast": forecast.tolist(),
                "method": method,
                "method_name": method_name,
                "parameters": {
                    "periods": periods,
                    "target_column": target_column
                },
                "historical_data": series.tolist(),
                "forecast_periods": periods
            }
            
        except Exception as e:
            logger.error(f"Basic forecasting failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": method
            }
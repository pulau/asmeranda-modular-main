"""
Utilities Service - Core data processing utilities.

Provides:
- Time series preprocessing functions
- Advanced missing value handling
- Outlier detection algorithms
- Data validation functions
- Data type detection and conversion
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import warnings

logger = logging.getLogger("asmeranda.services.utilities")


class UtilitiesService:
    """Service for core data processing utilities."""
    
    def __init__(self):
        self.supported_date_formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
            '%m/%d/%Y', '%m-%d-%Y', '%d.%m.%Y'
        ]
    
    def detect_data_types(self, data: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        """
        Detect data types for each column in the DataFrame.
        
        Args:
            data: Input DataFrame
            
        Returns:
            Dictionary with data type information for each column
        """
        result = {}
        
        for column in data.columns:
            col_data = data[column]
            dtype_info = {
                'pandas_type': str(col_data.dtype),
                'inferred_type': self._infer_column_type(col_data),
                'missing_count': int(col_data.isna().sum()),
                'missing_percentage': float(col_data.isna().sum() / len(col_data) * 100),
                'unique_count': int(col_data.nunique()),
                'sample_values': col_data.dropna().head(5).tolist()
            }
            result[column] = dtype_info
            
        return result
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """Infer the logical data type of a column."""
        if series.dtype == 'object':
            # Check if it's datetime
            try:
                pd.to_datetime(series.head(10), errors='raise')
                return 'datetime'
            except:
                # Check if it's categorical
                if series.nunique() / len(series) < 0.5:
                    return 'categorical'
                return 'text'
        elif pd.api.types.is_numeric_dtype(series):
            if series.dtype == 'int64' or series.dtype == 'int32':
                return 'integer'
            elif series.dtype == 'float64' or series.dtype == 'float32':
                return 'float'
            return 'numeric'
        elif pd.api.types.is_bool_dtype(series):
            return 'boolean'
        return 'unknown'
    
    def handle_missing_values(
        self,
        data: pd.DataFrame,
        strategy: str = 'auto',
        numeric_strategy: str = 'mean',
        categorical_strategy: str = 'mode',
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Handle missing values in the DataFrame.
        
        Args:
            data: Input DataFrame
            strategy: Overall strategy ('auto', 'drop', 'fill', 'none')
            numeric_strategy: Strategy for numeric columns ('mean', 'median', 'mode', 'forward_fill', 'backward_fill')
            categorical_strategy: Strategy for categorical columns ('mode', 'constant', 'drop')
            threshold: Threshold for dropping columns with too many missing values
            
        Returns:
            Dictionary with cleaned data and metadata
        """
        try:
            df = data.copy()
            original_shape = df.shape
            missing_info = {}
            
            # Check missing values
            missing_counts = df.isna().sum()
            missing_percentages = (missing_counts / len(df)) * 100
            
            # Drop columns with too many missing values
            if strategy == 'auto' or strategy == 'drop':
                cols_to_drop = missing_percentages[missing_percentages > threshold * 100].index.tolist()
                if cols_to_drop:
                    df = df.drop(columns=cols_to_drop)
                    missing_info['dropped_columns'] = cols_to_drop
            
            # Handle remaining missing values
            if strategy == 'auto' or strategy == 'fill':
                # Numeric columns
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if df[col].isna().any():
                        if numeric_strategy == 'mean':
                            df[col].fillna(df[col].mean(), inplace=True)
                        elif numeric_strategy == 'median':
                            df[col].fillna(df[col].median(), inplace=True)
                        elif numeric_strategy == 'mode':
                            mode_val = df[col].mode()[0] if not df[col].mode().empty else 0
                            df[col].fillna(mode_val, inplace=True)
                        elif numeric_strategy == 'forward_fill':
                            df[col].fillna(method='ffill', inplace=True)
                        elif numeric_strategy == 'backward_fill':
                            df[col].fillna(method='bfill', inplace=True)
                
                # Categorical columns
                categorical_cols = df.select_dtypes(include=['object']).columns
                for col in categorical_cols:
                    if df[col].isna().any():
                        if categorical_strategy == 'mode':
                            mode_val = df[col].mode()[0] if not df[col].mode().empty else 'unknown'
                            df[col].fillna(mode_val, inplace=True)
                        elif categorical_strategy == 'constant':
                            df[col].fillna('unknown', inplace=True)
                        elif categorical_strategy == 'drop':
                            df = df.dropna(subset=[col])
            
            return {
                'success': True,
                'data': df,
                'original_shape': original_shape,
                'new_shape': df.shape,
                'missing_info': missing_info,
                'strategy': strategy,
                'numeric_strategy': numeric_strategy,
                'categorical_strategy': categorical_strategy
            }
            
        except Exception as e:
            logger.error(f"Missing value handling failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_data': data
            }
    
    def detect_outliers(
        self,
        data: pd.DataFrame,
        method: str = 'iqr',
        threshold: float = 1.5,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect outliers in numeric columns.
        
        Args:
            data: Input DataFrame
            method: Detection method ('iqr', 'zscore', 'isolation_forest')
            threshold: Threshold for outlier detection
            columns: Specific columns to check (None for all numeric)
            
        Returns:
            Dictionary with outlier information
        """
        try:
            df = data.copy()
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            outlier_info = {}
            
            for col in columns:
                if col not in df.columns:
                    continue
                    
                col_data = df[col].dropna()
                outliers = []
                
                if method == 'iqr':
                    Q1 = col_data.quantile(0.25)
                    Q3 = col_data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR
                    outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)].index.tolist()
                    
                elif method == 'zscore':
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    outliers = col_data[z_scores > threshold].index.tolist()
                    
                elif method == 'isolation_forest':
                    try:
                        from sklearn.ensemble import IsolationForest
                        iso_forest = IsolationForest(contamination=0.1, random_state=42)
                        predictions = iso_forest.fit_predict(col_data.values.reshape(-1, 1))
                        outliers = col_data[predictions == -1].index.tolist()
                    except ImportError:
                        logger.warning("sklearn not available, falling back to IQR")
                        Q1 = col_data.quantile(0.25)
                        Q3 = col_data.quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - threshold * IQR
                        upper_bound = Q3 + threshold * IQR
                        outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)].index.tolist()
                
                outlier_info[col] = {
                    'outlier_count': len(outliers),
                    'outlier_percentage': len(outliers) / len(col_data) * 100,
                    'outlier_indices': outliers[:100],  # Limit to first 100
                    'method': method,
                    'threshold': threshold
                }
            
            return {
                'success': True,
                'outlier_info': outlier_info,
                'method': method,
                'threshold': threshold,
                'columns_analyzed': columns
            }
            
        except Exception as e:
            logger.error(f"Outlier detection failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_data(
        self,
        data: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
        column_types: Optional[Dict[str, str]] = None,
        value_ranges: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> Dict[str, Any]:
        """
        Validate data against specified constraints.
        
        Args:
            data: Input DataFrame
            required_columns: List of required column names
            column_types: Dictionary mapping column names to expected types
            value_ranges: Dictionary mapping column names to (min, max) ranges
            
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'column_validation': {}
            }
            
            # Check required columns
            if required_columns:
                missing_cols = [col for col in required_columns if col not in data.columns]
                if missing_cols:
                    validation_results['is_valid'] = False
                    validation_results['errors'].append(f"Missing required columns: {missing_cols}")
            
            # Check column types
            if column_types:
                for col, expected_type in column_types.items():
                    if col in data.columns:
                        actual_type = str(data[col].dtype)
                        if expected_type == 'numeric' and not pd.api.types.is_numeric_dtype(data[col]):
                            validation_results['column_validation'][col] = {
                                'expected': expected_type,
                                'actual': actual_type,
                                'valid': False
                            }
                            validation_results['is_valid'] = False
                        else:
                            validation_results['column_validation'][col] = {
                                'expected': expected_type,
                                'actual': actual_type,
                                'valid': True
                            }
            
            # Check value ranges
            if value_ranges:
                for col, (min_val, max_val) in value_ranges.items():
                    if col in data.columns and pd.api.types.is_numeric_dtype(data[col]):
                        out_of_range = data[(data[col] < min_val) | (data[col] > max_val)]
                        if not out_of_range.empty:
                            validation_results['warnings'].append(
                                f"Column {col} has {len(out_of_range)} values outside range [{min_val}, {max_val}]"
                            )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def preprocess_timeseries(
        self,
        data: pd.DataFrame,
        date_column: Optional[str] = None,
        value_column: Optional[str] = None,
        frequency: str = 'D'
    ) -> Dict[str, Any]:
        """
        Preprocess time series data.
        
        Args:
            data: Input DataFrame
            date_column: Name of date column
            value_column: Name of value column
            frequency: Time series frequency ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            Dictionary with preprocessed time series data
        """
        try:
            df = data.copy()
            
            # Auto-detect date column if not specified
            if date_column is None:
                for col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='raise')
                        date_column = col
                        break
                    except:
                        continue
            
            if date_column and date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column])
                df = df.sort_values(date_column)
                df.set_index(date_column, inplace=True)
            
            # Handle missing time points
            if frequency:
                df = df.asfreq(frequency)
            
            # Fill missing values
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            return {
                'success': True,
                'data': df,
                'original_shape': data.shape,
                'new_shape': df.shape,
                'date_column': date_column,
                'frequency': frequency,
                'date_range': {
                    'start': str(df.index.min()) if hasattr(df.index, 'min') else None,
                    'end': str(df.index.max()) if hasattr(df.index, 'max') else None
                }
            }
            
        except Exception as e:
            logger.error(f"Time series preprocessing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert_data_types(
        self,
        data: pd.DataFrame,
        type_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Convert data types for specified columns.
        
        Args:
            data: Input DataFrame
            type_mapping: Dictionary mapping column names to target types
            
        Returns:
            Dictionary with converted data and conversion info
        """
        try:
            df = data.copy()
            conversion_info = {}
            
            for col, target_type in type_mapping.items():
                if col not in df.columns:
                    conversion_info[col] = {'success': False, 'error': 'Column not found'}
                    continue
                
                original_type = str(df[col].dtype)
                
                try:
                    if target_type == 'numeric':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    elif target_type == 'datetime':
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    elif target_type == 'category':
                        df[col] = df[col].astype('category')
                    elif target_type == 'string':
                        df[col] = df[col].astype(str)
                    elif target_type == 'boolean':
                        df[col] = df[col].astype(bool)
                    
                    conversion_info[col] = {
                        'success': True,
                        'original_type': original_type,
                        'new_type': str(df[col].dtype)
                    }
                except Exception as e:
                    conversion_info[col] = {
                        'success': False,
                        'error': str(e),
                        'original_type': original_type
                    }
            
            return {
                'success': True,
                'data': df,
                'conversion_info': conversion_info
            }
            
        except Exception as e:
            logger.error(f"Data type conversion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
"""
Preprocessing service - handling imputasi, scaling, encoding, train-test split.

Service ini pure-Python (tidak depend on FastAPI). Output disimpan
ke state registry (``core.state``) dan state_id dikembalikan ke caller.
"""
from __future__ import annotations

import pickle
import uuid
import asyncio
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    LabelEncoder,
    MinMaxScaler,
    OneHotEncoder,
    PowerTransformer,
    QuantileTransformer,
    RobustScaler,
    StandardScaler,
)

from core.state import get_state


def _impute(
    df: pd.DataFrame,
    num_cols: List[str],
    cat_cols: List[str],
    strategy: str,
) -> pd.DataFrame:
    """Isi missing values (mean/median/most_frequent/drop/auto)."""
    out = df.copy()
    if strategy in ("auto", ""):
        strategy = "mean"
    if strategy == "drop":
        out = out.dropna().reset_index(drop=True)
        return out
    for c in num_cols:
        if c in out.columns and out[c].isnull().any():
            if strategy == "median":
                out[c] = out[c].fillna(out[c].median())
            elif strategy == "most_frequent":
                mode_val = out[c].mode()
                fill = mode_val.iloc[0] if len(mode_val) else 0
                out[c] = out[c].fillna(fill)
            else:  # default: mean
                out[c] = out[c].fillna(out[c].mean())
    for c in cat_cols:
        if c in out.columns and out[c].isnull().any():
            mode_val = out[c].mode()
            fill = mode_val.iloc[0] if len(mode_val) else "missing"
            out[c] = out[c].fillna(fill)
    return out


def _scale(
    X: pd.DataFrame,
    num_cols: List[str],
    method: str,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Scaling kolom numerik sesuai metode."""
    info: Dict[str, Any] = {"method": method}
    if method == "none" or not num_cols:
        return X, info
    valid_cols = [c for c in num_cols if c in X.columns]
    if not valid_cols:
        return X, info
    if method == "standard":
        scaler = StandardScaler()
    elif method == "minmax":
        scaler = MinMaxScaler()
    elif method == "robust":
        scaler = RobustScaler()
    elif method == "power":
        scaler = PowerTransformer(method="yeo-johnson")
    elif method == "quantile":
        scaler = QuantileTransformer(output_distribution="normal", random_state=0)
    else:
        # auto: pilih otomatis
        skew = X[valid_cols].skew().abs().mean()
        if skew > 1.0:
            scaler = PowerTransformer(method="yeo-johnson")
            method_use = "power"
        elif skew > 0.5:
            scaler = QuantileTransformer(output_distribution="normal", random_state=0)
            method_use = "quantile"
        else:
            scaler = StandardScaler()
            method_use = "standard"
        info["method"] = method_use
        scaler.fit(X[valid_cols])
        X[valid_cols] = scaler.transform(X[valid_cols])
        info["scaler"] = pickle.dumps(scaler).hex()
        return X, info

    scaler.fit(X[valid_cols])
    X[valid_cols] = scaler.transform(X[valid_cols])
    info["scaler"] = pickle.dumps(scaler).hex()
    return X, info


def _encode(
    X: pd.DataFrame,
    cat_cols: List[str],
    apply_encoding: bool,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """One-hot encoding untuk kolom kategorikal (dibatasi agar ukuran tidak meledak)."""
    info: Dict[str, Any] = {"encoded_columns": []}
    if not apply_encoding or not cat_cols:
        return X, info
    valid_cols = [c for c in cat_cols if c in X.columns]
    for c in valid_cols:
        n_unique = X[c].nunique(dropna=True)
        if n_unique <= 20:
            # One-hot encode
            dummies = pd.get_dummies(X[c], prefix=c, drop_first=True, dummy_na=False)
            X = pd.concat([X.drop(columns=[c]), dummies], axis=1)
            info["encoded_columns"].extend(dummies.columns.tolist())
        else:
            # Frequency encoding (lebih aman untuk high-cardinality)
            freq = X[c].value_counts(normalize=True)
            X[c + "_freq"] = X[c].map(freq)
            X = X.drop(columns=[c])
            info["encoded_columns"].append(c + "_freq")
    return X, info


def _feature_selection(
    X: pd.DataFrame,
    y: Optional[pd.Series],
    method: str,
    max_features: int,
    threshold: float,
) -> Tuple[pd.DataFrame, List[str], Dict[str, Any]]:
    """Feature selection menggunakan berbagai metode."""
    info: Dict[str, Any] = {"method": method, "selected_features": []}
    
    if method == "none" or not method:
        return X, X.columns.tolist(), info
    
    try:
        from sklearn.feature_selection import (
            VarianceThreshold, SelectKBest, f_classif, f_regression,
            RFE, SelectFromModel
        )
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        # Jika sklearn tidak tersedia, return original
        return X, X.columns.tolist(), info
    
    X_numeric = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    
    if method == "variance":
        selector = VarianceThreshold(threshold=threshold)
        X_selected = selector.fit_transform(X_numeric)
        selected_features = X_numeric.columns[selector.get_support()].tolist()
        X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        info["selected_features"] = selected_features
        return X_selected, selected_features, info
        
    elif method == "correlation":
        # Remove highly correlated features
        corr_matrix = X_numeric.corr().abs()
        upper = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        to_drop = [
            column for column in upper.columns 
            if any(upper[column] > threshold)
        ]
        X_selected = X_numeric.drop(columns=to_drop)
        selected_features = X_selected.columns.tolist()
        info["selected_features"] = selected_features
        info["dropped_features"] = to_drop
        return X_selected, selected_features, info
        
    elif method == "kbest":
        if y is None:
            return X, X.columns.tolist(), info
        score_func = f_classif if y.dtype == 'object' or y.nunique() < 10 else f_regression
        k = min(max_features, X_numeric.shape[1])
        selector = SelectKBest(score_func=score_func, k=k)
        X_selected = selector.fit_transform(X_numeric, y)
        selected_features = X_numeric.columns[selector.get_support()].tolist()
        X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        info["selected_features"] = selected_features
        return X_selected, selected_features, info
        
    elif method == "rfe":
        if y is None:
            return X, X.columns.tolist(), info
        k = min(max_features, X_numeric.shape[1])
        estimator = RandomForestClassifier(n_estimators=50, random_state=42)
        selector = RFE(estimator, n_features_to_select=k)
        X_selected = selector.fit_transform(X_numeric, y)
        selected_features = X_numeric.columns[selector.get_support()].tolist()
        X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        info["selected_features"] = selected_features
        return X_selected, selected_features, info
    
    # Default: return original
    return X, X.columns.tolist(), info


def auto_configure_pipeline(df: pd.DataFrame, target_column: Optional[str] = None, problem_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Otomatis mendeteksi karakteristik data dan menghasilkan konfigurasi preprocessing optimal.
    """
    n_rows, n_cols = df.shape
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    if target_column and target_column in num_cols:
        num_cols = [c for c in num_cols if c != target_column]
    if target_column and target_column in cat_cols:
        cat_cols = [c for c in cat_cols if c != target_column]

    config: Dict[str, Any] = {
        "imputation_strategy": "median" if len(num_cols) > 0 else "auto",
        "scaling_method": "auto",
        "apply_encoding": True,
        "test_size": 0.2,
        "random_state": 42,
    }

    # Skewness & Scaling choice
    if num_cols:
        skewness = df[num_cols].skew().abs().mean()
        if skewness > 1.5:
            config["scaling_method"] = "robust"
        elif skewness > 0.8:
            config["scaling_method"] = "power"
        else:
            config["scaling_method"] = "standard"

    # Dimensionality & Feature Selection
    if n_cols > 30 and n_rows > 50:
        config["feature_selection"] = {
            "method": "variance" if n_cols > 100 else "correlation",
            "threshold": 0.90 if n_cols <= 50 else 0.80,
            "max_features": min(30, n_cols),
        }

    # Imbalance Detection
    if target_column and target_column in df.columns and problem_type == "Classification":
        vc = df[target_column].value_counts(normalize=True)
        if len(vc) >= 2 and vc.min() < 0.20:
            config["imbalance_handling"] = {
                "method": "smote" if len(df) > 100 else "oversample",
                "sampling_strategy": "auto",
            }

    return config


def _handle_imbalance(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    method: str,
    sampling_strategy: str,
) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
    """Handle imbalance dataset menggunakan imblearn dengan adaptive k_neighbors."""
    info: Dict[str, Any] = {"method": method, "sampling_strategy": sampling_strategy}
    
    if method == "none" or not method:
        return X_train, y_train, info
    
    try:
        from imblearn.over_sampling import SMOTE, RandomOverSampler, ADASYN
        from imblearn.under_sampling import RandomUnderSampler
    except ImportError:
        info["error"] = "imblearn not installed"
        return X_train, y_train, info
    
    # Convert X_train to numeric for imblearn
    X_train_numeric = X_train.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    
    # Hitung jumlah sampel kelas minoritas
    class_counts = y_train.value_counts()
    min_class_count = int(class_counts.min()) if len(class_counts) > 0 else 0

    if method == "oversample":
        sampler = RandomOverSampler(sampling_strategy=sampling_strategy, random_state=42)
    elif method == "undersample":
        sampler = RandomUnderSampler(sampling_strategy=sampling_strategy, random_state=42)
    elif method == "smote":
        if min_class_count < 2:
            sampler = RandomOverSampler(sampling_strategy=sampling_strategy, random_state=42)
            info["note"] = "Minority samples < 2, fallback to RandomOverSampler"
        else:
            k_neighbors = min(min_class_count - 1, 5)
            sampler = SMOTE(sampling_strategy=sampling_strategy, k_neighbors=k_neighbors, random_state=42)
    elif method == "adasyn":
        if min_class_count < 3:
            sampler = RandomOverSampler(sampling_strategy=sampling_strategy, random_state=42)
            info["note"] = "Minority samples < 3, fallback to RandomOverSampler"
        else:
            n_neighbors = min(min_class_count - 1, 5)
            sampler = ADASYN(sampling_strategy=sampling_strategy, n_neighbors=n_neighbors, random_state=42)
    else:
        info["error"] = f"Unknown method: {method}"
        return X_train, y_train, info
    
    try:
        X_resampled, y_resampled = sampler.fit_resample(X_train_numeric, y_train)
        X_resampled = pd.DataFrame(X_resampled, columns=X_train.columns, index=X_resampled.index)
        info["original_shape"] = X_train.shape
        info["resampled_shape"] = X_resampled.shape
        info["class_distribution_before"] = y_train.value_counts().to_dict()
        info["class_distribution_after"] = y_resampled.value_counts().to_dict()
        return X_resampled, y_resampled, info
    except Exception as e:
        info["error"] = str(e)
        return X_train, y_train, info


def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Jalankan preprocessing sesuai config.

    Parameters
    ----------
    config : dict
        {
          'dataset_id': str,
          'target_column': str|None,
          'problem_type': 'Classification'|'Regression'|'Forecasting'|None,
          'numerical_features': [str],
          'categorical_features': [str],
          'scaling_method': 'auto'|'standard'|...,
          'imputation_strategy': 'auto'|'mean'|...,
          'apply_encoding': bool,
          'test_size': float,
          'random_state': int,
        }

    Returns
    -------
    dict
        {
          'success': bool,
          'state_id': str,
          'n_samples_train': int,
          'n_samples_test': int,
          'n_features': int,
          'feature_names': [str],
          'target_column': str|None,
          'problem_type': str|None,
          'preprocessing_steps': [str],
          'error': str|None,
        }
    """
    from backend.services import dataset_service
    # Import WebSocket manager (lazy, agar tidak circular import)
    try:
        from backend.api.v1.ws import manager as ws_manager
    except Exception:
        ws_manager = None

    async def _broadcast(d_id: str, progress: int, message: str):
        if ws_manager and d_id:
            await ws_manager.broadcast(d_id, {"progress": progress, "message": message})

    def _try_broadcast(d_id: str, progress: int, message: str):
        """Coba broadcast tanpa blocking."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_broadcast(d_id, progress, message))
            else:
                loop.run_until_complete(_broadcast(d_id, progress, message))
        except Exception:
            pass  # broadcast gagal tidak boleh menghentikan preprocessing

    dataset_id = config.get("dataset_id")
    df = dataset_service.get_dataset(dataset_id) if dataset_id else None
    if df is None:
        return {"success": False, "error": f"Dataset {dataset_id} tidak ditemukan"}

    _try_broadcast(dataset_id, 5, "Memulai preprocessing...")
    steps: List[str] = []
    target_column = config.get("target_column")
    problem_type = config.get("problem_type")

    # Tentukan kolom fitur
    if config.get("numerical_features") is None:
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    else:
        num_cols = list(config["numerical_features"])
    if config.get("categorical_features") is None:
        cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    else:
        cat_cols = list(config["categorical_features"])

    if target_column and target_column in num_cols:
        num_cols = [c for c in num_cols if c != target_column]
    if target_column and target_column in cat_cols:
        cat_cols = [c for c in cat_cols if c != target_column]

    # 1) Imputasi
    df_clean = _impute(df, num_cols, cat_cols, config.get("imputation_strategy", "auto"))
    steps.append(f"imputation={config.get('imputation_strategy', 'auto')}")
    _try_broadcast(dataset_id, 30, "Imputasi selesai. Memisahkan target...")

    # 2) Pisahkan target
    y: Optional[pd.Series] = None
    if target_column and target_column in df_clean.columns:
        y = df_clean[target_column]
        X = df_clean.drop(columns=[target_column])
    else:
        X = df_clean.copy()

    # 3) Scaling numerik
    X, scale_info = _scale(X, num_cols, config.get("scaling_method", "auto"))
    steps.append(f"scaling={scale_info.get('method', 'auto')}")
    _try_broadcast(dataset_id, 60, "Scaling selesai. Encoding kategorikal...")

    # 4) Encoding kategorikal
    X, enc_info = _encode(X, cat_cols, config.get("apply_encoding", True))
    if enc_info.get("encoded_columns"):
        steps.append(f"encoding={len(enc_info['encoded_columns'])} new cols")
    _try_broadcast(dataset_id, 70, "Encoding selesai. Feature selection...")

    # 5) Feature selection
    fs_config = config.get("feature_selection")
    if fs_config:
        fs_method = fs_config.get("method", "none")
        fs_max_features = fs_config.get("max_features", 10)
        fs_threshold = fs_config.get("threshold", 0.05)
        X, selected_features, fs_info = _feature_selection(
            X, y, fs_method, fs_max_features, fs_threshold
        )
        if fs_info.get("selected_features"):
            steps.append(f"feature_selection={fs_method} ({len(selected_features)} features)")
            _try_broadcast(dataset_id, 75, "Feature selection selesai. Train-test split...")
        else:
            _try_broadcast(dataset_id, 75, "Feature selection skipped. Train-test split...")
    else:
        _try_broadcast(dataset_id, 75, "Feature selection skipped. Train-test split...")

    # 6) Train-test split
    test_size = float(config.get("test_size", 0.2))
    random_state = int(config.get("random_state", 42))
    if y is not None and problem_type in ("Classification", "Regression"):
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state,
                stratify=y if problem_type == "Classification" and y.nunique() > 1 else None,
            )
        except Exception:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
    else:
        # Forecasting / unsupervised: split sequential
        n = len(X)
        idx = int(n * (1 - test_size))
        X_train, X_test = X.iloc[:idx], X.iloc[idx:]
        y_train = y.iloc[:idx] if y is not None else None
        y_test = y.iloc[idx:] if y is not None else None

    steps.append(f"split={1 - test_size:.2f}/{test_size:.2f}")
    _try_broadcast(dataset_id, 85, "Split selesai. Handling imbalance...")

    # 7) Handle imbalance (hanya untuk training data)
    imb_config = config.get("imbalance_handling")
    if imb_config and y_train is not None:
        imb_method = imb_config.get("method", "none")
        imb_strategy = imb_config.get("sampling_strategy", "auto")
        X_train, y_train, imb_info = _handle_imbalance(
            X_train, y_train, imb_method, imb_strategy
        )
        if imb_info.get("error"):
            steps.append(f"imbalance_handling={imb_method} (failed: {imb_info['error']})")
        else:
            steps.append(f"imbalance_handling={imb_method}")
            _try_broadcast(dataset_id, 90, "Imbalance handling selesai. Menyimpan state...")
    else:
        _try_broadcast(dataset_id, 90, "Imbalance handling skipped. Menyimpan state...")

    # 8) Simpan ke state registry
    state_id = uuid.uuid4().hex
    state = get_state(state_id)
    state["data"] = df
    state["target_column"] = target_column
    state["problem_type"] = problem_type
    state["X_train"] = X_train
    state["X_test"] = X_test
    state["y_train"] = y_train
    state["y_test"] = y_test
    state["numerical_columns"] = [c for c in num_cols if c in X.columns]
    state["categorical_columns"] = [c for c in cat_cols if c in X.columns]
    state["feature_names"] = X_train.columns.tolist()
    state["scaler_info"] = scale_info
    state["encoding_info"] = enc_info
    if fs_config:
        state["feature_selection_info"] = fs_info
    if imb_config:
        state["imbalance_handling_info"] = imb_info

    _try_broadcast(dataset_id, 100, "Preprocessing selesai!")
    return {
        "success": True,
        "state_id": state_id,
        "n_samples_train": int(len(X_train)),
        "n_samples_test": int(len(X_test)),
        "n_features": int(X_train.shape[1]),
        "feature_names": X_train.columns.tolist(),
        "target_column": target_column,
        "problem_type": problem_type,
        "preprocessing_steps": steps,
        "feature_selection_info": fs_info if fs_config else None,
        "imbalance_handling_info": imb_info if imb_config else None,
    }

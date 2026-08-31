"""
Timeseries service - forecasting & anomaly detection sederhana.

Menggunakan:
- ``statsmodels`` untuk stationarity test & seasonality decomposition
- ``sklearn`` IsolationForest untuk anomaly detection
- ``utils.prepare_timeseries_data`` & ``utils.advanced_data_scaling`` (refactored)

Catatan: tidak semua algoritma berat (Prophet, DLinear) dipakai sebagai
default; fokus pada yang cepat & robust. Frontend bisa menambahkan
pilihan algoritma tambahan nanti.
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

try:
    from statsmodels.tsa.stattools import adfuller  # type: ignore

    STATSMODELS_AVAILABLE = True
except Exception:
    STATSMODELS_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest  # type: ignore

    ISO_FOREST_AVAILABLE = True
except Exception:
    ISO_FOREST_AVAILABLE = False

# Additional imports for advanced forecasting
try:
    from statsmodels.tsa.arima.model import ARIMA  # type: ignore
    ARIMA_AVAILABLE = True
except Exception:
    ARIMA_AVAILABLE = False

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore
    SARIMA_AVAILABLE = True
except Exception:
    SARIMA_AVAILABLE = False

try:
    from prophet import Prophet  # type: ignore
    PROPHET_AVAILABLE = True
except Exception:
    PROPHET_AVAILABLE = False

try:
    from tensorflow.keras.models import Sequential  # type: ignore
    from tensorflow.keras.layers import LSTM, Dense  # type: ignore
    TENSORFLOW_AVAILABLE = True
except Exception:
    TENSORFLOW_AVAILABLE = False

from backend.services import dataset_service


def _detect_datetime_column(df: pd.DataFrame) -> Optional[str]:
    """Coba deteksi kolom datetime pertama."""
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                pd.to_datetime(df[col].head(20), errors="raise")
                return col
            except Exception:
                continue
    return None


def detect_timeseries(
    dataset_id: str,
    target_column: Optional[str] = None,
    date_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Analisis awal data timeseries: stasioneritas, seasonality, outliers."""
    df = dataset_service.get_dataset(dataset_id)
    if df is None:
        return {"success": False, "error": f"Dataset {dataset_id} tidak ditemukan"}

    if date_column is None:
        date_column = _detect_datetime_column(df)
    if target_column is None:
        # Pilih kolom numerik dengan unique values paling banyak
        num = df.select_dtypes(include=["number"])
        if num.shape[1] == 0:
            return {"success": False, "error": "Tidak ada kolom numerik"}
        target_column = num.var().idxmax()

    if target_column not in df.columns:
        return {"success": False, "error": f"Kolom target {target_column} tidak ada"}
    if date_column and date_column not in df.columns:
        return {"success": False, "error": f"Kolom date {date_column} tidak ada"}

    series = df[target_column].dropna()
    if len(series) < 10:
        return {"success": False, "error": "Data terlalu sedikit (min 10 baris)"}

    result: Dict[str, Any] = {
        "success": True,
        "dataset_id": dataset_id,
        "target_column": target_column,
        "date_column": date_column,
        "n_observations": int(len(series)),
        "mean": float(series.mean()),
        "std": float(series.std()),
        "min": float(series.min()),
        "max": float(series.max()),
        "is_stationary": None,
        "adf_statistic": None,
        "adf_pvalue": None,
        "n_anomalies": 0,
        "anomaly_indices": [],
    }

    # ADF test
    if STATSMODELS_AVAILABLE:
        try:
            adf_result = adfuller(series.values, autolag="AIC")
            result["adf_statistic"] = float(adf_result[0])
            result["adf_pvalue"] = float(adf_result[1])
            result["is_stationary"] = bool(adf_result[1] < 0.05)
        except Exception as exc:
            result["adf_error"] = str(exc)

    # IsolationForest anomaly detection
    if ISO_FOREST_AVAILABLE:
        try:
            iso = IsolationForest(contamination=0.05, random_state=42)
            arr = series.values.reshape(-1, 1)
            preds = iso.fit_predict(arr)
            anomaly_idx = np.where(preds == -1)[0].tolist()
            result["n_anomalies"] = int(len(anomaly_idx))
            result["anomaly_indices"] = [int(i) for i in anomaly_idx[:200]]  # cap
        except Exception as exc:
            result["anomaly_error"] = str(exc)

    return result


def forecast(
    dataset_id: str,
    target_column: str,
    date_column: Optional[str] = None,
    horizon: int = 10,
    method: str = "naive",  # naive | drift | mean | arima | sarima | prophet | lstm
) -> Dict[str, Any]:
    """
    Forecasting dengan berbagai metode (naive / drift / mean / arima / sarima / prophet / lstm).
    """
    df = dataset_service.get_dataset(dataset_id)
    if df is None:
        return {"success": False, "error": f"Dataset {dataset_id} tidak ditemukan"}
    if target_column not in df.columns:
        return {"success": False, "error": f"Kolom target {target_column} tidak ada"}
    series = df[target_column].dropna().reset_index(drop=True)
    if len(series) < horizon + 2:
        return {"success": False, "error": "Data terlalu sedikit untuk forecasting"}

    horizon = int(max(1, min(horizon, len(series))))
    last_idx = len(series) - 1

    # Advanced forecasting methods
    if method == "arima" and ARIMA_AVAILABLE:
        return _arima_forecast(series, horizon)
    elif method == "sarima" and SARIMA_AVAILABLE:
        return _sarima_forecast(series, horizon)
    elif method == "prophet" and PROPHET_AVAILABLE:
        return _prophet_forecast(series, horizon)
    elif method == "lstm" and TENSORFLOW_AVAILABLE:
        return _lstm_forecast(series, horizon)
    
    # Basic forecasting methods
    forecast_values: List[float] = []
    if method == "naive":
        forecast_values = [float(series.iloc[-1])] * horizon
    elif method == "drift":
        # Linear trend using scipy
        x = np.arange(len(series))
        slope, intercept, _, _, _ = stats.linregress(x, series.values)
        forecast_values = [float(intercept + slope * (len(series) + i + 1)) for i in range(horizon)]
    elif method == "mean":
        forecast_values = [float(series.mean())] * horizon
    else:
        return {"success": False, "error": f"Method {method} tidak dikenal atau library tidak tersedia."}

    return {
        "success": True,
        "method": method,
        "target_column": target_column,
        "horizon": horizon,
        "last_observed": float(series.iloc[-1]),
        "forecast": forecast_values,
        "forecast_index": [int(last_idx + i + 1) for i in range(horizon)],
    }


def _arima_forecast(series: pd.Series, horizon: int) -> Dict[str, Any]:
    """ARIMA forecasting."""
    try:
        # Simple ARIMA(1,1,1) model
        model = ARIMA(series, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=horizon)
        
        return {
            "success": True,
            "method": "arima",
            "horizon": horizon,
            "last_observed": float(series.iloc[-1]),
            "forecast": forecast.tolist(),
            "forecast_index": [int(len(series) + i + 1) for i in range(horizon)],
            "aic": float(model_fit.aic),
            "params": {k: float(v) for k, v in model_fit.params.items()}
        }
    except Exception as e:
        return {"success": False, "error": f"ARIMA forecasting failed: {str(e)}", "method": "arima"}


def _sarima_forecast(series: pd.Series, horizon: int) -> Dict[str, Any]:
    """SARIMA forecasting."""
    try:
        # Simple SARIMA(1,1,1)(1,1,1,12) model with seasonal period 12
        model = SARIMAX(series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=horizon)
        
        return {
            "success": True,
            "method": "sarima",
            "horizon": horizon,
            "last_observed": float(series.iloc[-1]),
            "forecast": forecast.tolist(),
            "forecast_index": [int(len(series) + i + 1) for i in range(horizon)],
            "aic": float(model_fit.aic),
            "params": {k: float(v) for k, v in model_fit.params.items()}
        }
    except Exception as e:
        return {"success": False, "error": f"SARIMA forecasting failed: {str(e)}", "method": "sarima"}


def _prophet_forecast(series: pd.Series, horizon: int) -> Dict[str, Any]:
    """Prophet forecasting."""
    try:
        # Prepare data for Prophet
        df = pd.DataFrame({
            'ds': pd.date_range(start='2020-01-01', periods=len(series)),
            'y': series.values
        })
        
        # Fit Prophet model
        model = Prophet()
        model.fit(df)
        
        # Make future dataframe and predict
        future = model.make_future_dataframe(periods=horizon)
        forecast = model.predict(future)
        
        # Extract forecast values
        forecast_values = forecast['yhat'].tail(horizon).tolist()
        
        return {
            "success": True,
            "method": "prophet",
            "horizon": horizon,
            "last_observed": float(series.iloc[-1]),
            "forecast": forecast_values,
            "forecast_index": [int(len(series) + i + 1) for i in range(horizon)],
            "trend_components": {
                'trend': forecast['trend'].tail(horizon).tolist()
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Prophet forecasting failed: {str(e)}", "method": "prophet"}


def _lstm_forecast(series: pd.Series, horizon: int) -> Dict[str, Any]:
    """LSTM forecasting."""
    try:
        from sklearn.preprocessing import MinMaxScaler
        
        # Scale data
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(series.values.reshape(-1, 1))
        
        # Prepare LSTM data
        look_back = min(10, len(series) // 2)
        X, y = [], []
        for i in range(len(scaled_data) - look_back):
            X.append(scaled_data[i:(i + look_back), 0])
            y.append(scaled_data[i + look_back, 0])
        
        X = np.array(X)
        y = np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        # Build LSTM model
        model = Sequential()
        model.add(LSTM(50, activation='relu', input_shape=(look_back, 1)))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mse')
        
        # Train model
        model.fit(X, y, epochs=10, batch_size=1, verbose=0)
        
        # Make predictions
        last_sequence = scaled_data[-look_back:]
        predictions = []
        current_sequence = last_sequence.copy()
        
        for _ in range(horizon):
            current_sequence_reshaped = current_sequence.reshape(1, look_back, 1)
            next_pred = model.predict(current_sequence_reshaped, verbose=0)
            predictions.append(next_pred[0, 0])
            current_sequence = np.append(current_sequence[1:], next_pred[0, 0])
        
        # Inverse transform predictions
        forecast_values = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten().tolist()
        
        return {
            "success": True,
            "method": "lstm",
            "horizon": horizon,
            "last_observed": float(series.iloc[-1]),
            "forecast": forecast_values,
            "forecast_index": [int(len(series) + i + 1) for i in range(horizon)],
            "look_back": look_back
        }
    except Exception as e:
        return {"success": False, "error": f"LSTM forecasting failed: {str(e)}", "method": "lstm"}


def anomaly_detection(
    dataset_id: str,
    target_column: str,
    contamination: float = 0.05,
) -> Dict[str, Any]:
    """Deteksi anomali pada satu kolom numerik."""
    if not ISO_FOREST_AVAILABLE:
        return {"success": False, "error": "IsolationForest tidak tersedia"}
    df = dataset_service.get_dataset(dataset_id)
    if df is None:
        return {"success": False, "error": f"Dataset {dataset_id} tidak ditemukan"}
    if target_column not in df.columns:
        return {"success": False, "error": f"Kolom target {target_column} tidak ada"}
    series = df[target_column].dropna().reset_index(drop=True)
    if len(series) < 10:
        return {"success": False, "error": "Data terlalu sedikit"}

    arr = series.values.reshape(-1, 1)
    iso = IsolationForest(contamination=float(contamination), random_state=42)
    preds = iso.fit_predict(arr)
    scores = iso.decision_function(arr)
    anomaly_idx = np.where(preds == -1)[0]
    anomaly_records = [
        {
            "index": int(i),
            "value": float(series.iloc[i]),
            "score": float(scores[i]),
        }
        for i in anomaly_idx
    ]
    return {
        "success": True,
        "target_column": target_column,
        "n_observations": int(len(series)),
        "n_anomalies": int(len(anomaly_idx)),
        "contamination": float(contamination),
        "anomalies": anomaly_records,
    }

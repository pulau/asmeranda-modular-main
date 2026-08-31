"""
Interpretation service - SHAP & LIME untuk model yang sudah dilatih.

Service ini:
- Load model dari disk via ``training_service.load_model``
- Jalankan SHAP / LIME pada sample data
- Kembalikan summary numeric (feature importance) dan base64-encoded plot
"""
from __future__ import annotations

import base64
import io
import pickle
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import shap  # type: ignore

    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False

try:
    from lime import lime_tabular  # type: ignore

    LIME_AVAILABLE = True
except Exception:
    LIME_AVAILABLE = False

from core.state import get_state
from backend.services import training_service


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure ke base64 PNG string."""
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")
    except Exception:
        return ""


def _feature_importance_from_model(model, feature_names: List[str]) -> List[Dict[str, Any]]:
    """Ambil feature importance dari model (kalau ada)."""
    importances = None
    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        importances = np.mean(np.abs(coef), axis=0) if coef.ndim > 1 else np.abs(coef)
    if importances is None or len(importances) != len(feature_names):
        return []
    pairs = sorted(
        zip(feature_names, importances.tolist()),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    return [{"feature": f, "importance": float(v)} for f, v in pairs]


def run_shap(
    model_id: str,
    state_id: Optional[str] = None,
    max_samples: int = 200,
) -> Dict[str, Any]:
    """
    Hitung SHAP values (atau fallback ke feature importance).

    Parameters
    ----------
    model_id : str
        ID model hasil training.
    state_id : str | None
        State ID hasil preprocessing (untuk ambil X_test).
    max_samples : int
        Maksimum jumlah sample untuk komputasi (biar tidak OOM).
    """
    meta = training_service.get_metadata(model_id)
    if meta is None:
        return {"success": False, "error": f"Model {model_id} tidak ditemukan"}
    loaded = training_service.load_model(model_id)
    if loaded is None:
        return {"success": False, "error": "Model file tidak bisa dibaca"}
    model = loaded["model"]
    feature_names = loaded.get("feature_names") or meta.get("feature_names") or []

    # Ambil data sample
    X_sample = None
    if state_id:
        state = get_state(state_id)
        X_sample = state.get("X_test")
    if X_sample is None:
        return {
            "success": False,
            "error": "state_id dengan X_test tidak ditemukan. Jalankan preprocessing dulu.",
        }
    # numeric coercion
    X_sample = X_sample.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if max_samples and len(X_sample) > max_samples:
        X_sample = X_sample.sample(n=max_samples, random_state=42)

    feature_importance = _feature_importance_from_model(model, list(X_sample.columns))

    result: Dict[str, Any] = {
        "success": True,
        "model_id": model_id,
        "method": "shap",
        "shap_available": SHAP_AVAILABLE,
        "n_samples": int(len(X_sample)),
        "feature_importance": feature_importance,
        "plot_base64": "",
        "shap_values_summary": None,
        "error": None,
    }

    if not SHAP_AVAILABLE:
        result["error"] = "Library SHAP tidak terpasang; hanya feature importance."
        # Generate fallback plot
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            if feature_importance:
                top = feature_importance[: min(20, len(feature_importance))]
                fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(top))))
                ax.barh(
                    [t["feature"] for t in top][::-1],
                    [t["importance"] for t in top][::-1],
                )
                ax.set_xlabel("Importance")
                ax.set_title("Feature Importance (fallback - SHAP not available)")
                result["plot_base64"] = _fig_to_base64(fig)
                plt.close(fig)
        except Exception as exc:
            result["error"] = f"Gagal render fallback plot: {exc}"
        return result

    # Pakai SHAP
    try:
        import shap
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Pilih explainer sesuai model
        try:
            explainer = shap.Explainer(model, X_sample)
            shap_values = explainer(X_sample)
            # Ringkas jadi numeric array untuk dikirim ke frontend
            values = np.asarray(shap_values.values)
            if values.ndim == 3:
                # Multiclass: ambil rata-rata absolut per fitur
                mean_abs = np.mean(np.abs(values), axis=(0, 2))
            else:
                mean_abs = np.mean(np.abs(values), axis=0)
            shap_summary = [
                {"feature": X_sample.columns[i], "mean_abs_shap": float(v)}
                for i, v in enumerate(mean_abs)
            ]
            shap_summary.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
            result["shap_values_summary"] = shap_summary

            # Bar plot
            top = shap_summary[: min(20, len(shap_summary))]
            fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(top))))
            ax.barh([t["feature"] for t in top][::-1], [t["mean_abs_shap"] for t in top][::-1])
            ax.set_xlabel("mean |SHAP value|")
            ax.set_title(f"SHAP Feature Importance (n={len(X_sample)})")
            result["plot_base64"] = _fig_to_base64(fig)
            plt.close(fig)
        except Exception as exc:
            # Fallback ke Tree/Kernel explainer
            try:
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_sample)
                if isinstance(shap_values, list):
                    shap_arr = np.asarray(shap_values[0])
                else:
                    shap_arr = np.asarray(shap_values)
                mean_abs = np.mean(np.abs(shap_arr), axis=0)
                shap_summary = [
                    {"feature": X_sample.columns[i], "mean_abs_shap": float(v)}
                    for i, v in enumerate(mean_abs)
                ]
                shap_summary.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
                result["shap_values_summary"] = shap_summary

                top = shap_summary[: min(20, len(shap_summary))]
                fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(top))))
                ax.barh([t["feature"] for t in top][::-1], [t["mean_abs_shap"] for t in top][::-1])
                ax.set_xlabel("mean |SHAP value|")
                ax.set_title(f"SHAP Feature Importance (TreeExplainer, n={len(X_sample)})")
                result["plot_base64"] = _fig_to_base64(fig)
                plt.close(fig)
            except Exception as exc2:
                result["error"] = f"SHAP gagal: {exc}; fallback: {exc2}"
                if feature_importance:
                    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(feature_importance[:20]))))
                    top = feature_importance[:20]
                    ax.barh([t["feature"] for t in top][::-1], [t["importance"] for t in top][::-1])
                    ax.set_xlabel("Importance")
                    ax.set_title("Feature Importance (final fallback)")
                    result["plot_base64"] = _fig_to_base64(fig)
                    plt.close(fig)
    except Exception as exc:
        result["success"] = False
        result["error"] = f"Gagal komputasi SHAP: {exc}"

    return result


def run_lime(
    model_id: str,
    state_id: Optional[str] = None,
    sample_index: int = 0,
    num_features: int = 10,
) -> Dict[str, Any]:
    """
    Jalankan LIME untuk satu instance.

    Parameters
    ----------
    model_id : str
    state_id : str | None
    sample_index : int
        Index baris di X_test yang akan dijelaskan.
    num_features : int
        Jumlah fitur yang ditampilkan.
    """
    meta = training_service.get_metadata(model_id)
    if meta is None:
        return {"success": False, "error": f"Model {model_id} tidak ditemukan"}
    loaded = training_service.load_model(model_id)
    if loaded is None:
        return {"success": False, "error": "Model file tidak bisa dibaca"}
    model = loaded["model"]
    problem_type = loaded.get("problem_type", "Classification")

    X_sample = None
    if state_id:
        state = get_state(state_id)
        X_sample = state.get("X_test")
    if X_sample is None:
        return {
            "success": False,
            "error": "state_id dengan X_test tidak ditemukan.",
        }
    X_sample = X_sample.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if sample_index >= len(X_sample):
        sample_index = 0
    if sample_index < 0:
        sample_index = len(X_sample) + sample_index

    result: Dict[str, Any] = {
        "success": True,
        "model_id": model_id,
        "method": "lime",
        "lime_available": LIME_AVAILABLE,
        "sample_index": int(sample_index),
        "explanation": [],
        "plot_base64": "",
        "error": None,
    }

    if not LIME_AVAILABLE:
        result["error"] = "Library LIME tidak terpasang."
        return result

    try:
        from lime import lime_tabular
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Determine class names for classification
        class_names = None
        if problem_type == "Classification" and hasattr(model, "classes_"):
            class_names = [str(c) for c in model.classes_]

        explainer = lime_tabular.LimeTabularExplainer(
            training_data=np.asarray(X_sample),
            feature_names=list(X_sample.columns),
            class_names=class_names,
            mode=problem_type.lower() if problem_type in ("Classification", "Regression") else "regression",
            random_state=42,
        )
        row_df = X_sample.iloc[[sample_index]]
        row = np.asarray(row_df)
        predict_fn = model.predict_proba if problem_type == "Classification" else model.predict
        exp = explainer.explain_instance(
            data_row=row[0],
            predict_fn=predict_fn,
            num_features=min(num_features, X_sample.shape[1]),
        )

        # Explanation list
        explanation = []
        try:
            if problem_type == "Classification":
                label = int(np.argmax(model.predict_proba(row_df)[0]))
            else:
                label = 0
            for feat, weight in exp.as_list(label=label):
                explanation.append({"feature": feat, "weight": float(weight)})
        except Exception:
            for feat, weight in exp.as_list():
                explanation.append({"feature": feat, "weight": float(weight)})
        result["explanation"] = explanation

        # Plot to base64
        try:
            fig = exp.as_pyplot_figure()
            result["plot_base64"] = _fig_to_base64(fig)
            plt.close(fig)
        except Exception:
            # fallback: bar plot
            fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(explanation))))
            ax.barh(
                [e["feature"] for e in explanation[::-1]],
                [e["weight"] for e in explanation[::-1]],
            )
            ax.set_xlabel("LIME weight")
            ax.set_title(f"LIME explanation for sample #{sample_index}")
            result["plot_base64"] = _fig_to_base64(fig)
            plt.close(fig)

    except Exception as exc:
        result["success"] = False
        result["error"] = f"Gagal komputasi LIME: {exc}"

    return result

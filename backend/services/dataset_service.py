"""
Dataset service - mengelola upload, list, dan load dataset tabular.

Dataset disimpan sebagai Parquet di ``settings.data_dir`` (per-dataset,
nama file = ``{dataset_id}.parquet``). Metadata disimpan sebagai
``{dataset_id}.meta.json`` agar tetap tersedia setelah restart backend.
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

import pandas as pd
import polars as pl

from backend.core.config import settings
from backend.core.security_utils import sql_validator


# In-memory metadata registry (dataset_id -> metadata).
_METADATA: Dict[str, Dict[str, Any]] = {}


def _metadata_path(dataset_id: str) -> Path:
    return Path(settings.data_dir) / f"{dataset_id}.parquet"


def _meta_json_path(dataset_id: str) -> Path:
    return Path(settings.data_dir) / f"{dataset_id}.meta.json"


def _save_metadata(metadata: Dict[str, Any]) -> None:
    """Persist metadata ke disk sebagai JSON sidecar."""
    dataset_id = metadata["dataset_id"]
    path = _meta_json_path(dataset_id)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, ensure_ascii=False, indent=2)


def _load_metadata_from_disk(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Baca metadata dari file JSON sidecar."""
    path = _meta_json_path(dataset_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _rebuild_metadata_from_parquet(path: Path) -> Optional[Dict[str, Any]]:
    """Regenerasi metadata dari file parquet bila sidecar JSON hilang."""
    dataset_id = path.stem
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
    return {
        "dataset_id": dataset_id,
        "filename": f"{dataset_id}.parquet",
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "numerical_columns": numerical_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "size_bytes": int(path.stat().st_size),
        "uploaded_at": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat() + "Z",
    }


def _load_registry_from_disk() -> None:
    """Muat ulang registry metadata dari disk saat startup."""
    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        return
    for parquet_path in sorted(data_dir.glob("*.parquet")):
        dataset_id = parquet_path.stem
        if dataset_id in _METADATA:
            continue
        meta = _load_metadata_from_disk(dataset_id) or _rebuild_metadata_from_parquet(parquet_path)
        if meta:
            _METADATA[dataset_id] = meta
            if not _meta_json_path(dataset_id).exists():
                _save_metadata(meta)


_load_registry_from_disk()


def list_datasets() -> List[Dict[str, Any]]:
    """Kembalikan metadata semua dataset yang tersimpan."""
    return list(_METADATA.values())


def get_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    """Load dataset dari disk sebagai pandas DataFrame (untuk kompatibilitas ML lama)."""
    path = _metadata_path(dataset_id)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def get_dataset_pl(dataset_id: str) -> Optional[pl.DataFrame]:
    """Load dataset dari disk menggunakan Polars untuk pemrosesan cepat (Big Data)."""
    path = _metadata_path(dataset_id)
    if not path.exists():
        return None
    return pl.read_parquet(path)


def get_paginated_data(dataset_id: str, page: int = 1, size: int = 50) -> Optional[Dict[str, Any]]:
    """Ambil sebagian data (server-side pagination) menggunakan Polars."""
    path = _metadata_path(dataset_id)
    if not path.exists():
        return None
    try:
        # Polars lazy frame untuk optimasi jika file sangat besar (scan_parquet)
        df = pl.scan_parquet(path)
        total_rows = df.select(pl.len()).collect().item()
        
        offset = (page - 1) * size
        # Ambil subset
        subset = df.slice(offset, size).collect()
        
        # Konversi ke dict (records) yang siap diubah jadi JSON
        # Harus ganti NaN/Null agar aman di JSON
        records = subset.fill_null(None).fill_nan(None).to_dicts()
        
        return {
            "data": records,
            "total_rows": total_rows,
            "page": page,
            "size": size,
            "total_pages": (total_rows + size - 1) // size
        }
    except Exception as exc:
        import logging
        logging.getLogger("asmeranda.services.dataset").error(f"Pagination error: {exc}")
        return None


def get_metadata(dataset_id: str) -> Optional[Dict[str, Any]]:
    return _METADATA.get(dataset_id)


def ingest(
    content: bytes,
    filename: str,
    original_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse file upload, simpan ke disk, kembalikan metadata.

    Supported formats: CSV, XLSX, XLS, Parquet.
    """
    name = original_name or filename
    suffix = (filename or "").lower().split(".")[-1]

    df: Optional[pl.DataFrame] = None
    parse_error: Optional[str] = None

    bio = io.BytesIO(content)
    try:
        if suffix == "csv":
            df = pl.read_csv(bio, ignore_errors=True)
        elif suffix in ("xlsx", "xls"):
            df = pl.read_excel(bio)
        elif suffix == "parquet":
            df = pl.read_parquet(bio)
        elif suffix == "json":
            df = pl.read_json(bio)
        elif suffix == "tsv":
            df = pl.read_csv(bio, separator="\t", ignore_errors=True)
        else:
            # Coba CSV sebagai fallback
            try:
                bio.seek(0)
                df = pl.read_csv(bio, ignore_errors=True)
                suffix = "csv"
            except Exception as exc:
                parse_error = (
                    f"Format file .{suffix} belum didukung. "
                    "Gunakan CSV/XLSX/Parquet. Detail: " + str(exc)
                )
    except Exception as exc:
        parse_error = f"Gagal mem-parse file: {exc}"

    if df is None:
        raise ValueError(parse_error or "Gagal membaca file dataset.")

    # Generate ID & persist
    dataset_id = uuid.uuid4().hex
    path = _metadata_path(dataset_id)
    df.write_parquet(path)

    # Detect column types using Polars datatypes
    numerical_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in pl.NUMERIC_DTYPES]
    categorical_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in (pl.String, pl.Categorical, pl.Boolean)]
    datetime_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in pl.TEMPORAL_DTYPES]

    metadata = {
        "dataset_id": dataset_id,
        "filename": name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "numerical_columns": numerical_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "size_bytes": int(path.stat().st_size),
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }
    _METADATA[dataset_id] = metadata
    _save_metadata(metadata)
    return metadata


def delete_dataset(dataset_id: str) -> bool:
    """Hapus dataset dari disk & registry. Return True jika ada."""
    path = _metadata_path(dataset_id)
    meta_path = _meta_json_path(dataset_id)
    existed = path.exists() or meta_path.exists() or dataset_id in _METADATA
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass
    if meta_path.exists():
        try:
            meta_path.unlink()
        except Exception:
            pass
    _METADATA.pop(dataset_id, None)
    return existed


def summary(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Kembalikan ringkasan dataset untuk EDA menggunakan Polars."""
    df = get_dataset_pl(dataset_id)
    if df is None:
        return None
    meta = _METADATA.get(dataset_id, {})

    numerical_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in pl.NUMERIC_DTYPES]
    categorical_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype in (pl.String, pl.Categorical)]

    describe_num = {}
    if numerical_cols:
        # Polars describe mengembalikan stat di kolom 'statistic'
        desc_df = df.select(numerical_cols).describe()
        stats = desc_df["statistic"].to_list()
        for col in numerical_cols:
            describe_num[col] = dict(zip(stats, desc_df[col].to_list()))

    describe_cat: Dict[str, Dict[str, Any]] = {}
    for col in categorical_cols:
        # Hitung unique, top, freq
        vc = df[col].value_counts(sort=True).head(1)
        if len(vc) > 0:
            describe_cat[col] = {
                "unique": df[col].n_unique(),
                "top": str(vc[col][0]),
                "freq": int(vc["count"][0] if "count" in vc.columns else vc[vc.columns[1]][0]),
            }

    # Hitung missing values
    missing = df.null_count().to_dicts()[0]
    total_rows = max(df.height, 1)
    missing_pct = {col: round((count / total_rows) * 100, 2) for col, count in missing.items()}

    return {
        "metadata": meta,
        "shape": {"rows": df.height, "columns": df.width},
        "dtypes": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
        "describe_numeric": describe_num,
        "describe_categorical": describe_cat,
        "missing": {
            "counts": missing,
            "percentages": missing_pct,
        },
    }

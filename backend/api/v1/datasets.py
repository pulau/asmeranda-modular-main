"""
Endpoint /datasets - upload, list, get, delete dataset tabular.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.schemas.models import (
    DatasetListResponse,
    DatasetMetadata,
    DatasetUploadResponse,
)
from backend.services import dataset_service
from backend.core.config import settings
from backend.core.security_audit import audit_logger
from backend.core.security_utils import input_sanitizer

logger = logging.getLogger("asmeranda.api.datasets")
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Security: Allowed file types and MIME types
ALLOWED_MIME_TYPES = [
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/parquet",
    "application/json",
    "text/tab-separated-values",
    "application/octet-stream"  # Fallback for some file types
]

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.parquet', '.json', '.tsv', '.txt'}


@router.get("", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    """List semua dataset yang sudah di-upload."""
    items = dataset_service.list_datasets()
    return DatasetListResponse(datasets=items, total=len(items))


@router.post("", response_model=DatasetUploadResponse)
@limiter.limit("10/minute")  # Limit to 10 uploads per minute per IP
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> DatasetUploadResponse:
    """
    Upload file dataset (CSV/XLSX/Parquet/JSON/TSV).
    File disimpan ke ``settings.data_dir/{dataset_id}.parquet``.
    """
    # Get client IP for audit logging
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Security: Validate file type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                "File type not allowed",
                extra={
                    "dataset_filename": file.filename,
                    "content_type": file.content_type,
                    "allowed_types": ALLOWED_MIME_TYPES
                }
            )
            audit_logger.log_file_upload_rejected(
                filename=file.filename or "unknown",
                reason=f"Invalid MIME type: {file.content_type}",
                ip_address=client_ip
            )
            return DatasetUploadResponse(
                success=False, 
                error=f"File type {file.content_type} not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )
        
        # Security: Validate file extension
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            logger.warning(
                "File extension not allowed",
                extra={
                    "dataset_filename": file.filename,
                    "file_extension": file_ext,
                    "allowed_extensions": ALLOWED_EXTENSIONS
                }
            )
            audit_logger.log_file_upload_rejected(
                filename=file.filename or "unknown",
                reason=f"Invalid file extension: {file_ext}",
                ip_address=client_ip
            )
            return DatasetUploadResponse(
                success=False,
                error=f"File extension {file_ext} not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Security: Validate filename
        if file.filename and not input_sanitizer.validate_filename(file.filename):
            logger.warning(
                "Invalid filename detected",
                extra={
                    "dataset_filename": file.filename
                }
            )
            audit_logger.log_file_upload_rejected(
                filename=file.filename or "unknown",
                reason="Invalid filename (potential path traversal)",
                ip_address=client_ip
            )
            return DatasetUploadResponse(
                success=False,
                error="Invalid filename. Please use a valid filename without special characters."
            )
        
        content = await file.read()
        if not content:
            audit_logger.log_file_upload_rejected(
                filename=file.filename or "unknown",
                reason="Empty file",
                ip_address=client_ip
            )
            raise HTTPException(status_code=400, detail="File kosong")
        
        # Validate file size before processing
        file_size_mb = len(content) / (1024 * 1024)
        max_size_mb = settings.max_upload_size_mb
        if file_size_mb > max_size_mb:
            logger.warning(
                "File size exceeds limit",
                extra={
                    "dataset_filename": file.filename,
                    "file_size_mb": file_size_mb,
                    "max_size_mb": max_size_mb
                }
            )
            audit_logger.log_file_upload_rejected(
                filename=file.filename or "unknown",
                reason=f"File size exceeds limit: {file_size_mb:.2f}MB",
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=413, 
                detail=f"File terlalu besar ({file_size_mb:.2f}MB). Maksimum {max_size_mb}MB"
            )
        
        # Security: Validate file content (basic check for executable content)
        if file_size_mb > 0:
            # Check for potential executable signatures
            if content[:2] == b'MZ':  # Windows executable
                audit_logger.log_file_upload_rejected(
                    filename=file.filename or "unknown",
                    reason="Executable file detected (MZ header)",
                    ip_address=client_ip
                )
                raise HTTPException(status_code=415, detail="Executable files not allowed")
            if content[:4] == b'\x7fELF':  # Linux executable
                audit_logger.log_file_upload_rejected(
                    filename=file.filename or "unknown",
                    reason="Executable file detected (ELF header)",
                    ip_address=client_ip
                )
                raise HTTPException(status_code=415, detail="Executable files not allowed")
        
        meta = dataset_service.ingest(
            content=content,
            filename=file.filename or "dataset",
            original_name=file.filename,
        )
        
        logger.info(
            "Dataset uploaded successfully",
            extra={
                "dataset_id": meta.get("dataset_id"),
                "dataset_filename": file.filename,
                "file_size_mb": file_size_mb,
                "rows": meta.get("rows"),
                "columns": meta.get("columns")
            }
        )
        
        # Log successful upload
        audit_logger.log_file_upload(
            filename=file.filename or "unknown",
            file_size_mb=file_size_mb,
            file_type=file.content_type or "unknown",
            ip_address=client_ip,
            success=True
        )
        
        return DatasetUploadResponse(success=True, metadata=meta)
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Upload validation failed: %s",
            str(exc),
            extra={"dataset_filename": file.filename},
        )
        audit_logger.log_file_upload_rejected(
            filename=file.filename or "unknown",
            reason=f"Validation failed: {str(exc)}",
            ip_address=client_ip
        )
        return DatasetUploadResponse(success=False, error=str(exc))
    except Exception as exc:
        logger.error(
            "Upload dataset failed unexpectedly",
            exc_info=True,
            extra={
                "dataset_filename": file.filename,
                "file_size_mb": len(content) / (1024 * 1024) if content else 0,
                "error_type": type(exc).__name__,
            },
        )
        audit_logger.log_file_upload_rejected(
            filename=file.filename or "unknown",
            reason=f"Internal error: {str(exc)}",
            ip_address=client_ip
        )
        return DatasetUploadResponse(success=False, error=f"Internal error: {exc}")


@router.get("/{dataset_id}", response_model=DatasetMetadata)
def get_dataset(dataset_id: str) -> DatasetMetadata:
    """Ambil metadata dataset (tidak termasuk isi)."""
    meta = dataset_service.get_metadata(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} tidak ditemukan")
    return DatasetMetadata(**meta)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    """Hapus dataset."""
    ok = dataset_service.delete_dataset(dataset_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} tidak ditemukan")
    return {"success": True, "dataset_id": dataset_id, "deleted": True}

"""
Error Handler module for Asmeranda AI.

Provides centralized error handling, classification, user-friendly messages,
suggestions, and multi-language support (ID & EN).
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("asmeranda.error_handler")


def format_error_info(
    exc: Optional[Exception],
    context: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Format exception into structured information dictionary.
    
    Parameters
    ----------
    exc : Exception or None
        The exception to format
    context : str, optional
        Context where the error occurred
        
    Returns
    -------
    dict or None
        Structured error information
    """
    if exc is None:
        return None

    exc_type = type(exc).__name__
    exc_message = str(exc) or exc_type
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc.__traceback__ else ""

    return {
        "message": exc_message,
        "context": context or "general",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technical_details": {
            "exc_type": exc_type,
            "details": exc_message,
            "traceback": tb_str,
        },
        "exc_type": exc_type,
    }


class ErrorHandler:
    """Centralized Error Handler with classification and suggestions."""

    SUGGESTIONS_MAP = {
        "FileNotFoundError": [
            "Pastikan file dataset berada di path yang benar.",
            "Periksa kembali nama file yang diunggah.",
        ],
        "ValueError": [
            "Periksa kembali parameter input yang dimasukkan.",
            "Pastikan tipe data kolom sesuai dengan yang diharapkan model.",
        ],
        "KeyError": [
            "Periksa apakah nama kolom target ada dalam dataset.",
            "Pastikan kolom yang dipilih tidak terhapus selama preprocessing.",
        ],
        "ZeroDivisionError": [
            "Terdapat pembagian dengan nol pada kalkulasi numerik.",
            "Periksa apakah ada data bernilai 0 atau kosong.",
        ],
        "PermissionError": [
            "Aplikasi tidak memiliki izin untuk mengakses file tersebut.",
            "Periksa izin read/write pada direktori penyimpanan.",
        ],
    }

    SUGGESTIONS_MAP_EN = {
        "FileNotFoundError": [
            "Ensure dataset file exists in the specified path.",
            "Check the uploaded file name.",
        ],
        "ValueError": [
            "Review the provided input parameters.",
            "Ensure column data types match model expectations.",
        ],
        "KeyError": [
            "Verify target column exists in the dataset.",
            "Ensure selected column was not dropped during preprocessing.",
        ],
        "ZeroDivisionError": [
            "Encountered division by zero in numerical calculations.",
            "Check for zero or empty values in input columns.",
        ],
        "PermissionError": [
            "Application does not have permission to access the file.",
            "Check read/write permissions on the storage directory.",
        ],
    }

    def __init__(self):
        pass

    def handle_error(
        self,
        exc: Exception,
        context: Optional[str] = None,
        user_message: Optional[str] = None,
        language: str = "id"
    ) -> Optional[Dict[str, Any]]:
        """
        Handle and classify an exception safely without raising.
        
        Parameters
        ----------
        exc : Exception
            Exception to handle
        context : str, optional
            Context of error
        user_message : str, optional
            Custom user-facing message
        language : str
            Language code ('id' or 'en')
            
        Returns
        -------
        dict
            Formatted error response
        """
        try:
            if exc is None:
                return None

            exc_type = type(exc).__name__
            info = format_error_info(exc, context=context) or {}
            
            # Suggestions based on language
            if language == "en":
                suggestions = self.SUGGESTIONS_MAP_EN.get(
                    exc_type,
                    ["An unexpected error occurred. Please check application logs."]
                )
            else:
                suggestions = self.SUGGESTIONS_MAP.get(
                    exc_type,
                    ["Terjadi kesalahan tidak terduga. Silakan periksa log aplikasi."]
                )

            message = user_message or info.get("message", "Terjadi kesalahan")

            logger.error(
                "Error handled in context '%s': %s (%s)",
                context,
                message,
                exc_type,
            )

            return {
                "success": False,
                "error": True,
                "message": message,
                "context": context or "general",
                "exc_type": exc_type,
                "suggestions": suggestions,
                "technical_details": info.get("technical_details", {}),
                "timestamp": info.get("timestamp", datetime.now(timezone.utc).isoformat()),
            }
        except Exception as handler_exc:
            logger.critical("Error inside ErrorHandler itself: %s", handler_exc)
            return {
                "success": False,
                "error": True,
                "message": str(exc) if exc else "Unknown error",
                "context": context or "general",
                "suggestions": ["Check server logs"],
                "technical_details": str(exc),
            }

"""
Data Encryption & Masking Module for Asmeranda AI Backend.

Provides:
- Symmetric data encryption at rest using Fernet
- Dynamic encryption key management
- Data masking utility based on classification sensitivity
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet

try:
    from backend.core.config import settings
except ImportError:
    from core.config import settings

logger = logging.getLogger("asmeranda.security.encryption")


class DataSensitivity(str, Enum):
    """Sensitivity classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataEncryption:
    """Encryption manager using Fernet."""

    def __init__(self, secret_key: Optional[str] = None):
        raw_secret = secret_key or getattr(settings, "jwt_secret", "asmeranda-secret-key-salt-2026")
        # Derive 32-byte urlsafe base64 key
        digest = hashlib.sha256(raw_secret.encode()).digest()
        self._fernet_key = base64.urlsafe_b64encode(digest)
        self._cipher = Fernet(self._fernet_key)

    def encrypt(self, plain_text: str) -> str:
        """Encrypt string to ciphertext."""
        if not plain_text:
            return ""
        return self._cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        """Decrypt ciphertext to string."""
        if not cipher_text:
            return ""
        try:
            return self._cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError("Gagal mendekripsi data: ciphertext tidak valid")

    def encrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
        """Encrypt specific keys in dictionary."""
        result = data.copy()
        for k in sensitive_keys:
            if k in result and isinstance(result[k], str):
                result[k] = self.encrypt(result[k])
        return result

    def decrypt_dict(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict[str, Any]:
        """Decrypt specific keys in dictionary."""
        result = data.copy()
        for k in sensitive_keys:
            if k in result and isinstance(result[k], str):
                result[k] = self.decrypt(result[k])
        return result


def mask_sensitive_data(data: Any, sensitivity: Union[DataSensitivity, str]) -> Any:
    """
    Mask sensitive values based on sensitivity level.
    
    Parameters
    ----------
    data : Any
        String or collection to mask
    sensitivity : DataSensitivity or str
        Sensitivity level ('restricted', 'confidential', etc.)
    """
    if isinstance(sensitivity, str):
        try:
            sensitivity = DataSensitivity(sensitivity.lower())
        except ValueError:
            sensitivity = DataSensitivity.INTERNAL

    if not isinstance(data, str):
        if isinstance(data, dict):
            return {k: mask_sensitive_data(v, sensitivity) for k, v in data.items()}
        elif isinstance(data, list):
            return [mask_sensitive_data(item, sensitivity) for item in data]
        return data

    if sensitivity == DataSensitivity.RESTRICTED:
        return "******"
    elif sensitivity == DataSensitivity.CONFIDENTIAL:
        if len(data) <= 4:
            return "****"
        return data[:2] + "****" + data[-2:]
    return data


# Global instance
data_encryption = DataEncryption()

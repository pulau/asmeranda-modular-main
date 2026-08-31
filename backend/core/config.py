"""
Konfigurasi terpusat untuk Asmeranda Backend.

Semua nilai konfigurasi dibaca dari environment variables (dengan
prefix ``ASMERANDA_``). Tipe-typed via pydantic-settings (atau
pydantic v2 BaseSettings fallback) agar IDE bisa autocomplete.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import List, Optional

# Pakai pydantic-settings bila tersedia, kalau tidak fallback ke dataclass
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
    from pydantic import Field

    _HAVE_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover
    _HAVE_PYDANTIC_SETTINGS = False
    Field = None  # type: ignore


# ---------------------------------------------------------------------------
# Path absolut root project (folder berisi ``core/``, ``ml_engine/``, dll)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def _build_settings():
    default_secret = secrets.token_urlsafe(32)

    if _HAVE_PYDANTIC_SETTINGS:

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(
                env_prefix="ASMERANDA_",
                env_file=str(PROJECT_ROOT / ".env"),
                env_file_encoding="utf-8",
                extra="ignore",
            )

            app_name: str = "Asmeranda AI Backend"
            app_version: str = "0.1.0"
            debug: bool = False

            # Server & Hosts
            host: str = "0.0.0.0"
            port: int = 8000
            allowed_hosts: List[str] = [
                "*",
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "backend",
                "asmeranda-backend",
                "frontend",
                "asmeranda-frontend",
                "nginx",
                "asmeranda-nginx",
                "asmeranda.ai",
                "*.asmeranda.ai",
                "testserver"
            ]

            # SSL/TLS Configuration
            ssl_enabled: bool = False
            ssl_keyfile: Optional[Path] = None
            ssl_certfile: Optional[Path] = None

            # CORS - safe origins for dev, docker, and prod
            cors_origins: List[str] = [
                "http://localhost",
                "http://127.0.0.1",
                "http://localhost:80",
                "http://127.0.0.1:80",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://backend:8000",
                "http://frontend:3000",
                "https://asmeranda.ai"
            ]

            # Storage dataset & max request payload
            data_dir: Path = PROJECT_ROOT / "data"
            max_upload_size_mb: int = 200
            max_request_size_bytes: int = 10 * 1024 * 1024  # 10MB default for non-upload requests

            # Security (JWT & API Keys)
            jwt_secret: str = default_secret
            jwt_algorithm: str = "HS256"
            jwt_expire_minutes: int = 60 * 24
            api_keys: List[str] = ["asmeranda-dev-api-key"]

            # Production safety checks
            production_mode: bool = False

            # Logging
            log_level: str = "INFO"

        return Settings()

    # Fallback: dataclass sederhana
    from dataclasses import dataclass, field

    @dataclass
    class Settings:  # type: ignore[no-redef]
        app_name: str = "Asmeranda AI Backend"
        app_version: str = "0.1.0"
        debug: bool = False
        host: str = "0.0.0.0"
        port: int = 8000
        allowed_hosts: List[str] = field(default_factory=lambda: ["*", "localhost", "127.0.0.1", "0.0.0.0", "backend", "asmeranda-backend", "frontend", "asmeranda-frontend", "nginx", "asmeranda-nginx", "asmeranda.ai", "*.asmeranda.ai", "testserver"])
        ssl_enabled: bool = False
        ssl_keyfile: Optional[Path] = None
        ssl_certfile: Optional[Path] = None
        cors_origins: List[str] = field(default_factory=lambda: ["http://localhost", "http://127.0.0.1", "http://localhost:80", "http://127.0.0.1:80", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://localhost:8000", "http://127.0.0.1:8000", "http://backend:8000", "http://frontend:3000", "https://asmeranda.ai"])
        data_dir: Path = PROJECT_ROOT / "data"
        max_upload_size_mb: int = 200
        max_request_size_bytes: int = 10 * 1024 * 1024
        jwt_secret: str = default_secret
        jwt_algorithm: str = "HS256"
        jwt_expire_minutes: int = 1440
        api_keys: List[str] = field(default_factory=lambda: ["asmeranda-dev-api-key"])
        production_mode: bool = False
        log_level: str = "INFO"

    return Settings()


settings = _build_settings()


# Production safety validation
def _validate_production_safety():
    """Validate critical security settings in production mode."""
    if settings.production_mode:
        warnings = []
        
        if settings.jwt_secret == "change-me-in-production":
            warnings.append("JWT_SECRET is using default value - set a strong secret in production")
        
        if settings.cors_origins == ["*"]:
            warnings.append("CORS_ORIGINS is set to wildcard - restrict to specific origins in production")
        
        if settings.debug:
            warnings.append("DEBUG mode is enabled in production - disable for security")
        
        if warnings:
            logger = logging.getLogger("asmeranda.backend")
            logger.warning("Production safety warnings: %s", "; ".join(warnings))


_validate_production_safety()

# Auto-create data dir
os.makedirs(settings.data_dir, exist_ok=True)

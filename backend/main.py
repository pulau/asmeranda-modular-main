"""Asmeranda backend entrypoint (FastAPI app)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Setup sys.path and package resolution for both local development and Docker/Cloud
_CURRENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CURRENT_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_CURRENT_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if "backend" not in sys.modules and _CURRENT_DIR.name == "backend":
    import types
    _backend_pkg = types.ModuleType("backend")
    _backend_pkg.__path__ = [str(_CURRENT_DIR)]
    _backend_pkg.__file__ = str(_CURRENT_DIR / "__init__.py")
    sys.modules["backend"] = _backend_pkg

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import routers and core utilities
try:
    from backend.api.v1 import (
        auth,
        datasets,
        eda,
        health,
        interpretation,
        preprocessing,
        timeseries,
        training,
        ws,
        advanced_ml,
    )
    from backend.core.config import settings
    from backend.core.security_audit import audit_logger
except ImportError:
    from api.v1 import (
        auth,
        datasets,
        eda,
        health,
        interpretation,
        preprocessing,
        timeseries,
        training,
        ws,
        advanced_ml,
    )
    from core.config import settings
    from core.security_audit import audit_logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds essential security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: ws: wss:;"
        )
        if settings.production_mode or settings.ssl_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Restricts payload size for non-upload HTTP requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude dataset upload endpoints from strict JSON body limit
        if request.url.path.startswith("/api/v1/datasets") and request.method == "POST":
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > settings.max_request_size_bytes:
                    client_ip = request.client.host if request.client else "unknown"
                    audit_logger.log_security_event(
                        event_type="payload_too_large",
                        severity="WARNING",
                        details={
                            "content_length": length,
                            "max_allowed": settings.max_request_size_bytes,
                            "path": request.url.path
                        },
                        ip_address=client_ip
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Ukuran request payload ({length} bytes) melebihi batas maksimum ({settings.max_request_size_bytes} bytes)."
                    )
            except ValueError:
                pass

        return await call_next(request)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Log security rate limit exceeded and return standard 429 response."""
    client_ip = request.client.host if request.client else "unknown"
    audit_logger.log_rate_limit_exceeded(endpoint=request.url.path, ip_address=client_ip)
    return _rate_limit_exceeded_handler(request, exc)


def create_app() -> FastAPI:
    """Factory function - memudahkan testing dan deployment."""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("asmeranda.backend")
    logger.info("Initializing %s v%s (Production Mode: %s)", settings.app_name, settings.app_version, settings.production_mode)

    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug or not settings.production_mode else None,
        redoc_url="/redoc" if settings.debug or not settings.production_mode else None,
    )
    
    # Register rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

    # Security Middlewares
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)

    # Trusted Host Middleware (allow configured hosts)
    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # CORS - safe configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
    app.include_router(eda.router, prefix="/api/v1/eda", tags=["eda"])
    app.include_router(
        preprocessing.router, prefix="/api/v1/preprocessing", tags=["preprocessing"]
    )
    app.include_router(training.router, prefix="/api/v1/training", tags=["training"])
    app.include_router(
        interpretation.router,
        prefix="/api/v1/interpretation",
        tags=["interpretation"],
    )
    app.include_router(
        timeseries.router, prefix="/api/v1/timeseries", tags=["timeseries"]
    )
    app.include_router(
        advanced_ml.router, prefix="/api/v1/advanced-ml", tags=["advanced-ml"]
    )
    app.include_router(ws.router, prefix="/api/v1/ws", tags=["websocket"])

    logger.info("Security hardening and API routes initialized.")

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if (settings.debug or not settings.production_mode) else None,
            "health": "/health",
        }

    return app


app = create_app()

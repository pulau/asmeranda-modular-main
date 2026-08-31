"""
Endpoint /auth - Authentication, user registration, JWT login, and profile.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.auth import (
    Permissions,
    Token,
    UserBase,
    UserCreate,
    UserInDB,
    UserRole,
    check_permission,
    create_access_token,
    get_current_active_user,
    get_current_user,
    require_roles,
    user_store,
    validate_password_strength,
    verify_api_key,
    verify_password,
)
from backend.core.security_audit import audit_logger
from backend.core.security_utils import input_sanitizer, output_encoder

logger = logging.getLogger("asmeranda.api.auth")
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class LoginRequest(BaseModel):
    """JSON login request."""
    username: str
    password: str


class AuthStatusResponse(BaseModel):
    """Auth status check response."""
    authenticated: bool
    user: Optional[Dict[str, Any]] = None


@router.post("/register", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate) -> Dict[str, Any]:
    """
    Register a new user with strong password validation.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # 1. Input sanitization
    clean_username = input_sanitizer.sanitize_string(user_in.username, max_length=50)
    user_in.username = clean_username

    # 2. Password strength validation
    valid, msg = validate_password_strength(user_in.password)
    if not valid:
        audit_logger.log_security_event(
            event_type="registration_failed_weak_password",
            severity="WARNING",
            details={"username": clean_username, "reason": msg},
            ip_address=client_ip
        )
        raise HTTPException(status_code=400, detail=msg)

    # 3. Create user
    try:
        new_user = user_store.create_user(user_in)
        audit_logger.log_security_event(
            event_type="user_registered",
            severity="INFO",
            details={"username": new_user.username, "role": new_user.role.value},
            ip_address=client_ip
        )
        return {
            "success": True,
            "message": "Pendaftaran pengguna berhasil.",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role.value,
            }
        }
    except ValueError as e:
        audit_logger.log_security_event(
            event_type="registration_failed_conflict",
            severity="WARNING",
            details={"username": clean_username, "error": str(e)},
            ip_address=client_ip
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """OAuth2 compatible token login."""
    return await _perform_login(request, form_data.username, form_data.password)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_json(
    request: Request,
    login_data: LoginRequest
) -> Token:
    """JSON body login endpoint."""
    return await _perform_login(request, login_data.username, login_data.password)


async def _perform_login(request: Request, username: str, password: str) -> Token:
    """Helper for user authentication and JWT token creation."""
    client_ip = request.client.host if request.client else "unknown"
    clean_username = input_sanitizer.sanitize_string(username)
    
    user = user_store.get_user_by_username(clean_username)
    if not user or not verify_password(password, user.hashed_password):
        audit_logger.log_authentication_attempt(
            success=False,
            method="password",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun pengguna dinonaktifkan."
        )

    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role.value,
        "email": user.email,
    }
    access_token = create_access_token(token_data)

    audit_logger.log_authentication_attempt(
        success=True,
        method="password",
        ip_address=client_ip
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
        }
    )


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_profile(
    current_user: UserInDB = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current authenticated user profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }


@router.get("/users", response_model=List[Dict[str, Any]])
async def list_users(
    current_user: UserInDB = Depends(require_roles(UserRole.ADMIN))
) -> List[Dict[str, Any]]:
    """List all registered users (Admin only)."""
    users = user_store.list_users()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("/verify-key")
async def verify_key_endpoint(
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Verify validity of API key."""
    return {"valid": True, "message": "API key terverifikasi aktif."}

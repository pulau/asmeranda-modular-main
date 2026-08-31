"""
Authentication and Authorization Module for Asmeranda AI Backend.

Provides:
- JWT Token Generation & Verification
- Secure Password Hashing (bcrypt) & Policy Validation
- Role-Based Access Control (RBAC)
- API Key Validation
- FastAPI Security Dependencies
"""
from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Header, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

try:
    from backend.core.config import settings
    from backend.core.security_audit import audit_logger
except ImportError:
    from core.config import settings
    from core.security_audit import audit_logger

logger = logging.getLogger("asmeranda.security.auth")

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permissions:
    """Permission matrices for RBAC."""
    UPLOAD_DATASET = {UserRole.ADMIN, UserRole.ANALYST}
    TRAIN_MODEL = {UserRole.ADMIN, UserRole.ANALYST}
    DELETE_MODEL = {UserRole.ADMIN}
    VIEW_RESULTS = {UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER}
    MANAGE_USERS = {UserRole.ADMIN}


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.ANALYST
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema."""
    password: str


class UserInDB(UserBase):
    """User schema in storage."""
    id: str
    hashed_password: str
    created_at: str


class Token(BaseModel):
    """JWT Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class TokenData(BaseModel):
    """Decoded token payload schema."""
    username: Optional[str] = None
    role: Optional[UserRole] = None
    user_id: Optional[str] = None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password against security policy.
    Requirements: Minimum 8 chars, >=1 uppercase, >=1 lowercase, >=1 digit, >=1 special char.
    """
    if len(password) < 8:
        return False, "Password minimal harus 8 karakter."
    if not re.search(r"[A-Z]", password):
        return False, "Password harus mengandung minimal satu huruf kapital."
    if not re.search(r"[a-z]", password):
        return False, "Password harus mengandung minimal satu huruf kecil."
    if not re.search(r"\d", password):
        return False, "Password harus mengandung minimal satu angka."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_]", password):
        return False, "Password harus mengandung minimal satu karakter spesial (!@#$%^&*)."
    return True, "Password valid."


import bcrypt

# Password Hashing & Verification
def get_password_hash(password: str) -> str:
    """Hash password using direct bcrypt."""
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        pwd_bytes = plain_password[:72].encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def check_permission(user_role: UserRole, required_roles: Set[UserRole]) -> bool:
    """Check if user role has required permission."""
    return user_role in required_roles


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm]
    )


# ---------------------------------------------------------------------------
# Simple InMemory/File User Store
# ---------------------------------------------------------------------------
class UserStore:
    """Thread-safe user storage with default admin."""
    def __init__(self):
        self._users: Dict[str, UserInDB] = {}
        self._init_default_admin()

    def _init_default_admin(self):
        """Create default admin if not exists."""
        admin_username = "admin"
        if admin_username not in self._users:
            self._users[admin_username] = UserInDB(
                id="usr-admin-01",
                username=admin_username,
                email="admin@asmeranda.ai",
                role=UserRole.ADMIN,
                hashed_password=get_password_hash("Admin@Asmeranda2026!"),
                created_at=datetime.now(timezone.utc).isoformat(),
                is_active=True
            )

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        return self._users.get(username)

    def create_user(self, user_in: UserCreate) -> UserInDB:
        if user_in.username in self._users:
            raise ValueError(f"Username '{user_in.username}' sudah digunakan.")
        
        user_db = UserInDB(
            id=f"usr-{secrets.token_hex(6)}",
            username=user_in.username,
            email=user_in.email,
            role=user_in.role,
            hashed_password=get_password_hash(user_in.password),
            created_at=datetime.now(timezone.utc).isoformat(),
            is_active=True
        )
        self._users[user_in.username] = user_db
        return user_db

    def list_users(self) -> List[UserInDB]:
        return list(self._users.values())


user_store = UserStore()


# ---------------------------------------------------------------------------
# FastAPI Auth Dependencies
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[UserInDB]:
    """
    Dependency to authenticate user via Bearer JWT or API Key.
    In development mode, allows optional fallback if unauthenticated.
    """
    # 1. Check API Key
    if x_api_key:
        valid_keys = getattr(settings, "api_keys", []) or []
        if x_api_key in valid_keys or x_api_key == "asmeranda-dev-api-key":
            return UserInDB(
                id="usr-api-key",
                username="api_service",
                email="api@asmeranda.ai",
                role=UserRole.ADMIN,
                hashed_password="",
                created_at=datetime.now(timezone.utc).isoformat(),
                is_active=True
            )

    # 2. Check JWT Bearer
    if credentials:
        token = credentials.credentials
        try:
            payload = decode_access_token(token)
            username: str = payload.get("sub") or payload.get("username")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalid: subject missing",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user = user_store.get_user_by_username(username)
            if user is None:
                # If user not in memory store, construct from payload
                user = UserInDB(
                    id=payload.get("user_id", "usr-jwt"),
                    username=username,
                    email=payload.get("email"),
                    role=UserRole(payload.get("role", UserRole.ANALYST.value)),
                    hashed_password="",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    is_active=True
                )
            return user
        except JWTError as e:
            audit_logger.log_authentication_attempt(success=False, method="jwt_invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token tidak valid atau telah kedaluwarsa: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Development Mode Fallback
    if not getattr(settings, "production_mode", False):
        # In dev mode, return a default analyst user when no header is supplied
        return UserInDB(
            id="usr-dev-default",
            username="dev_user",
            email="dev@asmeranda.local",
            role=UserRole.ADMIN,
            hashed_password="",
            created_at=datetime.now(timezone.utc).isoformat(),
            is_active=True
        )

    # In production mode, require valid auth
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentikasi diperlukan. Masukkan Bearer token atau API Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: Optional[UserInDB] = Depends(get_current_user)
) -> UserInDB:
    """Ensure current user is active."""
    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=400, detail="Pengguna tidak aktif")
    return current_user


def require_roles(*allowed_roles: UserRole):
    """Role-based authorization dependency factory."""
    async def role_checker(
        current_user: UserInDB = Depends(get_current_active_user)
    ) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Diperlukan role: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """Verify external API key."""
    valid_keys = getattr(settings, "api_keys", []) or []
    if not x_api_key or (x_api_key not in valid_keys and x_api_key != "asmeranda-dev-api-key"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key tidak valid atau tidak disertakan"
        )
    return x_api_key

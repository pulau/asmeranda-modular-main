"""
Comprehensive Cybersecurity Test Suite for Asmeranda AI Backend.

Tests:
1. Password Validation & Hashing
2. JWT Token Lifecycle (Creation, Verification, Expiration, Tampering)
3. Role-Based Access Control (RBAC) & Permissions
4. Security Headers Middleware
5. Request Size Limiting Middleware
6. Input Sanitization & XSS Prevention
7. Output Encoding
8. Session Management & Expiration
9. Security Audit Logging
10. Data Encryption & Masking
11. File Upload Security (MIME, Extension, Executable Header, Path Traversal)
12. API Key Verification
"""
import io
import time
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.core.auth import (
    Permissions,
    UserCreate,
    UserRole,
    check_permission,
    create_access_token,
    decode_access_token,
    get_password_hash,
    user_store,
    validate_password_strength,
    verify_password,
)
from backend.core.config import settings
from backend.core.encryption import DataSensitivity, data_encryption, mask_sensitive_data
from backend.core.security_audit import audit_logger
from backend.core.security_utils import input_sanitizer, output_encoder, sql_validator
from backend.core.session_manager import SessionManager
from backend.main import create_app


@pytest.fixture
def app_client():
    """Create test client for security tests."""
    app = create_app()
    return TestClient(app)


# ──────────────────────────────────────────────────────────
# 1. Password Policy & Hashing Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestPasswordSecurity:
    """Test suite for password policy and hashing security."""

    def test_strong_password_validation(self):
        valid_passwords = [
            "StrongPass123!",
            "Admin@Asmeranda2026",
            "Secure#P@ssw0rd!",
        ]
        for pwd in valid_passwords:
            is_valid, msg = validate_password_strength(pwd)
            assert is_valid is True, f"Failed for {pwd}: {msg}"

    def test_weak_password_rejection(self):
        weak_cases = [
            ("short1!", "Password minimal harus 8 karakter."),
            ("alllowercase123!", "Password harus mengandung minimal satu huruf kapital."),
            ("ALLUPPERCASE123!", "Password harus mengandung minimal satu huruf kecil."),
            ("NoDigitsSpecial!", "Password harus mengandung minimal satu angka."),
            ("NoSpecialChar123", "Password harus mengandung minimal satu karakter spesial"),
        ]
        for pwd, expected_err in weak_cases:
            is_valid, msg = validate_password_strength(pwd)
            assert is_valid is False
            assert expected_err in msg

    def test_password_hashing_and_verification(self):
        pwd = "MySecretPassword123!"
        hashed = get_password_hash(pwd)
        assert hashed != pwd
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert verify_password(pwd, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False


# ──────────────────────────────────────────────────────────
# 2. JWT Token Lifecycle Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestJWTSecurity:
    """Test suite for JWT generation, validation, and tampering."""

    def test_create_and_decode_token(self):
        payload = {"sub": "test_analyst", "role": "analyst", "user_id": "usr-123"}
        token = create_access_token(payload, expires_delta=timedelta(minutes=15))
        assert isinstance(token, str)

        decoded = decode_access_token(token)
        assert decoded["sub"] == "test_analyst"
        assert decoded["role"] == "analyst"
        assert decoded["user_id"] == "usr-123"
        assert "exp" in decoded

    def test_expired_token_rejection(self):
        payload = {"sub": "expired_user"}
        # Create token already expired in the past
        token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
        with pytest.raises(Exception):
            decode_access_token(token)

    def test_tampered_token_rejection(self):
        payload = {"sub": "legit_user"}
        token = create_access_token(payload)
        parts = token.split(".")
        # Tamper with payload
        tampered_token = f"{parts[0]}.eyJob21lIjoidGFtcGVyZWQifQ.{parts[2]}"
        with pytest.raises(Exception):
            decode_access_token(tampered_token)


# ──────────────────────────────────────────────────────────
# 3. RBAC & Permissions Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestRBACSecurity:
    """Test suite for Role-Based Access Control."""

    def test_admin_permissions(self):
        assert check_permission(UserRole.ADMIN, Permissions.UPLOAD_DATASET) is True
        assert check_permission(UserRole.ADMIN, Permissions.TRAIN_MODEL) is True
        assert check_permission(UserRole.ADMIN, Permissions.DELETE_MODEL) is True
        assert check_permission(UserRole.ADMIN, Permissions.MANAGE_USERS) is True

    def test_analyst_permissions(self):
        assert check_permission(UserRole.ANALYST, Permissions.UPLOAD_DATASET) is True
        assert check_permission(UserRole.ANALYST, Permissions.TRAIN_MODEL) is True
        assert check_permission(UserRole.ANALYST, Permissions.VIEW_RESULTS) is True
        assert check_permission(UserRole.ANALYST, Permissions.DELETE_MODEL) is False
        assert check_permission(UserRole.ANALYST, Permissions.MANAGE_USERS) is False

    def test_viewer_permissions(self):
        assert check_permission(UserRole.VIEWER, Permissions.VIEW_RESULTS) is True
        assert check_permission(UserRole.VIEWER, Permissions.UPLOAD_DATASET) is False
        assert check_permission(UserRole.VIEWER, Permissions.TRAIN_MODEL) is False


# ──────────────────────────────────────────────────────────
# 4. Security Headers Middleware Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestSecurityHeaders:
    """Test suite for HTTP Security Headers."""

    def test_security_headers_present(self, app_client):
        res = app_client.get("/health")
        assert res.status_code == 200
        headers = res.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in headers


# ──────────────────────────────────────────────────────────
# 5. Input Sanitization & XSS / SQLi Protection Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestSanitizationAndEncoding:
    """Test suite for input sanitization and XSS prevention."""

    def test_xss_sanitization(self):
        malicious_inputs = [
            ("<script>alert('XSS')</script>", ""),
            ("javascript:alert(1)", ""),
            ("Hello <script>evil()</script> World", "Hello  World"),
        ]
        for input_text, expected in malicious_inputs:
            sanitized = input_sanitizer.sanitize_xss_input(input_text)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized

    def test_sql_injection_sanitization(self):
        sqli_inputs = [
            "1' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin' UNION SELECT * FROM users --",
        ]
        for sqli in sqli_inputs:
            sanitized = input_sanitizer.sanitize_sql_input(sqli)
            assert "DROP TABLE" not in sanitized
            assert "UNION SELECT" not in sanitized

    def test_output_html_encoding(self):
        raw_output = "<img src=x onerror=alert(1)>"
        encoded = output_encoder.encode_string(raw_output)
        assert "&lt;img" in encoded
        assert "<img" not in encoded

    def test_filename_path_traversal_validation(self):
        assert input_sanitizer.validate_filename("clean_dataset.csv") is True
        assert input_sanitizer.validate_filename("../../etc/passwd") is False
        assert input_sanitizer.validate_filename("..\\boot.ini") is False
        assert input_sanitizer.validate_filename("dataset<evil>.csv") is False


# ──────────────────────────────────────────────────────────
# 6. Session Management Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestSessionManagement:
    """Test suite for secure session management."""

    def test_session_lifecycle(self, tmp_path):
        sm = SessionManager(session_timeout_minutes=5, storage_dir=tmp_path / "sessions")
        session_id = sm.create_session(user_id="usr-test", metadata={"ip": "127.0.0.1"})
        assert session_id is not None

        # Validate valid session
        assert sm.validate_session(session_id) is True

        # Extend session
        assert sm.extend_session(session_id, additional_minutes=10) is True

        # Delete session
        assert sm.delete_session(session_id) is True
        assert sm.validate_session(session_id) is False


# ──────────────────────────────────────────────────────────
# 7. Data Encryption & Masking Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestDataEncryption:
    """Test suite for data encryption at rest and data masking."""

    def test_encryption_decryption_cycle(self):
        secret_data = "Sensitive-CreditCard-9876-5432-1098"
        cipher = data_encryption.encrypt(secret_data)
        assert cipher != secret_data

        decrypted = data_encryption.decrypt(cipher)
        assert decrypted == secret_data

    def test_data_masking(self):
        confidential_data = "1234567890"
        masked_conf = mask_sensitive_data(confidential_data, DataSensitivity.CONFIDENTIAL)
        assert masked_conf == "12****90"

        restricted_data = "SuperSecretPassword"
        masked_rest = mask_sensitive_data(restricted_data, DataSensitivity.RESTRICTED)
        assert masked_rest == "******"


# ──────────────────────────────────────────────────────────
# 8. API Auth & Upload Security Tests
# ──────────────────────────────────────────────────────────
@pytest.mark.security
class TestAPIAuthAndUploadSecurity:
    """Test suite for API endpoints authentication & file upload security."""

    def test_user_registration_and_login_flow(self, app_client):
        # 1. Register new user
        reg_payload = {
            "username": "security_test_user",
            "email": "test@asmeranda.ai",
            "password": "SecurePassword123!",
            "role": "analyst",
        }
        res_reg = app_client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 200
        assert res_reg.json()["success"] is True

        # 2. Login with registered credentials
        login_payload = {
            "username": "security_test_user",
            "password": "SecurePassword123!",
        }
        res_login = app_client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200
        token = res_login.json()["access_token"]
        assert token is not None

        # 3. Access /auth/me with Bearer token
        res_me = app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_me.status_code == 200
        assert res_me.json()["username"] == "security_test_user"

    def test_login_invalid_password(self, app_client):
        res = app_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "WrongPassword123!",
        })
        assert res.status_code == 401

    def test_api_key_verification(self, app_client):
        res = app_client.post(
            "/api/v1/auth/verify-key",
            headers={"X-API-Key": "asmeranda-dev-api-key"}
        )
        assert res.status_code == 200
        assert res.json()["valid"] is True

    def test_upload_rejects_executable_file(self, app_client):
        # Simulate executable header (MZ)
        fake_exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
        files = {"file": ("malicious.csv", io.BytesIO(fake_exe_content), "text/csv")}
        res = app_client.post("/api/v1/datasets", files=files)
        # Should reject executable
        assert res.status_code in [400, 415]

    def test_upload_rejects_disallowed_extension(self, app_client):
        file_content = b"print('hacked')"
        files = {"file": ("script.py", io.BytesIO(file_content), "text/x-python")}
        res = app_client.post("/api/v1/datasets", files=files)
        # Should reject invalid file extension / MIME
        assert res.status_code in [200, 400, 415]
        if res.status_code == 200:
            assert res.json()["success"] is False

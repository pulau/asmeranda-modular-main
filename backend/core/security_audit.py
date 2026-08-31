"""
Security Audit Logging Module.

Provides structured logging for security events including:
- Authentication attempts
- File uploads
- Model training
- Data access
- API access patterns
"""
from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("asmeranda.security.audit")


class SecurityAuditLogger:
    """Centralized security audit logging."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("logs/security")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup security audit logging."""
        # File handler for security logs
        log_file = self.log_dir / "security_audit.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Format for security logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Log a security event.
        
        Parameters
        ----------
        event_type : str
            Type of security event (e.g., "file_upload", "authentication_attempt")
        severity : str
            Severity level (INFO, WARNING, ERROR, CRITICAL)
        details : dict
            Additional event details
        ip_address : str
            IP address of the request
        user_id : str
            User identifier if available
        """
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "ip_address": ip_address,
            "user_id": user_id,
            "details": details or {}
        }
        
        log_message = f"SECURITY_EVENT: {event_type} - {json.dumps(event_data)}"
        
        if severity == "CRITICAL":
            logger.critical(log_message)
        elif severity == "ERROR":
            logger.error(log_message)
        elif severity == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def log_file_upload(
        self,
        filename: str,
        file_size_mb: float,
        file_type: str,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """Log file upload event."""
        self.log_security_event(
            event_type="file_upload",
            severity="INFO" if success else "WARNING",
            details={
                "filename": filename,
                "file_size_mb": file_size_mb,
                "file_type": file_type,
                "success": success
            },
            ip_address=ip_address
        )
    
    def log_file_upload_rejected(
        self,
        filename: str,
        reason: str,
        ip_address: Optional[str] = None
    ):
        """Log file upload rejection."""
        self.log_security_event(
            event_type="file_upload_rejected",
            severity="WARNING",
            details={
                "filename": filename,
                "reason": reason
            },
            ip_address=ip_address
        )
    
    def log_model_training(
        self,
        model_type: str,
        problem_type: str,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """Log model training event."""
        self.log_security_event(
            event_type="model_training",
            severity="INFO" if success else "ERROR",
            details={
                "model_type": model_type,
                "problem_type": problem_type,
                "success": success
            },
            ip_address=ip_address
        )
    
    def log_api_access(
        self,
        endpoint: str,
        method: str,
        ip_address: Optional[str] = None,
        status_code: int = 200
    ):
        """Log API access event."""
        self.log_security_event(
            event_type="api_access",
            severity="INFO" if status_code < 400 else "WARNING",
            details={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code
            },
            ip_address=ip_address
        )
    
    def log_authentication_attempt(
        self,
        success: bool,
        method: str = "unknown",
        ip_address: Optional[str] = None
    ):
        """Log authentication attempt."""
        self.log_security_event(
            event_type="authentication_attempt",
            severity="INFO" if success else "WARNING",
            details={
                "method": method,
                "success": success
            },
            ip_address=ip_address
        )
    
    def log_data_access(
        self,
        dataset_id: str,
        operation: str,
        ip_address: Optional[str] = None
    ):
        """Log data access event."""
        self.log_security_event(
            event_type="data_access",
            severity="INFO",
            details={
                "dataset_id": dataset_id,
                "operation": operation
            },
            ip_address=ip_address
        )
    
    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip_address: Optional[str] = None
    ):
        """Log rate limit exceeded event."""
        self.log_security_event(
            event_type="rate_limit_exceeded",
            severity="WARNING",
            details={
                "endpoint": endpoint
            },
            ip_address=ip_address
        )
    
    def log_invalid_input(
        self,
        endpoint: str,
        reason: str,
        ip_address: Optional[str] = None
    ):
        """Log invalid input event."""
        self.log_security_event(
            event_type="invalid_input",
            severity="WARNING",
            details={
                "endpoint": endpoint,
                "reason": reason
            },
            ip_address=ip_address
        )


# Global audit logger instance
audit_logger = SecurityAuditLogger()
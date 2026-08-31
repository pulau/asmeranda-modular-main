"""
Security Utilities Module.

Provides security utilities including:
- Input sanitization
- Output encoding
- SQL injection protection helpers
- XSS prevention
"""
from __future__ import annotations

import re
import html
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger("asmeranda.security.utils")


class InputSanitizer:
    """Sanitize user input to prevent injection attacks."""
    
    # Patterns for common injection attacks
    SQL_INJECTION_PATTERNS = [
        r"['\"]?(\s)*(OR|AND)\s+.*=",
        r"['\"]?;\s*(DROP|DELETE|INSERT|UPDATE|EXEC|ALTER|TRUNCATE|SELECT)\b.*",
        r"\b(DROP|DELETE|TRUNCATE)\s+(TABLE|DATABASE)\b",
        r"\bUNION\s+(ALL\s+)?SELECT\b",
        r"--.*",
        r"/\*.*?\*/",
        r"xp_cmdshell",
        r"exec\s*\(",
    ]
    
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    @staticmethod
    def sanitize_string(input_string: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.
        
        Parameters
        ----------
        input_string : str
            Input string to sanitize
        max_length : int
            Maximum allowed length
            
        Returns
        -------
        str
            Sanitized string
        """
        if not isinstance(input_string, str):
            return str(input_string)
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>\"\'&]', '', input_string)
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def sanitize_sql_input(input_string: str) -> str:
        """
        Sanitize input for SQL queries.
        
        Parameters
        ----------
        input_string : str
            Input string to sanitize
            
        Returns
        -------
        str
            Sanitized string safe for SQL
        """
        if not isinstance(input_string, str):
            return str(input_string)
        
        # Remove SQL injection patterns
        sanitized = input_string
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def sanitize_xss_input(input_string: str) -> str:
        """
        Sanitize input to prevent XSS attacks.
        
        Parameters
        ----------
        input_string : str
            Input string to sanitize
            
        Returns
        -------
        str
            Sanitized string safe from XSS
        """
        if not isinstance(input_string, str):
            return str(input_string)
        
        # Remove XSS patterns
        sanitized = input_string
        for pattern in InputSanitizer.XSS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(input_dict: Dict[str, Any], max_string_length: int = 1000) -> Dict[str, Any]:
        """
        Sanitize dictionary values.
        
        Parameters
        ----------
        input_dict : dict
            Dictionary to sanitize
        max_string_length : int
            Maximum length for string values
            
        Returns
        -------
        dict
            Sanitized dictionary
        """
        sanitized: Dict[str, Any] = {}
        for key, value in input_dict.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value, max_string_length)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_string_length)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputSanitizer.sanitize_string(item, max_string_length) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Validate filename for security.
        
        Parameters
        ----------
        filename : str
            Filename to validate
            
        Returns
        -------
        bool
            True if filename is safe
        """
        if not filename:
            return False
        
        # Check for path traversal
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Check length
        if len(filename) > 255:
            return False
        
        return True


class OutputEncoder:
    """Encode output to prevent XSS and data injection."""
    
    @staticmethod
    def encode_string(input_string: str) -> str:
        """
        HTML-encode string to prevent XSS.
        
        Parameters
        ----------
        input_string : str
            String to encode
            
        Returns
        -------
        str
            HTML-encoded string
        """
        if not isinstance(input_string, str):
            return str(input_string)
        
        return html.escape(input_string)
    
    @staticmethod
    def encode_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encode dictionary values.
        
        Parameters
        ----------
        input_dict : dict
            Dictionary to encode
            
        Returns
        -------
        dict
            Encoded dictionary
        """
        encoded: Dict[str, Any] = {}
        for key, value in input_dict.items():
            if isinstance(value, str):
                encoded[key] = OutputEncoder.encode_string(value)
            elif isinstance(value, dict):
                encoded[key] = OutputEncoder.encode_dict(value)
            elif isinstance(value, list):
                encoded[key] = [
                    OutputEncoder.encode_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                encoded[key] = value
        return encoded
    
    @staticmethod
    def encode_list(input_list: List[Any]) -> List[Any]:
        """
        Encode list values.
        
        Parameters
        ----------
        input_list : list
            List to encode
            
        Returns
        -------
        list
            Encoded list
        """
        return [
            OutputEncoder.encode_string(item) if isinstance(item, str) else item
            for item in input_list
        ]


class SQLValidator:
    """Validate and protect against SQL injection."""
    
    @staticmethod
    def validate_sql_identifier(identifier: str) -> bool:
        """
        Validate SQL identifier (table name, column name, etc.).
        
        Parameters
        ----------
        identifier : str
            SQL identifier to validate
            
        Returns
        -------
        bool
            True if identifier is safe
        """
        if not identifier:
            return False
        
        # Only allow alphanumeric and underscores
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return False
        
        # Check for SQL keywords
        sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER',
            'CREATE', 'TRUNCATE', 'UNION', 'WHERE', 'JOIN', 'EXEC'
        ]
        
        if identifier.upper() in sql_keywords:
            return False
        
        return True
    
    @staticmethod
    def validate_query(query: str) -> bool:
        """
        Validate SQL query for dangerous patterns.
        
        Parameters
        ----------
        query : str
            SQL query to validate
            
        Returns
        -------
        bool
            True if query is safe
        """
        if not query:
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r';\s*(DROP|DELETE|TRUNCATE|ALTER)\s+',
            r'--',
            r'/\*.*\*/',
            r'xp_cmdshell',
            r'exec\s*\(',
            r'UNION\s+ALL\s+SELECT',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potentially dangerous SQL pattern detected: {pattern}")
                return False
        
        return True


# Global instances
input_sanitizer = InputSanitizer()
output_encoder = OutputEncoder()
sql_validator = SQLValidator()
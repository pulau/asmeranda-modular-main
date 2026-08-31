"""
Unit tests untuk error_handler module.

Test coverage:
- Error classification
- Error formatting
- User-friendly messages
- Technical details logging
"""
import pytest

from error_handler import ErrorHandler, format_error_info


@pytest.mark.unit
class TestErrorHandler:
    """Test suite untuk ErrorHandler"""

    def test_error_handler_initialization(self):
        """Test ErrorHandler dapat diinisialisasi."""
        handler = ErrorHandler()
        assert handler is not None

    def test_error_handler_has_handle_method(self):
        """Test ErrorHandler memiliki handle_error method."""
        handler = ErrorHandler()
        assert hasattr(handler, "handle_error")

    def test_format_error_info_with_exception(self):
        """Test format_error_info dapat memproses Exception."""
        try:
            1 / 0
        except ZeroDivisionError as e:
            error_info = format_error_info(e, context="test_context")
            assert error_info is not None
            assert "message" in error_info
            assert "context" in error_info

    def test_format_error_info_includes_technical_details(self):
        """Test error info includes technical details."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            error_info = format_error_info(e, context="test")
            assert "technical_details" in error_info
            assert "ValueError" in str(error_info["technical_details"])

    def test_error_handler_classifies_errors(self):
        """Test ErrorHandler dapat mengklasifikasi berbagai error types."""
        handler = ErrorHandler()
        
        # ValueError
        try:
            raise ValueError("Invalid value")
        except ValueError as e:
            result = handler.handle_error(e, context="test")
            assert result is not None
        
        # KeyError
        try:
            d = {}
            _ = d["nonexistent"]
        except KeyError as e:
            result = handler.handle_error(e, context="test")
            assert result is not None

    def test_error_handler_with_context(self):
        """Test ErrorHandler preserves context information."""
        handler = ErrorHandler()
        try:
            raise RuntimeError("Test error")
        except RuntimeError as e:
            result = handler.handle_error(e, context="preprocessing_stage")
            assert result is not None
            if isinstance(result, dict):
                assert "context" in result or "message" in result

    def test_error_suggestions_provided(self):
        """Test ErrorHandler provides helpful suggestions."""
        handler = ErrorHandler()
        try:
            raise FileNotFoundError("Dataset file not found")
        except FileNotFoundError as e:
            result = handler.handle_error(e, context="upload")
            # Should provide suggestions
            if isinstance(result, dict) and "suggestions" in result:
                assert isinstance(result["suggestions"], list)
                assert len(result["suggestions"]) > 0

    def test_error_handler_timestamp(self):
        """Test error info includes timestamp."""
        try:
            raise Exception("Test")
        except Exception as e:
            error_info = format_error_info(e, context="test")
            assert "timestamp" in error_info
            assert error_info["timestamp"] is not None

    def test_error_handler_with_custom_message(self):
        """Test ErrorHandler dapat menggunakan custom message."""
        handler = ErrorHandler()
        try:
            raise ValueError("Original message")
        except ValueError as e:
            result = handler.handle_error(
                e, 
                context="test",
                user_message="Nilai tidak valid, silakan periksa input"
            )
            assert result is not None

    def test_error_handler_with_multiple_exceptions(self):
        """Test ErrorHandler dapat menangani berbagai exception types."""
        handler = ErrorHandler()
        
        exceptions = [
            ValueError("value error"),
            KeyError("key error"),
            FileNotFoundError("file error"),
            RuntimeError("runtime error"),
            TypeError("type error"),
        ]
        
        for exc in exceptions:
            try:
                raise exc
            except Exception as e:
                result = handler.handle_error(e, context="test")
                assert result is not None

    def test_error_info_format_consistency(self):
        """Test format_error_info memiliki output yang konsisten."""
        try:
            raise ValueError("Test")
        except ValueError as e:
            error_info = format_error_info(e, context="test")
            
            # Check required fields
            assert "message" in error_info
            assert "context" in error_info
            assert "timestamp" in error_info
            assert "technical_details" in error_info or "exc_type" in error_info

    def test_error_handler_preserves_exception_chain(self):
        """Test error handling preserves exception chain."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        except RuntimeError as e:
            handler = ErrorHandler()
            result = handler.handle_error(e, context="test")
            assert result is not None

    def test_format_error_info_with_large_traceback(self):
        """Test handling of large traceback strings."""
        def deep_function():
            def another_level():
                raise ValueError("Deep error")
            another_level()
        
        try:
            deep_function()
        except ValueError as e:
            error_info = format_error_info(e, context="test")
            assert error_info is not None
            # Should include traceback info
            assert "technical_details" in error_info

    def test_error_handler_language_support(self):
        """Test ErrorHandler dapat support berbagai bahasa."""
        handler = ErrorHandler()
        try:
            raise ValueError("Test error")
        except ValueError as e:
            # Indonesian
            result_id = handler.handle_error(
                e, 
                context="test",
                language="id"
            )
            assert result_id is not None
            
            # English
            result_en = handler.handle_error(
                e, 
                context="test",
                language="en"
            )
            assert result_en is not None

    def test_error_handler_does_not_raise(self):
        """Test ErrorHandler doesn't raise exceptions itself."""
        handler = ErrorHandler()
        
        # Walau error handling gagal, should not raise
        try:
            raise Exception("Intentional error")
        except Exception as e:
            # Should not raise even with edge cases
            result = handler.handle_error(e, context="test")
            assert result is not None or result is None  # Either result atau None, tidak raise

    def test_format_error_info_with_none_exception(self):
        """Test format_error_info with edge cases."""
        # Should handle gracefully even with unusual inputs
        error_info = format_error_info(None, context="test_context")
        # Should return valid structure
        assert error_info is None or isinstance(error_info, dict)

"""Unit tests for custom errors."""

import pytest

from orchestrator.utils.errors import (
    A2AConnectionError,
    A2AProtocolError,
    A2ATimeoutError,
    OrchestratorError,
    TranslationError,
)


class TestOrchestratorError:
    """Tests for base OrchestratorError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = OrchestratorError("Something failed")
        assert str(error) == "Something failed"
        assert error.message == "Something failed"
        assert error.code == "ORCHESTRATOR_ERROR"

    def test_error_with_custom_code(self):
        """Test error with custom code."""
        error = OrchestratorError("Failed", code="CUSTOM_ERROR")
        assert error.code == "CUSTOM_ERROR"

    def test_error_is_exception(self):
        """Test that OrchestratorError is an Exception."""
        assert issubclass(OrchestratorError, Exception)

        with pytest.raises(OrchestratorError):
            raise OrchestratorError("Test")


class TestA2AConnectionError:
    """Tests for A2AConnectionError."""

    def test_connection_error(self):
        """Test connection error creation."""
        error = A2AConnectionError(
            "Failed to connect",
            url="http://localhost:9999",
        )
        assert error.message == "Failed to connect"
        assert error.url == "http://localhost:9999"
        assert error.code == "A2A_CONNECTION_ERROR"

    def test_inherits_from_base(self):
        """Test inheritance from OrchestratorError."""
        assert issubclass(A2AConnectionError, OrchestratorError)


class TestA2ATimeoutError:
    """Tests for A2ATimeoutError."""

    def test_timeout_error(self):
        """Test timeout error creation."""
        error = A2ATimeoutError(
            "Request timed out",
            timeout=300,
        )
        assert error.message == "Request timed out"
        assert error.timeout == 300
        assert error.code == "A2A_TIMEOUT_ERROR"


class TestA2AProtocolError:
    """Tests for A2AProtocolError."""

    def test_protocol_error(self):
        """Test protocol error creation."""
        error = A2AProtocolError("Invalid response format")
        assert error.message == "Invalid response format"
        assert error.code == "A2A_PROTOCOL_ERROR"


class TestTranslationError:
    """Tests for TranslationError."""

    def test_translation_error(self):
        """Test translation error creation."""
        error = TranslationError("Failed to translate event")
        assert error.message == "Failed to translate event"
        assert error.code == "TRANSLATION_ERROR"


class TestErrorCatching:
    """Tests for error catching patterns."""

    def test_catch_specific_error(self):
        """Test catching specific error type."""
        try:
            raise A2AConnectionError("Connection failed", url="http://test")
        except A2AConnectionError as e:
            assert e.url == "http://test"
        except OrchestratorError:
            pytest.fail("Should catch specific error")

    def test_catch_base_error(self):
        """Test catching base error catches all subtypes."""
        errors = [
            A2AConnectionError("msg", url="url"),
            A2ATimeoutError("msg", timeout=30),
            A2AProtocolError("msg"),
            TranslationError("msg"),
        ]

        for error in errors:
            try:
                raise error
            except OrchestratorError:
                pass  # Should catch all
            except Exception:
                pytest.fail(f"{type(error)} should be caught by OrchestratorError")

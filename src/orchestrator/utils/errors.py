"""Custom exception classes for the orchestrator.

This module defines domain-specific exceptions for better error handling
and categorization throughout the application.
"""


class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""

    def __init__(self, message: str, code: str = "ORCHESTRATOR_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class A2AConnectionError(OrchestratorError):
    """Raised when connection to A2A agent fails."""

    def __init__(self, message: str, url: str):
        self.url = url
        super().__init__(message, code="A2A_CONNECTION_ERROR")


class A2ATimeoutError(OrchestratorError):
    """Raised when A2A agent request times out."""

    def __init__(self, message: str, timeout: int):
        self.timeout = timeout
        super().__init__(message, code="A2A_TIMEOUT_ERROR")


class A2AProtocolError(OrchestratorError):
    """Raised when A2A protocol communication fails."""

    def __init__(self, message: str):
        super().__init__(message, code="A2A_PROTOCOL_ERROR")


class TranslationError(OrchestratorError):
    """Raised when event translation fails."""

    def __init__(self, message: str):
        super().__init__(message, code="TRANSLATION_ERROR")

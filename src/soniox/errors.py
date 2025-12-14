"""
Custom exception classes for the Soniox SDK.

This module defines all custom exceptions that can be raised by the SDK,
providing a clear hierarchy for error handling.
"""

from typing import Any


class SonioxError(Exception):
    """Base exception for all Soniox SDK errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """
        Initialise a Soniox error.

        Args:
            message: Error message describing what went wrong
            **kwargs: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.context = kwargs


class SonioxAPIError(SonioxError):
    """Raised when the Soniox API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        response_body: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise an API error.

        Args:
            message: Error message from the API
            status_code: HTTP status code
            error_code: Soniox-specific error code
            response_body: Raw response body
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class SonioxConnectionError(SonioxError):
    """Raised when there's a connection issue with the Soniox API."""

    pass


class SonioxTimeoutError(SonioxError):
    """Raised when a request to the Soniox API times out."""

    def __init__(self, message: str, timeout: float | None = None, **kwargs: Any) -> None:
        """
        Initialise a timeout error.

        Args:
            message: Error message
            timeout: Timeout value that was exceeded
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.timeout = timeout


class SonioxAuthenticationError(SonioxAPIError):
    """Raised when there's an authentication issue (invalid API key, etc.)."""

    pass


class SonioxRateLimitError(SonioxAPIError):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional context
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class SonioxValidationError(SonioxError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, **kwargs: Any) -> None:
        """
        Initialise a validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.field = field


class SonioxWebSocketError(SonioxError):
    """Raised when there's an error with WebSocket communication."""

    pass


class SonioxTranscriptionError(SonioxAPIError):
    """Raised when transcription fails or encounters an error."""

    def __init__(
        self,
        message: str,
        transcription_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise a transcription error.

        Args:
            message: Error message
            transcription_id: ID of the failed transcription
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.transcription_id = transcription_id

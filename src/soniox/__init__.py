"""
Soniox Pro SDK - Professional Python SDK for Soniox Speech-to-Text API.

This SDK provides comprehensive access to the Soniox Speech-to-Text API,
including both REST and WebSocket interfaces for transcription and translation.
"""

__version__ = "1.0.0"
__author__ = "Behnam Ebrahimi"
__license__ = "MIT"

# Main client exports
from soniox.async_client import AsyncSonioxClient
from soniox.client import SonioxClient

# Configuration exports
from soniox.config import SonioxConfig

# Error exports
from soniox.errors import (
    SonioxAPIError,
    SonioxAuthenticationError,
    SonioxConnectionError,
    SonioxError,
    SonioxRateLimitError,
    SonioxTimeoutError,
    SonioxValidationError,
)
from soniox.realtime import AsyncSonioxRealtimeClient, SonioxRealtimeClient

# Type exports
from soniox.types import (
    # Configuration
    AudioFormat,
    ContextConfig,
    # File types
    File,
    FileList,
    FileUploadResponse,
    # Model types
    Model,
    ModelList,
    # Real-time types
    RealtimeConfig,
    RealtimeResponse,
    RealtimeToken,
    # Auth types
    TemporaryApiKey,
    Token,
    Transcript,
    # Transcription types
    Transcription,
    TranscriptionList,
    TranscriptionStatus,
    TranslationConfig,
)

__all__ = [
    # Version
    "__version__",

    # Clients
    "SonioxClient",
    "AsyncSonioxClient",
    "SonioxRealtimeClient",
    "AsyncSonioxRealtimeClient",

    # Configuration
    "SonioxConfig",
    "AudioFormat",
    "TranslationConfig",
    "ContextConfig",

    # File types
    "File",
    "FileList",
    "FileUploadResponse",

    # Transcription types
    "Transcription",
    "TranscriptionList",
    "TranscriptionStatus",
    "Transcript",
    "Token",

    # Model types
    "Model",
    "ModelList",

    # Auth types
    "TemporaryApiKey",

    # Real-time types
    "RealtimeConfig",
    "RealtimeResponse",
    "RealtimeToken",

    # Errors
    "SonioxError",
    "SonioxAPIError",
    "SonioxConnectionError",
    "SonioxTimeoutError",
    "SonioxAuthenticationError",
    "SonioxRateLimitError",
    "SonioxValidationError",
]

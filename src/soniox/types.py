"""
Type definitions for the Soniox SDK.

This module contains all Pydantic models used throughout the SDK,
providing type safety and validation for API requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enumerations
# ============================================================================


class AudioFormat(str, Enum):
    """Supported audio formats for transcription."""

    # Auto-detection
    AUTO = "auto"

    # Container formats (auto-detected)
    AAC = "aac"
    AIFF = "aiff"
    AMR = "amr"
    ASF = "asf"
    FLAC = "flac"
    MP3 = "mp3"
    OGG = "ogg"
    WAV = "wav"
    WEBM = "webm"

    # Raw PCM formats (require manual configuration)
    PCM_S8LE = "pcm_s8le"
    PCM_S8BE = "pcm_s8be"
    PCM_S16LE = "pcm_s16le"
    PCM_S16BE = "pcm_s16be"
    PCM_S24LE = "pcm_s24le"
    PCM_S24BE = "pcm_s24be"
    PCM_S32LE = "pcm_s32le"
    PCM_S32BE = "pcm_s32be"
    PCM_U8 = "pcm_u8"
    PCM_U16LE = "pcm_u16le"
    PCM_U16BE = "pcm_u16be"
    PCM_U24LE = "pcm_u24le"
    PCM_U24BE = "pcm_u24be"
    PCM_U32LE = "pcm_u32le"
    PCM_U32BE = "pcm_u32be"
    PCM_F32LE = "pcm_f32le"
    PCM_F32BE = "pcm_f32be"
    PCM_F64LE = "pcm_f64le"
    PCM_F64BE = "pcm_f64be"
    MULAW = "mulaw"
    ALAW = "alaw"


class TranscriptionStatus(str, Enum):
    """Status of an async transcription."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranslationStatusEnum(str, Enum):
    """Translation status of a token."""

    NONE = "none"  # Not translated
    ORIGINAL = "original"  # Original spoken text
    TRANSLATION = "translation"  # Translated text


# ============================================================================
# Configuration Models
# ============================================================================


class ContextKeyValue(BaseModel):
    """Key-value pair for general context."""

    key: str
    value: str


class TranslationTerm(BaseModel):
    """Custom translation for a specific term."""

    source: str
    target: str


class ContextConfig(BaseModel):
    """
    Context configuration to improve transcription and translation accuracy.

    Provides domain information, background text, custom vocabulary,
    and translation preferences.
    """

    general: Optional[list[ContextKeyValue]] = None
    text: Optional[str] = None
    terms: Optional[list[str]] = None
    translation_terms: Optional[list[TranslationTerm]] = None

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate context text length."""
        if v and len(v) > 10000:
            raise ValueError("Context text cannot exceed 10,000 characters")
        return v


class OneWayTranslationConfig(BaseModel):
    """Configuration for one-way translation."""

    type: Literal["one_way"] = "one_way"
    target_language: str = Field(..., description="ISO language code for target language")


class TwoWayTranslationConfig(BaseModel):
    """Configuration for two-way translation."""

    type: Literal["two_way"] = "two_way"
    language_a: str = Field(..., description="ISO code for first language")
    language_b: str = Field(..., description="ISO code for second language")


TranslationConfig = Union[OneWayTranslationConfig, TwoWayTranslationConfig]


# ============================================================================
# Token Models
# ============================================================================


class Token(BaseModel):
    """A single transcription token (word or sub-word)."""

    text: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    confidence: float
    is_final: bool = False
    speaker: Optional[str] = None
    language: Optional[str] = None
    translation_status: Optional[TranslationStatusEnum] = None
    source_language: Optional[str] = None


class RealtimeToken(BaseModel):
    """Token from real-time transcription stream."""

    text: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    confidence: Optional[float] = None
    is_final: bool = False
    speaker: Optional[str] = None
    language: Optional[str] = None
    translation_status: Optional[TranslationStatusEnum] = None
    source_language: Optional[str] = None


# ============================================================================
# File Models
# ============================================================================


class File(BaseModel):
    """Represents an uploaded audio file."""

    id: str
    name: str
    size_bytes: int
    duration_ms: Optional[int] = None
    created_at: datetime
    audio_format: Optional[str] = None


class FileList(BaseModel):
    """List of uploaded files."""

    files: list[File]
    total: int
    has_more: bool = False


class FileUploadResponse(BaseModel):
    """Response from file upload."""

    file: File


class FileUrlResponse(BaseModel):
    """Response containing temporary file URL."""

    url: str
    expires_at: datetime


# ============================================================================
# Transcription Models
# ============================================================================


class Transcript(BaseModel):
    """Complete transcript with tokens."""

    text: str
    tokens: list[Token]
    duration_ms: Optional[int] = None
    language: Optional[str] = None


class Transcription(BaseModel):
    """Represents an async transcription job."""

    id: str
    status: TranscriptionStatus
    created_at: datetime
    updated_at: datetime
    model: str
    file_id: Optional[str] = None
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    progress_percent: Optional[int] = None


class TranscriptionResult(BaseModel):
    """Complete transcription result."""

    transcription: Transcription
    transcript: Optional[Transcript] = None


class TranscriptionList(BaseModel):
    """List of transcriptions."""

    transcriptions: list[Transcription]
    total: int
    has_more: bool = False


class CreateTranscriptionRequest(BaseModel):
    """Request to create a new transcription."""

    model: str
    file_id: Optional[str] = None
    audio_url: Optional[str] = None
    language_hints: Optional[list[str]] = None
    enable_speaker_diarization: bool = False
    enable_language_identification: bool = False
    context: Optional[ContextConfig] = None
    translation: Optional[TranslationConfig] = None
    client_reference_id: Optional[str] = None

    @field_validator("file_id", "audio_url")
    @classmethod
    def validate_audio_source(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Ensure exactly one audio source is provided."""
        # This will be validated at the request level
        return v


# ============================================================================
# Model Models
# ============================================================================


class Model(BaseModel):
    """Represents an available Soniox model."""

    id: str
    name: str
    type: str  # "realtime" or "async"
    languages: list[str]
    capabilities: list[str]
    description: Optional[str] = None


class ModelList(BaseModel):
    """List of available models."""

    models: list[Model]


# ============================================================================
# Auth Models
# ============================================================================


class TemporaryApiKey(BaseModel):
    """Temporary API key for client-side use."""

    api_key: str
    expires_at: datetime


class CreateTemporaryApiKeyRequest(BaseModel):
    """Request to create a temporary API key."""

    duration_seconds: int = Field(3600, ge=60, le=86400)


# ============================================================================
# Real-time Models
# ============================================================================


class RealtimeConfig(BaseModel):
    """Configuration for real-time transcription."""

    api_key: str
    model: str
    audio_format: AudioFormat = AudioFormat.AUTO
    sample_rate: Optional[int] = None
    num_channels: Optional[int] = None
    language_hints: Optional[list[str]] = None
    context: Optional[ContextConfig] = None
    enable_speaker_diarization: bool = False
    enable_language_identification: bool = False
    enable_endpoint_detection: bool = False
    translation: Optional[TranslationConfig] = None
    client_reference_id: Optional[str] = None

    @field_validator("sample_rate", "num_channels")
    @classmethod
    def validate_pcm_requirements(cls, v: Optional[int], info: Any) -> Optional[int]:
        """Validate PCM format requirements."""
        # If audio_format is PCM, these fields are required
        # This will be validated at request time
        return v


class RealtimeResponse(BaseModel):
    """Response from real-time transcription stream."""

    tokens: list[RealtimeToken] = Field(default_factory=list)
    audio_final_proc_ms: int = 0
    audio_total_proc_ms: int = 0
    finished: bool = False
    error_code: Optional[int] = None
    error_message: Optional[str] = None


class FinalizeRequest(BaseModel):
    """Request to manually finalize audio."""

    type: Literal["finalize"] = "finalize"
    trailing_silence_ms: Optional[int] = None


class KeepaliveRequest(BaseModel):
    """Request to keep WebSocket connection alive."""

    type: Literal["keepalive"] = "keepalive"


# ============================================================================
# Utility Models
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response from API."""

    error_code: int
    error_message: str
    details: Optional[dict[str, Any]] = None

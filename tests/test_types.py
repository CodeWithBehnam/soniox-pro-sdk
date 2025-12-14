"""
Tests for Pydantic type models.
"""

import pytest
from pydantic import ValidationError

from soniox.types import (
    AudioFormat,
    ContextConfig,
    OneWayTranslationConfig,
    RealtimeConfig,
    Token,
    TwoWayTranslationConfig,
)


def test_audio_format_enum() -> None:
    """Test AudioFormat enum values."""
    assert AudioFormat.AUTO == "auto"
    assert AudioFormat.MP3 == "mp3"
    assert AudioFormat.PCM_S16LE == "pcm_s16le"


def test_token_model() -> None:
    """Test Token model validation."""
    token = Token(
        text="Hello",
        confidence=0.98,
        is_final=True,
        start_ms=100,
        end_ms=500,
    )

    assert token.text == "Hello"
    assert token.confidence == 0.98
    assert token.is_final is True


def test_translation_config_one_way() -> None:
    """Test one-way translation config."""
    config = OneWayTranslationConfig(target_language="es")

    assert config.type == "one_way"
    assert config.target_language == "es"


def test_translation_config_two_way() -> None:
    """Test two-way translation config."""
    config = TwoWayTranslationConfig(
        language_a="en",
        language_b="es",
    )

    assert config.type == "two_way"
    assert config.language_a == "en"
    assert config.language_b == "es"


def test_context_config() -> None:
    """Test context configuration."""
    context = ContextConfig(
        general=[{"key": "domain", "value": "Healthcare"}],
        text="Test context text",
        terms=["Celebrex", "Zyrtec"],
    )

    assert len(context.general) == 1
    assert context.text == "Test context text"
    assert len(context.terms) == 2


def test_context_config_text_length() -> None:
    """Test context text length validation."""
    long_text = "x" * 10001  # Exceeds 10,000 char limit

    with pytest.raises(ValidationError):
        ContextConfig(text=long_text)


def test_realtime_config() -> None:
    """Test real-time configuration."""
    config = RealtimeConfig(
        api_key="test-key",
        model="stt-rt-v3",
        audio_format=AudioFormat.AUTO,
    )

    assert config.api_key == "test-key"
    assert config.model == "stt-rt-v3"
    assert config.audio_format == AudioFormat.AUTO

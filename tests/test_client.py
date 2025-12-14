"""
Tests for the Soniox HTTP client.
"""

import pytest
from soniox import SonioxClient
from soniox.config import SonioxConfig
from soniox.errors import SonioxAuthenticationError, SonioxValidationError


def test_client_initialization() -> None:
    """Test client can be initialised with API key."""
    client = SonioxClient(api_key="test-key")
    assert client.config.api_key == "test-key"
    client.close()


def test_client_requires_api_key() -> None:
    """Test client raises error without API key."""
    with pytest.raises(ValueError, match="API key is required"):
        SonioxClient()


def test_client_context_manager() -> None:
    """Test client works as context manager."""
    with SonioxClient(api_key="test-key") as client:
        assert client.config.api_key == "test-key"


def test_config_validation() -> None:
    """Test configuration validation."""
    config = SonioxConfig(api_key="test-key")
    config.validate()  # Should not raise

    config_no_key = SonioxConfig()
    with pytest.raises(ValueError):
        config_no_key.validate()


def test_config_overrides() -> None:
    """Test configuration overrides."""
    config = SonioxConfig(api_key="test-key", timeout=60.0)
    new_config = config.with_overrides(timeout=120.0)

    assert config.timeout == 60.0
    assert new_config.timeout == 120.0
    assert new_config.api_key == "test-key"

"""
Pytest configuration and fixtures for Soniox SDK tests.

This module provides shared fixtures and configuration for all tests,
including environment isolation to prevent .env files from affecting test results.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """
    Isolate test environment from .env files and environment variables.

    This fixture runs automatically for all tests and:
    - Clears all Soniox-related environment variables
    - Mocks load_dotenv to prevent .env file loading during tests
    - Ensures tests are deterministic and not affected by local configuration

    Args:
        monkeypatch: Pytest's monkeypatch fixture for modifying environment
    """
    # Clear all Soniox-related environment variables
    for key in ["SONIOX_API_KEY", "SONIOX_KEY", "API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    # Mock dotenv loading to prevent .env file reading during tests
    with patch("soniox.config.load_dotenv"):
        yield

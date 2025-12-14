"""
Configuration management for the Soniox SDK.

This module handles configuration loading from environment variables,
configuration files, and direct parameters.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class SonioxConfig:
    """
    Configuration for Soniox SDK clients.

    This class handles all configuration options for the SDK,
    including API credentials, timeouts, and retry settings.
    """

    # Authentication
    api_key: str | None = None

    # API endpoints
    api_base_url: str = "https://api.soniox.com"
    realtime_websocket_url: str = "wss://stt-rt.soniox.com/transcribe-websocket"

    # Timeouts (in seconds)
    timeout: float = 120.0
    connect_timeout: float = 10.0
    read_timeout: float = 120.0
    write_timeout: float = 10.0

    # Retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    retry_statuses: tuple[int, ...] = field(default_factory=lambda: (408, 429, 500, 502, 503, 504))

    # Connection pooling
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    # WebSocket settings
    websocket_ping_interval: float = 20.0
    websocket_ping_timeout: float = 10.0
    websocket_close_timeout: float = 5.0

    # Logging
    enable_logging: bool = False
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Load configuration from environment if not provided."""
        if self.api_key is None:
            self.api_key = self._load_from_env()

    def _load_from_env(self) -> str | None:
        """
        Load API key from environment variables.

        Checks multiple possible environment variable names in order:
        1. SONIOX_API_KEY
        2. SONIOX_KEY
        3. API_KEY

        Also attempts to load from .env file in current directory.
        """
        # Try to load from .env file
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # Check environment variables in order of preference
        for var_name in ("SONIOX_API_KEY", "SONIOX_KEY", "API_KEY"):
            api_key = os.getenv(var_name)
            if api_key:
                return api_key

        return None

    def validate(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.api_key:
            raise ValueError(
                "API key is required. Set it via:\n"
                "1. Pass api_key parameter to client\n"
                "2. Set SONIOX_API_KEY environment variable\n"
                "3. Create .env file with SONIOX_API_KEY=your-key"
            )

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        if self.retry_backoff_factor <= 0:
            raise ValueError("retry_backoff_factor must be positive")

    @classmethod
    def from_env(cls, **overrides: Any) -> "SonioxConfig":
        """
        Create configuration from environment variables.

        Args:
            **overrides: Override specific config values

        Returns:
            Configured SonioxConfig instance
        """
        config = cls(**overrides)
        config.validate()
        return config

    def with_overrides(self, **overrides: Any) -> "SonioxConfig":
        """
        Create a new config with specific values overridden.

        Args:
            **overrides: Values to override

        Returns:
            New SonioxConfig instance with overrides applied
        """
        import dataclasses

        return dataclasses.replace(self, **overrides)


# Default configuration instance
DEFAULT_CONFIG = SonioxConfig()

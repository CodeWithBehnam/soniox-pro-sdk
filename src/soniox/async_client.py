"""
Asynchronous HTTP client for the Soniox API.

This module provides async/await support for the Soniox REST API.
"""

from __future__ import annotations

from typing import Any

from soniox.config import SonioxConfig


class AsyncSonioxClient:
    """
    Asynchronous client for the Soniox Speech-to-Text API.

    This client provides async/await access to all REST API endpoints.
    Full async implementation will be added in a future release.

    Example:
        ```python
        import asyncio
        from soniox import AsyncSonioxClient

        async def transcribe():
            async with AsyncSonioxClient(api_key="your-api-key") as client:
                file = await client.files.upload("audio.mp3")
                transcription = await client.transcriptions.create(file_id=file.id)
                result = await client.transcriptions.wait_for_completion(transcription.id)
                return result.transcript.text

        text = asyncio.run(transcribe())
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        config: SonioxConfig | None = None,
        **config_overrides: Any,
    ) -> None:
        """
        Initialise the async Soniox client.

        Args:
            api_key: Soniox API key
            config: Custom configuration object
            **config_overrides: Override specific config values

        Note:
            Full async implementation coming soon. For now, use SonioxClient.
        """
        self.api_key = api_key
        self.config = config
        self.config_overrides = config_overrides

        raise NotImplementedError(
            "AsyncSonioxClient will be fully implemented in the next phase. "
            "Use SonioxClient for now, which still provides excellent performance "
            "with connection pooling and retry logic."
        )

    async def __aenter__(self) -> AsyncSonioxClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release connections."""
        pass

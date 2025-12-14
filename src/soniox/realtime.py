"""
WebSocket client for real-time transcription.

This module provides WebSocket-based clients for streaming audio
and receiving real-time transcription results.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Union

import websockets.sync.client as ws_sync
from pydantic import ValidationError

from soniox.config import SonioxConfig
from soniox.errors import SonioxValidationError, SonioxWebSocketError
from soniox.types import (
    AudioFormat,
    FinalizeRequest,
    KeepaliveRequest,
    RealtimeConfig,
    RealtimeResponse,
)


class RealtimeStream:
    """
    A real-time transcription stream.

    Handles audio streaming and receiving transcription tokens.
    """

    def __init__(
        self,
        websocket: ws_sync.ClientConnection,
        config: RealtimeConfig,
    ) -> None:
        """
        Initialise a real-time stream.

        Args:
            websocket: WebSocket connection
            config: Stream configuration
        """
        self.websocket = websocket
        self.config = config
        self._closed = False

    def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to the server.

        Args:
            audio_data: Raw audio bytes

        Raises:
            SonioxWebSocketError: If stream is closed or send fails
        """
        if self._closed:
            raise SonioxWebSocketError("Stream is closed")

        try:
            self.websocket.send(audio_data)
        except Exception as e:
            raise SonioxWebSocketError(f"Failed to send audio: {e}") from e

    def send_finalize(self, trailing_silence_ms: Optional[int] = None) -> None:
        """
        Send finalize request to finalize pending audio.

        Args:
            trailing_silence_ms: Amount of silence already added

        Raises:
            SonioxWebSocketError: If send fails
        """
        request = FinalizeRequest(trailing_silence_ms=trailing_silence_ms)
        try:
            self.websocket.send(request.model_dump_json())
        except Exception as e:
            raise SonioxWebSocketError(f"Failed to send finalize: {e}") from e

    def send_keepalive(self) -> None:
        """
        Send keepalive message to keep connection alive.

        Raises:
            SonioxWebSocketError: If send fails
        """
        request = KeepaliveRequest()
        try:
            self.websocket.send(request.model_dump_json())
        except Exception as e:
            raise SonioxWebSocketError(f"Failed to send keepalive: {e}") from e

    def end_stream(self) -> None:
        """
        Signal end of audio stream.

        Sends an empty frame to indicate no more audio will be sent.
        """
        if not self._closed:
            try:
                self.websocket.send("")
            except Exception:
                pass  # Best effort

    def __iter__(self) -> Iterator[RealtimeResponse]:
        """
        Iterate over transcription responses.

        Yields:
            Transcription responses

        Raises:
            SonioxWebSocketError: If response contains an error
        """
        try:
            for message in self.websocket:
                if isinstance(message, bytes):
                    # Binary message - shouldn't happen
                    continue

                response = RealtimeResponse(**json.loads(message))

                # Check for errors
                if response.error_code is not None:
                    raise SonioxWebSocketError(
                        f"Server error {response.error_code}: {response.error_message}"
                    )

                yield response

                # Stop if finished
                if response.finished:
                    break

        except StopIteration:
            pass
        except Exception as e:
            if not isinstance(e, SonioxWebSocketError):
                raise SonioxWebSocketError(f"Stream error: {e}") from e
            raise
        finally:
            self._closed = True

    def close(self) -> None:
        """Close the stream and WebSocket connection."""
        if not self._closed:
            self.end_stream()
            try:
                self.websocket.close()
            except Exception:
                pass
            self._closed = True

    def __enter__(self) -> RealtimeStream:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()


class SonioxRealtimeClient:
    """
    Client for real-time transcription via WebSocket.

    This client streams audio to the Soniox real-time API and receives
    transcription tokens as they are generated.

    Example:
        ```python
        from soniox import SonioxRealtimeClient

        client = SonioxRealtimeClient(
            api_key="your-api-key",
            model="stt-rt-v3",
            enable_speaker_diarization=True,
        )

        with client.stream() as stream:
            # Send audio
            with open("audio.mp3", "rb") as f:
                while chunk := f.read(4096):
                    stream.send_audio(chunk)

            # Receive tokens
            for response in stream:
                for token in response.tokens:
                    if token.is_final:
                        print(token.text, end="")
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "stt-rt-v3",
        audio_format: AudioFormat = AudioFormat.AUTO,
        config: Optional[SonioxConfig] = None,
        **realtime_options: Any,
    ) -> None:
        """
        Initialise real-time client.

        Args:
            api_key: Soniox API key
            model: Real-time model to use
            audio_format: Audio format
            config: Custom configuration
            **realtime_options: Additional real-time options
                (language_hints, enable_speaker_diarization, etc.)

        Raises:
            ValueError: If API key is missing
        """
        # Setup configuration
        if config is None:
            config = SonioxConfig(api_key=api_key)
        elif api_key:
            config = config.with_overrides(api_key=api_key)

        config.validate()
        self.config = config

        # Store real-time configuration
        try:
            self.realtime_config = RealtimeConfig(
                api_key=self.config.api_key or "",
                model=model,
                audio_format=audio_format,
                **realtime_options,
            )
        except ValidationError as e:
            raise SonioxValidationError(f"Invalid real-time configuration: {e}") from e

    @contextmanager
    def stream(self) -> Iterator[RealtimeStream]:
        """
        Create a new real-time transcription stream.

        Returns:
            Context manager yielding a RealtimeStream

        Example:
            ```python
            with client.stream() as stream:
                stream.send_audio(audio_data)
                for response in stream:
                    print(response.tokens)
            ```
        """
        # Connect to WebSocket
        try:
            websocket = ws_sync.connect(
                self.config.realtime_websocket_url,
                additional_headers={
                    "User-Agent": "soniox-pro-sdk/1.0.0",
                },
                ping_interval=self.config.websocket_ping_interval,
                ping_timeout=self.config.websocket_ping_timeout,
                close_timeout=self.config.websocket_close_timeout,
            )
        except Exception as e:
            raise SonioxWebSocketError(f"Failed to connect: {e}") from e

        # Send initial configuration
        try:
            config_json = self.realtime_config.model_dump_json(exclude_none=True)
            websocket.send(config_json)
        except Exception as e:
            websocket.close()
            raise SonioxWebSocketError(f"Failed to send configuration: {e}") from e

        # Create and yield stream
        stream = RealtimeStream(websocket, self.realtime_config)
        try:
            yield stream
        finally:
            stream.close()

    def transcribe_file(
        self,
        file_path: Union[str, Path],
        chunk_size: int = 4096,
    ) -> list[RealtimeResponse]:
        """
        Transcribe an entire audio file.

        Args:
            file_path: Path to audio file
            chunk_size: Size of audio chunks to send

        Returns:
            List of all responses

        Example:
            ```python
            responses = client.transcribe_file("audio.mp3")
            for response in responses:
                for token in response.tokens:
                    if token.is_final:
                        print(token.text, end="")
            ```
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        responses: list[RealtimeResponse] = []

        with self.stream() as stream:
            # Send audio file
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    stream.send_audio(chunk)

            # Collect responses
            for response in stream:
                responses.append(response)

        return responses


# Async version stub (to be implemented)
class AsyncSonioxRealtimeClient:
    """
    Async client for real-time transcription via WebSocket.

    This is the async version of SonioxRealtimeClient.
    Full implementation requires async websockets library.

    Example:
        ```python
        import asyncio
        from soniox import AsyncSonioxRealtimeClient

        async def transcribe():
            client = AsyncSonioxRealtimeClient(api_key="your-api-key")
            async with client.stream() as stream:
                await stream.send_audio(audio_data)
                async for response in stream:
                    print(response.tokens)

        asyncio.run(transcribe())
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "stt-rt-v3",
        audio_format: AudioFormat = AudioFormat.AUTO,
        **realtime_options: Any,
    ) -> None:
        """
        Initialise async real-time client.

        Args:
            api_key: Soniox API key
            model: Real-time model to use
            audio_format: Audio format
            **realtime_options: Additional real-time options
        """
        # Store configuration for when async implementation is added
        self.api_key = api_key
        self.model = model
        self.audio_format = audio_format
        self.realtime_options = realtime_options

        raise NotImplementedError(
            "AsyncSonioxRealtimeClient will be implemented in the next phase. "
            "Use SonioxRealtimeClient for now."
        )

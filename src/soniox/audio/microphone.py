"""Microphone audio capture for real-time transcription.

This module provides cross-platform microphone input support for Soniox
real-time transcription using the sounddevice library.

Audio Format Requirements:
- Sample rate: 16000 Hz (optimal for speech recognition)
- Channels: 1 (mono)
- Format: PCM signed 16-bit little-endian (int16)
- Chunk size: 4096 bytes (256 samples at 16kHz)
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

try:
    import sounddevice as sd
    import numpy as np

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None  # type: ignore
    np = None  # type: ignore

logger = logging.getLogger(__name__)


class MicrophoneCapture:
    """Capture audio from system microphone for real-time transcription.

    This class handles microphone input with automatic conversion to the
    format required by Soniox API (16kHz, mono, PCM_S16LE).

    Example:
        >>> from soniox import SonioxClient
        >>> from soniox.audio import MicrophoneCapture
        >>>
        >>> client = SonioxClient(api_key="your-api-key")
        >>> mic = MicrophoneCapture(sample_rate=16000)
        >>>
        >>> with client.stream() as stream:
        ...     for audio_chunk in mic.capture(duration=10.0):
        ...         stream.send_audio(audio_chunk)
        ...     stream.end_stream()
        ...
        ...     for response in stream:
        ...         print(response.tokens)

    Args:
        sample_rate: Audio sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 for mono)
        chunk_size: Number of samples per chunk (default: 256)
        device: Audio device index (None for default device)

    Raises:
        ImportError: If sounddevice library is not installed
        RuntimeError: If audio device cannot be initialised
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 256,
        device: int | None = None,
    ) -> None:
        """Initialise microphone capture."""
        if not SOUNDDEVICE_AVAILABLE:
            raise ImportError(
                "sounddevice library is required for microphone capture. "
                "Install it with: uv add 'soniox-pro-sdk[microphone]'"
            )

        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device

        # Validate device if specified
        if device is not None:
            try:
                device_info = sd.query_devices(device)
                if device_info["max_input_channels"] < channels:
                    raise ValueError(
                        f"Device {device} has only {device_info['max_input_channels']} "
                        f"input channels, but {channels} requested"
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to query audio device {device}: {e}") from e

        logger.info(
            f"Initialised microphone capture: {sample_rate}Hz, "
            f"{channels} channel(s), chunk_size={chunk_size}"
        )

    def capture(
        self,
        duration: float | None = None,
    ) -> Generator[bytes, None, None]:
        """Capture audio from microphone.

        This method yields audio chunks in the format required by Soniox API:
        PCM signed 16-bit little-endian, at the configured sample rate.

        Args:
            duration: Maximum capture duration in seconds (None for infinite)

        Yields:
            Audio chunks as bytes (PCM_S16LE format)

        Raises:
            RuntimeError: If audio capture fails
        """
        try:
            # Calculate total chunks if duration is specified
            total_chunks = None
            if duration is not None:
                total_chunks = int(duration * self.sample_rate / self.chunk_size)

            chunks_captured = 0

            # Open input stream
            with sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype="int16",
                blocksize=self.chunk_size,
            ) as stream:
                logger.info("Started audio capture")

                while True:
                    # Check if we've reached duration limit
                    if total_chunks is not None and chunks_captured >= total_chunks:
                        break

                    # Read audio chunk
                    audio_data, overflowed = stream.read(self.chunk_size)

                    if overflowed:
                        logger.warning("Audio buffer overflow - some samples may be lost")

                    # Convert numpy array to bytes
                    audio_bytes = audio_data.tobytes()

                    chunks_captured += 1
                    yield audio_bytes

        except Exception as e:
            raise RuntimeError(f"Audio capture failed: {e}") from e
        finally:
            logger.info(f"Stopped audio capture after {chunks_captured} chunks")

    def capture_async(
        self,
        callback: Any,
        duration: float | None = None,
    ) -> None:
        """Capture audio asynchronously with callback.

        This method starts a non-blocking audio stream that calls the
        provided callback function for each audio chunk.

        Args:
            callback: Function to call with each audio chunk (bytes)
            duration: Maximum capture duration in seconds (None for infinite)

        Raises:
            RuntimeError: If audio capture fails
        """
        try:
            chunks_captured = 0
            total_chunks = None
            if duration is not None:
                total_chunks = int(duration * self.sample_rate / self.chunk_size)

            def audio_callback(
                indata: Any,
                frames: int,
                time_info: Any,
                status: Any,
            ) -> None:
                """Process audio chunks in callback."""
                nonlocal chunks_captured

                if status:
                    logger.warning(f"Audio callback status: {status}")

                if total_chunks is not None and chunks_captured >= total_chunks:
                    raise sd.CallbackStop()

                # Convert to bytes and invoke user callback
                audio_bytes = bytes(indata)
                callback(audio_bytes)
                chunks_captured += 1

            # Start stream
            with sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype="int16",
                blocksize=self.chunk_size,
                callback=audio_callback,
            ):
                logger.info("Started async audio capture")

                # Wait for stream to finish
                if duration is not None:
                    sd.sleep(int(duration * 1000))
                else:
                    # Infinite capture - user must stop manually
                    import time
                    while True:
                        time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Audio capture stopped by user")
        except Exception as e:
            raise RuntimeError(f"Async audio capture failed: {e}") from e
        finally:
            logger.info(f"Stopped async audio capture after {chunks_captured} chunks")


def list_audio_devices() -> list[dict[str, Any]]:
    """List all available audio input devices.

    Returns:
        List of device information dictionaries with keys:
        - index: Device index
        - name: Device name
        - channels: Number of input channels
        - sample_rate: Default sample rate

    Raises:
        ImportError: If sounddevice library is not installed

    Example:
        >>> from soniox.audio import list_audio_devices
        >>> devices = list_audio_devices()
        >>> for device in devices:
        ...     print(f"{device['index']}: {device['name']} ({device['channels']} channels)")
    """
    if not SOUNDDEVICE_AVAILABLE:
        raise ImportError(
            "sounddevice library is required for microphone capture. "
            "Install it with: uv add 'soniox-pro-sdk[microphone]'"
        )

    devices = []
    for i, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            devices.append({
                "index": i,
                "name": device["name"],
                "channels": device["max_input_channels"],
                "sample_rate": device["default_samplerate"],
            })

    return devices

"""FastAPI web application for real-time microphone transcription.

This application provides a web interface for testing Soniox real-time
transcription with microphone input.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import select
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel

# Import Soniox SDK (will be available in container)
try:
    from soniox import SonioxRealtimeClient
    from soniox.audio import list_audio_devices
except ImportError:
    # Fallback for development
    SonioxRealtimeClient = None  # type: ignore
    list_audio_devices = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread executor for running sync Soniox client
executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="soniox-")

app = FastAPI(
    title="Soniox Microphone Transcription",
    description="Real-time speech transcription with microphone input",
    version="1.0.0",
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


class TranscriptionConfig(BaseModel):
    """Configuration for transcription session."""

    sample_rate: int = 16000
    language: str = "en"
    enable_speaker_diarization: bool = False


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    """Render main transcription interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Soniox Real-time Transcription"},
    )


@app.get("/api/devices")
async def get_devices() -> dict[str, Any]:
    """Get list of available audio input devices.

    Returns:
        Dictionary with list of audio devices

    Example response:
        {
            "devices": [
                {
                    "index": 0,
                    "name": "Built-in Microphone",
                    "channels": 2,
                    "sample_rate": 44100.0
                }
            ]
        }
    """
    try:
        if list_audio_devices is None:
            return {"devices": [], "error": "Audio library not available"}

        devices = list_audio_devices()
        return {"devices": devices}
    except Exception as e:
        logger.error(f"Failed to list audio devices: {e}")
        return {"devices": [], "error": str(e)}


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    api_key = os.getenv("SONIOX_API_KEY")
    return {
        "status": "healthy",
        "api_key_configured": "yes" if api_key else "no",
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time transcription.

    Protocol:
        Client -> Server: Binary audio data (PCM_S16LE, 16kHz, mono)
        Server -> Client: JSON transcription results

    Message format (Server -> Client):
        {
            "type": "token",
            "text": "transcribed text",
            "is_final": true,
            "confidence": 0.95
        }

        {
            "type": "error",
            "message": "error description"
        }
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        await websocket.send_json({
            "type": "error",
            "message": "SONIOX_API_KEY not configured",
        })
        await websocket.close()
        return

    # Check SDK availability
    if SonioxRealtimeClient is None:
        await websocket.send_json({
            "type": "error",
            "message": "Soniox SDK not available",
        })
        await websocket.close()
        return

    # Queues for communication between async and sync code
    audio_queue: Queue[bytes | None] = Queue()
    token_queue: Queue[dict[str, Any] | None] = Queue()
    error_occurred = asyncio.Event()

    def sync_stream_handler() -> None:
        """Run sync Soniox client in separate thread."""
        try:
            # Create real-time client
            client = SonioxRealtimeClient(
                api_key=api_key,
                model="stt-rt-v3",
                audio_format="pcm_s16le",
                sample_rate=16000,
                num_channels=1,
            )

            logger.info("Starting Soniox real-time stream in thread")

            # Start real-time stream
            with client.stream() as stream:
                # Signal ready
                token_queue.put({"type": "ready"})

                # Process audio and responses simultaneously
                while not error_occurred.is_set():
                    # Check for audio data (non-blocking with timeout)
                    try:
                        audio_data = audio_queue.get(timeout=0.1)

                        # None signals end of stream
                        if audio_data is None:
                            logger.info("Received end signal, closing stream")
                            stream.end_stream()
                            break

                        # Send audio to Soniox
                        stream.send_audio(audio_data)

                    except Empty:
                        # No audio data available, continue to check for responses
                        pass

                    # Check for transcription responses (non-blocking)
                    try:
                        # Manually receive from WebSocket without using iterator
                        # This avoids triggering the __iter__ finally block

                        # Check if data is available (non-blocking)
                        if stream.websocket.socket and select.select([stream.websocket.socket], [], [], 0)[0]:
                            message = stream.websocket.recv()

                            if message and isinstance(message, str):
                                response_data = json.loads(message)

                                # Handle response
                                if "tokens" in response_data:
                                    for token_data in response_data["tokens"]:
                                        token_queue.put({
                                            "type": "token",
                                            "text": token_data.get("text", ""),
                                            "is_final": token_data.get("is_final", False),
                                            "confidence": token_data.get("confidence"),
                                        })

                                # Check for errors
                                if response_data.get("status") == "error":
                                    error_msg = response_data.get("message", "Unknown error")
                                    raise Exception(f"Soniox error: {error_msg}")

                    except Exception as e:
                        # Only log if it's not just "no data available"
                        if "timed out" not in str(e).lower():
                            logger.debug(f"Response check: {e}")
                        pass

                logger.info("Soniox stream closed")

        except Exception as e:
            logger.error(f"Error in sync stream handler: {e}")
            token_queue.put({
                "type": "error",
                "message": str(e),
            })
            error_occurred.set()

    # Start sync handler in thread
    loop = asyncio.get_event_loop()
    stream_future = loop.run_in_executor(executor, sync_stream_handler)

    try:
        # Receive audio from browser
        async def receive_audio() -> None:
            """Receive audio from browser WebSocket and queue it."""
            try:
                while True:
                    audio_data = await websocket.receive_bytes()
                    audio_queue.put(audio_data)

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                audio_queue.put(None)  # Signal end of stream
            except Exception as e:
                logger.error(f"Error receiving audio: {e}")
                audio_queue.put(None)
                error_occurred.set()

        # Send tokens to browser
        async def send_tokens() -> None:
            """Send transcription tokens to browser WebSocket."""
            try:
                while True:
                    # Check queue with timeout to allow clean shutdown
                    await asyncio.sleep(0.01)  # Small delay to prevent busy-waiting

                    # Get all available tokens
                    while not token_queue.empty():
                        try:
                            token = token_queue.get_nowait()

                            # None signals end
                            if token is None:
                                return

                            await websocket.send_json(token)

                            # If error occurred, stop
                            if token.get("type") == "error":
                                error_occurred.set()
                                return

                        except Empty:
                            break

                    # Stop if error occurred or stream ended
                    if error_occurred.is_set():
                        return

            except Exception as e:
                logger.error(f"Error sending tokens: {e}")
                error_occurred.set()

        # Run both tasks concurrently
        await asyncio.gather(
            receive_audio(),
            send_tokens(),
            return_exceptions=True,
        )

        # Wait for thread to complete
        await stream_future

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except:
            pass  # Ignore if websocket already closed

    finally:
        error_occurred.set()
        try:
            # Only close if not already closed
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
        except Exception:
            pass  # Ignore errors when closing
        logger.info("WebSocket connection closed")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )

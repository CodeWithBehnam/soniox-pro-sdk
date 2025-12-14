#!/usr/bin/env python3
"""
Example: Real-time Transcription

This example demonstrates real-time transcription using WebSocket streaming.
"""

import os
import sys
from pathlib import Path

from soniox import SonioxRealtimeClient
from soniox.types import AudioFormat


def main() -> None:
    """Run real-time transcription example."""
    # Get API key
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY environment variable not set")
        sys.exit(1)

    # Check if audio file provided
    if len(sys.argv) < 2:
        print("Usage: python realtime_transcription.py <audio-file>")
        sys.exit(1)

    audio_file = Path(sys.argv[1])
    if not audio_file.exists():
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)

    # Create real-time client
    print("Initialising real-time client...")
    client = SonioxRealtimeClient(
        api_key=api_key,
        model="stt-rt-v3",
        audio_format=AudioFormat.AUTO,
        enable_speaker_diarization=True,
        enable_language_identification=True,
        enable_endpoint_detection=True,
    )

    print(f"Streaming {audio_file.name}...\n")
    print("=" * 60)

    # Stream audio and receive tokens
    with client.stream() as stream:
        # Send audio file in chunks
        with open(audio_file, "rb") as f:
            while chunk := f.read(4096):
                stream.send_audio(chunk)

        # Receive and print tokens
        current_speaker = None
        for response in stream:
            for token in response.tokens:
                # Handle speaker changes
                if token.speaker and token.speaker != current_speaker:
                    current_speaker = token.speaker
                    print(f"\n\nSpeaker {current_speaker}:", end=" ")

                # Print final tokens only
                if token.is_final:
                    print(token.text, end="")

    print("\n" + "=" * 60)
    print("\nReal-time transcription complete!")


if __name__ == "__main__":
    main()

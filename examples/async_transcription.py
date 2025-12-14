#!/usr/bin/env python3
"""
Example: Async Transcription from File

This example demonstrates how to upload a file and transcribe it
using the async transcription API.
"""

import os
import sys
from pathlib import Path

from soniox import SonioxClient


def main() -> None:
    """Run async transcription example."""
    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY environment variable not set")
        sys.exit(1)

    # Check if audio file provided
    if len(sys.argv) < 2:
        print("Usage: python async_transcription.py <audio-file>")
        sys.exit(1)

    audio_file = Path(sys.argv[1])
    if not audio_file.exists():
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)

    # Create client
    print("Initialising Soniox client...")
    client = SonioxClient(api_key=api_key)

    try:
        # Upload file
        print(f"Uploading {audio_file.name}...")
        file = client.files.upload(audio_file)
        print(f"✓ Uploaded: {file.id}")

        # Create transcription
        print("Creating transcription...")
        transcription = client.transcriptions.create(
            file_id=file.id,
            model="stt-async-v3",
            enable_speaker_diarization=True,
            enable_language_identification=True,
        )
        print(f"✓ Transcription created: {transcription.id}")

        # Wait for completion
        print("Waiting for transcription to complete...")
        result = client.transcriptions.wait_for_completion(
            transcription.id, timeout=300
        )

        # Print results
        print("\n" + "=" * 60)
        print("TRANSCRIPT")
        print("=" * 60)
        print(result.transcript.text)
        print("=" * 60)

        # Print detailed tokens with speakers
        if result.transcript.tokens:
            print("\nDETAILED OUTPUT:")
            current_speaker = None
            for token in result.transcript.tokens:
                if token.speaker and token.speaker != current_speaker:
                    current_speaker = token.speaker
                    print(f"\n\nSpeaker {current_speaker}:", end="")
                print(token.text, end="")

        print("\n\nTranscription complete!")

    finally:
        client.close()


if __name__ == "__main__":
    main()

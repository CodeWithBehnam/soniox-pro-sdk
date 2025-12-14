#!/usr/bin/env python3
"""Test script to transcribe audio files using Soniox SDK."""

import os
from pathlib import Path

from soniox import SonioxRealtimeClient


def transcribe_file(file_path: str) -> str:
    """
    Transcribe an audio file using Soniox real-time API.

    Args:
        file_path: Path to the audio file

    Returns:
        Transcribed text
    """
    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise ValueError("SONIOX_API_KEY environment variable not set")

    # Create real-time client
    client = SonioxRealtimeClient(
        api_key=api_key,
        model="stt-rt-v3",
        audio_format="auto",  # Auto-detect format from file
    )

    print(f"\n{'='*60}")
    print(f"Transcribing: {file_path}")
    print(f"{'='*60}\n")

    # Transcribe the file
    transcription_parts = []

    try:
        responses = client.transcribe_file(file_path, chunk_size=4096)

        # Collect all final tokens
        for response in responses:
            for token in response.tokens:
                if token.is_final:
                    transcription_parts.append(token.text)
                    print(f"[FINAL] {token.text}")
                else:
                    print(f"[PARTIAL] {token.text}", end="\r")

        # Combine all parts
        full_transcription = " ".join(transcription_parts)

        print(f"\n\n{'='*60}")
        print("FULL TRANSCRIPTION:")
        print(f"{'='*60}")
        print(full_transcription)
        print(f"{'='*60}\n")

        return full_transcription

    except Exception as e:
        print(f"\n❌ Error transcribing {file_path}: {e}")
        raise


def main():
    """Test transcription with both test files."""
    test_files = [
        "tests/test1.mp3",
        "tests/test2.mp3",
    ]

    results = {}

    for test_file in test_files:
        if Path(test_file).exists():
            try:
                transcription = transcribe_file(test_file)
                results[test_file] = transcription
            except Exception as e:
                print(f"Failed to transcribe {test_file}: {e}")
                results[test_file] = None
        else:
            print(f"⚠️  File not found: {test_file}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for file_path, transcription in results.items():
        status = "✅ SUCCESS" if transcription else "❌ FAILED"
        print(f"\n{status}: {file_path}")
        if transcription:
            # Show first 100 characters
            preview = transcription[:100] + "..." if len(transcription) > 100 else transcription
            print(f"Preview: {preview}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Example: Real-time Translation

This example demonstrates real-time two-way translation between languages.
"""

import os
import sys
from pathlib import Path

from soniox import SonioxRealtimeClient
from soniox.types import AudioFormat, TwoWayTranslationConfig


def main() -> None:
    """Run real-time translation example."""
    # Get API key
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        print("Error: SONIOX_API_KEY environment variable not set")
        sys.exit(1)

    # Check if audio file provided
    if len(sys.argv) < 2:
        print("Usage: python translation_example.py <audio-file>")
        sys.exit(1)

    audio_file = Path(sys.argv[1])
    if not audio_file.exists():
        print(f"Error: File not found: {audio_file}")
        sys.exit(1)

    # Create client with translation
    print("Initialising real-time client with translation...")
    client = SonioxRealtimeClient(
        api_key=api_key,
        model="stt-rt-v3",
        audio_format=AudioFormat.AUTO,
        enable_language_identification=True,
        translation=TwoWayTranslationConfig(
            language_a="en",  # English
            language_b="es",  # Spanish
        ),
    )

    print(f"Streaming {audio_file.name} with translation...\n")
    print("=" * 60)

    # Stream and translate
    with client.stream() as stream:
        with open(audio_file, "rb") as f:
            while chunk := f.read(4096):
                stream.send_audio(chunk)

        # Receive tokens
        for response in stream:
            for token in response.tokens:
                if token.is_final:
                    # Display original and translation
                    if token.translation_status == "original":
                        print(f"\n[Original {token.language}] {token.text}", end="")
                    elif token.translation_status == "translation":
                        print(f"\n[Translation {token.language}] {token.text}", end="")
                    else:
                        print(f"\n[{token.language}] {token.text}", end="")

    print("\n" + "=" * 60)
    print("\nTranslation complete!")


if __name__ == "__main__":
    main()

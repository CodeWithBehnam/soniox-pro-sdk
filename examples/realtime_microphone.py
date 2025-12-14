#!/usr/bin/env python3
"""Real-time transcription from microphone input.

This example demonstrates how to use the Soniox SDK with microphone input
for real-time speech-to-text transcription.

Requirements:
    uv add "soniox-pro-sdk[microphone]"

Usage:
    # List available microphones
    uv run examples/realtime_microphone.py --list-devices

    # Transcribe with default microphone
    uv run examples/realtime_microphone.py

    # Transcribe with specific microphone (by index)
    uv run examples/realtime_microphone.py --device 1

    # Transcribe for 30 seconds
    uv run examples/realtime_microphone.py --duration 30

Environment:
    SONIOX_API_KEY: Your Soniox API key (required)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add src directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from soniox import SonioxClient
from soniox.audio import MicrophoneCapture, list_audio_devices


def list_devices() -> None:
    """List all available audio input devices."""
    try:
        devices = list_audio_devices()

        if not devices:
            print("No microphones found on your system.")
            return

        print("\n🎤 Available Audio Input Devices:\n")
        print(f"{'Index':<6} {'Device Name':<50} {'Channels':<10} {'Sample Rate'}")
        print("-" * 85)

        for device in devices:
            print(
                f"{device['index']:<6} "
                f"{device['name']:<50} "
                f"{device['channels']:<10} "
                f"{device['sample_rate']:.0f} Hz"
            )

        print(f"\nTotal: {len(devices)} device(s)")

    except ImportError as e:
        print(f"Error: {e}")
        print("\nPlease install microphone support:")
        print('  uv add "soniox-pro-sdk[microphone]"')
        sys.exit(1)


def transcribe_microphone(
    api_key: str,
    device: int | None = None,
    duration: float | None = None,
    sample_rate: int = 16000,
) -> None:
    """Transcribe audio from microphone in real-time.

    Args:
        api_key: Soniox API key
        device: Audio device index (None for default)
        duration: Recording duration in seconds (None for continuous)
        sample_rate: Audio sample rate in Hz
    """
    try:
        # Initialise Soniox client
        print("🔧 Initialising Soniox client...")
        client = SonioxClient(api_key=api_key)

        # Initialise microphone capture
        print(f"🎤 Setting up microphone (device: {device or 'default'})...")
        mic = MicrophoneCapture(
            sample_rate=sample_rate,
            channels=1,
            device=device,
        )

        # Start real-time stream
        print("🌐 Connecting to Soniox real-time API...")
        with client.stream() as stream:
            print("\n" + "=" * 70)
            print("🔴 RECORDING - Speak into your microphone")
            if duration:
                print(f"⏱️  Duration: {duration} seconds")
            else:
                print("⏱️  Duration: Continuous (press Ctrl+C to stop)")
            print("=" * 70 + "\n")

            try:
                # Capture and send audio chunks
                for audio_chunk in mic.capture(duration=duration):
                    stream.send_audio(audio_chunk)

                    # Check for transcription responses (non-blocking)
                    # Note: In production, you'd use threading or async for this
                    # This is a simplified example

            except KeyboardInterrupt:
                print("\n\n⏹️  Stopping recording...")

            # End stream and get final results
            stream.end_stream()

            print("\n📝 Transcription Results:\n")
            print("-" * 70)

            full_transcript = []
            for response in stream:
                for token in response.tokens:
                    # Print tokens as they arrive
                    if token.is_final:
                        print(f"✓ {token.text}", end=" ", flush=True)
                        full_transcript.append(token.text)
                    else:
                        print(f"  {token.text}", end="\r", flush=True)

            print("\n" + "-" * 70)
            print("\n📋 Full Transcript:")
            print(" ".join(full_transcript))
            print()

    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease install microphone support:")
        print('  uv add "soniox-pro-sdk[microphone]"')
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real-time transcription from microphone input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )

    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio device index (use --list-devices to see available devices)",
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Recording duration in seconds (default: continuous)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        choices=[8000, 16000, 44100, 48000],
        help="Audio sample rate in Hz (default: 16000)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Soniox API key (default: from SONIOX_API_KEY environment variable)",
    )

    args = parser.parse_args()

    # List devices and exit
    if args.list_devices:
        list_devices()
        return

    # Get API key
    api_key = args.api_key or os.getenv("SONIOX_API_KEY")
    if not api_key:
        print("❌ Error: SONIOX_API_KEY not set")
        print("\nSet your API key:")
        print("  export SONIOX_API_KEY='your-api-key'")
        print("\nOr pass it as an argument:")
        print("  uv run examples/realtime_microphone.py --api-key 'your-api-key'")
        sys.exit(1)

    # Start transcription
    transcribe_microphone(
        api_key=api_key,
        device=args.device,
        duration=args.duration,
        sample_rate=args.sample_rate,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Command-line interface for the Soniox Pro SDK.

This module provides a simple CLI for common operations.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from soniox import SonioxClient, SonioxRealtimeClient
from soniox.config import SonioxConfig


def transcribe_command(args: argparse.Namespace) -> None:
    """Handle transcribe command."""
    config = SonioxConfig.from_env()
    client = SonioxClient(config=config)

    try:
        # Upload file if needed
        file_id = args.file_id
        if not file_id:
            print(f"Uploading {args.audio}...")
            file = client.files.upload(args.audio)
            file_id = file.id
            print(f"✓ Uploaded: {file_id}")

        # Create transcription
        print("Creating transcription...")
        transcription = client.transcriptions.create(
            file_id=file_id,
            model=args.model,
            enable_speaker_diarization=args.diarization,
            enable_language_identification=args.language_id,
        )
        print(f"✓ Transcription ID: {transcription.id}")

        # Wait for completion
        if args.wait:
            print("Waiting for completion...")
            result = client.transcriptions.wait_for_completion(transcription.id)
            print("\n" + "=" * 60)
            print(result.transcript.text)
            print("=" * 60)

    finally:
        client.close()


def realtime_command(args: argparse.Namespace) -> None:
    """Handle realtime command."""
    config = SonioxConfig.from_env()
    client = SonioxRealtimeClient(
        config=config,
        model=args.model,
        enable_speaker_diarization=args.diarization,
        enable_language_identification=args.language_id,
    )

    print(f"Streaming {args.audio}...")
    print("=" * 60)

    with client.stream() as stream:
        with open(args.audio, "rb") as f:
            while chunk := f.read(4096):
                stream.send_audio(chunk)

        for response in stream:
            for token in response.tokens:
                if token.is_final:
                    print(token.text, end="")

    print("\n" + "=" * 60)


def files_command(args: argparse.Namespace) -> None:
    """Handle files command."""
    config = SonioxConfig.from_env()
    client = SonioxClient(config=config)

    try:
        if args.list:
            files = client.files.list(limit=args.limit)
            print(f"Found {files.total} files:")
            for file in files.files:
                print(f"  {file.id}: {file.name} ({file.size_bytes} bytes)")

        elif args.delete:
            client.files.delete(args.delete)
            print(f"✓ Deleted file: {args.delete}")

    finally:
        client.close()


def models_command(args: argparse.Namespace) -> None:
    """Handle models command."""
    config = SonioxConfig.from_env()
    client = SonioxClient(config=config)

    try:
        models = client.models.list()
        print(f"Available models ({len(models.models)}):")
        for model in models.models:
            print(f"\n  {model.id}")
            print(f"    Type: {model.type}")
            print(f"    Languages: {', '.join(model.languages[:5])}...")

    finally:
        client.close()


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Soniox Pro SDK Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Transcribe command
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe audio file")
    transcribe_parser.add_argument("audio", type=Path, help="Path to audio file")
    transcribe_parser.add_argument("--model", default="stt-async-v3", help="Model to use")
    transcribe_parser.add_argument("--file-id", help="Use existing uploaded file")
    transcribe_parser.add_argument("--diarization", action="store_true", help="Enable speaker diarization")
    transcribe_parser.add_argument("--language-id", action="store_true", help="Enable language identification")
    transcribe_parser.add_argument("--wait", action="store_true", help="Wait for completion")

    # Realtime command
    realtime_parser = subparsers.add_parser("realtime", help="Real-time transcription")
    realtime_parser.add_argument("audio", type=Path, help="Path to audio file")
    realtime_parser.add_argument("--model", default="stt-rt-v3", help="Model to use")
    realtime_parser.add_argument("--diarization", action="store_true", help="Enable speaker diarization")
    realtime_parser.add_argument("--language-id", action="store_true", help="Enable language identification")

    # Files command
    files_parser = subparsers.add_parser("files", help="Manage files")
    files_parser.add_argument("--list", action="store_true", help="List files")
    files_parser.add_argument("--delete", help="Delete file by ID")
    files_parser.add_argument("--limit", type=int, default=100, help="Limit for list")

    # Models command
    subparsers.add_parser("models", help="List available models")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == "transcribe":
            transcribe_command(args)
        elif args.command == "realtime":
            realtime_command(args)
        elif args.command == "files":
            files_command(args)
        elif args.command == "models":
            models_command(args)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

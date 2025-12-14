#!/usr/bin/env python3
"""Test script to transcribe audio files using Soniox async API."""

import logging
import os
import time
from pathlib import Path

from soniox import SonioxClient

# Enable logging
logging.basicConfig(level=logging.INFO)


def transcribe_file_async(file_path: str) -> str:
    """
    Transcribe an audio file using Soniox async API.

    Args:
        file_path: Path to the audio file

    Returns:
        Transcribed text
    """
    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise ValueError("SONIOX_API_KEY environment variable not set")

    # Create client
    client = SonioxClient(api_key=api_key)
    print(f"API Base URL: {client.config.api_base_url}")

    print(f"\n{'='*60}")
    print(f"Transcribing: {file_path}")
    print(f"{'='*60}\n")

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Step 1: Upload file
        print("📤 Uploading file...")
        try:
            upload_response = client.files.upload(file_path)
            file_id = upload_response.id
            print(f"✅ File uploaded: {file_id}")
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise

        # Step 2: Create transcription
        print("🎙️  Creating transcription job...")
        transcription = client.transcriptions.create(
            file_id=file_id,
            model="stt-async-v3",  # Use async model for file transcription
        )
        transcription_id = transcription.id
        print(f"✅ Transcription job created: {transcription_id}")

        # Step 3: Poll for completion
        print("⏳ Waiting for transcription to complete...")
        max_attempts = 60  # 60 seconds timeout
        attempt = 0

        while attempt < max_attempts:
            transcription = client.transcriptions.get(transcription_id)
            status = transcription.status

            if status == "completed":
                print(f"✅ Transcription completed!")
                break
            elif status == "failed":
                error_msg = getattr(transcription, "error", "Unknown error")
                raise Exception(f"Transcription failed: {error_msg}")
            else:
                print(f"⏳ Status: {status} (attempt {attempt + 1}/{max_attempts})")
                time.sleep(1)
                attempt += 1

        if attempt >= max_attempts:
            raise TimeoutError("Transcription timed out")

        # Step 4: Get transcription result with transcript
        print("📥 Fetching transcription result...")
        result = client.transcriptions.get_result(transcription_id)

        if result.transcript:
            full_text = result.transcript.text

            print(f"\n\n{'='*60}")
            print("FULL TRANSCRIPTION:")
            print(f"{'='*60}")
            print(full_text)
            print(f"{'='*60}\n")

            # Show word-level details if available
            if result.transcript.tokens:
                print(f"\n📊 Token count: {len(result.transcript.tokens)}")
                print(f"📊 First 5 tokens:")
                for i, token in enumerate(result.transcript.tokens[:5]):
                    confidence = getattr(token, "confidence", None)
                    conf_str = f" (confidence: {confidence:.2f})" if confidence else ""
                    print(f"  {i+1}. {token.text}{conf_str}")

            return full_text
        else:
            print("⚠️  No transcript available")
            return ""

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
                transcription = transcribe_file_async(test_file)
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
            print(f"Length: {len(transcription)} characters")


if __name__ == "__main__":
    main()

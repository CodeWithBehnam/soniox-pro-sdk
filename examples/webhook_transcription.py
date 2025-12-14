#!/usr/bin/env python3
"""
Example: Async transcription with webhooks.

This example demonstrates how to use webhooks with the Soniox SDK
to receive automatic notifications when transcriptions complete.

For local development, you'll need a tool like ngrok or cloudflared
to expose your webhook endpoint to the internet.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from soniox import SonioxClient, WebhookPayload

# Initialize FastAPI app for webhook endpoint
app = FastAPI()

# Store completed transcriptions (in production, use a database)
completed_transcriptions = {}


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle webhook callbacks from Soniox.

    This endpoint receives notifications when transcriptions complete.
    """
    # Parse webhook payload
    payload_data = await request.json()
    payload = WebhookPayload(**payload_data)

    print(f"\n📨 Webhook received:")
    print(f"  Transcription ID: {payload.id}")
    print(f"  Status: {payload.status}")

    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        print("⚠️  SONIOX_API_KEY not configured")
        return {"status": "error", "message": "API key not configured"}

    # Fetch the transcription result
    try:
        client = SonioxClient(api_key=api_key)

        if payload.status == "completed":
            result = client.transcriptions.get_result(payload.id)

            if result.transcript:
                print(f"\n✅ Transcription completed!")
                print(f"📝 Text: {result.transcript.text[:100]}...")

                # Store result (in production, save to database)
                completed_transcriptions[payload.id] = result.transcript.text
            else:
                print("⚠️  No transcript available")

        elif payload.status == "error":
            transcription = client.transcriptions.get(payload.id)
            error_msg = transcription.error_message or "Unknown error"
            print(f"❌ Transcription failed: {error_msg}")

        return {"status": "success"}

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


def start_transcription_with_webhook(
    file_path: str,
    webhook_url: str,
    auth_token: str | None = None,
) -> str:
    """
    Start an async transcription with webhook notification.

    Args:
        file_path: Path to audio file
        webhook_url: URL where webhooks will be sent
        auth_token: Optional authentication token

    Returns:
        Transcription ID
    """
    # Get API key from environment
    api_key = os.getenv("SONIOX_API_KEY")
    if not api_key:
        raise ValueError("SONIOX_API_KEY environment variable not set")

    client = SonioxClient(api_key=api_key)

    print(f"\n{'='*60}")
    print(f"Starting transcription with webhook")
    print(f"{'='*60}\n")

    # Upload file
    print(f"📤 Uploading file: {file_path}")
    file = client.files.upload(file_path)
    print(f"✅ File uploaded: {file.id}")

    # Create transcription with webhook
    print(f"🎙️  Creating transcription with webhook...")
    print(f"📍 Webhook URL: {webhook_url}")

    # Build transcription request
    kwargs = {
        "file_id": file.id,
        "model": "stt-async-v3",
        "webhook_url": webhook_url,
    }

    # Add authentication if provided
    if auth_token:
        kwargs["webhook_auth_header_name"] = "Authorization"
        kwargs["webhook_auth_header_value"] = f"Bearer {auth_token}"
        print(f"🔐 Authentication: Enabled")

    transcription = client.transcriptions.create(**kwargs)

    print(f"✅ Transcription job created: {transcription.id}")
    print(f"\n⏳ Waiting for webhook notification...")
    print(f"   (Soniox will POST to {webhook_url} when complete)\n")

    return transcription.id


def main():
    """
    Example usage.

    To run this example:
    1. Set SONIOX_API_KEY environment variable
    2. Expose webhook endpoint using ngrok or cloudflared:
       ngrok http 8000
    3. Use the ngrok URL as webhook_url
    4. Run this script
    5. In another terminal, run: uvicorn examples.webhook_transcription:app --port 8000
    """
    # Example file
    file_path = "tests/test1.mp3"

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        print("Please provide a valid audio file path")
        return

    # Webhook URL (replace with your ngrok/cloudflared URL)
    webhook_url = os.getenv("WEBHOOK_URL", "https://your-ngrok-url.ngrok.io/webhook")

    # Optional: Add authentication token
    auth_token = os.getenv("WEBHOOK_AUTH_TOKEN")

    try:
        transcription_id = start_transcription_with_webhook(
            file_path=file_path,
            webhook_url=webhook_url,
            auth_token=auth_token,
        )

        print(f"\n{'='*60}")
        print(f"Transcription started successfully!")
        print(f"{'='*60}")
        print(f"Transcription ID: {transcription_id}")
        print(f"\nYour webhook endpoint will receive a POST request when complete.")
        print(f"\nTo check status manually:")
        print(f"  client.transcriptions.get('{transcription_id}')")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Check if running as webhook server or starting transcription
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Run FastAPI server
        import uvicorn

        print("🚀 Starting webhook server on http://localhost:8000")
        print("   Webhook endpoint: http://localhost:8000/webhook\n")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Start transcription with webhook
        main()

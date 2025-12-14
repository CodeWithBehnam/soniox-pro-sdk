# Webhook Guide - Soniox Pro SDK

Complete guide to using webhooks for asynchronous transcription notifications with the Soniox Pro SDK.

## Table of Contents

- [Overview](#overview)
- [How Webhooks Work](#how-webhooks-work)
- [Quick Start](#quick-start)
- [Webhook Payload](#webhook-payload)
- [Authentication](#authentication)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Complete Examples](#complete-examples)

---

## Overview

Webhooks enable fully asynchronous transcription workflows. Instead of polling the API to check transcription status, Soniox automatically notifies your application when a transcription completes or fails.

### Benefits

- **No Polling**: Eliminate the need to repeatedly check transcription status
- **Real-Time Notifications**: Receive immediate callbacks when transcriptions finish
- **Scalable**: Handle thousands of concurrent transcriptions without overhead
- **Simple Integration**: Standard HTTP POST requests to your endpoint

---

## How Webhooks Work

```
1. Your App                  2. Soniox API               3. Your Webhook Endpoint
    │                              │                              │
    │ Create transcription         │                              │
    │ with webhook_url ────────────►                              │
    │                              │                              │
    │ Returns transcription_id     │                              │
    │◄──────────────────────────── │                              │
    │                              │                              │
    │                              │ Processes audio              │
    │                              │ in background                │
    │                              │                              │
    │                              │ POST /webhook                │
    │                              │ {id, status} ───────────────►│
    │                              │                              │
    │                              │                         200 OK
    │                              │◄──────────────────────────── │
```

**Workflow:**

1. **Create Transcription**: Start a transcription job with `webhook_url` parameter
2. **Background Processing**: Soniox processes the audio asynchronously
3. **Webhook Notification**: When complete, Soniox POSTs to your webhook URL
4. **Fetch Result**: Your endpoint retrieves the full transcription using the ID

---

## Quick Start

### 1. Create Transcription with Webhook

```python
from soniox import SonioxClient

client = SonioxClient(api_key="your-api-key")

# Upload file
file = client.files.upload("audio.mp3")

# Create transcription with webhook
transcription = client.transcriptions.create(
    file_id=file.id,
    model="stt-async-v3",
    webhook_url="https://your-domain.com/webhook",  # Your webhook endpoint
)

print(f"Transcription started: {transcription.id}")
```

### 2. Create Webhook Endpoint

```python
from fastapi import FastAPI, Request
from soniox import SonioxClient, WebhookPayload

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Parse webhook payload
    payload_data = await request.json()
    payload = WebhookPayload(**payload_data)

    if payload.status == "completed":
        # Fetch full transcription result
        client = SonioxClient(api_key="your-api-key")
        result = client.transcriptions.get_result(payload.id)

        print(f"Transcript: {result.transcript.text}")

    return {"status": "success"}
```

### 3. Run Webhook Server

```bash
uvicorn your_app:app --port 8000
```

---

## Webhook Payload

When a transcription completes or fails, Soniox sends a POST request to your webhook URL with the following JSON payload:

```json
{
  "id": "548d023b-2b3d-4dc2-a3ef-cca26d05fd9a",
  "status": "completed"
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | The transcription ID |
| `status` | string | Either `"completed"` or `"error"` |

### Parsing the Payload

```python
from soniox import WebhookPayload

# Option 1: Manual parsing
payload = WebhookPayload(**request_json)

# Option 2: Pydantic validation
try:
    payload = WebhookPayload.model_validate(request_json)
except ValidationError as e:
    print(f"Invalid payload: {e}")
```

### Handling Different Statuses

```python
@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = WebhookPayload(**await request.json())
    client = SonioxClient(api_key="your-api-key")

    if payload.status == "completed":
        # Success - fetch result
        result = client.transcriptions.get_result(payload.id)
        print(f"✅ Completed: {result.transcript.text}")

    elif payload.status == "error":
        # Failure - get error details
        transcription = client.transcriptions.get(payload.id)
        print(f"❌ Failed: {transcription.error_message}")

    return {"status": "success"}
```

---

## Authentication

Secure your webhook endpoint by requiring authentication headers.

### Setting Up Authentication

```python
transcription = client.transcriptions.create(
    file_id=file.id,
    model="stt-async-v3",
    webhook_url="https://your-domain.com/webhook",

    # Authentication
    webhook_auth_header_name="Authorization",
    webhook_auth_header_value="Bearer your-secret-token",
)
```

### Verifying Authentication

```python
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

SECRET_TOKEN = "your-secret-token"

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Verify authorization header
    auth_header = request.headers.get("Authorization")

    if auth_header != f"Bearer {SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Process webhook
    payload = WebhookPayload(**await request.json())
    # ... handle payload ...

    return {"status": "success"}
```

### Custom Authentication Headers

You can use any header name and value:

```python
# API Key authentication
webhook_auth_header_name="X-API-Key"
webhook_auth_header_value="your-api-key"

# Custom secret
webhook_auth_header_name="X-Webhook-Secret"
webhook_auth_header_value="your-webhook-secret"
```

---

## Local Development

For local development, you need to expose your local server to the internet so Soniox can reach your webhook endpoint.

### Option 1: Cloudflare Tunnel (Recommended)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Start tunnel
cloudflared tunnel --url http://localhost:8000

# Output: https://random-url.trycloudflare.com
```

Use the generated URL as your `webhook_url`:

```python
webhook_url="https://random-url.trycloudflare.com/webhook"
```

### Option 2: ngrok

```bash
# Install ngrok
brew install ngrok

# Start tunnel
ngrok http 8000

# Output: https://abc123.ngrok.io
```

Use the ngrok URL:

```python
webhook_url="https://abc123.ngrok.io/webhook"
```

### Option 3: VS Code Port Forwarding

If using VS Code:

1. Open the **Ports** panel
2. Forward port 8000
3. Right-click → **Port Visibility** → **Public**
4. Copy the forwarded URL

### Complete Local Development Example

```python
# 1. Start your webhook server
# In terminal 1:
uvicorn your_app:app --port 8000

# 2. Expose with cloudflared
# In terminal 2:
cloudflared tunnel --url http://localhost:8000
# Copy the https://xxx.trycloudflare.com URL

# 3. Start transcription with webhook
# In terminal 3 or Python:
from soniox import SonioxClient

client = SonioxClient(api_key="your-api-key")
file = client.files.upload("audio.mp3")

transcription = client.transcriptions.create(
    file_id=file.id,
    model="stt-async-v3",
    webhook_url="https://xxx.trycloudflare.com/webhook",  # Your tunnel URL
)

# Watch terminal 1 for webhook notifications!
```

---

## Production Deployment

### Webhook Endpoint Requirements

- **HTTPS Required**: Webhook URL must use HTTPS (HTTP not supported)
- **Public Access**: Endpoint must be publicly accessible from Soniox servers
- **Fast Response**: Respond quickly (within 10 seconds) to avoid timeouts
- **Idempotency**: Handle duplicate webhook deliveries gracefully

### Production-Ready Endpoint

```python
from fastapi import FastAPI, Request, BackgroundTasks
from soniox import SonioxClient, WebhookPayload
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

# Track processed webhooks (use Redis/database in production)
processed_webhooks = set()


async def process_transcription(transcription_id: str):
    """Process transcription in background to avoid blocking webhook response."""
    try:
        client = SonioxClient(api_key="your-api-key")
        result = client.transcriptions.get_result(transcription_id)

        # Save to database, send notifications, etc.
        # ... your business logic ...

        logger.info(f"Processed transcription {transcription_id}")

    except Exception as e:
        logger.error(f"Failed to process transcription {transcription_id}: {e}")


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Production webhook handler with:
    - Authentication
    - Idempotency
    - Background processing
    - Error handling
    """
    # 1. Verify authentication
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {os.getenv('WEBHOOK_SECRET')}":
        logger.warning("Unauthorized webhook attempt")
        return {"status": "error", "message": "Unauthorized"}, 401

    # 2. Parse payload
    try:
        payload = WebhookPayload(**await request.json())
    except Exception as e:
        logger.error(f"Invalid payload: {e}")
        return {"status": "error", "message": "Invalid payload"}, 400

    # 3. Check idempotency (prevent duplicate processing)
    if payload.id in processed_webhooks:
        logger.info(f"Duplicate webhook for {payload.id}, skipping")
        return {"status": "success", "message": "Already processed"}

    # 4. Mark as processed immediately
    processed_webhooks.add(payload.id)

    # 5. Process in background (don't block webhook response)
    if payload.status == "completed":
        background_tasks.add_task(process_transcription, payload.id)

    # 6. Respond quickly
    return {"status": "success"}
```

### Deployment Platforms

#### AWS Lambda + API Gateway

```python
# lambda_function.py
from mangum import Mangum
from your_app import app

handler = Mangum(app)
```

#### Google Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/webhook-handler', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/webhook-handler']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'gcloud'
      - 'run'
      - 'deploy'
      - 'webhook-handler'
      - '--image=gcr.io/$PROJECT_ID/webhook-handler'
      - '--region=us-central1'
```

#### Heroku

```bash
# Deploy
git push heroku main

# Get webhook URL
heroku apps:info
# Use: https://your-app.herokuapp.com/webhook
```

---

## Error Handling

### Failed Webhook Delivery

If webhook delivery fails, Soniox automatically retries multiple times. If all retries fail, you can still retrieve results manually:

```python
# Fallback: Poll for results if webhook fails
import time

transcription_id = "abc-123"

while True:
    transcription = client.transcriptions.get(transcription_id)

    if transcription.status == "completed":
        result = client.transcriptions.get_result(transcription_id)
        print(result.transcript.text)
        break

    elif transcription.status == "error":
        print(f"Failed: {transcription.error_message}")
        break

    time.sleep(2)  # Poll every 2 seconds
```

### Logging Failed Webhooks

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        payload = WebhookPayload(**await request.json())

        # Log all webhook deliveries
        logger.info(
            f"Webhook received",
            extra={
                "transcription_id": payload.id,
                "status": payload.status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Process webhook...

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

    return {"status": "success"}
```

---

## Best Practices

### 1. Use Background Tasks

Process transcription results in background tasks to avoid blocking webhook responses:

```python
from fastapi import BackgroundTasks

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = WebhookPayload(**await request.json())

    # Queue background task
    background_tasks.add_task(process_result, payload.id)

    # Respond immediately
    return {"status": "success"}


async def process_result(transcription_id: str):
    # Heavy processing here
    result = client.transcriptions.get_result(transcription_id)
    # Save to database, send emails, etc.
```

### 2. Handle Idempotency

Webhooks may be delivered multiple times. Track processed IDs to prevent duplicate processing:

```python
# In production, use Redis or database
from redis import Redis

redis = Redis()

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = WebhookPayload(**await request.json())

    # Check if already processed
    if redis.exists(f"webhook:{payload.id}"):
        return {"status": "success", "message": "Already processed"}

    # Mark as processed (with expiry)
    redis.setex(f"webhook:{payload.id}", 86400, "1")  # 24 hour TTL

    # Process webhook...
```

### 3. Add Metadata via URL Parameters

Include context in webhook URL to identify the source:

```python
webhook_url = f"https://your-domain.com/webhook?user_id=123&order_id=456"
```

Parse in webhook handler:

```python
@app.post("/webhook")
async def handle_webhook(request: Request):
    # Extract query parameters
    user_id = request.query_params.get("user_id")
    order_id = request.query_params.get("order_id")

    payload = WebhookPayload(**await request.json())

    # Associate transcription with user/order
    print(f"Transcription {payload.id} for user {user_id}, order {order_id}")
```

### 4. Monitor Webhook Failures

Track webhook delivery failures and set up alerts:

```python
from prometheus_client import Counter

webhook_failures = Counter(
    'webhook_failures_total',
    'Total webhook processing failures'
)

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        # Process webhook...
        pass
    except Exception as e:
        webhook_failures.inc()
        # Send alert via PagerDuty, Slack, etc.
        raise
```

### 5. Log Transcription IDs

Always log transcription IDs when starting jobs:

```python
transcription = client.transcriptions.create(
    file_id=file.id,
    model="stt-async-v3",
    webhook_url="https://your-domain.com/webhook",
)

# Log ID for manual recovery if webhook fails
logger.info(
    f"Started transcription {transcription.id}",
    extra={"user_id": user_id, "file_name": file_name}
)
```

---

## Complete Examples

### Example 1: Simple Webhook Handler

```python
from fastapi import FastAPI, Request
from soniox import SonioxClient, WebhookPayload

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = WebhookPayload(**await request.json())

    client = SonioxClient(api_key="your-api-key")

    if payload.status == "completed":
        result = client.transcriptions.get_result(payload.id)
        print(f"✅ {result.transcript.text}")

    return {"status": "success"}
```

### Example 2: Production-Ready Handler

```python
from fastapi import FastAPI, Request, BackgroundTasks
from soniox import SonioxClient, WebhookPayload
import logging
import os

app = FastAPI()
logger = logging.getLogger(__name__)

# Environment variables
SONIOX_API_KEY = os.getenv("SONIOX_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Track processed webhooks
processed = set()


async def process_transcription(transcription_id: str):
    """Background task to process transcription."""
    try:
        client = SonioxClient(api_key=SONIOX_API_KEY)
        result = client.transcriptions.get_result(transcription_id)

        # Your business logic here
        # - Save to database
        # - Send notifications
        # - Update UI
        # - etc.

        logger.info(f"Processed: {transcription_id}")

    except Exception as e:
        logger.error(f"Failed to process {transcription_id}: {e}")


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    # Verify authentication
    if request.headers.get("Authorization") != f"Bearer {WEBHOOK_SECRET}":
        return {"status": "unauthorized"}, 401

    # Parse payload
    payload = WebhookPayload(**await request.json())

    # Idempotency check
    if payload.id in processed:
        return {"status": "success", "message": "Already processed"}

    processed.add(payload.id)

    # Process in background
    if payload.status == "completed":
        background_tasks.add_task(process_transcription, payload.id)

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Example 3: Webhook with Database Storage

```python
from fastapi import FastAPI, Request, BackgroundTasks
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from soniox import SonioxClient, WebhookPayload

Base = declarative_base()
engine = create_engine("postgresql://localhost/transcriptions")
Session = sessionmaker(bind=engine)


class TranscriptionRecord(Base):
    __tablename__ = "transcriptions"

    id = Column(String, primary_key=True)
    text = Column(Text)
    status = Column(String)


app = FastAPI()


async def save_transcription(transcription_id: str):
    client = SonioxClient(api_key="your-api-key")
    result = client.transcriptions.get_result(transcription_id)

    session = Session()
    record = TranscriptionRecord(
        id=transcription_id,
        text=result.transcript.text,
        status="completed",
    )
    session.add(record)
    session.commit()


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = WebhookPayload(**await request.json())

    if payload.status == "completed":
        background_tasks.add_task(save_transcription, payload.id)

    return {"status": "success"}
```

---

## Summary

Webhooks provide a simple, scalable way to handle asynchronous transcriptions:

1. **Create transcription** with `webhook_url` parameter
2. **Implement endpoint** at your webhook URL
3. **Receive notification** when transcription completes
4. **Fetch result** using the transcription ID

For production use:
- ✅ Use HTTPS webhooks
- ✅ Verify authentication
- ✅ Handle idempotency
- ✅ Process in background
- ✅ Log all webhook deliveries
- ✅ Monitor failures

Happy transcribing! 🎙️

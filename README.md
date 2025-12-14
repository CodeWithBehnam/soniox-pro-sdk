# Soniox Pro SDK

[![PyPI version](https://badge.fury.io/py/soniox-pro-sdk.svg)](https://badge.fury.io/py/soniox-pro-sdk)
[![Python Support](https://img.shields.io/pypi/pyversions/soniox-pro-sdk.svg)](https://pypi.org/project/soniox-pro-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**The most powerful, flexible, and blazing-fast Python SDK for the Soniox Speech-to-Text API.**

Production-ready, fully-typed, and optimised for performance.

## Features

### Complete API Coverage
- REST API (Files, Transcriptions, Models, Authentication)
- WebSocket API (Real-time transcription and translation)
- Synchronous and asynchronous interfaces
- Full type safety with Pydantic models

### Performance Optimised
- Blazing fast with optional C extensions
- Connection pooling for HTTP and WebSocket
- Async I/O throughout
- Memory-efficient streaming

### Advanced Capabilities
- 60+ languages supported
- Real-time translation (one-way and two-way)
- Speaker diarization (up to 15 speakers)
- Language identification
- Endpoint detection
- Custom context and vocabulary
- Word-level timestamps
- Confidence scores

### Developer Experience
- Comprehensive documentation
- Full IDE autocomplete support
- 90%+ test coverage
- Type-checked with mypy
- Clean, Pythonic API

## Installation

### Basic Installation
```bash
# Using uv (recommended)
uv add soniox-pro-sdk

# Using pip
pip install soniox-pro-sdk
```

### Optional Dependencies
```bash
# Async support
pip install soniox-pro-sdk[async]

# Performance optimisations (C extensions)
pip install soniox-pro-sdk[performance]

# Development tools
pip install soniox-pro-sdk[dev]

# Everything
pip install soniox-pro-sdk[all]
```

## Quick Start

### Async Transcription
```python
from soniox import SonioxClient

# Initialise client
client = SonioxClient(api_key="your-api-key")

# Transcribe from URL
transcription = client.transcriptions.create(
    audio_url="https://example.com/audio.mp3",
    model="stt-async-v3",
    enable_speaker_diarization=True,
)

# Wait for completion
result = client.transcriptions.wait_for_completion(transcription.id)
print(result.transcript.text)
```

### Real-time Transcription
```python
from soniox import SonioxRealtimeClient

# Initialise real-time client
client = SonioxRealtimeClient(
    api_key="your-api-key",
    model="stt-rt-v3",
)

# Stream audio
with client.stream() as stream:
    with open("audio.mp3", "rb") as f:
        while chunk := f.read(4096):
            stream.send_audio(chunk)

    # Receive tokens
    for response in stream:
        for token in response.tokens:
            if token.is_final:
                print(token.text, end="")
```

### Async/Await Support
```python
import asyncio
from soniox import AsyncSonioxClient

async def transcribe():
    async with AsyncSonioxClient(api_key="your-api-key") as client:
        file = await client.files.upload("audio.mp3")
        transcription = await client.transcriptions.create(file_id=file.id)
        result = await client.transcriptions.wait_for_completion(transcription.id)
        return result.transcript.text

text = asyncio.run(transcribe())
```

## Documentation

Full documentation available at: <https://github.com/CodeWithBehnam/soniox-pro-sdk>

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=soniox

# Type check
uv run mypy src/soniox

# Lint
uv run ruff check src/soniox
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- Documentation: <https://github.com/CodeWithBehnam/soniox-pro-sdk>
- Source Code: <https://github.com/CodeWithBehnam/soniox-pro-sdk>
- Soniox API: <https://soniox.com/docs>

---

**Built for the developer community**

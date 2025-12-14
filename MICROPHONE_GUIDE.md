# Microphone Input Guide

Complete guide for using Soniox Pro SDK with microphone input for real-time transcription.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Web Interface (Docker)](#web-interface-docker)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Troubleshooting](#troubleshooting)
- [Platform-Specific Notes](#platform-specific-notes)

---

## Quick Start

### Web Interface (Easiest)

```bash
# 1. Clone repository
git clone https://github.com/CodeWithBehnam/soniox-pro-sdk.git
cd soniox-pro-sdk

# 2. Set up environment
cp .env.example .env
# Edit .env and add your SONIOX_API_KEY

# 3. Start Docker container
docker compose up

# 4. Open browser
open http://localhost:8000
```

### CLI Usage

```bash
# Install with microphone support
uv add "soniox-pro-sdk[microphone]"

# Set API key
export SONIOX_API_KEY='your-api-key'

# List available microphones
uv run examples/realtime_microphone.py --list-devices

# Start transcription
uv run examples/realtime_microphone.py
```

---

## Installation

### Option 1: Docker (Recommended)

**Advantages:**
- No local dependencies required
- Web interface included
- Cross-platform consistency
- Easy deployment

```bash
# Clone repository
git clone https://github.com/CodeWithBehnam/soniox-pro-sdk.git
cd soniox-pro-sdk

# Configure API key
cp .env.example .env
vim .env  # Add your SONIOX_API_KEY

# Start container
docker compose up

# Access at http://localhost:8000
```

### Option 2: Local Installation

**Requirements:**
- Python 3.12+
- System audio libraries (PortAudio)

**macOS:**
```bash
# Install PortAudio
brew install portaudio

# Install SDK with microphone support
uv add "soniox-pro-sdk[microphone]"
```

**Ubuntu/Debian:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    portaudio19-dev \
    libsndfile1 \
    python3-dev

# Install SDK
uv add "soniox-pro-sdk[microphone]"
```

**Windows:**
```powershell
# PortAudio is bundled with sounddevice on Windows
uv add "soniox-pro-sdk[microphone]"
```

---

## Web Interface (Docker)

### Starting the Web Interface

```bash
# Start in foreground
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Accessing the Interface

1. Open browser: [http://localhost:8000](http://localhost:8000)
2. Select your microphone from the dropdown
3. Click "▶️ Start Recording"
4. Speak into your microphone
5. View real-time transcription
6. Click "⏹️ Stop Recording" when done

### Features

- **Real-time Transcription**: See text appear as you speak
- **Audio Visualisation**: Visual feedback of microphone input
- **Device Selection**: Choose from available microphones
- **Statistics**: Track duration, word count, and data usage
- **Export**: Copy transcription to clipboard

### Configuration

Edit `docker-compose.yml` to customise:

```yaml
environment:
  # Change port
  - PORT=8080

  # Enable debug logging
  - LOG_LEVEL=debug

  # Custom API endpoint
  - SONIOX_API_BASE_URL=https://api.soniox.com
```

---

## CLI Usage

### List Audio Devices

```bash
uv run examples/realtime_microphone.py --list-devices
```

**Example output:**
```
🎤 Available Audio Input Devices:

Index  Device Name                                        Channels   Sample Rate
-------------------------------------------------------------------------------------
0      Built-in Microphone                                2          48000 Hz
1      USB Microphone                                     1          44100 Hz

Total: 2 device(s)
```

### Basic Transcription

```bash
# Use default microphone
uv run examples/realtime_microphone.py

# Use specific microphone
uv run examples/realtime_microphone.py --device 1

# Record for 30 seconds
uv run examples/realtime_microphone.py --duration 30

# Custom sample rate
uv run examples/realtime_microphone.py --sample-rate 16000
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--list-devices` | List available microphones and exit | - |
| `--device INDEX` | Audio device index | Default device |
| `--duration SECONDS` | Recording duration | Continuous |
| `--sample-rate RATE` | Sample rate (8000/16000/44100/48000) | 16000 |
| `--api-key KEY` | Soniox API key | `$SONIOX_API_KEY` |

---

## Python API

### Basic Example

```python
from soniox import SonioxClient
from soniox.audio import MicrophoneCapture

# Initialise client
client = SonioxClient(api_key="your-api-key")

# Create microphone capture
mic = MicrophoneCapture(sample_rate=16000)

# Start real-time stream
with client.stream() as stream:
    # Capture and send audio
    for audio_chunk in mic.capture(duration=10.0):
        stream.send_audio(audio_chunk)

    # End stream
    stream.end_stream()

    # Get transcription
    for response in stream:
        for token in response.tokens:
            print(token.text, end=" ", flush=True)
```

### Advanced Configuration

```python
from soniox import SonioxClient
from soniox.audio import MicrophoneCapture, list_audio_devices
from soniox.types import RealtimeConfig

# List available devices
devices = list_audio_devices()
print(f"Found {len(devices)} microphones")

# Create microphone with specific device
mic = MicrophoneCapture(
    sample_rate=16000,
    channels=1,
    chunk_size=256,  # Samples per chunk
    device=0,  # Device index
)

# Configure transcription
config = RealtimeConfig(
    audio_format="pcm_s16le",
    sample_rate_hertz=16000,
    enable_speaker_diarization=True,  # Identify speakers
    include_nonfinal=True,  # Get partial results
)

# Start stream with configuration
client = SonioxClient(api_key="your-api-key")
with client.stream(config=config) as stream:
    for audio_chunk in mic.capture():
        stream.send_audio(audio_chunk)

    stream.end_stream()

    for response in stream:
        for token in response.tokens:
            speaker = f"[Speaker {token.speaker_id}] " if hasattr(token, "speaker_id") else ""
            print(f"{speaker}{token.text}")
```

### Async Capture (Callback)

```python
from soniox import SonioxClient
from soniox.audio import MicrophoneCapture

client = SonioxClient(api_key="your-api-key")

with client.stream() as stream:
    mic = MicrophoneCapture(sample_rate=16000)

    # Define callback
    def on_audio(audio_bytes: bytes) -> None:
        stream.send_audio(audio_bytes)

    # Start async capture (non-blocking)
    mic.capture_async(callback=on_audio, duration=10.0)

    # Process transcription in main thread
    for response in stream:
        for token in response.tokens:
            print(token.text)
```

---

## Troubleshooting

### No Microphones Found

**macOS:**
```bash
# Check system permissions
# System Preferences → Security & Privacy → Microphone
# Ensure terminal/app has microphone access

# Reinstall PortAudio
brew uninstall portaudio
brew install portaudio
uv pip install --force-reinstall sounddevice
```

**Linux:**
```bash
# Check ALSA devices
arecord -l

# Test microphone
arecord -d 5 -f cd test.wav
aplay test.wav

# Check PulseAudio
pactl list sources short

# Fix permissions
sudo usermod -aG audio $USER
```

**Windows:**
```powershell
# Check privacy settings
# Settings → Privacy → Microphone
# Ensure app permissions are enabled

# Reinstall sounddevice
uv pip uninstall sounddevice
uv pip install sounddevice
```

### Audio Quality Issues

**Choppy/Distorted Audio:**
```python
# Increase chunk size for more stable capture
mic = MicrophoneCapture(
    sample_rate=16000,
    chunk_size=512,  # Larger chunks = more stable
)
```

**Low Volume:**
```bash
# macOS: System Preferences → Sound → Input → Input Volume
# Linux: alsamixer -c 0 (press F4 for capture devices)
# Windows: Settings → System → Sound → Input Device Properties
```

### Docker Audio Issues

**Linux:**
```yaml
# docker-compose.yml - Add audio group
services:
  web:
    group_add:
      - audio
```

**macOS:**
```bash
# Audio passthrough not supported in Docker Desktop
# Use local installation instead
```

### Import Errors

```bash
# Error: No module named 'sounddevice'
uv add "soniox-pro-sdk[microphone]"

# Error: No module named 'numpy'
uv add numpy

# Verify installation
python -c "import sounddevice; print(sounddevice.__version__)"
```

### WebSocket Errors

```python
# Timeout errors - increase chunk size
mic = MicrophoneCapture(chunk_size=512)

# Connection errors - check API key
export SONIOX_API_KEY='your-valid-api-key'

# Rate limiting - reduce sample rate
mic = MicrophoneCapture(sample_rate=8000)
```

---

## Platform-Specific Notes

### macOS

**Permissions:**
- Grant microphone access: System Preferences → Security & Privacy → Microphone
- Terminal/IDE needs explicit permission

**Recommended Settings:**
```python
MicrophoneCapture(
    sample_rate=16000,
    channels=1,
    chunk_size=256,
)
```

### Linux

**Best Performance:**
- Use PulseAudio for desktop environments
- Use ALSA directly for embedded/server environments

**PulseAudio Configuration:**
```bash
# Check default source
pactl info | grep "Default Source"

# Set default source
pactl set-default-source alsa_input.pci-0000_00_1f.3.analog-stereo
```

**Recommended Settings:**
```python
MicrophoneCapture(
    sample_rate=16000,
    channels=1,
    chunk_size=256,
    device=None,  # Use PulseAudio default
)
```

### Windows

**Permissions:**
- Settings → Privacy → Microphone → Allow apps to access microphone

**Recommended Settings:**
```python
MicrophoneCapture(
    sample_rate=16000,
    channels=1,
    chunk_size=512,  # Larger chunks for Windows
)
```

---

## Best Practices

### Audio Quality

1. **Use 16kHz sample rate** - Optimal for speech recognition
2. **Use mono (1 channel)** - Speech doesn't need stereo
3. **Chunk size 256-512 samples** - Balance latency vs stability
4. **Enable noise suppression** - In getUserMedia() for web
5. **Position microphone 15-30cm from mouth** - Best audio quality

### Performance

1. **Disable speaker diarization** if not needed - Faster processing
2. **Use partial results** (`include_nonfinal=True`) - Better UX
3. **Buffer audio locally** if network is unstable
4. **Monitor CPU usage** - Reduce sample rate if needed

### Production Deployment

1. **Use environment variables** for API keys
2. **Implement error handling** for device failures
3. **Add reconnection logic** for WebSocket drops
4. **Log audio statistics** for debugging
5. **Test on target platform** before deployment

---

## API Reference

### `MicrophoneCapture`

```python
class MicrophoneCapture:
    """Capture audio from system microphone."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 256,
        device: int | None = None,
    ) -> None:
        """Initialise microphone capture."""

    def capture(
        self,
        duration: float | None = None,
    ) -> Generator[bytes, None, None]:
        """Capture audio chunks."""

    def capture_async(
        self,
        callback: Callable[[bytes], None],
        duration: float | None = None,
    ) -> None:
        """Capture audio asynchronously with callback."""
```

### `list_audio_devices()`

```python
def list_audio_devices() -> list[dict[str, Any]]:
    """List all available audio input devices.

    Returns:
        List of device information:
        - index: Device index
        - name: Device name
        - channels: Number of input channels
        - sample_rate: Default sample rate
    """
```

---

## Support

- **Documentation**: https://codewithbehnam.github.io/soniox-pro-sdk
- **Issues**: https://github.com/CodeWithBehnam/soniox-pro-sdk/issues
- **Soniox API Docs**: https://soniox.com/docs

---

## Licence

MIT Licence - See [LICENCE](LICENCE) file for details.

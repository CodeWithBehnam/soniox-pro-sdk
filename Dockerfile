# Soniox Microphone Transcription - Docker Image
# Built with uv for fast, reliable Python dependency management

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio support
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    libsndfile1 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ ./src/
COPY web/ ./web/

# Install dependencies with uv
# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Install production dependencies + microphone extras
RUN uv pip install --system -e ".[microphone]" && \
    uv pip install --system fastapi uvicorn jinja2 python-multipart

# Create non-root user for security
RUN useradd -m -u 1000 soniox && \
    chown -R soniox:soniox /app

USER soniox

# Expose web interface port (default 4346, configurable via PORT env var)
EXPOSE 4346

# Set environment variables
ENV PORT=4346
ENV PYTHONUNBUFFERED=1

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import requests; requests.get(f'http://localhost:{os.getenv(\"PORT\", \"4346\")}/api/health')"

# Start web application (uses PORT env var)
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT}"]

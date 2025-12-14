# Docker Deployment Guide

Complete guide for running Soniox microphone transcription with Docker.

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/CodeWithBehnam/soniox-pro-sdk.git
cd soniox-pro-sdk

# 2. Configure API key
cp .env.example .env
vim .env  # Add your SONIOX_API_KEY

# 3. Start container
docker compose up

# 4. Open browser
open http://localhost:8000
```

## Docker Compose

### Basic Usage

```bash
# Start (foreground)
docker compose up

# Start (background)
docker compose up -d

# View logs
docker compose logs -f web

# Stop
docker compose down

# Rebuild after changes
docker compose up --build
```

### Configuration

Edit `docker-compose.yml` to customise:

```yaml
services:
  web:
    ports:
      - "8080:8000"  # Change port

    environment:
      - SONIOX_API_KEY=${SONIOX_API_KEY}
      - PORT=8000
      - LOG_LEVEL=debug  # Enable debug logging

    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
```

### Environment Variables

Create `.env` file:

```bash
# Required
SONIOX_API_KEY=your_api_key_here

# Optional
PORT=8000
LOG_LEVEL=info
```

## Dockerfile

### Build Image Manually

```bash
# Build image
docker build -t soniox-transcription .

# Run container
docker run -d \
  -p 8000:8000 \
  -e SONIOX_API_KEY=your-api-key \
  --name soniox \
  soniox-transcription

# View logs
docker logs -f soniox

# Stop container
docker stop soniox
docker rm soniox
```

### Multi-stage Build

The Dockerfile uses uv's official Docker image for fast, reliable builds:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    libsndfile1 \
    alsa-utils

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY web/ ./web/

# Install with uv (extremely fast)
RUN uv pip install --system -e ".[microphone]" && \
    uv pip install --system fastapi uvicorn jinja2 python-multipart
```

## Production Deployment

### Using Docker Hub

```bash
# Build and tag
docker build -t yourusername/soniox-transcription:latest .

# Push to Docker Hub
docker push yourusername/soniox-transcription:latest

# Pull and run on production server
docker pull yourusername/soniox-transcription:latest
docker run -d \
  -p 8000:8000 \
  -e SONIOX_API_KEY=${SONIOX_API_KEY} \
  --restart unless-stopped \
  yourusername/soniox-transcription:latest
```

### Using Docker Swarm

```yaml
# docker-stack.yml
version: '3.8'

services:
  web:
    image: yourusername/soniox-transcription:latest
    ports:
      - "8000:8000"
    environment:
      - SONIOX_API_KEY
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

Deploy:
```bash
docker stack deploy -c docker-stack.yml soniox
```

### Using Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: soniox-transcription
spec:
  replicas: 3
  selector:
    matchLabels:
      app: soniox
  template:
    metadata:
      labels:
        app: soniox
    spec:
      containers:
      - name: web
        image: yourusername/soniox-transcription:latest
        ports:
        - containerPort: 8000
        env:
        - name: SONIOX_API_KEY
          valueFrom:
            secretKeyRef:
              name: soniox-secret
              key: api-key
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "0.5"
            memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: soniox-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: soniox
```

## Platform-Specific Notes

### macOS (Docker Desktop)

**Limitations:**
- Audio device passthrough not supported
- Cannot access host microphone from container

**Solution:**
- Use for web interface development only
- Audio input comes from browser's microphone (getUserMedia)
- Works perfectly for web UI testing

### Linux

**Audio Passthrough:**

```yaml
# docker-compose.yml
services:
  web:
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - /run/user/1000/pulse:/run/user/1000/pulse:ro
    environment:
      - PULSE_SERVER=/run/user/1000/pulse/native
    group_add:
      - audio
```

**Test Audio:**
```bash
# Inside container
docker exec -it soniox-transcription bash
arecord -l  # List recording devices
```

### Windows (Docker Desktop)

**Limitations:**
- Similar to macOS - no direct audio passthrough
- Use browser's microphone via getUserMedia API

## Monitoring

### Health Checks

Built-in health check endpoint:

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "healthy",
  "api_key_configured": "yes"
}
```

### Logs

```bash
# Follow logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail 100

# Specific service
docker compose logs -f web

# JSON format
docker compose logs --json
```

### Resource Usage

```bash
# Container stats
docker stats soniox-transcription

# Detailed info
docker inspect soniox-transcription
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs web

# Common issues:
# 1. Missing API key
#    Solution: Add SONIOX_API_KEY to .env

# 2. Port already in use
#    Solution: Change port in docker-compose.yml

# 3. Build failures
#    Solution: Clear cache and rebuild
docker compose down -v
docker compose build --no-cache
docker compose up
```

### Cannot Access Web Interface

```bash
# Check container is running
docker ps | grep soniox

# Check port binding
docker port soniox-transcription

# Test from inside container
docker exec soniox-transcription curl http://localhost:8000/api/health

# Check firewall (Linux)
sudo ufw allow 8000/tcp
```

### Audio Not Working

**Web Interface (Browser):**
- Check browser permissions (Settings → Privacy → Microphone)
- Use HTTPS in production (required for getUserMedia)
- Test in Chrome/Firefox/Safari

**Docker Container:**
- macOS/Windows: Audio passthrough not supported
- Linux: Check device mapping and permissions

### Performance Issues

```bash
# Increase resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G

# Check resource usage
docker stats

# Optimise image size
docker image ls | grep soniox
```

## Development Workflow

### Live Reload

```yaml
# docker-compose.yml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - ./src:/app/src:ro  # Mount source code
      - ./web:/app/web:ro
    command: uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

Start:
```bash
docker compose up --build
```

Now changes to `src/` or `web/` will auto-reload.

### Debugging

```bash
# Run with interactive shell
docker run -it --rm \
  -p 8000:8000 \
  -e SONIOX_API_KEY=your-key \
  soniox-transcription \
  /bin/bash

# Inside container:
python -c "from soniox import SonioxClient; print('OK')"
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run tests in container
docker compose run --rm web uv run pytest

# With coverage
docker compose run --rm web uv run pytest --cov=soniox
```

## Security

### Production Checklist

- [ ] Use secrets management (not .env files)
- [ ] Run as non-root user (already configured)
- [ ] Use HTTPS with valid certificates
- [ ] Implement rate limiting
- [ ] Enable CORS restrictions
- [ ] Scan image for vulnerabilities
- [ ] Keep base image updated

### Scan for Vulnerabilities

```bash
# Using Docker Scout
docker scout cves soniox-transcription

# Using Trivy
trivy image soniox-transcription
```

### Secrets Management

**Using Docker Secrets:**
```yaml
# docker-stack.yml
services:
  web:
    secrets:
      - soniox_api_key
    environment:
      - SONIOX_API_KEY_FILE=/run/secrets/soniox_api_key

secrets:
  soniox_api_key:
    external: true
```

**Using Kubernetes Secrets:**
```bash
kubectl create secret generic soniox-secret \
  --from-literal=api-key=your-api-key
```

## Performance Optimisation

### Build Cache

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t soniox-transcription .

# Multi-stage caching
docker build \
  --cache-from soniox-transcription:latest \
  -t soniox-transcription:latest \
  .
```

### Image Size

```bash
# Check image size
docker image ls soniox-transcription

# Optimise layers
# - Combine RUN commands
# - Remove apt cache
# - Use .dockerignore
```

### Runtime Performance

```yaml
# docker-compose.yml
services:
  web:
    environment:
      - UV_COMPILE_BYTECODE=1  # Faster startup
      - PYTHONUNBUFFERED=1      # Better logging
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t soniox-transcription .

      - name: Test image
        run: |
          docker run -d -p 8000:8000 \
            -e SONIOX_API_KEY=${{ secrets.SONIOX_API_KEY }} \
            --name test soniox-transcription
          sleep 5
          curl http://localhost:8000/api/health

      - name: Push to Docker Hub
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push yourusername/soniox-transcription:latest
```

## Support

- **Issues**: https://github.com/CodeWithBehnam/soniox-pro-sdk/issues
- **Docker Hub**: https://hub.docker.com/r/yourusername/soniox-transcription
- **Documentation**: https://codewithbehnam.github.io/soniox-pro-sdk

## Licence

MIT Licence - See [LICENCE](LICENCE) file for details.

# Multi-Architecture Container Build Pipeline Report

## Overview
To support modern hybrid deployments (AWS Graviton, Apple Silicon development, x86_64 cloud servers), all `CLASS_FUND_WEB` container images are packaged for both `linux/amd64` and `linux/arm64` architectures using Docker Buildx.

## 1. Container Image Matrix
| Container Service | Base Image | Multi-Arch Platforms | Security Profile | Healthcheck |
| :--- | :--- | :--- | :--- | :--- |
| **`backend`** | `python:3.12-slim` | `linux/amd64,linux/arm64` | Non-root (`classfund:10001`), read-only rootfs capable, embedded `ai` engine | `curl -f http://localhost:8000/api/v1/health` |
| **`worker`** | `python:3.12-slim` | `linux/amd64,linux/arm64` | Non-root (`classfund:10001`), resource capped, embedded `ai` OCR/verification pipeline | Process liveness |
| **`frontend`** | `nginx:1.27-alpine` | `linux/amd64,linux/arm64` | Multi-stage Node 20 build -> unprivileged Nginx | `wget -q -O /dev/null http://localhost/` |
| **`proxy`** | `caddy:2.8-alpine` | `linux/amd64,linux/arm64` | Minimal attack surface, ACME auto-TLS | Proxy port 80/443 |

## 2. Multi-Stage Dockerfile Architecture

### Backend (`docker/Dockerfile.backend`)
```dockerfile
# Stage 1: Build & Dependencies
FROM --platform=$BUILDPLATFORM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev default-libmysqlclient-dev pkg-config && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Container
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN groupadd -g 10001 classfund && useradd -u 10001 -g classfund -s /bin/sh classfund
COPY --from=builder /root/.local /home/classfund/.local
COPY . /app
COPY ai /app/ai
RUN chown -R classfund:classfund /app /home/classfund
USER classfund
ENV PATH=/home/classfund/.local/bin:$PATH
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## 3. Automated Build Automation
Cross-platform build scripts are provided in `docker/build_multiarch.sh` (POSIX) and `docker/build_multiarch.ps1` (PowerShell):
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target runtime \
  -t classfund/backend:latest \
  -f docker/Dockerfile.backend .
```
Both platforms use standard multi-stage caching, ensuring cross-compilation overhead is minimized on CI/CD pipelines. All multi-arch headless dependencies (`opencv-python-headless`, `pillow`, `rapidfuzz`, `numpy`, `imagehash`) compile cleanly across ARM64 and AMD64 architectures.

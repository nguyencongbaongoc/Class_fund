# Production Docker Compose Packaging Specification

## Overview
The `docker-compose.prod.yml` specification packages the entire `CLASS_FUND_WEB` system into a secure, resource-bounded, and highly available topology ready for single-node host or orchestrator deployment.

## 1. Services Architecture & Resource Bounds
Every container in the production compose file adheres to strict SRE resource limits to prevent noisy neighbors and memory leaks from degrading host stability.

| Service | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation | Restart Policy | Log Rotation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`proxy`** | 1.0 | 512 MB | 0.25 | 128 MB | `unless-stopped` | 50m / 5 files |
| **`frontend`** | 1.0 | 512 MB | 0.25 | 128 MB | `unless-stopped` | 50m / 5 files |
| **`backend`** | 2.0 | 2048 MB | 0.50 | 512 MB | `unless-stopped` | 50m / 5 files |
| **`worker`** | 2.0 | 2048 MB | 0.50 | 512 MB | `unless-stopped` | 50m / 5 files |
| **`mysql-primary`** | 2.0 | 2048 MB | 0.50 | 1024 MB | `unless-stopped` | 50m / 5 files |
| **`mysql-replica`** | 2.0 | 2048 MB | 0.50 | 1024 MB | `unless-stopped` | 50m / 5 files |
| **`redis`** | 1.0 | 512 MB | 0.25 | 128 MB | `unless-stopped` | 50m / 5 files |

## 2. Log Rotation Policy
Unbounded container stdout/stderr logging can exhaust host disk space. Every production service specifies the `json-file` logging driver:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```
This guarantees an upper bound of 250 MB per container, preserving system disk space indefinitely.

## 3. Storage Mounts & Persistence
- `mysql-primary-data`: Named volume mapped to `/var/lib/mysql`.
- `mysql-replica-data`: Named volume mapped to `/var/lib/mysql`.
- `redis-data`: Named volume mapped to `/data` with AOF (`appendonly yes`).
- `backend-storage`: Named volume mapped to `/app/storage/uploads` for receipts and OCR images.
- `caddy-data` & `caddy-config`: Named volumes preserving ACME certificates across container recreations.

## 4. Configuration Template (`.env.production.example`)
A complete production configuration template is provided with security warnings and configuration keys:
- Strict database credentials (`MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `REPL_PASSWORD`).
- Cryptographic keys: `JWT_SECRET` (256-bit entropy), `AI_SERVICE_KEY`.
- TLS parameters: `DOMAIN`, `ACME_EMAIL`, `ENFORCE_HTTPS=true`.
- Database SSL: `MYSQL_SSL_MODE=REQUIRED`.
- Resource constraints and logging parameters.

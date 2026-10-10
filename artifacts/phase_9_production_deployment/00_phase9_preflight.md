# Phase 9 Preflight Assessment: Production-Grade Deployment Transition

## Executive Summary
This document establishes the preflight audit, operational readiness verification, and deployment roadmap for **Phase 9: Production Deployment & Failback Architecture** of the `CLASS_FUND_WEB` system. Building upon the Phase 8 qualification (which achieved 100% pass on 215 backend tests and verified active-passive replication with zero financial divergence), Phase 9 hardens the stack for enterprise production deployment.

## 1. System Baseline Assessment
The qualified baseline consists of:
- **FastAPI Core**: Async REST and WebSocket API (`/api/v1`) with SQLAlchemy ORM and Alembic migrations.
- **Financial Gateway**: Strictly enforced single mutation gateway `verify_and_post_from_ai()` with immutable double-entry ledger semantics, `DECIMAL(18,2)` precision, and compensating `REVERT` entries.
- **MySQL GTID Replication**:
  - Primary MySQL (Windows Service `MySQL97`, Port 3306) operating in read-write mode (`server_id=1`).
  - Replica MySQL (MySQL 8.4, Port 3308) running with `super_read_only = ON` (`server_id=2`).
  - GTID auto-positioning enabled, replication lag = 0s, 0.00 VND ledger discrepancy.
- **Redis 7.2 Cache & Broker**: Pub/Sub broker for real-time WebSocket feeds and distributed worker leasing.
- **Ollama AI Vision Subsystem**: Circuit-breaker protected local LLM pipeline (`qwen2.5vl:3b` / `qwen3.5:4b`).

## 2. Phase 9 Core Deliverables & Production Requirements
Phase 9 transitions this qualified application into an enterprise production deployment through five mission-critical workstreams:

### Workstream A: Automated Failback Engine
- Implement an automated failback reconciler in `scripts/failover_manager.py` capable of:
  - Rejoining a recovering primary as a read-only replica with split-brain immunity (`super_read_only = ON` enforced before any network exposure).
  - Executing GTID auto-positioning (`CHANGE REPLICATION SOURCE TO SOURCE_AUTO_POSITION = 1`).
  - Validating zero balance discrepancy across all fund accounts prior to promoting or restoring original topology.
  - Planned, zero-downtime failback execution.

### Workstream B: CA-Signed TLS & Edge Ingress Reverse Proxy
- Production edge ingress with Caddy / Nginx reverse proxy.
- ACME automated TLS issuance with fallback to internal TLS (`tls internal`).
- Complete security headers: HSTS (`Strict-Transport-Security`), CSP, X-Content-Type-Options, X-Frame-Options (`DENY`), Permissions-Policy.
- WSS proxying for real-time WebSocket endpoints (`/ws/*`).
- Internal network isolation preventing direct exposure of MySQL (3306/3308) and Redis (6379) to the public internet.

### Workstream C: Multi-Architecture Container Build Pipeline
- Automated Docker Buildx multi-arch pipeline targeting `linux/amd64` and `linux/arm64`.
- Multi-stage Dockerfiles for Backend, Worker, Frontend, and Ingress Proxy with non-root security contexts (`classfund:10001`).

### Workstream D: Production Observability & Health Probes
- Deep health probe endpoint (`/api/v1/health/deep`) checking primary MySQL, replica MySQL, Redis pub/sub, worker heartbeat, and Ollama inference gateway.
- Prometheus `/metrics` exposition format for scraping.
- Structured JSON logging with `CorrelationIdMiddleware` propagating `X-Correlation-ID` across all requests.
- Proactive alerting thresholds for replication lag (>10s), deadlock retry exhaustion, and circuit breaker trip events.

### Workstream E: Production Compose Packaging & Smoke Qualification
- `docker-compose.prod.yml` and `.env.production.example` incorporating strict CPU/Memory resource limits, reservations, log rotation (json-file, max-size: 50m, max-file: 5), and restart policies (`unless-stopped`).
- Production smoke test suite validating edge ingress headers, health probes, Prometheus metrics, and automated failback operations.

## 3. Preflight Readiness Verification Matrix
| Dimension | Baseline State | Phase 9 Target | Status |
| :--- | :--- | :--- | :--- |
| Database Replication | Primary (3306) -> Replica (3308) GTID | Automated Failover + Rejoin + Failback | Verified |
| Financial Integrity | `verify_and_post_from_ai()` immutable | 0.00 VND variance across nodes | Verified |
| Split-Brain Immunity | Manual `read_only` flag | Pre-attachment `super_read_only = ON` | Verified |
| Edge Ingress | Direct port exposure | Caddy/Nginx reverse proxy + TLS + HSTS | Configured |
| Telemetry | Basic `/health` endpoint | Deep health + Prometheus `/metrics` + JSON Logs | Configured |
| Container Platform | Local dev setup | Multi-arch `linux/amd64,linux/arm64` Buildx | Packaged |
| Configuration | Dev `.env` | Hardened `docker-compose.prod.yml` with limits | Packaged |

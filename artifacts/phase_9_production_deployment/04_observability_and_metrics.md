# Production Observability, Health Probes & Telemetry Architecture

## Overview
`CLASS_FUND_WEB` incorporates comprehensive production observability including deep health checks, Prometheus metrics exposition, structured JSON logging with correlation IDs, and threshold-based proactive alert monitoring.

## 1. Deep Health Check Probe (`/api/v1/health/deep`)
While `/api/v1/health` provides basic HTTP process liveness, `/api/v1/health/deep` executes real-time active diagnostics against every distributed subsystem:

```json
{
  "status": "healthy",
  "timestamp": "2026-10-10T05:00:00Z",
  "version": "0.1.0",
  "environment": "production",
  "components": {
    "mysql_primary": {
      "status": "up",
      "latency_ms": 1.25,
      "details": {
        "read_only": false,
        "super_read_only": false,
        "server_id": 1,
        "gtid_mode": "ON"
      }
    },
    "mysql_replica": {
      "status": "up",
      "latency_ms": 1.80,
      "details": {
        "replica_io_running": "Yes",
        "replica_sql_running": "Yes",
        "seconds_behind_source": 0,
        "super_read_only": true
      }
    },
    "redis": {
      "status": "up",
      "latency_ms": 0.85
    },
    "worker": {
      "status": "up",
      "last_heartbeat_seconds_ago": 4.2
    },
    "ollama_vision": {
      "status": "up",
      "circuit_breaker": "closed",
      "consecutive_failures": 0
    }
  }
}
```

### Degraded vs Unhealthy Semantics
- **`healthy` (HTTP 200)**: All core components (`mysql_primary`, `redis`, `worker`) are functional, replication lag <= 10s, and circuit breaker closed.
- **`degraded` (HTTP 200)**: Replica is lagging (>10s) or offline, but primary is handling write traffic, or Ollama vision is temporarily tripped to fallback OCR.
- **`unhealthy` (HTTP 503)**: Primary database is unreachable, read-write operations impossible, or unrecoverable system partition.

## 2. Prometheus Metrics Exposition (`/metrics`)
Metrics are exported in Prometheus text exposition format (version 0.04) and exposed on `/metrics` and `/api/v1/metrics`:
- **HTTP Metrics**:
  - `classfund_http_requests_total{method="POST",path="/api/v1/transactions",status="200"}`
  - `classfund_http_request_duration_seconds{method="POST",path="/api/v1/transactions",quantile="0.99"}`
- **Financial Metrics**:
  - `classfund_ledger_mutations_total{status="POSTED"}`
  - `classfund_ledger_balance_discrepancy_cents 0.0`
- **Replication Metrics**:
  - `classfund_mysql_replication_lag_seconds 0.0`
  - `classfund_mysql_replica_io_running 1.0`
  - `classfund_mysql_replica_sql_running 1.0`
- **Worker & AI Metrics**:
  - `classfund_worker_active_count 1.0`
  - `classfund_ollama_circuit_breaker_tripped 0.0`

## 3. Structured JSON Logging & Request Correlation
All backend application logs are structured as JSON via `JSONFormatter` in `app/core/logging.py`.
- **`CorrelationIdMiddleware`**:
  - Automatically intercepts inbound requests.
  - Checks for client-provided `X-Correlation-ID`. If missing, generates a new UUID v4.
  - Stores the correlation ID in Python `contextvars` (`ContextVar[str]`).
  - Attaches `X-Correlation-ID` to all response headers.
  - Injects `correlation_id` into every log entry emitted during request handling.

Example structured log payload:
```json
{
  "timestamp": "2026-10-10T05:02:30.123456Z",
  "level": "INFO",
  "logger": "app.services.ledger",
  "correlation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message": "Financial mutation posted successfully",
  "account_id": "acc-10293",
  "amount": "250000.00",
  "balance_after": "1250000.00"
}
```

## 4. Proactive Alerting Triggers
The alerting dispatcher (`app/core/alerting.py`) monitors critical thresholds:
1. **Replication Lag Alert**: Fires when `Seconds_Behind_Source > 10.0` for > 3 consecutive checks.
2. **Deadlock Limit Alert**: Fires when database deadlock retry attempts exceed configured limit (5 attempts).
3. **Circuit Breaker Trip Alert**: Fires when Ollama consecutive failures exceed 3, notifying operations of fallback activation.

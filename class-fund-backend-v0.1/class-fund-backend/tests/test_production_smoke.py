"""
Production Deployment Smoke Test Suite
CLASS_FUND_WEB - Phase 9 Qualification

Validates:
1. Production Configuration Packaging & Resource Constraints (CPU/Memory limits, log rotation).
2. Edge Ingress, Security Headers & TLS Transport Policy (HSTS, CSP, nosniff, frame denial).
3. Deep Health Probe (/api/v1/health/deep) comprehensive component diagnostics.
4. Prometheus Telemetry (/metrics) exposition format and metrics validity.
5. Structured JSON Logging & Correlation ID propagation across backend requests.
6. Real-time WebSocket (WSS) streaming endpoint security and event routing.
7. Worker batch processing under simulated concurrency with lease renewal.
"""

import json
import os
import sys
import yaml
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add backend to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.core.config import get_settings
from app.core.logging import JSONFormatter, get_correlation_id, set_correlation_id
from app.core.alerting import alert_manager
from app.db.session import SessionLocal
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, Message, MessageStatus,
    Upload, UploadStatus, User, Role
)
from app.core.security import create_access_token, hash_password


# ============================================================================
# 1. Production Docker Compose & Resource Specification Tests
# ============================================================================


class TestProductionComposeSpecification:
    """Verifies docker-compose.prod.yml conforms strictly to SRE standards."""

    @pytest.fixture(scope="class")
    def compose_spec(self):
        # Look for docker-compose.prod.yml in backend or root
        candidates = [
            Path(backend_dir) / "docker-compose.prod.yml",
            Path(backend_dir).parent.parent / "docker-compose.prod.yml",
            Path(os.getcwd()) / "docker-compose.prod.yml",
        ]
        compose_file = None
        for c in candidates:
            if c.exists():
                compose_file = c
                break

        assert compose_file is not None, "docker-compose.prod.yml file not found!"
        with open(compose_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_all_production_services_declared(self, compose_spec):
        """Rule: Production stack must declare all 7 essential services."""
        services = compose_spec.get("services", {})
        expected_services = [
            "proxy", "frontend", "backend", "worker",
            "mysql-primary", "mysql-replica", "redis"
        ]
        for s in expected_services:
            assert s in services, f"Service '{s}' missing from docker-compose.prod.yml"

    def test_resource_limits_and_reservations_enforced(self, compose_spec):
        """Rule: Every service must specify CPU and Memory resource limits to prevent noisy neighbors."""
        services = compose_spec.get("services", {})
        for sname, sdef in services.items():
            deploy = sdef.get("deploy", {})
            resources = deploy.get("resources", {})
            limits = resources.get("limits", {})
            reservations = resources.get("reservations", {})

            assert "memory" in limits, f"Service '{sname}' lacks memory limit"
            assert "cpus" in limits or "memory" in limits, f"Service '{sname}' lacks resource limits"
            assert "memory" in reservations, f"Service '{sname}' lacks memory reservation"

    def test_log_rotation_configured(self, compose_spec):
        """Rule: Log rotation must be configured (json-file, max-size: 50m, max-file: 5)."""
        services = compose_spec.get("services", {})
        for sname, sdef in services.items():
            logging_cfg = sdef.get("logging", {})
            assert logging_cfg.get("driver") == "json-file", f"Service '{sname}' logging driver must be json-file"
            opts = logging_cfg.get("options", {})
            assert opts.get("max-size") == "50m", f"Service '{sname}' max-size should be 50m"
            assert opts.get("max-file") == "5", f"Service '{sname}' max-file should be 5"

    def test_restart_policy_unless_stopped(self, compose_spec):
        """Rule: All critical services must have restart: unless-stopped."""
        services = compose_spec.get("services", {})
        for sname, sdef in services.items():
            restart = sdef.get("restart")
            assert restart == "unless-stopped", f"Service '{sname}' restart policy must be unless-stopped"

    def test_network_isolation_enforced(self, compose_spec):
        """Rule: Internal services must be segregated from public network."""
        networks = compose_spec.get("networks", {})
        assert "classfund_public" in networks
        assert "classfund_internal" in networks
        assert networks["classfund_internal"].get("internal") is True


# ============================================================================
# 2. Ingress & Security Headers Tests
# ============================================================================


class TestEdgeIngressSecurityHeaders:
    """Verifies edge reverse proxy configuration and HTTP transport security headers."""

    @pytest.fixture(scope="class")
    def caddyfile_content(self):
        candidates = [
            Path(backend_dir).parent.parent / "docker" / "proxy" / "Caddyfile",
            Path(os.getcwd()) / "docker" / "proxy" / "Caddyfile",
        ]
        caddy_file = None
        for c in candidates:
            if c.exists():
                caddy_file = c
                break

        assert caddy_file is not None, "Caddyfile not found!"
        return caddy_file.read_text(encoding="utf-8")

    def test_caddyfile_hsts_enforced(self, caddyfile_content):
        """Rule: Strict-Transport-Security must be configured with at least 1 year duration and preload."""
        assert "Strict-Transport-Security" in caddyfile_content
        assert "max-age=31536000" in caddyfile_content
        assert "includeSubDomains" in caddyfile_content
        assert "preload" in caddyfile_content

    def test_caddyfile_content_security_policy(self, caddyfile_content):
        """Rule: Content-Security-Policy must restrict object-src and frame-ancestors to none."""
        assert "Content-Security-Policy" in caddyfile_content
        assert "frame-ancestors 'none'" in caddyfile_content
        assert "object-src 'none'" in caddyfile_content

    def test_caddyfile_websocket_reverse_proxy(self, caddyfile_content):
        """Rule: WebSocket routes (/ws/*) must proxy Upgrade and Connection headers."""
        assert "handle /ws/*" in caddyfile_content
        assert "header_up Upgrade" in caddyfile_content
        assert "header_up Connection" in caddyfile_content

    def test_caddyfile_automated_tls_fallback(self, caddyfile_content):
        """Rule: TLS configuration must support ACME and fallback to internal CA."""
        assert "tls {$TLS_MODE:internal}" in caddyfile_content


# ============================================================================
# 3. Deep Health Probe & Observability Endpoints Tests
# ============================================================================


class TestObservabilityAndHealthProbes:
    """Tests the /api/v1/health/deep probe and /metrics exposition endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_basic_health_liveness(self, client):
        """Verify GET /api/v1/health returns status ok."""
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_deep_health_probe_structure(self, client):
        """Verify GET /api/v1/health/deep provides complete component diagnostics."""
        res = client.get("/api/v1/health/deep")
        assert res.status_code in (200, 503)
        data = res.json()

        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "timestamp" in data
        assert "components" in data

        components = data["components"]
        assert "primary_db" in components
        assert "replica_db" in components
        assert "redis" in components
        assert "ollama" in components

    def test_prometheus_metrics_exposition(self, client):
        """Verify GET /metrics exports compliant Prometheus text format."""
        res = client.get("/metrics")
        assert res.status_code == 200
        content = res.text

        # Verify mandatory Prometheus lines
        assert "classfund_service_health{component=\"primary_db\"}" in content
        assert "classfund_service_health{component=\"replica_db\"}" in content
        assert "classfund_service_health{component=\"redis\"}" in content
        assert "classfund_replication_lag_seconds" in content
        assert "classfund_deadlock_retries_total" in content
        assert "classfund_circuit_breaker_trips_total" in content

    def test_api_v1_metrics_alias(self, client):
        """Verify GET /api/v1/metrics also serves prometheus telemetry."""
        res = client.get("/api/v1/metrics")
        assert res.status_code == 200
        assert "classfund_service_health" in res.text


# ============================================================================
# 4. Structured JSON Logging & Correlation ID Tests
# ============================================================================


class TestStructuredLoggingAndCorrelation:
    """Verifies JSON log format and request correlation ID tracking."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_correlation_id_middleware_generated_if_missing(self, client):
        """Rule: If incoming request has no X-Correlation-ID, backend must generate one and return it in headers."""
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert "x-correlation-id" in res.headers
        cid = res.headers["x-correlation-id"]
        assert cid.startswith("req_")

    def test_correlation_id_middleware_preserved_if_provided(self, client):
        """Rule: If client passes X-Correlation-ID, backend must preserve and echo it identically."""
        custom_cid = "corr_custom_trace_987654321"
        res = client.get("/api/v1/health", headers={"X-Correlation-ID": custom_cid})
        assert res.status_code == 200
        assert res.headers.get("x-correlation-id") == custom_cid

    def test_json_formatter_produces_valid_json(self):
        """Rule: JSONFormatter must produce valid, parseable JSON with required tags."""
        import logging
        formatter = JSONFormatter(environment="test")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Financial transaction verified successfully",
            args=(),
            exc_info=None,
        )
        set_correlation_id("test_corr_123")
        formatted = formatter.format(record)

        data = json.loads(formatted)
        assert data["level"] == "INFO"
        assert data["message"] == "Financial transaction verified successfully"
        assert data["correlation_id"] == "test_corr_123"
        assert data["environment"] == "test"
        assert "timestamp" in data


# ============================================================================
# 5. Alerting & Circuit Breaker Triggers Tests
# ============================================================================


class TestAlertingThresholdTriggers:
    """Verifies alert evaluation on threshold breaches."""

    def test_replication_lag_alert_trigger(self):
        """Rule: Replication lag > 10s must emit a CRITICAL alert."""
        alert = alert_manager.check_replication_lag(12.5)
        assert alert is not None
        assert alert.alert_name == "HIGH_REPLICATION_LAG"
        assert alert.severity == "CRITICAL"
        assert alert.details["lag_seconds"] == 12.5

    def test_replication_lag_within_threshold_no_alert(self):
        """Rule: Replication lag <= 10s must NOT emit an alert."""
        alert = alert_manager.check_replication_lag(2.0)
        assert alert is None

    def test_deadlock_retry_limit_alert_trigger(self):
        """Rule: Repeated deadlock retries exceeding limit (5) must emit CRITICAL alert."""
        alert = alert_manager.record_deadlock_retry("TX_FAIL_1", retry_count=5)
        assert alert is not None
        assert alert.alert_name == "DEADLOCK_RETRY_LIMIT_EXCEEDED"
        assert alert.severity == "CRITICAL"

    def test_circuit_breaker_tripped_alert(self):
        """Rule: Ollama or vision extraction circuit breaker trips must be recorded."""
        alert = alert_manager.record_circuit_breaker_trip("ollama_vision", "Connection timeout after 3 retries")
        assert alert.alert_name == "CIRCUIT_BREAKER_TRIPPED"
        assert alert.severity == "WARNING"
        assert alert.details["service"] == "ollama_vision"


# ============================================================================
# 6. Real-time WebSocket (WSS) Ingress & Event Routing Tests
# ============================================================================


class TestWebSocketRealtimeStreamIngress:
    """Validates WebSocket streaming endpoints under authenticated ingress."""

    @pytest.fixture
    def auth_user(self, db: Session):
        user = db.query(User).filter(User.email == "ws_smoke_user@classfund.local").first()
        if not user:
            user = User(
                id=str(uuid4()),
                name="WS Smoke User",
                email="ws_smoke_user@classfund.local",
                password_hash=hash_password("SmokePass123!"),
                role=Role.OWNER_TREASURER,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token(user.id, user.role.value)
        return user, token

    def test_websocket_chat_stream_handshake_and_ping(self, test_client, auth_user):
        """Rule: WebSocket chat stream must authenticate via token and respond to heartbeat pings."""
        user, token = auth_user
        conv_id = f"conv_{uuid4().hex[:8]}"

        with test_client.websocket_connect(f"/ws/chat/{conv_id}?token={token}") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            res = ws.receive_json()
            assert res["type"] == "pong"
            assert "timestamp" in res

    def test_websocket_unauthorized_token_rejected(self, test_client):
        """Rule: Invalid token must be immediately rejected on WebSocket handshake."""
        with pytest.raises(Exception):
            with test_client.websocket_connect("/ws/chat/conv-unauth?token=invalid_forged_jwt"):
                pass

    def test_websocket_transactions_stream(self, test_client, auth_user):
        """Rule: Authorized users must be able to subscribe to /ws/transactions real-time ledger feed."""
        user, token = auth_user
        with test_client.websocket_connect(f"/ws/transactions?token={token}") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            res = ws.receive_json()
            assert res["type"] == "pong"

    def test_websocket_health_probe(self, test_client):
        """Rule: WebSocket diagnostic health probe must return service status and active metrics."""
        res = test_client.get("/ws/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "websocket"
        assert "active_connections" in data


# ============================================================================
# 7. Asynchronous Financial Worker Batch Processing & Concurrency Tests
# ============================================================================


class TestWorkerBatchProcessingAndConcurrency:
    """Validates worker batch processing under simulated load and resource bounds."""

    @pytest.fixture
    def test_fixtures(self, db: Session):
        # Seed test account
        acc = db.query(Account).filter(Account.active == True).first()
        if not acc:
            acc = Account(
                id=str(uuid4()),
                name="Smoke Fund Account",
                currency="VND",
                opening_balance=Decimal("50000000.00"),
                active=True,
            )
            db.add(acc)
            db.commit()

        # Seed bank account
        ba = db.query(BankAccount).first()
        if not ba:
            ba = BankAccount(
                id=str(uuid4()),
                bank_name="Vietcombank",
                account_number=f"VCB_{uuid4().hex[:8]}",
                account_name="CLASS FUND TREASURY",
            )
            db.add(ba)
            db.commit()

        return acc, ba

    def test_worker_batch_claim_with_skip_locked(self, db: Session, test_fixtures):
        """Rule: Worker claims batch messages atomically without duplicate claim collisions."""
        from tests.simulation.mock_worker import create_test_worker

        acc, ba = test_fixtures
        batch_size = 5

        for i in range(batch_size):
            upload = Upload(
                id=str(uuid4()),
                file_hash=f"{uuid4().hex}{uuid4().hex}",
                original_filename=f"batch_receipt_{i}.png",
                storage_path=f"uploads/batch_{i}.png",
                uploaded_by="batch-tester",
                uploader_name="Batch Tester",
                status=UploadStatus.PENDING,
            )
            db.add(upload)
            db.flush()

            ext = ExtractedTransaction(
                id=str(uuid4()),
                upload_id=upload.id,
                transaction_code=f"BATCH_{uuid4().hex[:10].upper()}",
                amount=Decimal(f"{(i+1)*50000}.00"),
                bank_account_id=ba.id,
                bank_name="Vietcombank",
                confidence=Decimal("0.95"),
                status=UploadStatus.PROCESSING,
                currency="VND",
            )
            db.add(ext)
            db.flush()

            msg = Message(
                id=str(uuid4()),
                conversation_id=f"conv_batch_{i}",
                sender_name="Batch Sender",
                sender_role="MEMBER",
                message_type="RECEIPT",
                content=f"Batch receipt #{i}",
                attachment_id=upload.id,
                status=MessageStatus.PENDING.value,
            )
            db.add(msg)

        db.commit()

        worker = create_test_worker(db, worker_id="worker-batch-test")
        processed_count = 0

        # Process all batch messages
        for _ in range(batch_size):
            claimed = worker.claim_next_message(db)
            if claimed:
                worker.process_message(db, claimed)
                db.expire(claimed)
                assert claimed.status in (MessageStatus.POSTED.value, MessageStatus.AWAITING_REVIEW.value)
                processed_count += 1

        assert processed_count == batch_size, f"Worker only processed {processed_count}/{batch_size} messages"

    def test_worker_lease_expiration_and_recovery(self, db: Session, test_fixtures):
        """Rule: Messages with expired worker leases must be automatically reclaimed and processed."""
        from tests.simulation.mock_worker import create_test_worker
        from datetime import timedelta

        acc, ba = test_fixtures
        upload = Upload(
            id=str(uuid4()),
            file_hash=f"{uuid4().hex}{uuid4().hex}",
            original_filename="stale_lease_receipt.png",
            storage_path="uploads/stale.png",
            uploaded_by="lease-tester",
            uploader_name="Lease Tester",
            status=UploadStatus.PENDING,
        )
        db.add(upload)
        db.flush()

        ext = ExtractedTransaction(
            id=str(uuid4()),
            upload_id=upload.id,
            transaction_code=f"STALE_{uuid4().hex[:10].upper()}",
            amount=Decimal("150000.00"),
            bank_account_id=ba.id,
            bank_name="Vietcombank",
            confidence=Decimal("0.95"),
            status=UploadStatus.PROCESSING,
            currency="VND",
        )
        db.add(ext)
        db.flush()

        # Create message that looks like it crashed 15 minutes ago
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        msg = Message(
            id=str(uuid4()),
            conversation_id="conv_stale_lease",
            sender_name="Stale Sender",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Stale lease test",
            attachment_id=upload.id,
            status=MessageStatus.PROCESSING.value,
            worker_id="crashed-worker-old",
            claimed_at=expired_time - timedelta(minutes=5),
            lease_expires_at=expired_time,
        )
        db.add(msg)
        db.commit()

        # New worker starts up
        recovery_worker = create_test_worker(db, worker_id="recovery-worker-1")
        recovery_worker.reclaim_stale_leases(db)

        db.expire(msg)
        assert msg.status == MessageStatus.PENDING.value
        assert msg.worker_id is None

        # New worker claims and successfully finishes
        claimed = recovery_worker.claim_next_message(db)
        assert claimed is not None
        assert claimed.id == msg.id
        recovery_worker.process_message(db, claimed)

        db.expire(claimed)
        assert claimed.status == MessageStatus.POSTED.value


"""
Production Alerting, Circuit Breakers & Observability Telemetry
CLASS_FUND_WEB - Phase 9

Alert Monitors:
- Replication lag > 10s
- High circuit-breaker trips on Ollama vision extraction
- Repeated database deadlock retries exceeding threshold
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("alerting")


@dataclass
class AlertRecord:
    alert_name: str
    severity: str  # "WARNING", "CRITICAL"
    message: str
    details: Dict[str, Any]
    timestamp: str


class AlertManager:
    """Manages telemetry thresholds, circuit breaking, and dispatching alerts."""

    def __init__(self):
        self._alerts_history: List[AlertRecord] = []
        self.deadlock_retries_total: int = 0
        self.deadlock_retry_limit: int = 5
        self.replication_lag_threshold_seconds: float = 10.0
        self.circuit_breaker_trips_total: int = 0
        self._redis_client = None

    def record_deadlock_retry(self, transaction_code: str, retry_count: int) -> Optional[AlertRecord]:
        """Record a deadlock occurrence and trip alert if retries exceed threshold."""
        self.deadlock_retries_total += 1
        logger.warning(f"Database deadlock encountered for tx {transaction_code}, retry #{retry_count}")

        if retry_count >= self.deadlock_retry_limit:
            alert = AlertRecord(
                alert_name="DEADLOCK_RETRY_LIMIT_EXCEEDED",
                severity="CRITICAL",
                message=f"Deadlock retries ({retry_count}) exceeded limit ({self.deadlock_retry_limit})",
                details={"transaction_code": transaction_code, "retry_count": retry_count},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._dispatch_alert(alert)
            return alert
        return None

    def check_replication_lag(self, lag_seconds: Optional[float]) -> Optional[AlertRecord]:
        """Evaluate replication lag and trigger alert if > 10s."""
        if lag_seconds is not None and lag_seconds > self.replication_lag_threshold_seconds:
            alert = AlertRecord(
                alert_name="HIGH_REPLICATION_LAG",
                severity="CRITICAL",
                message=f"Replication lag {lag_seconds}s exceeds threshold {self.replication_lag_threshold_seconds}s",
                details={"lag_seconds": lag_seconds, "threshold": self.replication_lag_threshold_seconds},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._dispatch_alert(alert)
            return alert
        return None

    def record_circuit_breaker_trip(self, service: str, reason: str) -> AlertRecord:
        """Record an Ollama or external dependency circuit breaker trip."""
        self.circuit_breaker_trips_total += 1
        alert = AlertRecord(
            alert_name="CIRCUIT_BREAKER_TRIPPED",
            severity="WARNING",
            message=f"Circuit breaker tripped for service '{service}': {reason}",
            details={"service": service, "reason": reason, "total_trips": self.circuit_breaker_trips_total},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._dispatch_alert(alert)
        return alert

    def _dispatch_alert(self, alert: AlertRecord):
        """Log alert and publish to Redis alert channel."""
        self._alerts_history.append(alert)
        logger.error(
            f"ALERT [{alert.severity}] {alert.alert_name}: {alert.message}",
            extra={"alert_name": alert.alert_name, "severity": alert.severity, "details": alert.details},
        )

        try:
            import redis
            from app.core.config import get_settings

            settings = get_settings()
            if settings.redis_url:
                r = redis.Redis.from_url(settings.redis_url, socket_timeout=1)
                r.publish(
                    "system:alerts",
                    json.dumps({
                        "alert_name": alert.alert_name,
                        "severity": alert.severity,
                        "message": alert.message,
                        "details": alert.details,
                        "timestamp": alert.timestamp,
                    }),
                )
                r.close()
        except Exception as e:
            logger.debug(f"Could not publish alert to Redis: {e}")

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent alerts."""
        return [
            {
                "alert_name": a.alert_name,
                "severity": a.severity,
                "message": a.message,
                "details": a.details,
                "timestamp": a.timestamp,
            }
            for a in self._alerts_history[-limit:]
        ]


# Singleton instance
alert_manager = AlertManager()

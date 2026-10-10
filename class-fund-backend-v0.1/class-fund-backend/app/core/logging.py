"""
Structured JSON Logging & Correlation ID Tracking
CLASS_FUND_WEB - Phase 9 Production Observability
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import time
import uuid
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for request-bound telemetry
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
worker_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("worker_id", default="")
transaction_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("transaction_id", default="")


def get_correlation_id() -> str:
    """Retrieve current correlation ID or empty string."""
    return correlation_id_ctx.get()


def set_correlation_id(cid: str) -> None:
    """Set current correlation ID."""
    correlation_id_ctx.set(cid)


class JSONFormatter(logging.Formatter):
    """Formats log records as structured, single-line JSON objects."""

    def __init__(self, environment: Optional[str] = None):
        super().__init__()
        self.environment = environment or os.environ.get("ENVIRONMENT", "production")

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": self.environment,
            "correlation_id": correlation_id_ctx.get() or getattr(record, "correlation_id", None),
            "worker_id": worker_id_ctx.get() or getattr(record, "worker_id", None),
            "transaction_id": transaction_id_ctx.get() or getattr(record, "transaction_id", None),
            "source": f"{record.filename}:{record.lineno}",
        }

        # Include custom extra kwargs if present
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName", "environment", "correlation_id", "worker_id", "transaction_id", "source"
            ):
                if not key.startswith("_"):
                    try:
                        json.dumps(val)  # Test serialization
                        log_obj[key] = val
                    except Exception:
                        log_obj[key] = str(val)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_structured_logging(level: int = logging.INFO, environment: Optional[str] = None) -> None:
    """Configure root logger with structured JSON handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(environment=environment))
    root_logger.addHandler(handler)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware that enforces X-Correlation-ID header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
        if not cid:
            cid = f"req_{uuid4().hex}"

        set_correlation_id(cid)
        request.state.correlation_id = cid

        start_time = time.time()
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            duration_ms = (time.time() - start_time) * 1000
            # Optional access log record
            logger = logging.getLogger("access")
            logger.info(
                f"{request.method} {request.url.path} completed in {duration_ms:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                },
            )

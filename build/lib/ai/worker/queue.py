from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import redis
from celery import Celery, Task
from celery.signals import task_failure, task_retry, task_success, worker_ready

from ai.contracts import UploadMetadata, VerificationResult
from ai.verification.service import VerificationPolicy, VerificationService


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


@dataclass
class QueueConfig:
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "verification_jobs"
    max_retries: int = 3
    retry_delay: int = 60
    task_timeout: int = 300
    result_ttl: int = 86400


class VerificationWorker:
    def __init__(
        self,
        verification_service: VerificationService,
        config: QueueConfig | None = None,
    ) -> None:
        self.verification_service = verification_service
        self.config = config or QueueConfig()
        self.redis_client = redis.from_url(self.config.redis_url, decode_responses=True)

    def enqueue_job(
        self,
        upload_id: uuid.UUID,
        image_bytes: bytes,
        metadata: UploadMetadata,
        priority: int = 0,
    ) -> str:
        job_id = str(uuid.uuid4())

        job_data = {
            "job_id": job_id,
            "upload_id": str(upload_id),
            "image_data": image_bytes.hex(),
            "metadata": metadata.model_dump(),
            "status": JobStatus.QUEUED.value,
            "priority": priority,
            "attempt": 1,
            "created_at": datetime.utcnow().isoformat(),
        }

        self.redis_client.lpush(f"{self.config.queue_name}:pending", json.dumps(job_data))
        self.redis_client.hset(f"{self.config.queue_name}:jobs", job_id, json.dumps(job_data))

        return job_id

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        data = self.redis_client.hget(f"{self.config.queue_name}:jobs", job_id)
        if data:
            return json.loads(data)
        return None

    def get_job_result(self, job_id: str) -> VerificationResult | None:
        data = self.redis_client.hget(f"{self.config.queue_name}:results", job_id)
        if data:
            return VerificationResult.model_validate_json(data)
        return None


celery_app = Celery("verification_worker")

celery_app.conf.update(
    broker_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="verification",
    task_routes={
        "ai.worker.tasks.process_verification": {"queue": "verification"},
    },
)


class VerificationTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def __init__(self) -> None:
        super().__init__()
        self._verification_service: VerificationService | None = None

    @property
    def verification_service(self) -> VerificationService:
        if self._verification_service is None:
            from ai.duplicate.service import DuplicateDetector
            from ai.extraction.service import ExtractionService
            from ai.matching.service import MatchingService
            from ai.ocr.service import OCRService
            from ai.verification.service import VerificationPolicy, VerificationService

            ocr_service = OCRService()
            extraction_service = ExtractionService()
            matching_service = MatchingService(roster=[])
            duplicate_detector = DuplicateDetector()
            policy = VerificationPolicy()

            self._verification_service = VerificationService(
                ocr_service=ocr_service,
                extraction_service=extraction_service,
                matching_service=matching_service,
                duplicate_detector=duplicate_detector,
                policy=policy,
            )
        return self._verification_service

    def set_services(
        self,
        ocr_service,
        extraction_service,
        matching_service,
        duplicate_detector,
        policy: VerificationPolicy | None = None,
    ) -> None:
        self._verification_service = VerificationService(
            ocr_service=ocr_service,
            extraction_service=extraction_service,
            matching_service=matching_service,
            duplicate_detector=duplicate_detector,
            policy=policy or VerificationPolicy(),
        )


@celery_app.task(bind=True, base=VerificationTask, name="ai.worker.tasks.process_verification")
def process_verification_task(
    self,
    upload_id: str,
    image_data_hex: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    import time

    start_time = time.perf_counter()

    try:
        image_bytes = bytes.fromhex(image_data_hex)

        self.update_state(
            state="PROCESSING",
            meta={"stage": "ocr", "progress": 10},
        )

        result = self.verification_service.verify(
            upload_id=upload_id,
            image_bytes=image_bytes,
        )

        processing_time = int((time.perf_counter() - start_time) * 1000)

        self.update_state(
            state="SUCCESS",
            meta={"stage": "completed", "progress": 100},
        )

        return {
            "job_id": self.request.id,
            "upload_id": upload_id,
            "status": result.status.value,
            "confidence": result.confidence,
            "verification_result": result.model_dump(),
            "processing_time_ms": processing_time,
        }

    except Exception as exc:
        processing_time = int((time.perf_counter() - start_time) * 1000)

        self.update_state(
            state="FAILURE",
            meta={
                "stage": "failed",
                "error": str(exc),
                "processing_time_ms": processing_time,
            },
        )
        raise


@celery_app.task(bind=True, name="ai.worker.tasks.retry_verification")
def retry_verification_task(
    self,
    upload_id: str,
    image_data_hex: str,
    metadata: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    return process_verification_task.apply_async(
        args=[upload_id, image_data_hex, metadata],
        countdown=60 * attempt,
    )


@worker_ready.connect
def on_worker_ready(**kwargs):
    pass


@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    if result and isinstance(result, dict) and "verification_result" in result:
        pass


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    pass


@task_retry.connect
def on_task_retry(sender=None, request=None, reason=None, einfo=None, **kwargs):
    pass


def create_celery_app() -> Celery:
    return celery_app

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class ExtractionEvidence(BaseModel):
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str
    source_span: tuple[int, int] | None = None
    rule: str | None = None


class AmountExtraction(BaseModel):
    amount: int
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    currency: str = "VND"


class TransactionCodeExtraction(BaseModel):
    code: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    bank_pattern: str | None = None


class SenderExtraction(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    candidates: list[str] = Field(default_factory=list)


class BankExtraction(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    code: str | None = None


class DateTimeExtraction(BaseModel):
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    timezone: str | None = None


class OCRResult(BaseModel):
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_boxes: list[dict[str, Any]] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    words: list[dict[str, Any]] = Field(default_factory=list)
    engine: str
    engine_version: str
    processing_time_ms: int


class StudentMatch(BaseModel):
    student_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_name: str
    candidate_list: list[dict[str, Any]] = Field(default_factory=list)
    match_method: str


class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    layer: str
    confidence: float = Field(ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)
    matched_upload_id: str | None = None


class ExtractionResult(BaseModel):
    amount: AmountExtraction | None = None
    transaction_code: TransactionCodeExtraction | None = None
    sender: SenderExtraction | None = None
    bank: BankExtraction | None = None
    datetime: DateTimeExtraction | None = None
    raw_extractions: dict[str, Any] = Field(default_factory=dict)


class RiskFlag(StrEnum):
    MISSING_TRANSACTION_CODE = "MISSING_TRANSACTION_CODE"
    MISSING_AMOUNT = "MISSING_AMOUNT"
    ABNORMAL_TEXT = "ABNORMAL_TEXT"
    ABNORMAL_TIMESTAMP = "ABNORMAL_TIMESTAMP"
    SENDER_MISMATCH = "SENDER_MISMATCH"
    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT"
    INCONSISTENT_FIELDS = "INCONSISTENT_FIELDS"


class VerificationResult(BaseModel):
    upload_id: uuid.UUID
    transaction_code: str | None = None
    amount: int | None = None
    sender_name: str | None = None
    bank_name: str | None = None
    transaction_time: datetime | None = None
    student_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    status: VerificationStatus
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    ocr_version: str = "1.0.0"
    extractor_version: str = "1.0.0"
    matcher_version: str = "1.0.0"
    preprocessor_version: str = "1.0.0"
    verification_policy_version: str = "1.0.0"
    evidence: dict[str, Any] = Field(default_factory=dict)
    duplicate_checks: list[DuplicateCheckResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str | VerificationStatus) -> VerificationStatus:
        if isinstance(v, str):
            return VerificationStatus(v.upper())
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    def model_dump_json(self, **kwargs: Any) -> str:
        return super().model_dump_json(**kwargs)


class ProcessingJob(BaseModel):
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    upload_id: uuid.UUID
    attempt: int = 1
    status: VerificationStatus = VerificationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    processing_version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class UploadMetadata(BaseModel):
    upload_id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    file_hash: str
    perceptual_hash: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: str | None = None

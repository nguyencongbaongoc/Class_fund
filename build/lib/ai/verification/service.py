from __future__ import annotations

from dataclasses import dataclass

from ai.contracts import (
    DuplicateCheckResult,
    ExtractionResult,
    OCRResult,
    RiskFlag,
    StudentMatch,
    VerificationResult,
    VerificationStatus,
)
from ai.duplicate.service import DuplicateDetector
from ai.extraction.service import ExtractionService
from ai.matching.service import MatchingService
from ai.ocr.service import OCRService


@dataclass
class VerificationPolicy:
    min_confidence_threshold: float = 0.75
    require_transaction_code: bool = True
    require_amount: bool = True
    require_sender_match: bool = True
    require_student_match: bool = True
    min_ocr_confidence: float = 0.5
    min_extraction_confidence: float = 0.6
    min_matching_confidence: float = 0.7


class VerificationService:
    def __init__(
        self,
        ocr_service: OCRService,
        extraction_service: ExtractionService,
        matching_service: MatchingService,
        duplicate_detector: DuplicateDetector,
        policy: VerificationPolicy | None = None,
    ) -> None:
        self.ocr_service = ocr_service
        self.extraction_service = extraction_service
        self.matching_service = matching_service
        self.duplicate_detector = duplicate_detector
        self.policy = policy or VerificationPolicy()

    def verify(
        self,
        upload_id: str,
        image_bytes: bytes,
        preprocess_strategy: str = "default",
    ) -> VerificationResult:
        import time
        start_time = time.perf_counter()

        ocr_result = self.ocr_service.process(image_bytes, preprocess_strategy=preprocess_strategy)
        extraction_result = self.extraction_service.extract_all(ocr_result)

        student_match = None
        if extraction_result.sender:
            student_match = self.matching_service.match_sender(extraction_result.sender)

        partial_verification = self._build_partial_verification(
            upload_id, ocr_result, extraction_result, student_match
        )

        duplicate_checks = self.duplicate_detector.check_all(image_bytes, partial_verification)

        is_duplicate = any(dc.is_duplicate for dc in duplicate_checks)

        risk_flags = self._analyze_risk_flags(
            ocr_result, extraction_result, student_match, duplicate_checks
        )

        status = self._determine_status(
            ocr_result, extraction_result, student_match, is_duplicate, risk_flags
        )

        final_confidence = self._calculate_final_confidence(
            ocr_result, extraction_result, student_match, risk_flags
        )

        processing_time = int((time.perf_counter() - start_time) * 1000)

        result = VerificationResult(
            upload_id=upload_id,
            transaction_code=extraction_result.transaction_code.code if extraction_result.transaction_code else None,
            amount=extraction_result.amount.amount if extraction_result.amount else None,
            sender_name=extraction_result.sender.name if extraction_result.sender else None,
            bank_name=extraction_result.bank.name if extraction_result.bank else None,
            transaction_time=extraction_result.datetime.timestamp if extraction_result.datetime else None,
            student_id=student_match.student_id if student_match else None,
            confidence=final_confidence,
            status=status,
            risk_flags=risk_flags,
            evidence={
                "ocr": ocr_result.model_dump(),
                "extraction": extraction_result.raw_extractions,
                "matching": student_match.model_dump() if student_match else None,
                "duplicate_checks": [dc.model_dump() for dc in duplicate_checks],
            },
            duplicate_checks=duplicate_checks,
            processing_time_ms=processing_time,
        )

        if not is_duplicate:
            self.duplicate_detector.register(image_bytes, result)

        return result

    def _build_partial_verification(
        self,
        upload_id: str,
        ocr_result: OCRResult,
        extraction_result: ExtractionResult,
        student_match: StudentMatch | None,
    ) -> VerificationResult:
        return VerificationResult(
            upload_id=upload_id,
            transaction_code=extraction_result.transaction_code.code if extraction_result.transaction_code else None,
            amount=extraction_result.amount.amount if extraction_result.amount else None,
            sender_name=extraction_result.sender.name if extraction_result.sender else None,
            bank_name=extraction_result.bank.name if extraction_result.bank else None,
            transaction_time=extraction_result.datetime.timestamp if extraction_result.datetime else None,
            student_id=student_match.student_id if student_match else None,
            confidence=0.0,
            status=VerificationStatus.PROCESSING,
        )

    def _analyze_risk_flags(
        self,
        ocr_result: OCRResult,
        extraction_result: ExtractionResult,
        student_match: StudentMatch | None,
        duplicate_checks: list[DuplicateCheckResult],
    ) -> list[RiskFlag]:
        flags = []

        if not extraction_result.transaction_code:
            flags.append(RiskFlag.MISSING_TRANSACTION_CODE)

        if not extraction_result.amount:
            flags.append(RiskFlag.MISSING_AMOUNT)

        if ocr_result.confidence < self.policy.min_ocr_confidence:
            flags.append(RiskFlag.LOW_IMAGE_QUALITY)

        if extraction_result.sender and student_match is None:
            flags.append(RiskFlag.SENDER_MISMATCH)

        if extraction_result.sender and student_match and student_match.confidence < self.policy.min_matching_confidence:
            flags.append(RiskFlag.SENDER_MISMATCH)

        if any(dc.is_duplicate for dc in duplicate_checks):
            flags.append(RiskFlag.DUPLICATE_RECEIPT)

        if extraction_result.amount and extraction_result.transaction_code:
            if extraction_result.amount.confidence < self.policy.min_extraction_confidence:
                flags.append(RiskFlag.INCONSISTENT_FIELDS)
            if extraction_result.transaction_code.confidence < self.policy.min_extraction_confidence:
                flags.append(RiskFlag.INCONSISTENT_FIELDS)

        if extraction_result.datetime:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            if extraction_result.datetime.timestamp > now + timedelta(days=1):
                flags.append(RiskFlag.ABNORMAL_TIMESTAMP)
            if extraction_result.datetime.timestamp < now - timedelta(days=365 * 2):
                flags.append(RiskFlag.ABNORMAL_TIMESTAMP)

        if ocr_result.raw_text and len(ocr_result.raw_text.strip()) < 20:
            flags.append(RiskFlag.ABNORMAL_TEXT)

        return flags

    def _determine_status(
        self,
        ocr_result: OCRResult,
        extraction_result: ExtractionResult,
        student_match: StudentMatch | None,
        is_duplicate: bool,
        risk_flags: list[RiskFlag],
    ) -> VerificationStatus:
        if is_duplicate:
            return VerificationStatus.DUPLICATE

        if RiskFlag.MISSING_TRANSACTION_CODE in risk_flags and self.policy.require_transaction_code:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.MISSING_AMOUNT in risk_flags and self.policy.require_amount:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.SENDER_MISMATCH in risk_flags and self.policy.require_sender_match:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.LOW_IMAGE_QUALITY in risk_flags:
            return VerificationStatus.NEEDS_REVIEW

        if self.policy.require_student_match and student_match is None:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.ABNORMAL_TIMESTAMP in risk_flags:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.ABNORMAL_TEXT in risk_flags:
            return VerificationStatus.NEEDS_REVIEW

        if RiskFlag.INCONSISTENT_FIELDS in risk_flags:
            return VerificationStatus.NEEDS_REVIEW

        return VerificationStatus.VERIFIED

    def _calculate_final_confidence(
        self,
        ocr_result: OCRResult,
        extraction_result: ExtractionResult,
        student_match: StudentMatch | None,
        risk_flags: list[RiskFlag],
    ) -> float:
        weights = {
            "ocr": 0.2,
            "extraction": 0.3,
            "matching": 0.3,
            "duplicate": 0.2,
        }

        ocr_conf = ocr_result.confidence

        extraction_confs = []
        if extraction_result.amount:
            extraction_confs.append(extraction_result.amount.confidence)
        if extraction_result.transaction_code:
            extraction_confs.append(extraction_result.transaction_code.confidence)
        if extraction_result.sender:
            extraction_confs.append(extraction_result.sender.confidence)
        if extraction_result.bank:
            extraction_confs.append(extraction_result.bank.confidence)
        if extraction_result.datetime:
            extraction_confs.append(extraction_result.datetime.confidence)

        extraction_conf = sum(extraction_confs) / len(extraction_confs) if extraction_confs else 0.0

        matching_conf = student_match.confidence if student_match else 0.0

        duplicate_conf = 1.0
        if RiskFlag.DUPLICATE_RECEIPT in risk_flags:
            duplicate_conf = 0.0

        final = (
            weights["ocr"] * ocr_conf +
            weights["extraction"] * extraction_conf +
            weights["matching"] * matching_conf +
            weights["duplicate"] * duplicate_conf
        )

        if risk_flags:
            penalty = min(len(risk_flags) * 0.05, 0.3)
            final = max(0.0, final - penalty)

        return round(final, 4)

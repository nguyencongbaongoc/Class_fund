import uuid
from datetime import datetime

from ai.contracts import (
    AmountExtraction,
    DuplicateCheckResult,
    ExtractionEvidence,
    OCRResult,
    ProcessingJob,
    RiskFlag,
    StudentMatch,
    UploadMetadata,
    VerificationResult,
    VerificationStatus,
)


class TestVerificationResult:
    def test_valid_verification_result(self):
        result = VerificationResult(
            upload_id=uuid.uuid4(),
            transaction_code="FT123456789",
            amount=50000,
            sender_name="NGUYEN VAN A",
            bank_name="MB Bank",
            transaction_time=datetime.now(),
            student_id="student-123",
            confidence=0.95,
            status=VerificationStatus.VERIFIED,
        )
        assert result.status == VerificationStatus.VERIFIED
        assert result.confidence == 0.95
        assert result.amount == 50000

    def test_confidence_clamping(self):
        result = VerificationResult(
            upload_id=uuid.uuid4(),
            confidence=1.5,
            status=VerificationStatus.VERIFIED,
        )
        assert result.confidence == 1.0

        result2 = VerificationResult(
            upload_id=uuid.uuid4(),
            confidence=-0.5,
            status=VerificationStatus.VERIFIED,
        )
        assert result2.confidence == 0.0

    def test_status_case_insensitive(self):
        result = VerificationResult(
            upload_id=uuid.uuid4(),
            confidence=0.9,
            status="verified",
        )
        assert result.status == VerificationStatus.VERIFIED

    def test_serialization(self):
        result = VerificationResult(
            upload_id=uuid.uuid4(),
            transaction_code="FT123456789",
            amount=50000,
            confidence=0.95,
            status=VerificationStatus.VERIFIED,
        )
        json_str = result.model_dump_json()
        assert "FT123456789" in json_str
        assert "50000" in json_str

    def test_risk_flags(self):
        result = VerificationResult(
            upload_id=uuid.uuid4(),
            confidence=0.9,
            status=VerificationStatus.NEEDS_REVIEW,
            risk_flags=[RiskFlag.MISSING_TRANSACTION_CODE, RiskFlag.LOW_IMAGE_QUALITY],
        )
        assert RiskFlag.MISSING_TRANSACTION_CODE in result.risk_flags
        assert RiskFlag.LOW_IMAGE_QUALITY in result.risk_flags


class TestExtractionEvidence:
    def test_valid_evidence(self):
        evidence = ExtractionEvidence(
            value="50000",
            confidence=0.9,
            source_text="Số tiền: 50.000 VND",
            source_span=(10, 25),
            rule="vnd_suffix",
        )
        assert evidence.value == "50000"
        assert evidence.confidence == 0.9


class TestAmountExtraction:
    def test_valid_amount(self):
        evidence = ExtractionEvidence(
            value="50000",
            confidence=0.95,
            source_text="50.000 VND",
            rule="vnd_suffix",
        )
        amount = AmountExtraction(amount=50000, confidence=0.95, evidence=evidence)
        assert amount.amount == 50000
        assert amount.currency == "VND"


class TestOCRResult:
    def test_valid_ocr_result(self):
        ocr = OCRResult(
            raw_text="Test text",
            confidence=0.85,
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )
        assert ocr.raw_text == "Test text"
        assert ocr.confidence == 0.85


class TestStudentMatch:
    def test_valid_match(self):
        match = StudentMatch(
            student_id="student-123",
            confidence=0.94,
            matched_name="Nguyễn Văn An",
            match_method="fuzzy",
        )
        assert match.student_id == "student-123"
        assert match.confidence == 0.94


class TestDuplicateCheckResult:
    def test_duplicate_found(self):
        result = DuplicateCheckResult(
            is_duplicate=True,
            layer="file_hash",
            confidence=1.0,
            details={"hash": "abc123"},
            matched_upload_id="upload-456",
        )
        assert result.is_duplicate is True
        assert result.layer == "file_hash"
        assert result.matched_upload_id == "upload-456"


class TestProcessingJob:
    def test_default_values(self):
        job = ProcessingJob(upload_id=uuid.uuid4())
        assert job.status == VerificationStatus.PENDING
        assert job.attempt == 1
        assert job.job_id is not None


class TestUploadMetadata:
    def test_valid_metadata(self):
        metadata = UploadMetadata(
            upload_id=uuid.uuid4(),
            filename="receipt.jpg",
            content_type="image/jpeg",
            file_size=102400,
            file_hash="abc123",
        )
        assert metadata.filename == "receipt.jpg"
        assert metadata.content_type == "image/jpeg"

import uuid
from unittest.mock import Mock

from ai.contracts import (
    AmountExtraction,
    BankExtraction,
    DateTimeExtraction,
    DuplicateCheckResult,
    ExtractionEvidence,
    ExtractionResult,
    OCRResult,
    RiskFlag,
    SenderExtraction,
    StudentMatch,
    TransactionCodeExtraction,
    VerificationStatus,
)
from ai.duplicate.service import DuplicateDetector
from ai.extraction.service import ExtractionService
from ai.matching.service import MatchingService
from ai.ocr.service import OCRService
from ai.verification.service import VerificationPolicy, VerificationService


class TestVerificationPolicy:
    def test_default_policy(self):
        policy = VerificationPolicy()
        assert policy.min_confidence_threshold == 0.75
        assert policy.require_transaction_code is True
        assert policy.require_amount is True
        assert policy.require_sender_match is True
        assert policy.require_student_match is True


class TestVerificationService:
    def setup_method(self):
        self.ocr_service = Mock(spec=OCRService)
        self.extraction_service = Mock(spec=ExtractionService)
        self.matching_service = Mock(spec=MatchingService)
        self.duplicate_detector = Mock(spec=DuplicateDetector)
        self.policy = VerificationPolicy()
        self.service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=self.duplicate_detector,
            policy=self.policy,
        )

    def create_mock_ocr(self, text="Test", confidence=0.9):
        return OCRResult(
            raw_text=text,
            confidence=confidence,
            lines=[text],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )

    def create_mock_extraction(self, amount=None, txn_code=None, sender=None, bank=None, dt=None):
        evidence = ExtractionEvidence(value="test", confidence=0.9, source_text="test")
        return ExtractionResult(
            amount=AmountExtraction(amount=amount, confidence=0.9, evidence=evidence) if amount else None,
            transaction_code=TransactionCodeExtraction(code=txn_code, confidence=0.9, evidence=evidence) if txn_code else None,
            sender=SenderExtraction(name=sender, confidence=0.9, evidence=evidence) if sender else None,
            bank=BankExtraction(name=bank, confidence=0.9, evidence=evidence) if bank else None,
            datetime=DateTimeExtraction(timestamp=dt, confidence=0.9, evidence=evidence) if dt else None,
            raw_extractions={},
        )

    def create_mock_student_match(self, student_id="student-1", confidence=0.95):
        return StudentMatch(
            student_id=student_id,
            confidence=confidence,
            matched_name="Test Student",
            match_method="exact",
        )

    def test_verify_verified(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt with enough text content", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]
        self.duplicate_detector.register = Mock()

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.VERIFIED
        assert result.confidence > 0.7
        assert result.amount == 50000
        assert result.transaction_code == "FT123456789"
        assert result.student_id == "student-1"

    def test_verify_needs_review_missing_transaction_code(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert RiskFlag.MISSING_TRANSACTION_CODE in result.risk_flags

    def test_verify_needs_review_missing_amount(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert RiskFlag.MISSING_AMOUNT in result.risk_flags

    def test_verify_needs_review_sender_mismatch(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="UNKNOWN PERSON", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = None
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert RiskFlag.SENDER_MISMATCH in result.risk_flags

    def test_verify_duplicate(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=True, layer="file_hash", confidence=1.0, details={}, matched_upload_id="other-upload"),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.DUPLICATE
        assert RiskFlag.DUPLICATE_RECEIPT in result.risk_flags

    def test_verify_low_ocr_confidence(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.3)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert RiskFlag.LOW_IMAGE_QUALITY in result.risk_flags

    def test_verify_confidence_calculation(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match(confidence=0.95)
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]
        self.duplicate_detector.register = Mock()

        result = self.service.verify(upload_id, image_bytes)

        assert result.confidence > 0.8
        assert result.confidence <= 1.0

    def test_risk_flags_abnormal_timestamp_future(self):
        from datetime import datetime, timedelta
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        future_time = datetime.utcnow() + timedelta(days=10)

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank", dt=future_time
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert RiskFlag.ABNORMAL_TIMESTAMP in result.risk_flags

    def test_risk_flags_abnormal_timestamp_past(self):
        from datetime import datetime, timedelta
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        past_time = datetime.utcnow() - timedelta(days=800)

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank", dt=past_time
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]

        result = self.service.verify(upload_id, image_bytes)

        assert RiskFlag.ABNORMAL_TIMESTAMP in result.risk_flags

    def test_evidence_in_result(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]
        self.duplicate_detector.register = Mock()

        result = self.service.verify(upload_id, image_bytes)

        assert "ocr" in result.evidence
        assert "extraction" in result.evidence
        assert "matching" in result.evidence
        assert "duplicate_checks" in result.evidence

    def test_processing_time_recorded(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test receipt with enough text content for processing", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]
        self.duplicate_detector.register = Mock()

        result = self.service.verify(upload_id, image_bytes)

        # processing_time_ms should be >= 0 (can be 0 in fast mock tests)
        assert result.processing_time_ms >= 0

    def test_version_fields_present(self):
        upload_id = str(uuid.uuid4())
        image_bytes = b"fake image"

        self.ocr_service.process.return_value = self.create_mock_ocr("Test", 0.9)
        self.extraction_service.extract_all.return_value = self.create_mock_extraction(
            amount=50000, txn_code="FT123456789", sender="NGUYEN VAN A", bank="MB Bank"
        )
        self.matching_service.match_sender.return_value = self.create_mock_student_match()
        self.duplicate_detector.check_all.return_value = [
            DuplicateCheckResult(is_duplicate=False, layer="file_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="perceptual_hash", confidence=1.0, details={}),
            DuplicateCheckResult(is_duplicate=False, layer="transaction_identity", confidence=1.0, details={}),
        ]
        self.duplicate_detector.register = Mock()

        result = self.service.verify(upload_id, image_bytes)

        assert result.ocr_version == "1.0.0"
        assert result.extractor_version == "1.0.0"
        assert result.matcher_version == "1.0.0"
        assert result.preprocessor_version == "1.0.0"
        assert result.verification_policy_version == "1.0.0"

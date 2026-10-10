import uuid
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from ai.contracts import (
    OCRResult,
    RiskFlag,
    VerificationStatus,
)
from ai.duplicate.service import DuplicateDetector
from ai.extraction.service import ExtractionService
from ai.matching.service import MatchingService, StudentRecord
from ai.ocr.service import OCRService, TesseractEngine
from ai.verification.service import VerificationPolicy, VerificationService


def create_test_image():
    image = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class TestFullPipeline:
    def setup_method(self):
        self.ocr_service = OCRService()
        self.extraction_service = ExtractionService()
        self.matching_service = MatchingService([
            StudentRecord(student_id="student-1", full_name="Nguyễn Văn An"),
            StudentRecord(student_id="student-2", full_name="Trần Thị Bích"),
        ])
        self.duplicate_detector = DuplicateDetector()
        self.policy = VerificationPolicy()
        self.service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=self.duplicate_detector,
            policy=self.policy,
        )

    @patch.object(TesseractEngine, "recognize")
    def test_full_pipeline_valid_receipt(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK\n25/12/2024 14:30:00",
            confidence=0.85,
            lines=[
                "Người gửi: NGUYEN VAN AN",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
                "25/12/2024 14:30:00",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        upload_id = str(uuid.uuid4())
        image_bytes = create_test_image()

        result = self.service.verify(upload_id, image_bytes)

        assert result.status in [VerificationStatus.VERIFIED, VerificationStatus.NEEDS_REVIEW]
        assert result.transaction_code == "FT1234567890"
        assert result.amount == 50000
        assert result.sender_name == "NGUYEN VAN AN"
        assert result.bank_name == "MB Bank"
        assert result.student_id == "student-1"
        assert result.confidence > 0

    @patch.object(TesseractEngine, "recognize")
    def test_full_pipeline_missing_fields(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND",
            confidence=0.85,
            lines=["Người gửi: NGUYEN VAN AN", "Số tiền: 50.000 VND"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        upload_id = str(uuid.uuid4())
        image_bytes = create_test_image()

        result = self.service.verify(upload_id, image_bytes)

        assert result.status == VerificationStatus.NEEDS_REVIEW
        assert RiskFlag.MISSING_TRANSACTION_CODE in result.risk_flags
        assert RiskFlag.SENDER_MISMATCH not in result.risk_flags

    @patch.object(TesseractEngine, "recognize")
    def test_full_pipeline_duplicate_detection(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK",
            confidence=0.85,
            lines=[
                "Người gửi: NGUYEN VAN AN",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        upload_id1 = str(uuid.uuid4())
        upload_id2 = str(uuid.uuid4())
        image_bytes = create_test_image()

        result1 = self.service.verify(upload_id1, image_bytes)
        result2 = self.service.verify(upload_id2, image_bytes)

        assert result1.status != VerificationStatus.DUPLICATE
        assert result2.status == VerificationStatus.DUPLICATE
        assert RiskFlag.DUPLICATE_RECEIPT in result2.risk_flags


class TestConcurrencyScenarios:
    def setup_method(self):
        self.ocr_service = OCRService()
        self.extraction_service = ExtractionService()
        self.matching_service = MatchingService([
            StudentRecord(student_id="student-1", full_name="Nguyễn Văn An"),
        ])
        self.policy = VerificationPolicy()

    @patch.object(TesseractEngine, "recognize")
    def test_same_upload_processed_twice(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK",
            confidence=0.85,
            lines=[
                "Người gửi: NGUYEN VAN AN",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        duplicate_detector = DuplicateDetector()
        service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=duplicate_detector,
            policy=self.policy,
        )

        upload_id = str(uuid.uuid4())
        image_bytes = create_test_image()

        result1 = service.verify(upload_id, image_bytes)
        result2 = service.verify(upload_id, image_bytes)

        assert result1.status != VerificationStatus.DUPLICATE
        assert result2.status == VerificationStatus.DUPLICATE

    @patch.object(TesseractEngine, "recognize")
    def test_same_transaction_code_different_images(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK",
            confidence=0.85,
            lines=[
                "Người gửi: NGUYEN VAN AN",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        duplicate_detector = DuplicateDetector()
        service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=duplicate_detector,
            policy=self.policy,
        )

        upload_id1 = str(uuid.uuid4())
        upload_id2 = str(uuid.uuid4())

        image1 = Image.new("RGB", (800, 600), color="white")
        buffer1 = BytesIO()
        image1.save(buffer1, format="PNG")
        image_bytes1 = buffer1.getvalue()

        image2 = Image.new("RGB", (800, 600), color="lightgray")
        buffer2 = BytesIO()
        image2.save(buffer2, format="PNG")
        image_bytes2 = buffer2.getvalue()

        result1 = service.verify(upload_id1, image_bytes1)
        result2 = service.verify(upload_id2, image_bytes2)

        assert result1.status != VerificationStatus.DUPLICATE
        assert result2.status == VerificationStatus.DUPLICATE

    @patch.object(TesseractEngine, "recognize")
    def test_different_transaction_codes_same_image_hash(self, mock_recognize):
        # Use an iterator that cycles through the two results
        call_count = [0]
        def side_effect(*args, **kwargs):
            if call_count[0] % 12 < 6:  # First 6 calls (first verify) -> first result
                call_count[0] += 1
                return OCRResult(
                    raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT111111111\nMB BANK",
                    confidence=0.85,
                    lines=["Người gửi: NGUYEN VAN AN", "Số tiền: 50.000 VND", "Mã GD: FT111111111", "MB BANK"],
                    engine="tesseract",
                    engine_version="5.3.0",
                    processing_time_ms=1500,
                )
            else:  # Next calls (second verify) -> second result
                call_count[0] += 1
                return OCRResult(
                    raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT222222222\nMB BANK",
                    confidence=0.85,
                    lines=["Người gửi: NGUYEN VAN AN", "Số tiền: 50.000 VND", "Mã GD: FT222222222", "MB BANK"],
                    engine="tesseract",
                    engine_version="5.3.0",
                    processing_time_ms=1500,
                )
        mock_recognize.side_effect = side_effect

        duplicate_detector = DuplicateDetector()
        service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=duplicate_detector,
            policy=self.policy,
        )

        image_bytes = create_test_image()
        upload_id1 = str(uuid.uuid4())
        upload_id2 = str(uuid.uuid4())

        result1 = service.verify(upload_id1, image_bytes)
        result2 = service.verify(upload_id2, image_bytes)

        # First should succeed, second should be duplicate by file_hash
        assert result1.status != VerificationStatus.DUPLICATE
        assert result2.status == VerificationStatus.DUPLICATE
        assert any(dc.layer == "file_hash" and dc.is_duplicate for dc in result2.duplicate_checks)


class TestWorkerRetrySafety:
    def setup_method(self):
        self.ocr_service = OCRService()
        self.extraction_service = ExtractionService()
        self.matching_service = MatchingService([
            StudentRecord(student_id="student-1", full_name="Nguyễn Văn An"),
        ])
        self.policy = VerificationPolicy()

    @patch.object(TesseractEngine, "recognize")
    def test_worker_crash_retry_idempotent(self, mock_recognize):
        mock_recognize.return_value = OCRResult(
            raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK",
            confidence=0.85,
            lines=[
                "Người gửi: NGUYEN VAN AN",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=1500,
        )

        duplicate_detector = DuplicateDetector()
        service = VerificationService(
            ocr_service=self.ocr_service,
            extraction_service=self.extraction_service,
            matching_service=self.matching_service,
            duplicate_detector=duplicate_detector,
            policy=self.policy,
        )

        upload_id = str(uuid.uuid4())
        image_bytes = create_test_image()

        result1 = service.verify(upload_id, image_bytes)

        result2 = service.verify(upload_id, image_bytes)

        assert result1.status != VerificationStatus.DUPLICATE
        assert result2.status == VerificationStatus.DUPLICATE
        assert result1.transaction_code == result2.transaction_code
        assert result1.amount == result2.amount

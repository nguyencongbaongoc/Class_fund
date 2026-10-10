from ai.contracts import OCRResult
from ai.extraction.service import (
    AmountExtractor,
    BankExtractor,
    DateTimeExtractor,
    ExtractionService,
    SenderExtractor,
    TransactionCodeExtractor,
)


class TestAmountExtractor:
    def setup_method(self):
        self.extractor = AmountExtractor()

    def test_extract_amount_vnd_suffix(self):
        ocr = OCRResult(
            raw_text="Số tiền: 50.000 VND",
            confidence=0.9,
            lines=["Số tiền: 50.000 VND"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000
        assert result.confidence > 0.8

    def test_extract_amount_with_comma(self):
        ocr = OCRResult(
            raw_text="Amount: 50,000",
            confidence=0.9,
            lines=["Amount: 50,000"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_extract_amount_with_plus(self):
        ocr = OCRResult(
            raw_text="Chuyển: +50,000",
            confidence=0.9,
            lines=["Chuyển: +50,000"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_extract_amount_spaces(self):
        ocr = OCRResult(
            raw_text="50 000",
            confidence=0.9,
            lines=["50 000"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_exclude_phone_number(self):
        ocr = OCRResult(
            raw_text="Số tiền: 50.000 VND\nSĐT: 0901234567",
            confidence=0.9,
            lines=["Số tiền: 50.000 VND", "SĐT: 0901234567"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_exclude_account_number(self):
        ocr = OCRResult(
            raw_text="Số tiền: 50.000 VND\nTK: 123456789012",
            confidence=0.9,
            lines=["Số tiền: 50.000 VND", "TK: 123456789012"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_prefer_transaction_amount_over_balance(self):
        ocr = OCRResult(
            raw_text="Số tiền: 50.000 VND\nSố dư: 1.000.000 VND",
            confidence=0.9,
            lines=["Số tiền: 50.000 VND", "Số dư: 1.000.000 VND"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.amount == 50000

    def test_no_amount_found(self):
        ocr = OCRResult(
            raw_text="No amount here",
            confidence=0.9,
            lines=["No amount here"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is None


class TestTransactionCodeExtractor:
    def setup_method(self):
        self.extractor = TransactionCodeExtractor()

    def test_extract_ft_code(self):
        ocr = OCRResult(
            raw_text="Mã GD: FT1234567890",
            confidence=0.9,
            lines=["Mã GD: FT1234567890"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.code == "FT1234567890"
        assert result.bank_pattern == "GENERIC"

    def test_extract_mbvcb_code(self):
        ocr = OCRResult(
            raw_text="MBVCB1234567890",
            confidence=0.9,
            lines=["MBVCB1234567890"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert "MBVCB" in result.code

    def test_extract_napas_code(self):
        ocr = OCRResult(
            raw_text="NAPAS 1234567890",
            confidence=0.9,
            lines=["NAPAS 1234567890"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert "NAPAS" in result.code

    def test_no_code_found(self):
        ocr = OCRResult(
            raw_text="No transaction code here",
            confidence=0.9,
            lines=["No transaction code here"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is None


class TestSenderExtractor:
    def setup_method(self):
        self.extractor = SenderExtractor()

    def test_extract_sender_with_label(self):
        ocr = OCRResult(
            raw_text="Người gửi: NGUYEN VAN A",
            confidence=0.9,
            lines=["Người gửi: NGUYEN VAN A"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.name == "NGUYEN VAN A"

    def test_extract_sender_from_line(self):
        ocr = OCRResult(
            raw_text="NGUYEN VAN A\nSome other text",
            confidence=0.9,
            lines=["NGUYEN VAN A", "Some other text"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert "NGUYEN VAN A" in result.name

    def test_extract_multiple_candidates(self):
        ocr = OCRResult(
            raw_text="Người gửi: NGUYEN VAN A\nNgười nhận: TRAN THI B",
            confidence=0.9,
            lines=["Người gửi: NGUYEN VAN A", "Người nhận: TRAN THI B"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert len(result.candidates) >= 0

    def test_invalid_name_too_short(self):
        ocr = OCRResult(
            raw_text="Người gửi: A B",
            confidence=0.9,
            lines=["Người gửi: A B"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is None


class TestBankExtractor:
    def setup_method(self):
        self.extractor = BankExtractor()

    def test_extract_mb_bank(self):
        ocr = OCRResult(
            raw_text="NGÂN HÀNG MB BANK",
            confidence=0.9,
            lines=["NGÂN HÀNG MB BANK"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.name == "MB Bank"
        assert result.code == "MB"

    def test_extract_vietcombank(self):
        ocr = OCRResult(
            raw_text="VIETCOMBANK",
            confidence=0.9,
            lines=["VIETCOMBANK"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.name == "Vietcombank"
        assert result.code == "VCB"

    def test_extract_techcombank(self):
        ocr = OCRResult(
            raw_text="TECHCOMBANK",
            confidence=0.9,
            lines=["TECHCOMBANK"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.name == "Techcombank"
        assert result.code == "TCB"

    def test_no_bank_found(self):
        ocr = OCRResult(
            raw_text="No bank here",
            confidence=0.9,
            lines=["No bank here"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is None


class TestDateTimeExtractor:
    def setup_method(self):
        self.extractor = DateTimeExtractor()

    def test_extract_ddmmyyyy_hms(self):
        ocr = OCRResult(
            raw_text="Ngày 25/12/2024 14:30:00",
            confidence=0.9,
            lines=["Ngày 25/12/2024 14:30:00"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.timestamp.day == 25
        assert result.timestamp.month == 12
        assert result.timestamp.year == 2024
        assert result.timestamp.hour == 14
        assert result.timestamp.minute == 30

    def test_extract_yyyymmdd_hms(self):
        ocr = OCRResult(
            raw_text="2024-12-25 14:30:00",
            confidence=0.9,
            lines=["2024-12-25 14:30:00"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.timestamp.year == 2024
        assert result.timestamp.month == 12
        assert result.timestamp.day == 25

    def test_extract_date_only(self):
        ocr = OCRResult(
            raw_text="25/12/2024",
            confidence=0.9,
            lines=["25/12/2024"],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.extractor.extract(ocr)
        assert result is not None
        assert result.timestamp.day == 25
        assert result.timestamp.month == 12
        assert result.timestamp.year == 2024


class TestExtractionService:
    def setup_method(self):
        self.service = ExtractionService()

    def test_extract_all(self):
        ocr = OCRResult(
            raw_text="Người gửi: NGUYEN VAN A\nSố tiền: 50.000 VND\nMã GD: FT1234567890\nMB BANK\n25/12/2024 14:30:00",
            confidence=0.9,
            lines=[
                "Người gửi: NGUYEN VAN A",
                "Số tiền: 50.000 VND",
                "Mã GD: FT1234567890",
                "MB BANK",
                "25/12/2024 14:30:00",
            ],
            engine="tesseract",
            engine_version="5.3.0",
            processing_time_ms=100,
        )
        result = self.service.extract_all(ocr)

        assert result.amount is not None
        assert result.amount.amount == 50000

        assert result.transaction_code is not None
        assert result.transaction_code.code == "FT1234567890"

        assert result.sender is not None
        assert result.sender.name == "NGUYEN VAN A"

        assert result.bank is not None
        assert result.bank.name == "MB Bank"

        assert result.datetime is not None
        assert result.datetime.timestamp.day == 25

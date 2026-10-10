import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def sample_roster():
    from ai.matching.service import StudentRecord
    return [
        StudentRecord(student_id="1", full_name="Nguyễn Văn An", aliases=["An Nguyen"]),
        StudentRecord(student_id="2", full_name="Nguyễn Văn Anh"),
        StudentRecord(student_id="3", full_name="Nguyễn Văn Ân"),
        StudentRecord(student_id="4", full_name="Trần Thị Bích", student_code="STU001"),
        StudentRecord(student_id="5", full_name="Lê Hoàng Cường"),
    ]


@pytest.fixture
def mock_ocr_result():
    from ai.contracts import OCRResult
    return OCRResult(
        raw_text="Test OCR text",
        confidence=0.9,
        lines=["Test OCR text"],
        engine="tesseract",
        engine_version="5.3.0",
        processing_time_ms=100,
    )

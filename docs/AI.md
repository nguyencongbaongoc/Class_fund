# CLASS FUND WEB — AI System Documentation

## Overview

The AI system (Ngọc) handles OCR, transaction extraction, student matching, duplicate detection, and verification for the CLASS FUND WEB project. It processes bank transfer receipt images and produces structured verification results.

## Architecture

```
image → OCRService → ExtractionService → MatchingService → DuplicateDetector → VerificationService → VerificationResult
```

### Components

1. **OCRService** (`ai/ocr/service.py`)
   - Preprocessing with multiple strategies
   - Tesseract OCR engine (Vietnamese + English)
   - Multiple strategy selection for best confidence

2. **ExtractionService** (`ai/extraction/service.py`)
   - AmountExtractor: Normalizes VND amounts from various formats
   - TransactionCodeExtractor: Bank-specific and generic patterns
   - SenderExtractor: Name extraction with candidate ranking
   - BankExtractor: Known bank keyword matching
   - DateTimeExtractor: Multiple date/time format support

3. **MatchingService** (`ai/matching/service.py`)
   - Unicode normalization (NFD + diacritic removal)
   - Exact matching → Fuzzy matching → Alias matching
   - Student code support
   - Returns confidence and candidate list

4. **DuplicateDetector** (`ai/duplicate/service.py`)
   - Layer 1: SHA-256 file hash (exact duplicates)
   - Layer 2: Perceptual hash (pHash, resize/compression resistant)
   - Layer 3: Transaction identity (bank + transaction code)
   - Layer 4: Database unique constraints (backend responsibility)

5. **VerificationService** (`ai/verification/service.py`)
   - Deterministic policy-based verification
   - Risk flag analysis
   - Weighted confidence calculation
   - Version tracking

6. **Worker/Queue** (`ai/worker/queue.py`)
   - Celery + Redis based job queue
   - Retry with exponential backoff
   - Idempotent processing
   - Task state tracking

## Data Contracts

### VerificationResult

```json
{
  "upload_id": "uuid",
  "transaction_code": "FT123456789",
  "amount": 50000,
  "sender_name": "NGUYEN VAN A",
  "bank_name": "MB Bank",
  "transaction_time": "2024-12-25T14:30:00",
  "student_id": "student-123",
  "confidence": 0.95,
  "status": "VERIFIED",
  "risk_flags": [],
  "ocr_version": "1.0.0",
  "extractor_version": "1.0.0",
  "matcher_version": "1.0.0",
  "preprocessor_version": "1.0.0",
  "verification_policy_version": "1.0.0",
  "evidence": {},
  "duplicate_checks": [],
  "created_at": "2024-12-25T14:30:00Z",
  "processing_time_ms": 2500
}
```

### Status Values

- `PENDING` - Job queued
- `PROCESSING` - Currently processing
- `NEEDS_REVIEW` - Insufficient confidence or missing fields
- `VERIFIED` - All checks passed
- `REJECTED` - Clearly invalid
- `DUPLICATE` - Duplicate detected

### Risk Flags

- `MISSING_TRANSACTION_CODE`
- `MISSING_AMOUNT`
- `ABNORMAL_TEXT`
- `ABNORMAL_TIMESTAMP`
- `SENDER_MISMATCH`
- `LOW_IMAGE_QUALITY`
- `DUPLICATE_RECEIPT`
- `INCONSISTENT_FIELDS`

## Configuration

Environment variables:
- `REDIS_URL` - Redis connection string (default: `redis://localhost:6379/0`)
- `TESSERACT_CMD` - Tesseract executable path

## Running the Worker

```bash
celery -A ai.worker.queue worker -Q verification -l info
```

## API Usage

```python
from ai import VerificationService, OCRService, ExtractionService, MatchingService, DuplicateDetector, StudentRecord

# Setup
ocr = OCRService()
extraction = ExtractionService()
matching = MatchingService([
    StudentRecord(student_id="1", full_name="Nguyễn Văn An"),
])
duplicate = DuplicateDetector()
service = VerificationService(ocr, extraction, matching, duplicate)

# Process
with open("receipt.jpg", "rb") as f:
    image_bytes = f.read()

result = service.verify("upload-uuid", image_bytes)
print(result.model_dump_json())
```

## Testing

```bash
# Unit tests
pytest ai/tests/test_contracts.py -v
pytest ai/tests/test_ocr.py -v
pytest ai/tests/test_extraction.py -v
pytest ai/tests/test_matching.py -v
pytest ai/tests/test_duplicate.py -v
pytest ai/tests/test_verification.py -v

# Integration tests
pytest ai/tests/test_integration.py -v

# All tests
pytest ai/tests/ -v --cov=ai
```

## Test Dataset Structure

```
ai/tests/data/
├── valid/              # Valid receipts
├── duplicate/          # Exact/near duplicates
├── blur/               # Blurry images
├── crop/               # Cropped receipts
├── compressed/         # Heavily compressed
├── low_light/          # Low light conditions
├── wrong_sender/       # Sender not in roster
├── missing_code/       # Missing transaction code
├── wrong_amount/       # Incorrect amount extraction
└── multiple_transactions/  # Multiple transactions in one image
```

## Versioning

Each result includes version fields:
- `ocr_version`
- `extractor_version`
- `matcher_version`
- `preprocessor_version`
- `verification_policy_version`

## Security

- File type validation via content inspection (not extension)
- File size limits enforced at upload
- No sensitive data in logs
- Path traversal protection

## Limitations

- Requires Tesseract OCR installed with Vietnamese language data
- Accuracy depends on image quality
- Student matching requires maintained roster
- Perceptual hash threshold may need tuning per deployment
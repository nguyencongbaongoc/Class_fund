# CLASS FUND WEB — AI System (Ngọc)

AI/OCR/Transaction Verification/Anti-Duplicate system for processing bank transfer receipts.

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-vie

# macOS:
brew install tesseract tesseract-lang

# Windows:
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Configuration

Create `.env` file:

```env
REDIS_URL=redis://localhost:6379/0
TESSERACT_CMD=tesseract
```

### Running the Worker

```bash
# Start Redis (required for queue)
redis-server

# Start Celery worker
celery -A ai.worker.queue worker -Q verification -l info
```

### Using the API

```python
from ai import (
    VerificationService,
    OCRService,
    ExtractionService,
    MatchingService,
    DuplicateDetector,
    StudentRecord,
    VerificationPolicy,
)
import uuid

# Initialize services
ocr = OCRService()
extraction = ExtractionService()
matching = MatchingService([
    StudentRecord(student_id="1", full_name="Nguyễn Văn An"),
    StudentRecord(student_id="2", full_name="Trần Thị Bích"),
])
duplicate = DuplicateDetector()
policy = VerificationPolicy()
service = VerificationService(ocr, extraction, matching, duplicate, policy)

# Process an image
with open("receipt.jpg", "rb") as f:
    image_bytes = f.read()

upload_id = str(uuid.uuid4())
result = service.verify(upload_id, image_bytes)

print(f"Status: {result.status}")
print(f"Amount: {result.amount} VND")
print(f"Transaction Code: {result.transaction_code}")
print(f"Student: {result.student_id}")
print(f"Confidence: {result.confidence}")
print(result.model_dump_json(indent=2))
```

## Project Structure

```
CLASS_FUND_WEB/
├── ai/
│   ├── contracts.py          # Data contracts (Pydantic models)
│   ├── ocr/
│   │   └── service.py        # OCR + preprocessing
│   ├── extraction/
│   │   └── service.py        # Field extraction
│   ├── matching/
│   │   └── service.py        # Student matching
│   ├── duplicate/
│   │   └── service.py        # Multi-layer duplicate detection
│   ├── verification/
│   │   └── service.py        # Verification logic
│   ├── worker/
│   │   └── queue.py          # Celery worker + queue
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_contracts.py
│   │   ├── test_ocr.py
│   │   ├── test_extraction.py
│   │   ├── test_matching.py
│   │   ├── test_duplicate.py
│   │   ├── test_verification.py
│   │   └── test_integration.py
│   └── __init__.py
├── docs/
│   ├── AI.md                 # Architecture overview
│   ├── AI_CONTRACT.md        # API contract specification
│   ├── AI_PIPELINE.md        # Pipeline documentation
│   └── AI_TESTING.md         # Testing guide
├── pyproject.toml
└── README.md
```

## Features

- **OCR**: Tesseract with Vietnamese + English, multi-strategy preprocessing
- **Extraction**: Amount, transaction code, sender, bank, datetime
- **Matching**: Unicode normalization, fuzzy matching, aliases, student codes
- **Duplicates**: File hash, perceptual hash (pHash), transaction identity
- **Verification**: Policy-based, risk flags, weighted confidence
- **Queue**: Celery + Redis, retries, idempotency
- **Contracts**: Type-safe Pydantic models with validation

## Testing

```bash
# Run all tests
pytest ai/tests/ -v --cov=ai

# Run specific category
pytest ai/tests/test_extraction.py -v
pytest ai/tests/test_integration.py -v
```

## Documentation

- [Architecture](docs/AI.md)
- [Contract Specification](docs/AI_CONTRACT.md)
- [Pipeline Details](docs/AI_PIPELINE.md)
- [Testing Guide](docs/AI_TESTING.md)

## Status Definitions

| Status | Meaning |
|--------|---------|
| `PENDING` | Queued for processing |
| `PROCESSING` | Currently processing |
| `NEEDS_REVIEW` | Low confidence or missing fields |
| `VERIFIED` | All checks passed |
| `REJECTED` | Clearly invalid |
| `DUPLICATE` | Already processed |

## Backend Integration

Ngọc produces `VerificationResult` JSON. Backend (Minh) must:
1. Re-verify critical fields
2. Enforce unique constraints on (bank, transaction_code)
3. Handle idempotency for duplicate submissions
4. Post to ledger only after verification

See [AI_CONTRACT.md](docs/AI_CONTRACT.md) for full schema.
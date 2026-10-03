# AI Testing Documentation

## Overview

This document describes the testing strategy, test structure, and how to run tests for the AI system.

## Test Structure

```
ai/tests/
├── conftest.py              # Shared fixtures
├── test_contracts.py        # Data contract validation
├── test_ocr.py              # OCR & preprocessing unit tests
├── test_extraction.py       # Field extraction unit tests
├── test_matching.py         # Student matching unit tests
├── test_duplicate.py        # Duplicate detection unit tests
├── test_verification.py     # Verification logic unit tests
├── test_integration.py      # Full pipeline integration tests
└── data/                    # Test images (not in repo)
    ├── valid/
    ├── duplicate/
    ├── blur/
    ├── crop/
    ├── compressed/
    ├── low_light/
    ├── wrong_sender/
    ├── missing_code/
    ├── wrong_amount/
    └── multiple_transactions/
```

## Test Categories

### 1. Unit Tests
Test individual components in isolation with mocked dependencies.

**Coverage Targets**:
- Preprocessing strategies: 100%
- Amount extraction patterns: 100%
- Transaction code patterns: 100%
- Sender extraction: 100%
- Bank extraction: 100%
- DateTime extraction: 100%
- Name normalization: 100%
- Fuzzy matching: 100%
- File hash: 100%
- Perceptual hash: 100%
- Transaction identity: 100%
- Verification policy: 100%
- Confidence calculation: 100%
- Risk flag detection: 100%

### 2. Integration Tests
Test component interactions with real (mocked OCR) data.

**Scenarios**:
- Valid receipt → VERIFIED
- Missing transaction code → NEEDS_REVIEW
- Missing amount → NEEDS_REVIEW
- Sender not in roster → NEEDS_REVIEW
- Low OCR confidence → NEEDS_REVIEW
- Duplicate file hash → DUPLICATE
- Duplicate perceptual hash → DUPLICATE
- Duplicate transaction identity → DUPLICATE
- Abnormal timestamp → NEEDS_REVIEW

### 3. Concurrency Tests
Test idempotency and race condition handling.

**Scenarios**:
- Same upload processed twice → second is DUPLICATE
- Same transaction code, different images → DUPLICATE
- Same image, different transaction codes → file_hash DUPLICATE
- Worker crash simulation → retry produces same result
- Queue retry → no double processing

### 4. E2E Tests (Manual/Staging)
Full pipeline with real images and real OCR.

**Requirements**:
- Tesseract installed with Vietnamese language
- Test images in `ai/tests/data/`
- Redis running for queue tests

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-vie

# Install Tesseract (macOS)
brew install tesseract tesseract-lang

# Install Tesseract (Windows)
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Run All Tests

```bash
# Unit + Integration
pytest ai/tests/ -v --cov=ai --cov-report=term-missing

# Specific test file
pytest ai/tests/test_extraction.py -v

# With coverage
pytest ai/tests/ --cov=ai --cov-report=html

# Parallel execution
pytest ai/tests/ -n auto
```

### Run by Category

```bash
# Unit tests only
pytest ai/tests/test_contracts.py ai/tests/test_ocr.py ai/tests/test_extraction.py ai/tests/test_matching.py ai/tests/test_duplicate.py ai/tests/test_verification.py -v

# Integration tests
pytest ai/tests/test_integration.py -v

# Concurrency tests (subset of integration)
pytest ai/tests/test_integration.py::TestConcurrencyScenarios -v
```

### Test with Real Images (Manual)

```bash
# Place test images in ai/tests/data/{category}/
# Run integration tests with real OCR
pytest ai/tests/test_integration.py -v -k "not mock"
```

## Test Data

### Synthetic Test Fixtures

Tests use mocked OCR results for deterministic unit testing. Example:

```python
# In test_verification.py
mock_ocr = OCRResult(
    raw_text="Người gửi: NGUYEN VAN AN\nSố tiền: 50.000 VND\nMã GD: FT1234567890",
    confidence=0.9,
    lines=["Người gửi: NGUYEN VAN AN", "Số tiền: 50.000 VND", "Mã GD: FT1234567890"],
    engine="tesseract",
    engine_version="5.3.0",
    processing_time_ms=100,
)
```

### Real Test Images (Not in Repo)

For integration/E2E testing, add real receipt images to:

```
ai/tests/data/valid/receipt_001.jpg
ai/tests/data/valid/receipt_002.png
ai/tests/data/blur/receipt_blur_001.jpg
...
```

Each image should have a corresponding `.json` with expected results:

```json
{
  "expected_status": "VERIFIED",
  "expected_transaction_code": "FT123456789",
  "expected_amount": 50000,
  "expected_sender": "NGUYEN VAN AN",
  "expected_bank": "MB Bank",
  "expected_student_id": "student-1",
  "min_confidence": 0.7
}
```

## Mocking Strategy

### OCR Engine Mocking

```python
@patch.object(TesseractEngine, "recognize")
def test_something(self, mock_recognize):
    mock_recognize.return_value = OCRResult(...)
```

### External Service Mocking

```python
# Redis for queue tests
@patch("ai.worker.queue.redis.from_url")
def test_enqueue(self, mock_redis):
    mock_client = Mock()
    mock_redis.return_value = mock_client
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: AI Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Tesseract
        run: sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
      - name: Install Python deps
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest ai/tests/ --cov=ai --cov-fail-under=80
```

## Test Quality Guidelines

### Do
- Test edge cases (empty strings, unicode, boundary values)
- Test both success and failure paths
- Use descriptive test names: `test_extract_amount_vnd_suffix`
- Assert on specific values, not just truthiness
- Mock at the right boundary (external services, not internal logic)

### Don't
- Mock the component under test
- Use random data in tests
- Depend on test execution order
- Skip assertions
- Hard-code expected confidence values (test relative ordering instead)

## Performance Testing

```bash
# Benchmark OCR latency
python -m pytest ai/tests/test_ocr.py::TestOCRService::test_process_multiple_strategies --benchmark-only

# Load test worker
locust -f ai/tests/load_test.py --host=http://localhost:8000
```

## Debugging Failed Tests

```bash
# Verbose output with print statements
pytest ai/tests/test_extraction.py::TestAmountExtractor::test_extract_amount_vnd_suffix -v -s

# Drop into debugger on failure
pytest ai/tests/test_extraction.py -x --pdb

# Show local variables on failure
pytest ai/tests/test_extraction.py -l
```

## Test Coverage Requirements

| Module | Minimum Coverage |
|--------|------------------|
| contracts | 100% |
| ocr/service | 90% |
| extraction/service | 90% |
| matching/service | 90% |
| duplicate/service | 90% |
| verification/service | 90% |
| worker/queue | 80% |

## Adding New Tests

1. Identify the component/function being tested
2. Choose appropriate test file (or create new)
3. Follow naming convention: `test_<function>_<scenario>`
4. Use fixtures from `conftest.py` for common setup
5. Add both positive and negative cases
6. Document any new test data requirements

## Known Test Gaps

- [ ] Real image E2E tests (requires test dataset)
- [ ] Load testing for queue throughput
- [ ] Chaos testing (worker kill, network partition)
- [ ] Cross-version compatibility tests
- [ ] Adversarial image tests (noise, rotation, perspective)
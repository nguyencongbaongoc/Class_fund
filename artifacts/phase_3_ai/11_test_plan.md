# 11_TEST_PLAN.md

## Phase 3 AI Pipeline — Test Plan

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This test plan covers all required test cases for Phase 3 AI Pipeline as specified in the Phase 3 requirements document §7. Tests are organized by category and priority.

### 1.1 Test Categories

| Category | Priority | Description |
|----------|----------|-------------|
| **Unit Tests** | P0 | Individual component testing |
| **Integration Tests** | P0 | End-to-end pipeline testing |
| **Contract Tests** | P0 | API contract compliance |
| **Evaluation Tests** | P0 | Accuracy measurement on labeled dataset |
| **Regression Tests** | P1 | Prevent regressions |
| **Performance Tests** | P1 | Latency, memory, throughput |
| **Security Tests** | P1 | Prompt injection, input validation |
| **Chaos Tests** | P2 | Failure scenarios |

### 1.2 Test Execution Strategy

```
┌─────────────────────────────────────────────────────────────┐
                    TEST EXECUTION PYRAMID
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐                                          │
│   │  Chaos      │  ◄── Few, slow, high confidence         │
│   │  Tests      │                                          │
│   └──────┬──────┘                                          │
│          │                                                 │
│   ┌──────┴──────┐                                          │
│   │ Performance │  ◄── Medium count, automated            │
│   │  Tests      │                                          │
│   └──────┬──────┘                                          │
│          │                                                 │
│   ┌──────┴──────┐                                          │
│   │  Security   │  ◄── Automated in CI                     │
│   │  Tests      │                                          │
│   └──────┬──────┘                                          │
│          │                                                 │
│   ┌──────┴──────┐                                          │
│   │ Evaluation  │  ◄── Run on model/config changes         │
│   │  Tests      │                                          │
│   └──────┬──────┘                                          │
│          │                                                 │
│   ┌──────┴──────┐                                          │
│   │ Integration │  ◄── Run on every PR                     │
│   │  Tests      │                                          │
│   └──────┬──────┘                                          │
│          │                                                 │
│   ┌──────┴──────┐                                          │
│   │   Unit      │  ◄── Many, fast, run on every commit     │
│   │  Tests      │                                          │
│   └─────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Unit Tests

### 2.1 Image Ingestion (`ai/ingestion/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| ING-001 | Valid JPEG receipt | ✅ ValidatedImage with all fields |
| ING-002 | Valid PNG receipt | ✅ ValidatedImage |
| ING-003 | Valid WebP receipt | ✅ ValidatedImage |
| ING-004 | Valid HEIC receipt | ✅ ValidatedImage (if libheif) |
| ING-005 | Corrupt JPEG (truncated) | ❌ CORRUPT_IMAGE |
| ING-006 | PDF renamed as .jpg | ❌ INVALID_MIME_TYPE |
| ING-007 | 50MB image | ❌ FILE_TOO_LARGE |
| ING-008 | 200x150 image | ❌ RESOLUTION_TOO_LOW |
| ING-009 | 5000x5000 image | ❌ RESOLUTION_TOO_HIGH |
| ING-010 | Blurry receipt (score < 100) | ❌ IMAGE_BLURRY |
| ING-011 | Rotated EXIF (orientation 6) | ✅ Auto-rotated, orientation_applied=true |
| ING-012 | PNG with transparency | ✅ Composited on white |
| ING-013 | CMYK TIFF | ✅ Converted to RGB |
| ING-014 | Animated GIF | ❌ UNSUPPORTED_FORMAT |
| ING-015 | File hash determinism | Same bytes → same SHA-256 |
| ING-016 | pHash stability | Minor compression → Hamming distance ≤ 5 |
| ING-017 | MIME mismatch warning | Extension ≠ content → warning only |

### 2.2 Ollama Model Manager (`ai/ollama/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| OLL-001 | Config from env vars | All values correctly parsed |
| OLL-002 | Health check success | Returns server + model status |
| OLL-003 | Health check failure | Handles connection error gracefully |
| OLL-004 | Circuit breaker opens | After 5 failures → OPEN state |
| OLL-005 | Circuit breaker recovery | Half-open → closed on 3 successes |
| OLL-006 | Vision request success | Valid image → structured output |
| OLL-007 | Text fallback success | OCR text → structured output |
| OLL-008 | JSON parse failure | Raises OllamaResponseError |
| OLL-009 | Schema validation failure | Raises OllamaResponseError |
| OLL-010 | Model not found | Raises OllamaModelNotFoundError |
| OLL-011 | Warmup both models | Both respond to dummy request |
| OLL-012 | Concurrent requests | Multiple parallel requests handled |
| OLL-013 | Long request (55s) | Completes within timeout |
| OLL-014 | Model switching | Vision → text model calls work |

### 2.3 OCR Pipeline (`ai/pipeline/ocr_pipeline.py`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| OCR-001 | Tesseract engine init | Loads with vie+eng |
| OCR-002 | All 6 preprocessing strategies | Each produces output |
| OCR-003 | Multi-strategy selection | Picks highest confidence |
| OCR-004 | Amount extraction | VND patterns, labels, standalone |
| OCR-005 | Tx code extraction | Bank-specific + generic patterns |
| OCR-006 | Sender extraction | Labels + name pattern |
| OCR-007 | Bank extraction | 11 bank keywords |
| OCR-008 | DateTime extraction | Multiple formats |
| OCR-009 | Schema adapter | Legacy → unified mapping correct |
| OCR-010 | Confidence aggregation | Weighted average correct |

### 2.4 Unified Schema (`ai/schema/v1/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| SCH-001 | Amount normalization | "500.000 VND" → 500000 |
| SCH-002 | Date parsing | "25/12/2024" → 2024-12-25T00:00:00Z |
| SCH-003 | Bank normalization | "VIETCOMBANK" → "Vietcombank", code VCB |
| SCH-004 | Tx code normalization | Uppercase, no spaces |
| SCH-005 | Name normalization | Uppercase, diacritics preserved |
| SCH-006 | Field confidence map | Auto-populated from fields |
| SCH-007 | has_required_fields() | Correctly identifies missing fields |
| SCH-008 | to_ai_result_in() | Maps all fields correctly |
| SCH-009 | Null semantics | null vs "unknown" vs omitted |

### 2.5 Verification Engine (`ai/verification/engine.py`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| VER-001 | Field presence validation | Missing required fields flagged |
| VER-002 | Field format validation | Invalid amounts, codes, dates flagged |
| VER-003 | Cross-field consistency | Bank name/code mismatch detected |
| VER-004 | OCR quality assessment | Blur, low text length flagged |
| VER-005 | Student matching | Exact, fuzzy, alias matches work |
| VER-006 | Campaign validation | Amount mismatch, student not found, already paid |
| VER-007 | Duplicate detection | All 4 layers work |
| VER-008 | Confidence calculation | Weighted average + penalties |
| VER-009 | Status determination | All status transitions correct |
| VER-010 | Prompt injection detection | Common patterns detected |

### 2.6 Confidence & Routing (`ai/confidence/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| CONF-001 | Perfect predictions calibrated | 1.0 → ~1.0 |
| CONF-002 | Random predictions calibrated | 0.5 → accuracy |
| CONF-003 | Monotonicity | Higher raw → higher calibrated |
| CONF-004 | ECE on test set | < 0.05 |
| CONF-005 | Auto-verify routing | Conf 0.95, no flags → AUTO_VERIFY |
| CONF-006 | Human review routing | Conf 0.85, no flags → HUMAN_REVIEW |
| CONF-007 | Blocking flag routing | Conf 0.95, missing tx_code → HUMAN_REVIEW |
| CONF-008 | Duplicate routing | Duplicate candidate → DUPLICATE |
| CONF-009 | Prompt injection routing | Injection detected → HUMAN_REVIEW |

### 2.7 Duplicate Detection (`ai/duplicate/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| DUP-001 | File hash exact match | Same bytes → candidate conf 1.0 |
| DUP-002 | File hash no match | Different bytes → no candidate |
| DUP-003 | pHash exact match | Same image → distance 0, conf 1.0 |
| DUP-004 | pHash near match | Re-compressed → distance ≤10, conf >0.8 |
| DUP-005 | pHash no match | Different image → distance >10 |
| DUP-006 | Transaction identity match | Same bank+code → candidate conf 1.0 |
| DUP-007 | Transaction identity no match | Different code → no candidate |
| DUP-008 | Fuzzy similarity | Same amount/date/sender/bank → high score |
| DUP-009 | Fuzzy no match | Different amount/date/sender → low score |
| DUP-010 | Registration persistence | Restart → existing hashes loaded |

### 2.8 Human Review Queue (`ai/review/`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| REV-001 | Enqueue → dequeue | Request retrieved correctly |
| REV-002 | Approve → backend post | Full flow works |
| REV-003 | Correct fields → re-verify | Correction flow works |
| REV-004 | Reject → upload rejected | Rejection flow works |
| REV-005 | SLA deadline → escalation | Escalation triggered |
| REV-006 | Workload balancing | Fair distribution |

---

## 3. Integration Tests

### 3.1 End-to-End Pipeline

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| INT-001 | Valid receipt → Ollama vision | UnifiedExtractionResult v1 |
| INT-002 | Valid receipt → Tesseract fallback | UnifiedExtractionResult v1 |
| INT-003 | Blurry image → low confidence → review | NEEDS_REVIEW |
| INT-004 | Rotated image → EXIF auto-rotate → correct OCR | VERIFIED |
| INT-005 | Low contrast → high contrast strategy wins | VERIFIED |
| INT-006 | No text image → low OCR confidence → review | NEEDS_REVIEW |
| INT-007 | Vietnamese diacritics → correctly recognized | VERIFIED |
| INT-008 | Campaign amount mismatch → review | NEEDS_REVIEW + CAMPAIGN_AMOUNT_MISMATCH |
| INT-009 | Duplicate image → file hash match | DUPLICATE |
| INT-010 | Near-duplicate image → pHash match | DUPLICATE |
| INT-011 | Cross-image same transaction → identity match | DUPLICATE |
| INT-012 | Prompt injection in image → flagged | NEEDS_REVIEW + PROMPT_INJECTION_DETECTED |

### 3.2 Backend Contract Compliance

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| CON-001 | VerificationResult → AIResultIn | All fields mapped correctly |
| CON-002 | Missing campaign_id | None in output |
| CON-003 | Missing student_id | None in output |
| CON-004 | Missing bank_account_id | None in output |
| CON-005 | Confidence Decimal precision | 4 decimal places |
| CON-006 | raw_ocr populated | From extraction.raw_ocr_text |

### 3.3 Vision API Endpoint (`app/api/routes/vision.py`)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| API-001 | Valid upload_id + image + idempotency | VisionProcessResponse |
| API-002 | Missing upload_id | 404 |
| API-003 | Missing idempotency key | 422 |
| API-004 | Already processed upload | already_processed status |
| API-005 | Image retrieval failure | 500 |
| API-006 | Vision error → NEEDS_REVIEW | status=needs_human_review |
| API-007 | Low confidence → NEEDS_REVIEW | status=needs_human_review |
| API-008 | High confidence → auto verify | status=SUCCESS/DUPLICATE |

---

## 4. Evaluation Tests (Accuracy Measurement)

### 4.1 Test Dataset Requirements

- **Minimum 500 real Vietnamese receipts** with verified ground truth
- **Test split**: 75 samples (held out, never used for tuning)
- **Stratified**: By bank, amount, quality, format, device

### 4.2 Evaluation Metrics to Compute

| Metric | Target | Measurement |
|--------|--------|-------------|
| Amount Exact Match | ≥95% (Ollama), ≥85% (Tesseract) | Test set |
| Transaction Code Exact Match | ≥90% (Ollama), ≥80% (Tesseract) | Test set |
| Transaction Date Exact Match | ≥90% (Ollama), ≥80% (Tesseract) | Test set |
| Bank Name Match | ≥95% (Ollama), ≥90% (Tesseract) | Test set |
| Sender Name F1 | ≥85% (Ollama), ≥75% (Tesseract) | Test set |
| Full Record Accuracy | ≥80% (Ollama), ≥65% (Tesseract) | Test set |
| ECE (Calibration) | < 0.05 | Test set |
| Invalid Document AUC | ≥0.95 | Test set |
| Human Review Recall | ≥95% | Test set |
| Human Review Precision | ≥60% | Test set |

### 4.3 Per-Slice Reporting

Report all metrics separately for:
- Each bank (12 banks)
- Each amount range (6 ranges)
- Each quality tier (4 tiers)
- Each format (4 formats)
- Each device type (3 types)

### 4.4 Regression Baseline

- Establish baseline metrics on test set
- Automated comparison on every model/config change
- Alert on >2% absolute regression

---

## 5. Regression Tests

### 5.1 Backward Compatibility

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| REG-001 | Schema v1.0.0 → v1.0.1 (add field) | Old consumers work |
| REG-002 | Schema v1.0.0 → v1.1.0 (new enum) | Old consumers work |
| REG-003 | APIResultIn unchanged | Backend tests pass |
| REG-004 | Vision API unchanged | Frontend tests pass |

### 5.2 Existing AI Package Tests

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| REG-005 | ai/tests/test_ocr.py | All pass |
| REG-006 | ai/tests/test_extraction.py | All pass |
| REG-007 | ai/tests/test_verification.py | All pass |
| REG-008 | ai/tests/test_duplicate.py | All pass |
| REG-009 | ai/tests/test_matching.py | All pass |
| REG-010 | ai/tests/test_contracts.py | All pass |

---

## 6. Performance Tests

### 6.1 Latency Targets

| Operation | P50 Target | P95 Target | P99 Target |
|-----------|------------|------------|------------|
| Image Ingestion | < 200ms | < 500ms | < 1000ms |
| Ollama Vision | < 3000ms | < 10000ms | < 15000ms |
| Tesseract OCR | < 2000ms | < 5000ms | < 10000ms |
| Regex Extraction | < 100ms | < 200ms | < 500ms |
| Verification | < 50ms | < 100ms | < 200ms |
| Duplicate Check | < 50ms | < 100ms | < 200ms |
| **Total (Ollama)** | < 5s | < 15s | < 20s |
| **Total (Tesseract)** | < 4s | < 10s | < 15s |

### 6.2 Throughput

| Scenario | Target |
|----------|--------|
| Sequential processing | > 10 images/min |
| Concurrent (4 workers) | > 30 images/min |
| Memory per worker | < 2GB |

### 6.3 Resource Limits

| Resource | Limit |
|----------|-------|
| CPU (per worker) | < 2 cores avg |
| Memory (per worker) | < 2GB |
| GPU Memory (Ollama) | < 4GB |
| Disk I/O | < 100 MB/s |

---

## 7. Security Tests

### 7.1 Input Validation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| SEC-001 | MIME type spoofing | Detected by python-magic |
| SEC-002 | Decompression bomb | PIL MAX_IMAGE_PIXELS blocks |
| SEC-003 | Oversized image | FILE_TOO_LARGE |
| SEC-004 | Malformed EXIF | Handled gracefully |
| SEC-005 | Null bytes in filename | Sanitized |

### 7.2 Prompt Injection

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| SEC-006 | "Ignore instructions" in receipt text | PROMPT_INJECTION_DETECTED flag |
| SEC-007 | "System prompt" in sender name | PROMPT_INJECTION_DETECTED flag |
| SEC-008 | JSON in description field | PROMPT_INJECTION_DETECTED flag |
| SEC-009 | HTML/XML tags in fields | PROMPT_INJECTION_DETECTED flag |
| SEC-010 | Code blocks in raw OCR | PROMPT_INJECTION_DETECTED flag |

### 7.3 Output Sanitization

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| SEC-011 | Model output validated against schema | Invalid JSON → error |
| SEC-012 | Raw OCR text length limited | Truncated in stored evidence |
| SEC-013 | No PII in logs | Sender names not logged |

### 7.4 Network Isolation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| SEC-014 | Ollama base_url = localhost | Enforced by config validation |
| SEC-015 | No external HTTP calls | Network monitor shows none |

---

## 8. Chaos Tests (Resilience)

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| CHA-001 | Ollama server down | Fallback to Tesseract |
| CHA-002 | Ollama timeout (60s) | Retry 3x → fallback |
| CHA-003 | Vision model not loaded | Attempt load → fallback |
| CHA-004 | Circuit breaker OPEN | Immediate fallback |
| CHA-005 | Supabase unavailable | Queue locally, retry |
| CHA-006 | Worker crash mid-processing | No duplicate on retry (idempotency) |
| CHA-007 | OOM on large image | Graceful error, NEEDS_REVIEW |
| CHA-008 | Tesseract binary missing | Clear error, NEEDS_REVIEW |

---

## 9. Test Infrastructure

### 9.1 Test Data

```python
# tests/fixtures/
├── receipts/
│   ├── valid/
│   │   ├── vietcombank_500k_sharp.jpg
│   │   ├── techcombank_1m_blur.jpg
│   │   └── ...
│   ├── invalid/
│   │   ├── corrupt.jpg
│   │   ├── not_image.pdf
│   │   └── ...
│   └── edge_cases/
│       ├── rotated_90.jpg
│       ├── very_long_tx_code.jpg
│       └── ...
├── ground_truth/
│   └── test_set.jsonl
└── mock_responses/
    ├── ollama_vision_success.json
    ├── ollama_vision_timeout.json
    └── ollama_text_fallback.json
```

### 9.2 Test Utilities

```python
# tests/conftest.py
@pytest.fixture
def valid_receipt_image():
    return load_fixture("receipts/valid/vietcombank_500k_sharp.jpg")

@pytest.fixture
def mock_ollama_vision(monkeypatch):
    # Mock httpx client to return predefined response
    pass

@pytest.fixture
def mock_supabase():
    # Mock Supabase client
    pass
```

### 9.3 CI/CD Integration

```yaml
# .github/workflows/test.yml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest ai/tests/ -v -m "unit"
  
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      ollama:
        image: ollama/ollama:latest
        ports: ["11434:11434"]
    steps:
      - run: ollama pull qwen2.5vl:3b
      - run: ollama pull qwen3.5:4b
      - run: pytest ai/tests/ -v -m "integration"
  
  evaluation:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    steps:
      - run: python ai/scripts/evaluate.py --split test
```

---

## 10. Test Execution Commands

```bash
# Unit tests (fast, no external deps)
pytest ai/tests/ -v -m "unit" --tb=short

# Integration tests (requires Ollama)
pytest ai/tests/ -v -m "integration" --tb=short

# Contract tests
pytest ai/tests/ -v -m "contract" --tb=short

# Security tests
pytest ai/tests/ -v -m "security" --tb=short

# Performance tests
pytest ai/tests/ -v -m "performance" --tb=short -x

# Full test suite
pytest ai/tests/ -v --tb=short

# Evaluation (requires dataset)
python ai/scripts/evaluate.py --split test --model ollama_vision
python ai/scripts/evaluate.py --split test --model tesseract

# Calibration
python ai/scripts/calibrate.py --split train

# Regression check
python ai/scripts/check_regression.py --baseline baseline.json --current current.json
```

---

## 11. Test Coverage Targets

| Component | Line Coverage | Branch Coverage |
|-----------|---------------|-----------------|
| Image Ingestion | ≥ 90% | ≥ 85% |
| Ollama Manager | ≥ 85% | ≥ 80% |
| OCR Pipeline | ≥ 85% | ≥ 80% |
| Unified Schema | ≥ 95% | ≥ 90% |
| Verification Engine | ≥ 90% | ≥ 85% |
| Confidence & Routing | ≥ 90% | ≥ 85% |
| Duplicate Detection | ≥ 85% | ≥ 80% |
| Human Review Queue | ≥ 85% | ≥ 80% |

---

## 12. Acceptance Criteria for Phase 3 Complete

Phase 3 **CANNOT** be declared COMPLETE without:

- [ ] All P0 unit tests passing
- [ ] All P0 integration tests passing
- [ ] All contract tests passing
- [ ] Evaluation metrics meet targets on test set
- [ ] Regression baseline established
- [ ] Performance targets met
- [ ] Security tests passing
- [ ] CI/CD pipeline configured and green

---

## 13. Test Maintenance

| Activity | Frequency | Owner |
|----------|-----------|-------|
| Review test coverage | Monthly | AI Engineer |
| Update test fixtures | Per release | AI Engineer |
| Run evaluation | Weekly (scheduled) | AI Engineer |
| Check regression | Per model change | AI Engineer |
| Update thresholds | Per evaluation cycle | AI Engineer |

---

*End of Test Plan*
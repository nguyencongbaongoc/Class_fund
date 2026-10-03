# 12_TEST_RESULTS.md

## Phase 3 AI Pipeline — Test Results

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: TEMPLATE — TO BE FILLED AFTER TEST EXECUTION

---

## 1. Test Execution Summary

| Test Suite | Total | Passed | Failed | Skipped | Duration | Status |
|------------|-------|--------|--------|---------|----------|--------|
| Unit Tests | X | X | X | X | Xs | ⬜ |
| Integration Tests | X | X | X | X | Xs | ⬜ |
| Contract Tests | X | X | X | X | Xs | ⬜ |
| Security Tests | X | X | X | X | Xs | ⬜ |
| Performance Tests | X | X | X | X | Xs | ⬜ |
| Chaos Tests | X | X | X | X | Xs | ⬜ |
| **Total** | **X** | **X** | **X** | **X** | **Xs** | **⬜** |

### 1.1 Test Environment

| Component | Version/Config |
|-----------|----------------|
| Python | X.Y.Z |
| Ollama | X.Y.Z |
| qwen2.5vl:3b | sha256:... |
| qwen3.5:4b | sha256:... |
| Tesseract | X.Y.Z |
| vie+eng langpack | Yes/No |
| Supabase | Project: X / Local: No |
| Redis | Not used (Supabase polling) |

### 1.2 Execution Command

```bash
# Command used to run tests
pytest ai/tests/ -v --tb=short --junitxml=test_results.xml
```

---

## 2. Unit Test Results

### 2.1 Image Ingestion

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| ING-001 | Valid JPEG receipt | ⬜ | Xms | |
| ING-002 | Valid PNG receipt | ⬜ | Xms | |
| ING-003 | Valid WebP receipt | ⬜ | Xms | |
| ING-004 | Valid HEIC receipt | ⬜ | Xms | |
| ING-005 | Corrupt JPEG | ⬜ | Xms | |
| ING-006 | PDF as .jpg | ⬜ | Xms | |
| ING-007 | 50MB image | ⬜ | Xms | |
| ING-008 | 200x150 image | ⬜ | Xms | |
| ING-009 | 5000x5000 image | ⬜ | Xms | |
| ING-010 | Blurry receipt | ⬜ | Xms | |
| ING-011 | Rotated EXIF | ⬜ | Xms | |
| ING-012 | PNG transparency | ⬜ | Xms | |
| ING-013 | CMYK TIFF | ⬜ | Xms | |
| ING-014 | Animated GIF | ⬜ | Xms | |
| ING-015 | File hash determinism | ⬜ | Xms | |
| ING-016 | pHash stability | ⬜ | Xms | |
| ING-017 | MIME mismatch warning | ⬜ | Xms | |

### 2.2 Ollama Model Manager

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| OLL-001 | Config from env | ⬜ | Xms | |
| OLL-002 | Health check success | ⬜ | Xms | |
| OLL-003 | Health check failure | ⬜ | Xms | |
| OLL-004 | Circuit breaker opens | ⬜ | Xms | |
| OLL-005 | Circuit breaker recovery | ⬜ | Xms | |
| OLL-006 | Vision request success | ⬜ | Xms | |
| OLL-007 | Text fallback success | ⬜ | Xms | |
| OLL-008 | JSON parse failure | ⬜ | Xms | |
| OLL-009 | Schema validation failure | ⬜ | Xms | |
| OLL-010 | Model not found | ⬜ | Xms | |
| OLL-011 | Warmup both models | ⬜ | Xms | |
| OLL-012 | Concurrent requests | ⬜ | Xms | |
| OLL-013 | Long request (55s) | ⬜ | Xms | |
| OLL-014 | Model switching | ⬜ | Xms | |

### 2.3 OCR Pipeline

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| OCR-001 | Tesseract engine init | ⬜ | Xms | |
| OCR-002 | 6 preprocessing strategies | ⬜ | Xms | |
| OCR-003 | Multi-strategy selection | ⬜ | Xms | |
| OCR-004 | Amount extraction | ⬜ | Xms | |
| OCR-005 | Tx code extraction | ⬜ | Xms | |
| OCR-006 | Sender extraction | ⬜ | Xms | |
| OCR-007 | Bank extraction | ⬜ | Xms | |
| OCR-008 | DateTime extraction | ⬜ | Xms | |
| OCR-009 | Schema adapter | ⬜ | Xms | |
| OCR-010 | Confidence aggregation | ⬜ | Xms | |

### 2.4 Unified Schema

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| SCH-001 | Amount normalization | ⬜ | Xms | |
| SCH-002 | Date parsing | ⬜ | Xms | |
| SCH-003 | Bank normalization | ⬜ | Xms | |
| SCH-004 | Tx code normalization | ⬜ | Xms | |
| SCH-005 | Name normalization | ⬜ | Xms | |
| SCH-006 | Field confidence map | ⬜ | Xms | |
| SCH-007 | has_required_fields() | ⬜ | Xms | |
| SCH-008 | to_ai_result_in() | ⬜ | Xms | |
| SCH-009 | Null semantics | ⬜ | Xms | |

### 2.5 Verification Engine

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| VER-001 | Field presence validation | ⬜ | Xms | |
| VER-002 | Field format validation | ⬜ | Xms | |
| VER-003 | Cross-field consistency | ⬜ | Xms | |
| VER-004 | OCR quality assessment | ⬜ | Xms | |
| VER-005 | Student matching | ⬜ | Xms | |
| VER-006 | Campaign validation | ⬜ | Xms | |
| VER-007 | Duplicate detection | ⬜ | Xms | |
| VER-008 | Confidence calculation | ⬜ | Xms | |
| VER-009 | Status determination | ⬜ | Xms | |
| VER-010 | Prompt injection detection | ⬜ | Xms | |

### 2.6 Confidence & Routing

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| CONF-001 | Perfect predictions calibrated | ⬜ | Xms | |
| CONF-002 | Random predictions calibrated | ⬜ | Xms | |
| CONF-003 | Monotonicity | ⬜ | Xms | |
| CONF-004 | ECE on test set | ⬜ | Xms | |
| CONF-005 | Auto-verify routing | ⬜ | Xms | |
| CONF-006 | Human review routing | ⬜ | Xms | |
| CONF-007 | Blocking flag routing | ⬜ | Xms | |
| CONF-008 | Duplicate routing | ⬜ | Xms | |
| CONF-009 | Prompt injection routing | ⬜ | Xms | |

### 2.7 Duplicate Detection

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| DUP-001 | File hash exact match | ⬜ | Xms | |
| DUP-002 | File hash no match | ⬜ | Xms | |
| DUP-003 | pHash exact match | ⬜ | Xms | |
| DUP-004 | pHash near match | ⬜ | Xms | |
| DUP-005 | pHash no match | ⬜ | Xms | |
| DUP-006 | Transaction identity match | ⬜ | Xms | |
| DUP-007 | Transaction identity no match | ⬜ | Xms | |
| DUP-008 | Fuzzy similarity | ⬜ | Xms | |
| DUP-009 | Fuzzy no match | ⬜ | Xms | |
| DUP-010 | Registration persistence | ⬜ | Xms | |

### 2.8 Human Review Queue

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| REV-001 | Enqueue → dequeue | ⬜ | Xms | |
| REV-002 | Approve → backend post | ⬜ | Xms | |
| REV-003 | Correct fields → re-verify | ⬜ | Xms | |
| REV-004 | Reject → upload rejected | ⬜ | Xms | |
| REV-005 | SLA deadline → escalation | ⬜ | Xms | |
| REV-006 | Workload balancing | ⬜ | Xms | |

---

## 3. Integration Test Results

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| INT-001 | Valid receipt → Ollama vision | ⬜ | Xms | |
| INT-002 | Valid receipt → Tesseract fallback | ⬜ | Xms | |
| INT-003 | Blurry image → review | ⬜ | Xms | |
| INT-004 | Rotated image → auto-rotate | ⬜ | Xms | |
| INT-005 | Low contrast → strategy wins | ⬜ | Xms | |
| INT-006 | No text image → review | ⬜ | Xms | |
| INT-007 | Vietnamese diacritics | ⬜ | Xms | |
| INT-008 | Campaign amount mismatch | ⬜ | Xms | |
| INT-009 | Duplicate image → file hash | ⬜ | Xms | |
| INT-010 | Near-duplicate → pHash | ⬜ | Xms | |
| INT-011 | Cross-image same tx → identity | ⬜ | Xms | |
| INT-012 | Prompt injection → flagged | ⬜ | Xms | |

### 3.2 Backend Contract Compliance

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| CON-001 | VerificationResult → AIResultIn | ⬜ | Xms | |
| CON-002 | Missing campaign_id | ⬜ | Xms | |
| CON-003 | Missing student_id | ⬜ | Xms | |
| CON-004 | Missing bank_account_id | ⬜ | Xms | |
| CON-005 | Confidence Decimal precision | ⬜ | Xms | |
| CON-006 | raw_ocr populated | ⬜ | Xms | |

### 3.3 Vision API Endpoint

| Test ID | Test Case | Status | Duration | Notes |
|---------|-----------|--------|----------|-------|
| API-001 | Valid request | ⬜ | Xms | |
| API-002 | Missing upload_id | ⬜ | Xms | |
| API-003 | Missing idempotency key | ⬜ | Xms | |
| API-004 | Already processed | ⬜ | Xms | |
| API-005 | Image retrieval failure | ⬜ | Xms | |
| API-006 | Vision error → review | ⬜ | Xms | |
| API-007 | Low confidence → review | ⬜ | Xms | |
| API-008 | High confidence → auto | ⬜ | Xms | |

---

## 4. Evaluation Test Results

### 4.1 Test Set Composition

| Dimension | Target | Actual | Status |
|-----------|--------|--------|--------|
| Total Samples | 75 | X | ⬜ |
| Banks covered | 12 | X | ⬜ |
| Amount ranges | 6 | X | ⬜ |
| Quality tiers | 4 | X | ⬜ |
| Formats | 4 | X | ⬜ |

### 4.2 Primary Metrics (Ollama Vision)

| Metric | Target | Actual | 95% CI | Status |
|--------|--------|--------|--------|--------|
| Amount Exact Match | ≥95% | X% | [X%, X%] | ⬜ |
| TxCode Exact Match | ≥90% | X% | [X%, X%] | ⬜ |
| Date Exact Match | ≥90% | X% | [X%, X%] | ⬜ |
| Bank Name Match | ≥95% | X% | [X%, X%] | ⬜ |
| Sender Name F1 | ≥85% | X% | [X%, X%] | ⬜ |
| Full Record Accuracy | ≥80% | X% | [X%, X%] | ⬜ |
| ECE | <0.05 | X.XXXX | - | ⬜ |
| Invalid Doc AUC | ≥0.95 | X.XXXX | [X, X] | ⬜ |
| HR Recall | ≥95% | X% | [X%, X%] | ⬜ |
| HR Precision | ≥60% | X% | [X%, X%] | ⬜ |
| FPR (Review) | ≤20% | X% | [X%, X%] | ⬜ |

### 4.3 Primary Metrics (Tesseract Fallback)

| Metric | Target | Actual | 95% CI | Status |
|--------|--------|--------|--------|--------|
| Amount Exact Match | ≥85% | X% | [X%, X%] | ⬜ |
| TxCode Exact Match | ≥80% | X% | [X%, X%] | ⬜ |
| Date Exact Match | ≥80% | X% | [X%, X%] | ⬜ |
| Bank Name Match | ≥90% | X% | [X%, X%] | ⬜ |
| Sender Name F1 | ≥75% | X% | [X%, X%] | ⬜ |
| Full Record Accuracy | ≥65% | X% | [X%, X%] | ⬜ |

### 4.4 Per-Slice Results

| Slice | Amount Acc | TxCode Acc | Full Record | N | Status |
|-------|------------|------------|-------------|---|--------|
| Vietcombank | X% | X% | X% | X | ⬜ |
| Techcombank | X% | X% | X% | X | ⬜ |
| BIDV | X% | X% | X% | X | ⬜ |
| MBBank | X% | X% | X% | X | ⬜ |
| VPBank | X% | X% | X% | X | ⬜ |
| ACB | X% | X% | X% | X | ⬜ |
| SHB | X% | X% | X% | X | ⬜ |
| Sacombank | X% | X% | X% | X | ⬜ |
| VietinBank | X% | X% | X% | X | ⬜ |
| Agribank | X% | X% | X% | X | ⬜ |
| SeABank | X% | X% | X% | X | ⬜ |
| NAPAS | X% | X% | X% | X | ⬜ |
| <100K | X% | X% | X% | X | ⬜ |
| 100K-500K | X% | X% | X% | X | ⬜ |
| 500K-1M | X% | X% | X% | X | ⬜ |
| 1M-5M | X% | X% | X% | X | ⬜ |
| 5M-20M | X% | X% | X% | X | ⬜ |
| >20M | X% | X% | X% | X | ⬜ |
| Excellent | X% | X% | X% | X | ⬜ |
| Good | X% | X% | X% | X | ⬜ |
| Fair | X% | X% | X% | X | ⬜ |
| Poor | X% | X% | X% | X | ⬜ |

### 4.5 Regression Check

| Metric | Baseline | Current | Delta | Status |
|--------|----------|---------|-------|--------|
| Amount Exact Match | X% | X% | X% | ⬜ |
| TxCode Exact Match | X% | X% | X% | ⬜ |
| Full Record Accuracy | X% | X% | X% | ⬜ |
| ECE | X.XXXX | X.XXXX | X.XXXX | ⬜ |
| Invalid Doc AUC | X.XXXX | X.XXXX | X.XXXX | ⬜ |

---

## 5. Performance Test Results

| Operation | P50 Target | P50 Actual | P95 Target | P95 Actual | P99 Target | P99 Actual | Status |
|-----------|------------|------------|------------|------------|------------|------------|--------|
| Image Ingestion | <200ms | Xms | <500ms | Xms | <1000ms | Xms | ⬜ |
| Ollama Vision | <3000ms | Xms | <10000ms | Xms | <15000ms | Xms | ⬜ |
| Tesseract OCR | <2000ms | Xms | <5000ms | Xms | <10000ms | Xms | ⬜ |
| Regex Extraction | <100ms | Xms | <200ms | Xms | <500ms | Xms | ⬜ |
| Verification | <50ms | Xms | <100ms | Xms | <200ms | Xms | ⬜ |
| Duplicate Check | <50ms | Xms | <100ms | Xms | <200ms | Xms | ⬜ |
| **Total (Ollama)** | <5s | Xs | <15s | Xs | <20s | Xs | ⬜ |
| **Total (Tesseract)** | <4s | Xs | <10s | Xs | <15s | Xs | ⬜ |

### Throughput

| Scenario | Target | Actual | Status |
|----------|--------|--------|--------|
| Sequential | >10/min | X/min | ⬜ |
| Concurrent (4 workers) | >30/min | X/min | ⬜ |
| Memory/worker | <2GB | X GB | ⬜ |

---

## 6. Security Test Results

| Test ID | Test Case | Status | Notes |
|---------|-----------|--------|-------|
| SEC-001 | MIME spoofing | ⬜ | |
| SEC-002 | Decompression bomb | ⬜ | |
| SEC-003 | Oversized image | ⬜ | |
| SEC-004 | Malformed EXIF | ⬜ | |
| SEC-005 | Null bytes in filename | ⬜ | |
| SEC-006 | "Ignore instructions" | ⬜ | |
| SEC-007 | "System prompt" | ⬜ | |
| SEC-008 | JSON in description | ⬜ | |
| SEC-009 | HTML/XML tags | ⬜ | |
| SEC-010 | Code blocks | ⬜ | |
| SEC-011 | Output schema validation | ⬜ | |
| SEC-012 | Raw OCR length limit | ⬜ | |
| SEC-013 | No PII in logs | ⬜ | |
| SEC-014 | Ollama localhost only | ⬜ | |
| SEC-015 | No external HTTP calls | ⬜ | |

---

## 7. Chaos Test Results

| Test ID | Test Case | Status | Notes |
|---------|-----------|--------|-------|
| CHA-001 | Ollama server down | ⬜ | |
| CHA-002 | Ollama timeout | ⬜ | |
| CHA-003 | Model not loaded | ⬜ | |
| CHA-004 | Circuit breaker OPEN | ⬜ | |
| CHA-005 | Supabase unavailable | ⬜ | |
| CHA-006 | Worker crash mid-process | ⬜ | |
| CHA-007 | OOM on large image | ⬜ | |
| CHA-008 | Tesseract missing | ⬜ | |

---

## 8. Failed Tests Analysis

| Test ID | Failure Reason | Root Cause | Fix Status |
|---------|----------------|------------|------------|
| | | | ⬜ Not Started |
| | | | ⬜ Not Started |
| | | | ⬜ Not Started |

---

## 9. Code Coverage

| Component | Line Coverage | Branch Coverage | Target | Status |
|-----------|---------------|-----------------|--------|--------|
| Image Ingestion | X% | X% | ≥90%/85% | ⬜ |
| Ollama Manager | X% | X% | ≥85%/80% | ⬜ |
| OCR Pipeline | X% | X% | ≥85%/80% | ⬜ |
| Unified Schema | X% | X% | ≥95%/90% | ⬜ |
| Verification Engine | X% | X% | ≥90%/85% | ⬜ |
| Confidence & Routing | X% | X% | ≥90%/85% | ⬜ |
| Duplicate Detection | X% | X% | ≥85%/80% | ⬜ |
| Human Review Queue | X% | X% | ≥85%/80% | ⬜ |
| **Overall** | **X%** | **X%** | **≥85%/80%** | **⬜** |

---

## 10. Sign-off

| Role | Name | Date | Tests Pass | Approved |
|------|------|------|------------|----------|
| AI Engineer (Ngọc) | | | X/X | ☐ |
| Backend Lead (Minh) | | | | ☐ |
| QA Lead | | | | ☐ |

---

## 11. Artifacts

```
test_results/
├── test_results.xml          # JUnit XML
├── coverage.xml              # Coverage report
├── test_results.json         # Structured results
├── evaluation_metrics.json   # Evaluation metrics
├── performance_results.json  # Latency/throughput
└── this_document.md          # This file (filled)
```

---

*End of Test Results Template — TO BE FILLED AFTER TEST EXECUTION*
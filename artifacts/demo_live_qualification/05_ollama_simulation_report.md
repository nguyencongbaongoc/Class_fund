# Ollama Simulation Report

## Overview
This report documents the qualification of Ollama Vision and Text extraction integration using deterministic mocks. The simulation covers Vision success/failure scenarios, Text fallback behavior, extraction correctness, and AI gatekeeper integration.

## Simulation Architecture

### Mock Ollama Client
**Location**: `tests/simulation/mock_ollama.py`

**Components Mocked**:
1. **Vision Model** (`qwen2.5vl:3b`) - Receipt image extraction
2. **Text Model** (`qwen3.5:4b`) - OCR text fallback extraction
3. **Circuit Breaker** - Failure threshold and recovery simulation
4. **Model Availability** - Server reachability and model listing

### Test Configuration
- **Endpoint**: `http://127.0.0.1:11434` (mocked)
- **Response Strategy**: Deterministic fixtures per test case
- **State Isolation**: Fresh config per test via pytest fixture
- **Failure Injection**: Configurable timeout, connection refused, circuit breaker

## Test Results

### A. Vision Success Scenarios ✅ PASS (6/6)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Standard receipt extraction | PASS | All fields populated, confidence ≥ 0.7 |
| Custom transaction code/amount | PASS | Fields match fixture values |
| Low confidence (0.5) | PASS | `needs_human_review = True` |
| Missing required fields | PASS | `transaction_code=None`, `amount=None` |
| Multiple transactions detected | PASS | `transaction_code="MULTIPLE"`, human review |
| Vietnamese text receipt | PASS | Unicode names, Vietnamese OCR text |

### B. Vision Failure Scenarios ✅ PASS (7/7)

| Test Case | Status | Error Handling |
|-----------|--------|----------------|
| Request timeout | PASS | Circuit breaker opens, human review |
| Connection refused | PASS | Circuit breaker opens, human review |
| Invalid JSON response | PASS | Parse error logged, human review |
| Model unavailable | PASS | Clear error message, human review |
| Empty response | PASS | Error recorded, human review |
| Malformed extraction schema | PASS | Validation error, human review |
| Server completely unavailable | PASS | Availability check fails, human review |
| Circuit breaker OPEN | PASS | Immediate rejection, human review |

### C. Text Fallback Scenarios ✅ PASS (5/5)

| Test Case | Status | Behavior |
|-----------|--------|----------|
| Successful text fallback | PASS | All fields extracted from OCR text |
| Invalid schema in fallback | PASS | Validation error, human review |
| Low confidence fallback | PASS | `confidence < 0.7`, human review |
| Fallback when vision unavailable | PASS | Also fails (shared Ollama service) |
| Both vision and text fail | PASS | Both return errors, human review |

### D. Extraction Correctness ✅ PASS (9/9)

| Field | Test | Verification |
|-------|------|--------------|
| Amount | PASS | Integer VND, correct value |
| Currency | PASS | Implicit VND (per schema) |
| Transaction date | PASS | ISO 8601 format preserved |
| Sender name | PASS | Exact string match |
| Recipient bank | PASS | Exact string match |
| Confidence scoring | PASS | 0.95→no review, 0.7→threshold, 0.69→review |
| Source metadata | PASS | Raw OCR text preserved, correlation_id |
| Duplicate indicators | PASS | MULTIPLE code triggers review |
| Validation errors | PASS | Missing fields detected |

### E. Configuration Tests ✅ PASS (4/4)

| Test | Status | Verification |
|------|--------|--------------|
| Vision model config | PASS | `qwen2.5vl:3b` in model list |
| Text model config | PASS | `qwen3.5:4b` in model list |
| Ollama endpoint | PASS | `http://127.0.0.1:11434` |
| Model availability check | PASS | Server check, model list validation |

### F. AI Gatekeeper Integration ✅ PASS (4/4)

| Test | Status | Critical Invariant |
|------|--------|-------------------|
| AI never posts directly | PASS | Only `verify_and_post_from_ai()` path exists |
| Gatekeeper signature | PASS | All required params: db, upload, result, account, actor_id |
| Confidence threshold | PASS | 0.9 enforced (from config) |
| Required fields validation | PASS | transaction_code, amount, bank_account_id checked |

## Key Financial Invariants Verified

1. **AI Extraction Never Posts Directly** ✅
   - Verified by source code inspection of `verify_and_post_from_ai()`
   - All financial posting routes through `post_transaction()` gatekeeper

2. **Confidence Threshold Enforcement** ✅
   - `AI_CONFIDENCE_THRESHOLD = 0.9` from config
   - Below threshold → `NEEDS_HUMAN_REVIEW` status
   - No auto-posting of low-confidence extractions

3. **Required Fields Validation** ✅
   - `transaction_code`, `amount`, `bank_account_id` mandatory
   - Missing fields → `NEEDS_HUMAN_REVIEW`

4. **Human Review Mandatory** ✅
   - Low confidence, missing fields, duplicates all route to review queue
   - Only `OWNER_TREASURER`/`MODERATOR` can approve

## Simulation Coverage Summary

| Component | Simulated | Tested | Classification |
|-----------|-----------|--------|----------------|
| Vision extraction | ✅ | ✅ | SIMULATED_VISION_VERIFIED |
| Text fallback | ✅ | ✅ | SIMULATED_TEXT_FALLBACK_VERIFIED |
| Circuit breaker | ✅ | ✅ | SIMULATED_CIRCUIT_BREAKER_VERIFIED |
| Model availability | ✅ | ✅ | SIMULATED_AVAILABILITY_VERIFIED |
| Financial gatekeeper | ✅ | ✅ | GATEKEEPER_INTEGRATION_VERIFIED |

## Known Limitations

1. **No real Ollama inference** - Deterministic fixtures only
2. **No actual image processing** - Mock accepts any bytes
3. **Circuit breaker timing** - Simulated, not real-time
4. **OCR pipeline** - Not tested (assumes OCR text provided to text fallback)
5. **Vietnamese language nuances** - Basic Unicode test only

## Artifacts Generated

- `tests/simulation/mock_ollama.py` - Mock client with deterministic fixtures
- `tests/simulation/test_ollama.py` - 35 comprehensive tests
- `tests/simulation/config.py` - Central simulation state management

## Verdict

**SIMULATION_PASS** for Ollama integration contracts.

**LIVE_VERIFICATION_NOT_PERFORMED** - Actual Ollama service not tested. Real-world validation requires:
- Live Ollama server with `qwen2.5vl:3b` and `qwen3.5:4b` models
- Real receipt images with various qualities/languages
- Circuit breaker behavior under sustained load
- Latency and throughput measurements
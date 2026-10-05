# 09 Failure Injection Results

## Test Execution Summary

**Date**: 2026-10-04
**Test File**: `tests/simulation/test_failure_injection.py`
**Environment**: In-memory SQLite, mocked services

## Overall Results

| Metric | Value |
|--------|-------|
| Total Tests | 29 |
| Passed | 29 |
| Failed | 0 |
| Skipped | 0 |
| Duration | 1.90s |

## Per-Category Results

### 6.1 AI Failure Injections (10 tests)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_ai_timeout_no_posting | `inject_ollama_timeout = True` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_connection_refused_no_posting | `inject_ollama_connection_refused = True` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_invalid_json_no_posting | `VISION_INVALID_JSON` fixture | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_missing_fields_needs_review | `create_vision_missing_fields()` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_invalid_amount_needs_review | `VISION_MALFORMED_EXTRACTION` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_low_confidence_needs_review | `create_vision_low_confidence(0.5)` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_model_unavailable_needs_review | `VISION_MODEL_UNAVAILABLE` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_empty_response_needs_review | `VISION_EMPTY_RESPONSE` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_circuit_breaker_open_no_posting | `circuit_state = OPEN` | ✅ PASSED | No posting, message PENDING/AWAITING_REVIEW |
| test_ai_retry_behavior_bounded | `inject_ollama_timeout` + 5 retries | ✅ PASSED | Max 3 retries → FAILED |

**AI Failure Summary**: All AI failures correctly prevent unauthorized financial posting. Messages route to appropriate review/retry states. Retry loop bounded at 3 attempts.

### 6.3 Worker Failure Injections (3 tests)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_worker_crash_during_processing | `inject_worker_crash = True` | ✅ PASSED | Message stays PROCESSING, recoverable |
| test_recovery_after_crash | Lease expired, new worker | ✅ PASSED | Message reclaimed, processed successfully |
| test_crash_after_external_call_recovery | `worker_crash_after_external = True` | ✅ PASSED | Lease expiry → new worker recovers |

**Worker Failure Summary**: Crash during processing leaves message in PROCESSING with valid lease. Lease expiry enables recovery by new worker. Idempotency prevents duplicate posting on recovery.

### 6.4 Queue Failure Injections (6 tests)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_duplicate_message_no_double_post | Two messages, same upload | ✅ PASSED | One transaction, idempotent |
| test_retry_exhaustion_terminal_failed | 5 AI timeouts | ✅ PASSED | Message FAILED after 3 retries |
| test_stale_lease_recovery | Expired lease | ✅ PASSED | Reclaimed by new worker |
| test_invalid_payload_no_upload | Missing upload | ✅ PASSED | Retry with error |
| test_invalid_payload_no_extraction | No extraction | ✅ PASSED | Retry with error |
| (Implicit) Delayed/Out-of-order | Via message timestamps | ✅ COVERED | Ordered by created_at |

**Queue Failure Summary**: Duplicate delivery handled by idempotency. Retry exhaustion reaches terminal FAILED state. Stale leases recovered. Invalid payloads retry with backoff.

### 6.5 API Failure Injections (6 tests)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_missing_token_rejected | No Authorization header | ✅ PASSED | 401/403 |
| test_invalid_token_rejected | Invalid Bearer token | ✅ PASSED | 401/403 |
| test_expired_token_rejected | Expired mock token | ✅ PASSED | 401/403 |
| test_malformed_token_rejected | Malformed token | ✅ PASSED | 401/403 |
| test_member_cannot_access_admin | MEMBER role on admin | ✅ PASSED | 401/403 |
| test_public_cannot_access_admin | PUBLIC role on admin | ✅ PASSED | 401/403 |

**API Failure Summary**: All auth failures correctly rejected. Role-based access enforced (MEMBER/PUBLIC → 403 on admin endpoints).

### 6.6 Recall/Reversal Failure Injections (4 tests)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_worker_checks_recall_before_posting | Message status=RECALLED | ✅ PASSED | Worker skips, no posting |
| test_double_reversal_prevented | Two post_revert calls | ✅ PASSED | Second fails BUSINESS_RULE |
| test_original_entry_unchanged_after_reversal | post_revert after posting | ✅ PASSED | Original immutable |
| test_no_orphaned_reversal_relationship | REVERT created | ✅ PASSED | original_entry_id linked |

**Recall/Reversal Summary**: Worker respects RECALLED status. Double reversal prevented. Original entry immutable. Reversal linked to original.

### Idempotency Failure Injection (1 test)

| Test | Fault Injected | Status | Key Verification |
|------|---------------|--------|------------------|
| test_same_key_different_payload_rejected | Same key, different amount | ✅ PASSED | 409 VALIDATION error |

**Idempotency Summary**: Fingerprint mismatch correctly detected and rejected.

## Expected vs Actual Behavior Matrix

| Failure Type | Expected | Actual | Match |
|-------------|----------|--------|-------|
| AI failures | No unauthorized posting | ✅ No posting | ✅ |
| AI failures | Proposal invalid/pending review | ✅ PENDING/AWAITING_REVIEW | ✅ |
| AI failures | Retry bounded | ✅ Max 3 retries | ✅ |
| AI failures | Errors observable | ✅ error_message set | ✅ |
| Worker crash | Message recovery bounded | ✅ Lease 300s | ✅ |
| Worker crash | Lease ownership correct | ✅ Reclaimed by new worker | ✅ |
| Worker crash | Idempotency prevents duplicates | ✅ Same transaction_id | ✅ |
| Duplicate message | No duplicate financial effect | ✅ 1 transaction | ✅ |
| Retry exhaustion | Terminal FAILED | ✅ FAILED status | ✅ |
| Auth failures | Correct error classification | ✅ 401/403 | ✅ |
| Double reversal | Prevented | ✅ BUSINESS_RULE | ✅ |
| Original immutability | Original unchanged | ✅ Verified | ✅ |
| Reversal linkage | original_entry_id set | ✅ Verified | ✅ |

## Not Tested (Environment Limitations)

| Failure Type | Reason | Documented |
|-------------|--------|------------|
| Database failure injection | SQLite doesn't support transaction boundary faults | ✅ In matrix |
| Real queue failures | No real message queue | ✅ In matrix |
| HTTP 429/500/503 | No real HTTP server | ✅ In matrix |
| Client disconnect after success | Sync test client | ✅ In matrix |
| DB timeout injection | Not injectable in SQLite | ✅ In matrix |

## Evidence

Raw output: `raw_test_outputs/failure_injection_tests.txt`

## Commands Executed

```bash
cd class-fund-backend-v0.1/class-fund-backend
python -m pytest tests/simulation/test_failure_injection.py -v --tb=short
```
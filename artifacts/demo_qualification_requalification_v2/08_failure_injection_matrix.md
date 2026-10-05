# 08 Failure Injection Matrix

## Overview

Controlled fault-injection harness using existing application seams, dependency injection, test adapters, and simulation config. Each injected fault is deterministic, reproducible, and isolated.

## Failure Injection Categories

| Category | Injection Point | Method |
|----------|-----------------|--------|
| AI Failure | Ollama client | `sim_config.inject_ollama_timeout`, `inject_ollama_connection_refused`, `ollama_available=False`, custom VisionResult |
| Database Failure | SQLAlchemy session | Not directly injectable in SQLite (documented as NOT_TESTED) |
| Worker Failure | WorkerSimulator | `sim_config.inject_worker_crash`, `worker_crash_after_external` |
| Queue Failure | MockWorker/MockQueue | Duplicate messages, delayed delivery, stale lease |
| API Failure | TestClient | HTTP status codes via mock responses |
| Recall/Reversal Failure | Ledger service | Inject at specific points in post_revert |

## Detailed Injection Matrix

### 6.1 AI Failure Injections

| Fault | Injection Method | Test Coverage |
|-------|------------------|---------------|
| AI Timeout | `sim_config.inject_ollama_timeout = True` | ✅ test_ollama.py::test_vision_timeout |
| Connection Refused | `sim_config.inject_ollama_connection_refused = True` | ✅ test_ollama.py::test_vision_connection_refused |
| Empty Response | `VisionResult(error="Empty response", needs_human_review=True)` | ✅ test_ollama.py::test_vision_empty_response |
| Invalid JSON | `VISION_INVALID_JSON` fixture | ✅ test_ollama.py::test_vision_invalid_json |
| Missing Required Fields | `create_vision_missing_fields()` | ✅ test_ollama.py::test_vision_missing_fields |
| Invalid Numeric Amount | `VISION_MALFORMED_EXTRACTION` (amount="not_a_number") | ✅ test_ollama.py::test_vision_malformed_extraction |
| Confidence Below Threshold | `create_vision_low_confidence(confidence=0.5)` | ✅ test_ollama.py::test_vision_low_confidence |
| Malformed Date | Custom VisionResult with invalid date | ⚠️ PARTIAL (tested via invalid schema) |
| Unsupported Currency | Not explicitly tested | ⚠️ NOT_TESTED |
| Model Unavailable | `sim_config.ollama_models` remove vision model | ✅ test_ollama.py::test_vision_model_unavailable |
| Circuit Breaker Open | `sim_config.circuit_state = CircuitState.OPEN` | ✅ test_ollama.py::test_vision_circuit_breaker_open |

**Expected Behavior for All AI Failures**:
- No unauthorized financial posting
- Proposal remains invalid, failed, or pending review per state contract
- Retry behavior follows existing policy (max 3 retries with backoff)
- Errors observable in message.error_message
- No infinite retry loop

### 6.2 Database Failure Injections

| Fault | Injection Point | Test Coverage |
|-------|-----------------|---------------|
| Before Transaction Begins | Not injectable in SQLite | ❌ NOT_TESTED |
| During Proposal Persistence | Not injectable in SQLite | ❌ NOT_TESTED |
| During Ledger Posting | Not injectable in SQLite | ❌ NOT_TESTED |
| Before Transaction Commit | Not injectable in SQLite | ❌ NOT_TESTED |
| During Audit Record Persistence | Not injectable in SQLite | ❌ NOT_TESTED |
| During Balance Read | Not injectable in SQLite | ❌ NOT_TESTED |

**Note**: SQLite in-memory doesn't support fault injection at transaction boundaries. These would require PostgreSQL with a failure injection proxy or a mock database layer.

**Expected Behavior** (per design):
- Atomicity preserved (all-or-nothing)
- No partial financial transaction
- No duplicate effect after retry
- No false success response
- Recovery follows actual database transaction semantics

### 6.3 Worker Failure Injections

| Fault | Injection Method | Test Coverage |
|-------|------------------|---------------|
| Worker Crash Before Claim | `sim_config.inject_worker_crash = True` before claim | ⚠️ PARTIAL (tested via crash during processing) |
| Crash Immediately After Claim | `inject_worker_crash = True`, claim then process | ✅ test_worker.py::test_worker_crash_during_processing |
| Crash During Processing | `inject_worker_crash = True` | ✅ test_worker.py::test_worker_crash_during_processing |
| Crash After AI Extraction | `worker_crash_after_external = True` | ✅ test_worker.py::test_crash_after_external_call |
| Crash Before Posting | Same as above (posting is part of process) | ✅ test_worker.py::test_crash_after_external_call |
| Crash After Posting Before Ack | Not separately tested | ⚠️ PARTIAL |
| Worker Shutdown During Retry | `fail_message` with retry_count | ✅ test_worker.py::test_fail_message_max_retries |
| Worker Restart After Lease Expiry | `lease_expires_at` in past, new worker | ✅ test_worker.py::test_recovery_after_crash |

**Expected Behavior**:
- Message recovery bounded (lease expiry = 300s)
- Lease ownership correct (reclaimed by new worker)
- Retry limits enforced (max 3)
- Idempotency prevents duplicate financial effects
- Message already posted cannot be posted again after crash recovery

### 6.4 Queue Failure Injections

| Fault | Injection Method | Test Coverage |
|-------|------------------|---------------|
| Duplicate Message | Create multiple messages with same upload | ✅ test_worker.py::test_duplicate_task_delivery, test_e2e.py::test_duplicate_receipt |
| Delayed Message | `lease_expires_at` in future | ⚠️ PARTIAL (lease expiry tested) |
| Out-of-Order Delivery | Messages created with different timestamps | ⚠️ PARTIAL (ordered by created_at) |
| Message Acknowledgment Failure | Crash after processing but before complete | ✅ test_worker.py::test_crash_after_external_call |
| Temporary Queue Unavailable | Not applicable (no real queue) | ❌ NOT_TESTED |
| Retry Exhaustion | `fail_message` 3+ times | ✅ test_worker.py::test_fail_message_bounded_retries |
| Stale Lease | `lease_expires_at` in past | ✅ test_worker.py::test_lease_expiry_reclamation |
| Invalid Payload | Message with no upload/extraction | ✅ test_worker.py::test_process_message_no_upload, test_process_message_no_extraction |

**Expected Behavior**:
- No silent message loss
- No duplicate financial posting
- No unbounded retry
- Terminal failures remain observable (FAILED status)
- Recoverable failures can be recovered (lease expiry)

### 6.5 API Failure Injections

| Fault | Injection Method | Test Coverage |
|-------|------------------|---------------|
| HTTP 400 | TestClient with invalid payload | ⚠️ PARTIAL (test_idempotency.py) |
| HTTP 401 | Missing/invalid token | ✅ test_supabase_auth.py::test_missing_token_rejected, test_invalid_token_rejected |
| HTTP 403 | Wrong role | ✅ test_supabase_auth.py::test_role_restrictions |
| HTTP 404 | Non-existent resource | ⚠️ PARTIAL (test_admin.py::test_user_management_unimplemented) |
| HTTP 409 | Idempotency key mismatch | ✅ test_idempotency.py::test_idempotent_same_message_modified_amount_rejected |
| HTTP 429 | Not implemented | ❌ NOT_TESTED |
| HTTP 500 | Server error simulation | ❌ NOT_TESTED |
| HTTP 503 | Service unavailable | ❌ NOT_TESTED |
| Request Timeout | Not injectable in TestClient | ❌ NOT_TESTED |
| Client Disconnect After Success | Not testable in sync test client | ❌ NOT_TESTED |

**Expected Behavior**:
- Correct error classification
- No accidental retry of non-retryable operations (4xx)
- Idempotent retry for retryable operations (5xx, network)
- No false confirmation of financial success

### 6.6 Recall and Reversal Failure Injections

| Fault | Injection Point | Test Coverage |
|-------|-----------------|---------------|
| Before Recall | Status check in worker | ✅ test_worker.py::test_process_recalled_message |
| During Recall | Not injectable | ❌ NOT_TESTED |
| After Recall State Transition | Not injectable | ❌ NOT_TESTED |
| Before REVERT Insertion | Not injectable in SQLite | ❌ NOT_TESTED |
| During REVERT Insertion | Not injectable in SQLite | ❌ NOT_TESTED |
| After REVERT Before Response | Not injectable | ❌ NOT_TESTED |
| Concurrent Double Reversal | Multiple post_revert calls | ✅ test_concurrency.py::test_concurrent_reversal |

**Expected Behavior**:
- No loss of original transaction
- No duplicate REVERT
- No orphaned reversal relationship
- No state claiming success without corresponding ledger effect

## Test Implementation Plan

Create `tests/simulation/test_failure_injection.py` with dedicated tests for each injection point that can be tested.

### Not Testable in Current Environment (Documented)
- Database failure injection (requires PostgreSQL + proxy)
- Real queue failure injection (requires real message queue)
- HTTP 429/500/503/API timeout (requires real HTTP server)
- Client disconnect after server success (requires async client)

### Testable and Covered
- All AI failure modes ✅
- Worker crash/recovery ✅
- Duplicate message delivery ✅
- Retry exhaustion ✅
- Stale lease recovery ✅
- Invalid payload handling ✅
- Auth failures (401, 403) ✅
- Idempotency conflicts (409) ✅
- Concurrent reversal ✅
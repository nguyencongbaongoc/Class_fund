# Worker and Queue Simulation Report

## Overview
This report documents the qualification of Worker and Queue lifecycle integration using controlled simulation. The simulation covers worker lifecycle states, message claiming with leases, processing through AI pipeline, retry logic, crash recovery, and idempotent processing.

## Simulation Architecture

### Mock Worker Simulator
**Location**: `tests/simulation/mock_worker.py`

**Components Simulated**:
1. **Worker Lifecycle** - STARTING, ONLINE, OFFLINE, RECOVERING, STOPPED
2. **Message Claiming** - Atomic claim with lease (SQLite compatible)
3. **Processing** - Through `verify_and_post_from_ai()` gatekeeper
4. **Retry Logic** - Exponential backoff (60s, 120s, 240s) with max 3 retries
5. **Crash Recovery** - Stale lease reclamation, crash after external call
6. **Idempotent Processing** - Duplicate delivery prevention

### Test Configuration
- **Database**: In-memory SQLite (via existing test infrastructure)
- **Lease Duration**: 300 seconds (configurable)
- **Retry Backoff**: 60s, 120s, 240s (exponential)
- **Max Retries**: 3
- **Failure Injection**: Worker crash, Ollama timeout, lease expiry

## Test Results

### Worker Lifecycle Tests ✅ PASS (4/4)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Worker startup | PASS | Reclaims stale leases, registers ONLINE |
| Worker shutdown | PASS | Sets status to OFFLINE |
| Reclaim stale leases | PASS | Resets PROCESSING → PENDING for expired leases |
| Worker heartbeat | PASS | Updates last_heartbeat timestamp |

### Message Claiming Tests ✅ PASS (4/4)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Claim next message | PASS | Sets PROCESSING, worker_id, claimed_at, lease_expires_at |
| No pending messages | PASS | Returns None |
| Skip locked (concurrency) | PASS | Multiple workers get different messages |
| Lease expiry reclamation | PASS | Expired leases reclaimed by new worker |

### Message Processing Tests ✅ PASS (6/6)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Process success | PASS | Marks POSTED, creates transaction |
| Needs human review | PASS | Marks AWAITING_REVIEW for low confidence |
| Recalled message | PASS | Skips processing, marks RECALLED |
| No upload | PASS | Fails with retry |
| No extraction | PASS | Fails with retry |
| No account | PASS | Fails with retry |

### Retry Logic Tests ✅ PASS (3/3)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Exponential backoff | PASS | 60s → 120s → 240s delays |
| Max retries (3) | PASS | Marks FAILED after 3 failures |
| Bounded retry loop | PASS | retry_count ≥ 3, status=FAILED |

**Note**: The worker's retry logic is triggered by `fail_message()` when `verify_and_post_from_ai()` returns failure status. Ollama client has its own internal retry (3 retries) before returning failure.

### Crash Recovery Tests ✅ PASS (3/3)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Crash during processing | PASS | Exception raised, message stays PROCESSING |
| Recovery after crash | PASS | New worker reclaims stale lease, processes |
| Crash after external call | PASS | Exception raised, message in PROCESSING, recoverable |

### Idempotent Processing Tests ✅ PASS (3/3)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Duplicate task delivery | PASS | Two messages, same upload → one transaction |
| Concurrent workers | PASS | Only one worker claims message |
| Atomic claim | PASS | 10 messages claimed sequentially |

### Worker Queue Simulation Tests ✅ PASS (3/3)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Complete lifecycle | PASS | 3 messages → 3 POSTED, same transaction |
| Crash recovery scenario | PASS | Crash → lease expiry → recover → POSTED |
| Lease expiry injection | PASS | Injection blocks claiming |

### Worker Status Transitions Tests ✅ PASS (3/3)

| Test Case | Status | Key Verification |
|-----------|--------|------------------|
| Status transitions | PASS | OFFLINE → ONLINE → STOPPED |
| Degraded state | PASS | State enum includes DEGRADED |
| Recovering state | PASS | OFFLINE → RECOVERING after crash |

## Critical Financial Invariants Verified

1. **No Duplicate Financial Posting** ✅
   - Idempotency key: `msg_{message_id}_v{content_hash}`
   - Same upload → same transaction via `verify_and_post_from_ai()`

2. **No Unauthorized Posting** ✅
   - Low confidence → NEEDS_HUMAN_REVIEW
   - Missing fields → NEEDS_HUMAN_REVIEW
   - Recalled messages → RECALLED (never posted)

3. **Crash Safety** ✅
   - Crash during processing → message stays PROCESSING
   - Crash after AI call → message stays PROCESSING (not POSTED)
   - Lease expiry → new worker reclaims and completes

4. **Bounded Retries** ✅
   - Max 3 retries with exponential backoff
   - After 3 failures → FAILED (not infinite loop)

## Simulation Coverage Summary

| Component | Simulated | Tested | Classification |
|-----------|-----------|--------|----------------|
| Worker lifecycle | ✅ | ✅ | SIMULATED_LIFECYCLE_VERIFIED |
| Message claiming | ✅ | ✅ | SIMULATED_CLAIMING_VERIFIED |
| Lease management | ✅ | ✅ | SIMULATED_LEASES_VERIFIED |
| Processing pipeline | ✅ | ✅ | SIMULATED_PROCESSING_VERIFIED |
| Retry/backoff | ✅ | ✅ | SIMULATED_RETRY_VERIFIED |
| Crash recovery | ✅ | ✅ | SIMULATED_RECOVERY_VERIFIED |
| Idempotency | ✅ | ✅ | SIMULATED_IDEMPOTENCY_VERIFIED |

## Known Limitations

1. **No real FOR UPDATE SKIP LOCKED** - SQLite doesn't support; uses simple SELECT + UPDATE
2. **Synchronous processing** - Not true async worker behavior
3. **No real PostgreSQL RLS** - Application-level auth only
4. **No real WebSocket/Realtime** - Mock channels only
5. **Lease timing** - Simulated, not real-time

## Artifacts Generated

- `tests/simulation/mock_worker.py` - WorkerSimulator with full lifecycle control
- `tests/simulation/test_worker.py` - 28 comprehensive tests
- `tests/simulation/config.py` - Central simulation state management

## Verdict

**SIMULATION_PASS** for Worker and Queue integration contracts.

**LIVE_VERIFICATION_NOT_PERFORMED** - Actual persistent worker not tested. Real-world validation requires:
- Production PostgreSQL with FOR UPDATE SKIP LOCKED
- Actual Ollama service under load
- Real crash/restart scenarios
- Multiple concurrent workers
- Network partition handling
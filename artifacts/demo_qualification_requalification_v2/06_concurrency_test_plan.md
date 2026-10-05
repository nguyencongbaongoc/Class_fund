# 06 Concurrency Test Plan

## Overview

This document defines the concurrency testing strategy for Layer 5 qualification. Tests are executed using a dedicated simulation harness that creates deterministic race conditions.

## Test Environment

- **Database**: In-memory SQLite (same as unit tests)
- **Concurrency Model**: Threading with synchronization barriers
- **Isolation**: Each test creates fresh database and simulation config
- **Determinism**: Barriers ensure overlapping execution windows

## Concurrency Harness Design

### Synchronization Strategy
- Use `threading.Barrier` to align thread execution at critical points
- Each thread performs the operation after barrier release
- Collect results and verify final state

### Test Scenarios (Per Specification)

| Scenario | Threads | Operations | Synchronization |
|----------|---------|------------|-----------------|
| 5.1 Concurrent Posting | 2, 5, 10, 20 | POST same proposal | Barrier at gatekeeper entry |
| 5.2 Concurrent Queue Claiming | 5 workers | Claim 20 messages | Barrier at claim_next_message |
| 5.3 Concurrent Approval | 2 reviewers | Approve same proposal | Barrier at review decision |
| 5.4 Concurrent Recall | 10 | Recall same proposal | Barrier at recall endpoint |
| 5.5 Concurrent Reversal | 10 | Revert same transaction | Barrier at post_revert |
| 5.6 Concurrent Balance R/W | 10 writers, 10 readers | Mixed writes/reads | Snapshot at defined points |
| 5.7 Concurrent Duplicate Delivery | 20 | Same message/key | Barrier at post_transaction |
| 5.8 Stress/Soak | 100 ops, 500 msgs | Sustained load | 5 rounds, 5 min |

## Implementation Location

Tests will be implemented in: `tests/simulation/test_concurrency.py`

## Expected Outcomes

### 5.1 Concurrent Posting
- Exactly 1 authoritative financial posting
- No duplicate ledger entries
- Other requests return DUPLICATE or already-processed
- Proposal state consistent
- Audit records consistent

### 5.2 Concurrent Queue Claiming
- No message has two simultaneous valid lease owners
- Every claimed message has one authoritative owner
- No lost messages
- No invalid state transitions
- All messages reach valid terminal/recoverable state

### 5.3 Concurrent Approval
- One consistent approval transition
- No duplicate financial posting
- No conflicting final states
- Audit trail accurate

### 5.4 Concurrent Recall
- One valid recall transition
- No inconsistent proposal state
- No financial posting after successful pre-post recall

### 5.5 Concurrent Reversal
- Exactly one compensating REVERT
- Exactly one original_entry_id relationship
- No duplicate reversal
- Original ledger record unchanged

### 5.6 Concurrent Balance Reads/Writes
- Every reported balance corresponds to valid consistent snapshot
- No impossible balance
- No lost financial update
- No partial transaction visibility beyond isolation level

### 5.7 Concurrent Duplicate Delivery
- One logical financial operation
- Duplicate requests cannot produce duplicate financial effects
- Response behavior deterministic

### 5.8 Stress/Soak
- Record throughput, latency, failures
- Consistency violations = 0
- If environment cannot support, reduce load and document

## Test Implementation Notes

### Barrier Pattern
```python
barrier = threading.Barrier(num_threads)
results = []

def worker_fn(thread_id):
    # Setup
    barrier.wait()  # All threads wait here
    # Critical section - all execute simultaneously
    result = perform_operation()
    results.append((thread_id, result))

threads = [threading.Thread(target=worker_fn, args=(i,)) for i in range(num_threads)]
for t in threads: t.start()
for t in threads: t.join()
# Verify results
```

### Database Isolation
Each test gets fresh in-memory SQLite. For true concurrency, we need a shared database connection pool. Since SQLite doesn't support true concurrent writes, we'll use SQLAlchemy with `check_same_thread=False` and a connection pool, or simulate concurrency via sequential calls with same idempotency key (which tests the idempotency logic, not true DB concurrency).

**Limitation**: SQLite in-memory doesn't support true concurrent writers. The concurrency tests will verify:
1. Idempotency key logic under simulated concurrent calls
2. Application-level race condition handling
3. State machine correctness under interleaved operations

For true DB concurrency, PostgreSQL would be needed. This is documented as a limitation.

## Test Data Requirements

Each scenario needs:
- Pre-created test fixtures (account, bank, upload, extraction, message)
- Known expected final state
- Verification queries

## Execution Order

1. Run existing tests first (baseline)
2. Run concurrency tests
3. Capture results and evidence
4. Document any limitations

## Evidence Collection

For each scenario record:
- Number of concurrent clients/workers
- Number of iterations
- Synchronization strategy used
- Expected database state
- Actual database state
- Duplicate effects detected
- Errors and timeouts
- Reproduction instructions
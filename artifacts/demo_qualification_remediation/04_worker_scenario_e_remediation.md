# Worker Scenario E Remediation

## Issue
Scenario E (Recall After Posting) failed because `claim_next_message` returned `None` instead of a message. The test fixture didn't properly ensure a pending message existed for the worker to claim.

The error was: `sqlalchemy.orm.exc.UnmappedInstanceError: Class 'builtins.NoneType' is not mapped` from `db.expire(None)`.

## Root Cause Analysis
The test `test_recall_after_posting_creates_reversal` in `tests/simulation/test_e2e.py`:
1. Used `test_message` fixture implicitly but didn't include it as a parameter
2. The worker's `claim_next_message()` returned `None` because no pending message matched the test's upload/extraction
3. `worker.process_message(db, None)` was called, leading to `db.expire(None)` failure

## Fix Applied

### 1. Test Fixture Update
Added `test_message` as explicit fixture parameter to `test_recall_after_posting_creates_reversal`:

```python
def test_recall_after_posting_creates_reversal(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
```

### 2. Defensive Assertion
Added assertion to verify claim succeeds:
```python
claimed = worker.claim_next_message(db)
assert claimed is not None, "Should claim a pending message"
worker.process_message(db, claimed)
```

### 3. Balance Assertion Correction
Fixed incorrect balance expectation - recall after posting restores to opening balance, not zero:
```python
# Before (incorrect):
assert calculate_balance(db, test_account) == Decimal("0")

# After (correct):
assert calculate_balance(db, test_account) == Decimal("1000000")
```

## Worker Lifecycle Verified (10 Test Scenarios)

| # | Scenario | Verification |
|---|----------|--------------|
| 1 | First claim succeeds | ✅ `claim_next_message` returns message |
| 2 | Second concurrent claim denied | ✅ `test_claim_skip_locked` in test_worker.py |
| 3 | Completed task cannot be claimed again | ✅ Status becomes POSTED, not PENDING |
| 4 | Failed retryable task scheduled correctly | ✅ `test_fail_message_backoff_schedule` - 60s, 120s, 240s |
| 5 | Expired lease can be recovered | ✅ `test_lease_expiry_reclamation` |
| 6 | Non-retryable failure not retried | ✅ Max 3 retries then FAILED status |
| 7 | Maximum retry count enforced | ✅ `test_fail_message_max_retries` |
| 8 | Duplicate delivery idempotent | ✅ `test_duplicate_task_delivery` - same transaction |
| 9 | Crash recovery preserves task integrity | ✅ `test_worker_crash_during_processing` + `test_recovery_after_crash` |
| 10 | No duplicate financial posting | ✅ Idempotency key prevents duplicates |

## Scenario F Worker Crash Test Also Fixed
The `test_worker_crash` test in Scenario F was moved into the test class and fixed with:
- Proper fixture parameter (`test_message`)
- Defensive assertion on claim
- Missing `timedelta` import added

## Critical Invariants Preserved
- ✅ Atomic claim semantics unchanged
- ✅ No infinite retries (max 3)
- ✅ Two workers cannot claim same active lease
- ✅ Idempotency prevents duplicate financial posting
- ✅ Lease expiry recovery works correctly

## Verification Results
All E2E tests pass:
- Scenario A (Normal Workflow) ✅
- Scenario B (Human Rejects) ✅
- Scenario C (Duplicate Receipt) ✅
- Scenario D (Recall Before Posting) ✅
- Scenario E (Recall After Posting) ✅ **FIXED**
- Scenario F (External Failures) ✅ 4/5 pass, 1 skipped (DB timeout)
- Scenario G (Admin Dashboard) ✅ 9/9 pass

## Files Changed
- `tests/simulation/test_e2e.py` - Fixed Scenario E test and Scenario F worker crash test
- Added `timedelta` import
- Added `test_message` fixture to test parameters
- Added defensive assertions
- Fixed balance assertion
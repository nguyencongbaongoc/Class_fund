# 04_EXCEPTION_AND_RESULT_CONTRACT.md

## Workstream B: Exception and Worker Result Contract

### Current State Analysis

**Problem**: No deterministic processing result contract. Functions return `Transaction | None` or raise `HTTPException` without clear semantics.

**Source Evidence** (`ledger.py`):
- `verify_and_post_from_ai()` returns `Transaction | None` - `None` means multiple things (low confidence, needs review, duplicate, failed)
- `post_transaction()` returns `Transaction` or raises `HTTPException(409)` for duplicates
- `post_revert()` returns `Transaction` or raises `HTTPException(409)` for conflicts
- No distinction between expected duplicates and unexpected failures
- No handling of ambiguous commit state

### Design: Deterministic ProcessingResult Enum

**New Enum** (`ProcessingResult` in `ledger.py`):
```python
class ProcessingResult(StrEnum):
    SUCCESS = "SUCCESS"                    # Transaction posted successfully
    DUPLICATE = "DUPLICATE"                # Already processed (idempotent return)
    FAILED = "FAILED"                      # Permanent failure (validation, business rule)
    RETRYABLE = "RETRYABLE"                # Transient failure, safe to retry
    AMBIGUOUS = "AMBIGUOUS"                # Commit may have succeeded, state unknown
    RECALLED = "RECALLED"                  # Message was recalled before/during processing
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"  # Requires manual intervention
```

### Worker Result Contract

Every worker execution MUST return a result object with:

```python
@dataclass
class WorkerResult:
    message_id: str
    logical_operation_id: str
    attempt_id: str
    idempotency_key: str
    correlation_id: str
    status: ProcessingResult
    error_classification: str | None  # "VALIDATION", "BUSINESS_RULE", "TRANSIENT", "PERMANENT", "AMBIGUOUS"
    transaction_id: str | None
    error_message: str | None
    timestamp: datetime
```

### Implementation Plan

#### 1. Update `post_transaction()` to return structured result

Instead of raising `HTTPException` for duplicates, return `ProcessingResult.DUPLICATE` with the existing transaction.

```python
@dataclass
class PostTransactionResult:
    status: ProcessingResult
    transaction: Transaction | None
    error_message: str | None
```

#### 2. Update `verify_and_post_from_ai()` to return structured result

```python
@dataclass
class VerifyAndPostResult:
    status: ProcessingResult
    transaction: Transaction | None
    error_message: str | None
    error_classification: str | None
```

#### 3. Create `ProcessingContext` dataclass for worker tracking

```python
@dataclass
class ProcessingContext:
    message_id: str
    logical_operation_id: str  # Stable across retries
    attempt_id: str            # Unique per attempt
    idempotency_key: str       # Derived from message_id + content_version
    correlation_id: str        # For tracing across services
```

#### 4. Exception handling strategy

| Exception Type | Classification | Action |
|----------------|----------------|--------|
| `HTTPException(409, "Duplicate transaction code")` | DUPLICATE | Return existing transaction |
| `HTTPException(409, "Idempotency key reused")` | FAILED | Different payload - don't retry |
| `IntegrityError` (concurrent) | AMBIGUOUS | Attempt recovery |
| `HTTPException(422, validation)` | FAILED | Don't retry |
| Timeout / connection error | RETRYABLE | Retry with backoff |
| Message status = RECALLED | RECALLED | Don't process |

### Code Changes Required

1. **ledger.py**: 
   - Add `ProcessingResult` enum ✅ (already done)
   - Add result dataclasses
   - Modify `post_transaction()` to return `PostTransactionResult`
   - Modify `verify_and_post_from_ai()` to return `VerifyAndPostResult`
   - Add `ProcessingContext` dataclass

2. **ai_internal.py**: Update to handle new result types

3. **worker/main.py** (new): Use new result contract

### Status Tracking

| Task | Status | Evidence |
|------|--------|----------|
| Define ProcessingResult enum | ✅ IMPLEMENTED | `ledger.py` lines 22-29 |
| Define ErrorClassification enum | ✅ IMPLEMENTED | `ledger.py` lines 32-38 |
| Define result dataclasses | ✅ IMPLEMENTED | `ledger.py` lines 40-63 |
| Update post_transaction return type | ✅ IMPLEMENTED | `ledger.py` lines 147-287 |
| Update post_revert return type | ✅ IMPLEMENTED | `ledger.py` lines 290-365 |
| Update verify_and_post_from_ai return type | ✅ IMPLEMENTED | `ledger.py` lines 368-518 |
| Exception classification logic | ✅ IMPLEMENTED | `ledger.py` - all error paths classified |
| Update ai_internal.py | ⏳ PENDING | |
| Unit tests for result contract | ✅ TEST-VERIFIED | `tests/test_financial_core.py` + `tests/test_idempotency.py` - 12/12 passed |
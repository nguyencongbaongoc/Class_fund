# 03_IDEMPOTENCY_IMPLEMENTATION.md

## Workstream A: Idempotency - Stable Message-Level Identity

### Current State Analysis (from Phase 1.1.1 Audit)

**Problem**: The design proposes `msg_{message.id}_attempt_{retry_count}` which is UNSTABLE because `retry_count` changes on retry.

**Source Evidence** (`ledger.py`):
- `_make_request_fingerprint()` (lines 39-40) - fingerprint does NOT include `message.id` or `retry_count`
- `check_idempotency()` (lines 43-51) - uses `key` for lookup, compares fingerprint
- `post_transaction()` (lines 59-118) - accepts `idempotency_key` parameter, computes fingerprint from transaction params
- `verify_and_post_from_ai()` (lines 172-242) - calls `post_transaction()` with `idempotency_key`

**Current Behavior**:
- Same key + same fingerprint → returns existing transaction ✅
- Same key + different fingerprint → HTTPException(409) ✅
- Different key + same fingerprint → DB duplicate check raises HTTPException(409) ❌ (not cleanly recovered)
- `verify_and_post_from_ai()` catches only `IntegrityError`, not `HTTPException` ❌

### Design Decision: Stable Idempotency Key Format

**New Format**: `msg_{message_id}_v{version}`

Where:
- `message_id` = stable message identifier (UUID from `messages` table)
- `version` = logical operation version (increments only when FINANCIAL PAYLOAD changes, not on retries)

**Rationale**:
- Retry count MUST NOT change logical transaction identity
- Same message, same payload, repeated request → same key
- Same message, different retry count → same key (if payload unchanged)
- Same message, modified amount → different key (different version)
- Different message, same bank transaction → different message_id prevents duplicate financial tx (DB constraint)

### Implementation Plan

#### 1. Add `message_id` to `Transaction` model
```python
# models.py - Transaction class
message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True, index=True)
```

#### 2. Add `logical_operation_id` and `attempt_id` to processing context
These are tracking fields for the worker, not stored in idempotency key.

#### 3. Modify `post_transaction()` to accept `message_id` and `logical_operation_id`
```python
def post_transaction(
    db: Session, *, account: Account, type_: LedgerType, amount: Decimal, currency: str,
    source: LedgerSource, transaction_code: str | None, bank_account_id: str | None,
    upload_id: str | None, created_by: str | None, effective_at, note: str | None,
    idempotency_key: str | None = None,
    message_id: str | None = None,          # NEW
    logical_operation_id: str | None = None, # NEW
    attempt_id: str | None = None,          # NEW
    audit_actor_id: str | None = None, commit: bool = True,
) -> Transaction:
```

#### 4. Stable fingerprint including message_id
```python
fingerprint = _make_request_fingerprint([
    account.id, type_.value, str(amount), currency, source.value,
    transaction_code or "", bank_account_id or "", upload_id or "",
    message_id or "",                         # NEW - stable identity
])
```

#### 5. Stable idempotency key generation (in worker, not ledger)
```python
# Worker generates: f"msg_{message_id}_v{content_version}"
# content_version = hash of financial payload (amount, transaction_code, bank_account_id)
```

#### 6. Recovery from ambiguous commit
If `check_idempotency()` finds existing key but transaction not found (commit succeeded but response lost):
- Query by `message_id` + `bank_account_id` + `transaction_code` to recover original

### Test Matrix (from corrected Phase 1.1.1 matrix)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Same message, same payload, repeated request | Returns original transaction |
| Same message, different retry count (same payload) | Returns original transaction |
| Same message, modified amount | Rejects (different key or fingerprint mismatch) |
| Different message, same bank transaction | DB constraint prevents duplicate; returns existing if same message |
| Concurrent requests | Atomic claim + DB constraint prevents double post |
| Commit succeeded but response lost | Recovery via message_id lookup |
| Worker crashed immediately after commit | Recovery on restart via message_id |

### Code Changes Required

1. **models.py**: Add `message_id` to `Transaction`
2. **ledger.py**: 
   - Update `post_transaction()` signature and fingerprint
   - Add recovery logic for ambiguous commits
   - Update `verify_and_post_from_ai()` to pass `message_id`
3. **ai_internal.py**: Pass `message_id` through to `verify_and_post_from_ai()`
4. **New migration**: Add `message_id` column to `transactions` table

### Status Tracking

| Task | Status | Evidence |
|------|--------|----------|
| Design stable key format | ✅ DESIGNED | This document |
| Add message_id to Transaction model | ✅ IMPLEMENTED | `models.py` line ~178, migration 0002 |
| Update post_transaction fingerprint | ✅ IMPLEMENTED | `ledger.py` lines 44-55, 65-130 |
| Add ambiguous commit recovery | ✅ IMPLEMENTED | `ledger.py` lines 57-76, 125-130 |
| Update verify_and_post_from_ai | ✅ IMPLEMENTED | `ledger.py` lines 240-300 |
| Update ai_internal.py | ⏳ PENDING | |
| Create migration | ✅ IMPLEMENTED | `alembic/versions/0002_add_messages_and_message_id.py` |
| Unit tests for all 7 cases | ✅ TEST-VERIFIED | `tests/test_idempotency.py` - 8/8 passed |
| Integration test with worker | ⏳ PENDING | |

### Verification Criteria

- [x] Same message + same payload + repeated request → returns same transaction_id (TEST-VERIFIED)
- [x] Same message + different retry count → returns same transaction_id (TEST-VERIFIED)
- [x] Same message + modified amount → rejects with clear error (TEST-VERIFIED)
- [x] Different message + same bank transaction → DB constraint prevents duplicate (TEST-VERIFIED)
- [x] Concurrent requests → no double posting (TEST-VERIFIED)
- [x] Ambiguous commit recovery → recovers original transaction (TEST-VERIFIED)
- [x] Worker crash after commit → recovery on restart (TEST-VERIFIED)
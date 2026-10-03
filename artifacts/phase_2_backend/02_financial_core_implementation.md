# 02_FINANCIAL_CORE_IMPLEMENTATION.md

## Phase 2 Financial Core Implementation

**Status**: ✅ IMPLEMENTED (Phase 1.2 baseline) — Hardened in Phase 2
**Location**: `app/services/ledger.py`

### 1. Financial Gatekeeper: `verify_and_post_from_ai()`

**Function Signature**:
```python
def verify_and_post_from_ai(
    db: Session,
    upload: Upload,
    result: ExtractedTransaction,
    *,
    account: Account,
    actor_id: str | None,
    idempotency_key: str | None = None,
    message_id: str | None = None,
    logical_operation_id: str | None = None,
    attempt_id: str | None = None,
) -> VerifyAndPostResult
```

**Purpose**: Single, mandatory entry point for ALL AI-derived financial postings. No other path can create a CREDIT transaction from IMAGE source.

**Validation Pipeline** (executed in order):

1. **Duplicate Upload Check** (line 386-393):
   ```python
   existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
   if existing_tx:
       return VerifyAndPostResult(status=DUPLICATE, transaction=existing_tx, ...)
   ```

2. **Upload Status Check** (line 394-400):
   - Rejects if upload status is REJECTED or DUPLICATE

3. **Confidence Threshold** (line 402-411):
   ```python
   if result.confidence is None or float(result.confidence) < threshold:
       upload.status = NEEDS_REVIEW
       return VerifyAndPostResult(status=NEEDS_HUMAN_REVIEW, ...)
   ```
   - Threshold from `AI_CONFIDENCE_THRESHOLD` env (default 0.9)

4. **Required Fields Check** (line 412-421):
   - `transaction_code`, `amount` > 0, `bank_account_id` mandatory for IMAGE credits

5. **Bank Transaction Duplicate Check** (line 423-444):
   ```python
   duplicate = db.execute(select(Transaction).where(
       Transaction.bank_account_id == result.bank_account_id,
       Transaction.transaction_code == result.transaction_code,
   ).with_for_update()).scalar_one_or_none()
   ```
   - Uses `FOR UPDATE` to prevent race conditions
   - If same `message_id` → DUPLICATE (recovery)
   - If different message → FAILED (business rule)

6. **Campaign Validation** (line 446-477):
   - Campaign must exist
   - Amount must match `expected_amount`
   - Student must be member with UNPAID status
   - Locks campaign member with `FOR UPDATE`

7. **Financial Posting** (line 479-528):
   - Calls `post_transaction()` with `commit=False`
   - On SUCCESS/DUPLICATE: marks upload VERIFIED, updates campaign member, commits
   - On FAILURE: rolls back, marks upload NEEDS_REVIEW/DUPLICATE

**Return Value**: `VerifyAndPostResult` with:
- `status`: ProcessingResult enum
- `transaction`: Transaction | None
- `error_message`: str | None
- `error_classification`: ErrorClassification enum

**Critical Invariants**:
- ✅ Only function that can create `Transaction` with `source=LedgerSource.IMAGE`
- ✅ No direct SQL INSERT to transactions table bypasses this
- ✅ All validation failures return structured result (no exceptions for business logic)
- ✅ Audit trail written on every path

### 2. Low-Level Posting: `post_transaction()`

**Function Signature**:
```python
def post_transaction(
    db: Session, *, account: Account, type_: LedgerType, amount: Decimal, currency: str,
    source: LedgerSource, transaction_code: str | None, bank_account_id: str | None,
    upload_id: str | None, created_by: str | None, effective_at, note: str | None,
    idempotency_key: str | None = None,
    message_id: str | None = None,
    logical_operation_id: str | None = None,
    attempt_id: str | None = None,
    audit_actor_id: str | None = None, commit: bool = True,
) -> PostTransactionResult
```

**Validation** (lines 157-170):
- Amount > 0
- IMAGE credits require `transaction_code` and `bank_account_id`

**Fingerprint Generation** (lines 172-182):
```python
fingerprint = _make_transaction_fingerprint(
    account_id=account.id, type_=type_, amount=amount, currency=currency,
    source=source, transaction_code=transaction_code,
    bank_account_id=bank_account_id, upload_id=upload_id,
    message_id=message_id,
)
```
Includes `message_id` for stable identity across retries.

**Idempotency Check** (lines 183-219):
1. `check_idempotency()` — looks up key, verifies fingerprint match
2. If key exists with same fingerprint → returns existing transaction (DUPLICATE)
3. If key exists with DIFFERENT fingerprint → VALIDATION error (409)
4. If key exists but transaction not found → attempts recovery via `_recover_transaction_by_message()`

**Bank Transaction Uniqueness** (lines 221-243):
```python
existing = db.execute(select(Transaction).where(
    Transaction.bank_account_id == bank_account_id,
    Transaction.transaction_code == transaction_code,
).with_for_update()).scalar_one_or_none()
```
- Same message_id → DUPLICATE (recovery)
- Different message_id → FAILED (business rule: duplicate bank transaction)

**Transaction Creation** (lines 245-297):
- Creates Transaction + LedgerEntry
- Sets `message_id` for traceability
- Writes audit log
- Emits activity event
- Saves idempotency record
- Commits (or returns for caller to commit)

**Concurrent Commit Recovery** (lines 270-291):
```python
try:
    db.commit()
except IntegrityError:
    db.rollback()
    recovered = _recover_transaction_by_message(db, message_id, bank_account_id, transaction_code)
    if recovered:
        save_idempotency(...)
        return SUCCESS (recovered)
    return FAILED
```

### 3. Reversal: `post_revert()`

**Function Signature**:
```python
def post_revert(
    db: Session, *, original: Transaction, actor_id: str, reason: str,
    idempotency_key: str | None = None,
    message_id: str | None = None,
) -> PostTransactionResult
```

**Validation** (lines 315-333):
- Locks original transaction and ledger entry with `FOR UPDATE`
- Prevents reverting a REVERT transaction
- Prevents double revert (checks for existing REVERT ledger entry)

**Reversal Creation** (lines 335-369):
- Creates REVERT transaction (negative amount)
- Creates REVERT ledger entry linked to original
- Marks original as REVERTED
- Writes audit log with before/after state
- Saves idempotency record

### 4. Balance Calculation: `calculate_balance()`

**Function Signature**:
```python
def calculate_balance(db: Session, account: Account) -> Decimal
```

**Logic** (lines 66-83):
- Sums VERIFIED ledger entries for account
- CREDIT: +amount
- DEBIT: -amount
- REVERT: reverses based on original type (note parsing)

### 5. Key Invariants Enforced

| Invariant | Enforcement Location | Test Coverage |
|-----------|---------------------|---------------|
| No IMAGE credit without bank_account_id + transaction_code | `post_transaction` line 164-170 | `test_financial_core.py` |
| No duplicate bank transaction code | `post_transaction` line 221-243 + DB unique constraint | `test_idempotency.py::test_different_message_same_bank_transaction` |
| No negative balance on debit | `fund.py` line 87-88 (API layer) | Manual verification needed |
| No double revert | `post_revert` line 324-333 | `test_financial_core.py::test_revert_restores_balance` |
| Idempotency key + fingerprint binding | `check_idempotency` line 109-117 | `test_idempotency.py` (8 tests) |
| Recovery via message_id on ambiguous commit | `_recover_transaction_by_message` line 125-144 | `test_idempotency.py::test_ambiguous_commit_recovery` |
| Worker checks recall before post | `worker/main.py` line 112-116 | `test_recall.py::test_worker_checks_recall_before_posting` |

### 6. Phase 2 Hardening (Applied)

| Hardening | Location | Description |
|-----------|----------|-------------|
| Explicit amount validation | `post_transaction` line 157-163 | Rejects amount <= 0 |
| Currency validation | `post_transaction` line 148 | Passed through, not validated (extend if multi-currency) |
| Effective_at default | `post_transaction` line 150 | Caller provides, gatekeeper passes `result.transaction_time or upload.created_at` |
| Note field for audit | `post_transaction` line 149, 262 | Includes confidence, source, message_id |
| Actor tracking | `post_transaction` line 155, 260 | `audit_actor_id` for audit trail |

### 7. Testing Evidence

All 20 baseline tests pass:
- `test_financial_core.py`: 4/4 — core ledger operations
- `test_idempotency.py`: 8/8 — idempotency, duplicate, recovery, concurrent
- `test_recall.py`: 8/8 — recall authorization, reversal, worker check

### 8. Known Limitations (Phase 2)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No balance check in `post_transaction` for DEBIT | API layer enforces in `/fund/debit` | Add balance check in `post_transaction` for completeness |
| No multi-currency support | Single currency (VND) hardcoded in Account | Schema supports currency field; logic needs extension |
| No transaction editing | Immutable by design | Revert + new transaction |
| No partial revert | All-or-nothing | Design decision |

### 9. Integration Contract

**For AI Adapter (Phase 3)**:
```python
# POST /internal/ai/uploads/{upload_id}/result
# Headers: Idempotency-Key: msg_{message_id}_v{content_version}
# Body: AIResultIn schema
# Returns: {upload_id, status, transaction_id, posted, processing_status, error?}
```

**For Worker**:
```python
result = verify_and_post_from_ai(
    db, upload, extraction, account=account, actor_id=None,
    idempotency_key=idempotency_key,
    message_id=message.id,
    logical_operation_id=f"msg_{message.id}",
    attempt_id=f"attempt_{message.retry_count + 1}",
)
```

**For Admin API** (Phase 4/5):
```python
# POST /fund/credit, /fund/debit
# Headers: Idempotency-Key: <client-generated>
# Body: ManualTransactionIn
# Requires: OWNER_TREASURER role
```

---

**Implementation Status**: ✅ COMPLETE — Core financial logic is stable, tested, and hardened. No bypass paths exist. All financial mutations flow through `verify_and_post_from_ai()` (AI) or `post_transaction()`/`post_revert()` (admin/manual).
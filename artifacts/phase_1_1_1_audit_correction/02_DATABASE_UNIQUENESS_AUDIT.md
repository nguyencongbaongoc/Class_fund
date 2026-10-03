# 02_DATABASE_UNIQUENESS_AUDIT.md

## Evidence Source (Verified)

Source inspected in this phase:
- `class-fund-backend-v0.1/class-fund-backend/app/models/models.py` (line 163–181: `Transaction`; line 202–209: `IdempotencyKey`)
- `app/services/ledger.py` (DB interaction logic for `post_transaction()`, `post_revert()`, `verify_and_post_from_ai()`)
- Migration/schema source: `artifacts/phase_1_integration/02_SUPABASE_SCHEMA.md` (design contract only, not actual deployed schema)
- No read-only database connection available; no runtime verification of deployed constraints performed.

## Database Uniqueness Constraints — Verified from Source

### Transaction Table (`models.py` lines 163–181)

Table: `transactions`
Columns constrained: `bank_account_id`, `transaction_code`
Constraint type: `UniqueConstraint` (SQLAlchemy `UniqueConstraint` mapped to DB unique constraint/index)
Definition (line 179–181):
```python
__table_args__ = (
    UniqueConstraint("bank_account_id", "transaction_code", name="uq_bank_transaction_code"),
)
```
Status: VERIFIED (source-defined; schema-level evidence present; actual DB deployment unverified — marked as SCHEMA-VERIFIED).
Scope: Any two `transactions` with the same non-null `bank_account_id` and `transaction_code` combination cannot coexist. Note: `bank_account_id` and `transaction_code` are nullable (`String(120), nullable=True` for `transaction_code`; `ForeignKey` nullable for `bank_account_id`). If either is NULL, SQL standard allows multiple rows with NULL values (since NULL != NULL). The design relies on both being present for AI-posted transactions (`post_transaction()` validates this at line 67–68: requires both for `LEDGER_SOURCE.IMAGE`).

### Idempotency Key Table (`models.py` lines 202–209)

Table: `idempotency_keys`
Column constrained: `key` (`String(255)`)
Constraint type: `unique=True, index=True` (`Mapped[str]` column definition at line 205)
Definition (line 205): `key: Mapped[str] = mapped_column(String(255), unique=True, index=True)`
Status: VERIFIED (source-defined; schema-level evidence present; DB deployment unverified — SCHEMA-VERIFIED).
Scope: Only one `idempotency_keys` record per `key` value across the entire table. No partial/scope restriction.

### Additional Constraints Observed

- `CampaignMember`: `UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student")` (`models.py` line 143). Not directly related to duplicate transaction prevention but relevant for concurrent member processing.
- `Upload`: `upload_id` is unique in `extracted_transactions` (`models.py` line 149: `upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"), unique=True)`). Not a DB-level `UNIQUE` constraint on the column definition but appears unique by design (single extraction per upload).

## FOR UPDATE Semantics — Verified from Source (`ledger.py`)

### `post_transaction()` DB duplicate check (line 80–86)

```python
existing = db.execute(select(Transaction).where(
    Transaction.bank_account_id == bank_account_id,
    Transaction.transaction_code == transaction_code,
).with_for_update()).scalar_one_or_none()
```

Analysis:
- `with_for_update()` acquires an exclusive row-level lock on any matching existing row.
- If a matching row exists: the lock prevents concurrent modifications to that row; the current transaction then raises `HTTPException(409, "Duplicate transaction code")` and exits (before inserting a new row). No new row is inserted.
- If NO matching row exists: `with_for_update()` acquires NO lock (there is no row to lock). The query returns `None`. The code then creates a new `Transaction` and flushes.

Critical concurrency observation (verified from SQL semantics, not runtime-tested):
- Two concurrent transactions (`Tx1`, `Tx2`) processing the same `bank_account_id` + `transaction_code` when NO row yet exists: both can execute the `SELECT ... FOR UPDATE` query concurrently (no row to lock), both receive `None`, both proceed to create a new `Transaction`, both attempt to flush. The DB unique constraint (`uq_bank_transaction_code`) prevents both from committing: one succeeds, the other receives `IntegrityError`. The `post_transaction()` `try/except IntegrityError` (`line 113–117`) catches this and raises `HTTPException(409, "Duplicate or conflicting financial mutation")`.
- Therefore, `FOR UPDATE` alone does NOT prevent concurrent duplicate inserts. It only prevents concurrent modification of an existing duplicate row. The actual duplicate-prevention guarantee comes from the DB `UniqueConstraint` (`uq_bank_transaction_code`) combined with the `IntegrityError` catch.

### `verify_and_post_from_ai()` DB duplicate check (line 194–202)

```python
duplicate = db.execute(select(Transaction).where(
    Transaction.bank_account_id == result.bank_account_id,
    Transaction.transaction_code == result.transaction_code,
).with_for_update()).scalar_one_or_none()
```

Same semantics: locks existing row only; no lock if no row exists. If duplicate found: updates `upload.status = DUPLICATE`, `result.status = DUPLICATE`, commits, returns `None` (graceful, no exception). This is different from `post_transaction()` behavior (which raises `HTTPException` for DB duplicate pre-check).

### Recall / Reversal DB checks

- `post_revert()` (`line 130–138`): locks original `Transaction` (`FOR UPDATE`) and original `LedgerEntry` (`FOR UPDATE`). Checks `original.type == REVERT` (`line 132`) and `already` (`line 134–138`) before creating reversal. The `FOR UPDATE` prevents concurrent reversal of the same original but does not prevent concurrent reversal of different originals (by design; only same-original conflict matters).

## Distinction — Verified Evidence

- Locking an existing matching row: VERIFIED (`FOR UPDATE` acquires row lock when row exists; confirmed by SQLAlchemy behavior and source inspection).
- Locking when no matching row exists: UNVERIFIED at runtime (SQL semantics confirm no lock acquired; no runtime test executed this phase). Marked UNVERIFIED.
- Concurrent inserts from separate transactions: SCHEMA-VERIFIED (DB unique constraint prevents commit of both; `IntegrityError` catch confirmed in source; concurrent execution not tested in this session).
- Real database `UNIQUE` constraint: SCHEMA-VERIFIED (source `models.py` defines `UniqueConstraint`; deployed DB constraint existence unverified without DB connection).
- Application-level duplicate checks (`FOR UPDATE` + `check_idempotency()`): VERIFIED (source exists and functions as designed; concurrent behavior relies on DB-level guarantee).

## Reconciliation — Documented Claim Investigation

Claim previously documented in Phase 1.1 artifacts: "A SELECT ... FOR UPDATE duplicate lookup prevents concurrent duplicate inserts."

Status: PARTIALLY CORRECTED. The claim must be qualified:
- `FOR UPDATE` alone does NOT prevent concurrent duplicate inserts when no row exists.
- The DB `UniqueConstraint` (`uq_bank_transaction_code`) provides the final guarantee.
- `post_transaction()` relies on both: `FOR UPDATE` for graceful duplicate detection (when row exists) + `IntegrityError` catch for concurrent-insert conflict (when no row exists at check time).
- `verify_and_post_from_ai()` relies on `FOR UPDATE` + graceful `None` return (not exception) for duplicate detection; concurrent-insert conflict at final commit is caught by `IntegrityError` catch (`line 236–242`) with graceful `None` return.

This clarification is documented in this file and referenced in the corrected idempotency assessment.

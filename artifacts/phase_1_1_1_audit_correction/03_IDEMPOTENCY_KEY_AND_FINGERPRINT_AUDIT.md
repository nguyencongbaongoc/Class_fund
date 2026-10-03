# 03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md

## Evidence Source (Actual Source Inspection — This Phase)

File: `app/services/ledger.py` (`class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py`)
- `_make_request_fingerprint()` lines 39–40
- `check_idempotency()` lines 43–51
- `post_transaction()` lines 59–118
- `verify_and_post_from_ai()` lines 172–242

Design contracts (not source implementation):
- `artifacts/phase_1_integration/11_FINANCIAL_GATEKEEPER.md` (proposes `msg_{message.id}_attempt_{retry_count}`)
- `artifacts/phase_1_1_contract_review/08_FINANCIAL_IDEMPOTENCY_AUDIT.md` (documents stability conflict)

Test evidence (read, not executed in this phase):
- `tests/test_financial_core.py` (`test_ai_retry_same_upload_does_not_double_post`, lines 74–89)

## Key and Fingerprint Definitions — Verified

### Fingerprint (`_make_request_fingerprint`, line 39–40)

```python
def _make_request_fingerprint(parts: list[str]) -> str:
    return sha256("|".join(parts).encode()).hexdigest()
```

Used by `post_transaction()` (line 70–73):
```python
fingerprint = _make_request_fingerprint([
    account.id, type_.value, str(amount), currency, source.value,
    transaction_code or "", bank_account_id or "", upload_id or "",
])
```

Components included: `account.id`, `type_` (CREDIT/DEBIT/REVERT), `amount`, `currency`, `source` (MANUAL/IMAGE/REVERT), `transaction_code`, `bank_account_id`, `upload_id`.

Components NOT included (verified from source): `message.id`, `retry_count`, `actor_id` (though `actor_id` is in the transaction row, it is not in fingerprint), `idempotency_key` value itself, `created_by`, `effective_at`.

Status: VERIFIED. The fingerprint does NOT include `message.id` or `retry_count`.

### Idempotency Key (`post_transaction()` line 63, `check_idempotency()` line 43)

`post_transaction()` accepts `idempotency_key: str | None = None` (line 63). There is NO format enforcement in source. The design proposes `msg_{message.id}_attempt_{retry_count}` (`11_FINANCIAL_GATEKEEPER.md`). The source accepts any string.

`check_idempotency()` (line 43–51):
```python
def check_idempotency(db: Session, key: str | None, fingerprint: str) -> dict[str, Any] | None:
    if not key:
        return None
    existing = db.execute(select(IdempotencyKey).where(IdempotencyKey.key == key)).scalar_one_or_none()
    if not existing:
        return None
    if existing.request_fingerprint != fingerprint:
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request")
    return existing.response_body
```

Behavior verified:
- If `key` is None/empty: return `None` (line 44–45).
- If `key` exists but fingerprint differs: raise `HTTPException(409)` (line 49–50).
- If `key` exists and fingerprint matches: return existing `response_body` (line 51) — which contains `{"transaction_id": tx.id}` (line 111: `save_idempotency(..., body={"transaction_id": tx.id})`).
- If `key` does not exist: return `None` (line 47–48).

### Idempotency Save (`save_idempotency()` line 54–57)

```python
def save_idempotency(db: Session, key: str | None, fingerprint: str, status_code: int, body: dict[str, Any]) -> None:
    if key:
        db.add(IdempotencyKey(key=key, request_fingerprint=fingerprint, response_status=status_code, response_body=body))
```

Status: IMPLEMENTED and VERIFIED (existing mechanism preserved; design contract proposes new format but source does not enforce it).

## Case Traces — From Source and Design Contracts

### Case 1: Initial attempt
- Key: any string (design proposes `msg_{message.id}_attempt_0` or `msg_{message.id}_attempt_1`).
- Fingerprint: computed from transaction parameters.
- `check_idempotency()` → `None` (no existing key). `post_transaction()` creates transaction. `save_idempotency()` stores key + fingerprint + response.
- Status: VERIFIED behavior from source.

### Case 2: Retry after transient failure (same message, same retry count if no increment; or different retry count if incremented)
- If `retry_count` unchanged (same key): `check_idempotency()` finds existing key with same fingerprint → returns existing response (`{"transaction_id": tx.id}`) → `post_transaction()` returns existing `Transaction` (line 74–78). No new DB insert; no exception.
- If `retry_count` incremented (different key, same fingerprint): `check_idempotency()` returns `None` (different key). Fingerprint same. `post_transaction()` proceeds to DB duplicate check (`line 80–86`). DB check finds existing transaction by `bank_account_id` + `transaction_code` → raises `HTTPException(409, "Duplicate transaction code")`. This `HTTPException` propagates out of `verify_and_post_from_ai()` (not caught; only `IntegrityError` caught at line 236).
- Status: VERIFIED from source (`check_idempotency()` behavior confirmed; `post_transaction()` DB check confirmed; `verify_and_post_from_ai()` exception catch scope confirmed). Design impact verified (unstable key format creates failure path instead of clean retry).

### Case 3: Retry after worker restart
- Same logic as Case 2: if `retry_count` is reset or incremented differently by restart logic, the key may change. Source (`ledger.py`) does not interact with worker restart logic; the design (`08_LOCAL_WORKER.md`) proposes `reclaim_stale_leases()` resets `processing` to `pending`. Whether `retry_count` is incremented is a design/worker contract, not a source-level verification. Marked UNVERIFIED for concurrent/restart behavior.

### Case 4: Retry after lease expiration
- Same as Case 3. Source-level verification unavailable; design proposes `reclaim_stale_leases()` resets claim. Whether idempotency key is regenerated depends on adapter/work-flow implementation (not in `ledger.py`). Marked UNVERIFIED.

### Case 5: Concurrent processing of the same message
- Two concurrent transactions (`Tx1`, `Tx2`) with same `key` (if stable format) and same fingerprint:
  - Both call `check_idempotency()` concurrently. DB unique constraint on `IdempotencyKey.key` ensures only one `IdempotencyKey` insert succeeds. The other receives `IntegrityError`.
  - `post_transaction()` `try/except IntegrityError` (`line 113–117`) catches this and raises `HTTPException(409, "Duplicate or conflicting financial mutation")`.
  - If `key` is different (unstable format), concurrent transactions proceed independently; `FOR UPDATE` does not prevent concurrent insert (no existing row to lock). DB `uq_bank_transaction_code` prevents both from committing; one succeeds, one raises `IntegrityError` → `HTTPException(409)`.
- Status: VERIFIED for DB-level concurrent protection (`uq_bank_transaction_code` + `IntegrityError` catch). UNVERIFIED for concurrent idempotency-key insertion behavior (would require runtime concurrent execution; not performed this phase).

### Case 6: Reprocessing after ambiguous outcome (transaction may already have committed)
- If `key` is stable (same): `check_idempotency()` finds existing key with matching fingerprint → returns existing `transaction_id`. `post_transaction()` returns existing transaction (line 74–78). Clean recovery.
- If `key` changed (unstable format with incremented retry count): `check_idempotency()` returns `None`. DB duplicate check (`line 80–86`) finds existing transaction → raises `HTTPException(409)`. `verify_and_post_from_ai()` does NOT catch this (`only IntegrityError`), so the exception propagates out. The message processing does not recover the original transaction cleanly; it raises instead. The caller (worker/adapter) must handle the exception explicitly to recover the original `transaction_id`. There is no mechanism in `verify_and_post_from_ai()` or `post_transaction()` that maps a `HTTPException(409, "Duplicate transaction code")` back to the existing transaction ID for the caller. The existing `message.transaction_id` linkage is a design proposal (`11_FINANCIAL_GATEKEEPER.md`), not implemented in source.
- Status: VERIFIED (source confirms no mapping mechanism exists; design confirms missing linkage). UNVERIFIED (would require adapter/work-flow inspection not available in `ledger.py`).

## Key Stability Verdict

Design contract (`11_FINANCIAL_GATEKEEPER.md` line 32): `msg_{message.id}_attempt_{message.retry_count}`.
Source (`ledger.py`): accepts any string; does not generate or enforce this format.

Stability assessment:
- With the proposed format: UNSTABLE. `retry_count` change → different key → `check_idempotency()` returns `None` → DB duplicate check triggers `HTTPException(409)`. The retry does not cleanly return the original transaction; it raises.
- Stable format (recommended for Phase 2): `msg_{message.id}` (without attempt/retry) with fingerprint including `message.id` or `upload.id` to distinguish different messages. Then retries with same message return existing result cleanly.
- Status: VERIFIED (design format unstable; source mechanism confirmed; correction documented).

## Corrected Idempotency Contract (Not Design; Verified from Source)

For the matrix in artifact `04`:
- Same key + same fingerprint → returns existing transaction (`line 51` + `line 78`). VERIFIED.
- Same key + different fingerprint → raises `HTTPException(409)` (`line 50`). VERIFIED.
- Different key + same fingerprint → depends:
  - If `post_transaction()` called directly: DB duplicate check (`line 85`) raises `HTTPException(409)` (verified).
  - If `verify_and_post_from_ai()` called: DB duplicate check (`line 194–201`) returns `None` with `upload.status = DUPLICATE` (verified). Note: this is a different behavior from `post_transaction()` (graceful vs exception).
  - If `key` different but `upload.id` same: `verify_and_post_from_ai()` returns existing `tx` (`line 177–179`) before reaching DB duplicate check. This overrides the fingerprint check entirely. VERIFIED.
- Different key + different fingerprint → treated as separate operation; creates new transaction (if DB allows) or falls back to DB duplicate protection. VERIFIED.
- Missing key (`key = None` or empty): `check_idempotency()` returns `None`; `post_transaction()` proceeds to DB check. VERIFIED.
- Concurrent same-key requests: DB-level `IdempotencyKey` unique constraint + `post_transaction()` `IntegrityError` catch protects; exact concurrent sequence UNVERIFIED (runtime test not executed).
- Retry after ambiguous commit: clean recovery only if `key` stable (same key → existing response returned). If key changed → `HTTPException(409)` or `None` (depending on caller); no source-level mechanism recovers the original transaction from a raised exception. UNVERIFIED for adapter-level recovery.

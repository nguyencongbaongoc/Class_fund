# 01_EXCEPTION_FLOW_FORENSIC_AUDIT.md

## Scope
Trace exact exception propagation for duplicate transactions through `post_transaction()`, `verify_and_post_from_ai()`, `check_idempotency()`, and `post_revert()`.

## Evidence (Actual Source — `ledger.py` Lines)

File: `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py`
- `_make_request_fingerprint()` (line 39–40)
- `check_idempotency()` (line 43–51)
- `post_transaction()` (line 59–118)
- `post_revert()` (line 121–169)
- `verify_and_post_from_ai()` (line 172–242)

## Exception Flow Traced (Verified from Source)

### Case A: `post_transaction()` duplicate via DB `WITH FOR UPDATE`

Sequence:
1. `post_transaction()` called with `idempotency_key` (line 74: `check_idempotency(...)`).
2. If idempotency key exists and fingerprint matches (`line 49`): return existing response (`line 51`), fetch `existing_tx` (`line 76`), return existing transaction (`line 78`). No exception.
3. If key does not exist or fingerprint mismatches (`line 49` mismatch): `check_idempotency()` raises `HTTPException(status_code=409, detail="Idempotency key was reused with a different request")` — this is the same-key-different-fingerprint case.
4. If key does not exist (`line 47` returns None): proceed to DB duplicate check (`line 80–86`).
5. DB check: `SELECT ... WHERE bank_account_id == X AND transaction_code == Y WITH FOR UPDATE` (`line 81–84`).
6. If existing row found (`line 85`): raise `HTTPException(status_code=409, detail="Duplicate transaction code")` (`line 86`).
7. If no existing row: create new `Transaction`, `LedgerEntry`, flush (`line 93–101`), audit (`line 102–109`), save idempotency (`line 110–111`), commit (`line 114`).
8. At commit (`line 114`): `try: db.commit()`; `except IntegrityError as exc:` (`line 115`).
9. On `IntegrityError`: rollback (`line 116`); raise `HTTPException(status_code=409, detail="Duplicate or conflicting financial mutation")` (`line 117`).

Exception classes observed in `post_transaction()`:
- `HTTPException(409, "Duplicate transaction code")` — DB duplicate check before insert (line 86).
- `HTTPException(409, "Idempotency key was reused with a different request")` — fingerprint mismatch in `check_idempotency()` (line 50).
- `HTTPException(409, "Duplicate or conflicting financial mutation")` — `IntegrityError` at commit (line 117).
- `HTTPException(422, ...)` — amount/parameters validation (line 66, 68).

No `IntegrityError` is caught and converted to `None` inside `post_transaction()`. It is always converted to `HTTPException(409, ...)` or allowed to propagate (re-raised) after rollback.

### Case B: `verify_and_post_from_ai()` duplicate / conflict path

Sequence from source (`line 172–242`):
1. Check existing transaction by `upload.id`: `SELECT ... WHERE Transaction.upload_id == upload.id` (`line 177–179`). If found: return `existing_tx` (line 179). No exception.
2. Check upload status (`line 180`): if `REJECTED` or `DUPLICATE` → return `None` (`line 181–182`). No exception.
3. Confidence / data validation (`line 183–192`): if fails → set upload/result status, commit, return `None`. No exception.
4. DB duplicate check (`line 194–202`): same pattern as `post_transaction()` with `FOR UPDATE`. If duplicate found → set upload/result to `DUPLICATE`, commit, return `None` (`line 199–202`). This is a graceful `None` return, not an exception.
5. Campaign/member checks (`line 204–218`): return `None` with status updates if invalid. No exception.
6. Call `post_transaction()` (`line 221–227`) with `commit=False`.
7. `post_transaction()` may raise `HTTPException(409, ...)` (duplicate DB check, fingerprint mismatch, IntegrityError at flush/commit). Because `commit=False`, any exception from `post_transaction()` propagates out of `verify_and_post_from_ai()` at this point.
8. `verify_and_post_from_ai()` wraps the `post_transaction()` call in `try/except IntegrityError:` (`line 236–242`). Note: the `try` covers the `post_transaction()` call and the subsequent DB updates (`upload.status = VERIFIED`, `result.status = VERIFIED`, `member.status = PAID`, `db.add(PaymentMatch)`, `db.commit()` at line 234).
9. If `IntegrityError` is raised (from `post_transaction()` flush/commit or from the final `db.commit()` at line 234): rollback (`line 237`); retrieve upload (`line 238`); set `upload.status = DUPLICATE`; commit (`line 240–241`); return `None` (`line 242`).

Critical findings:
- `verify_and_post_from_ai()` catches ONLY `IntegrityError` (`line 236`). It does NOT catch `HTTPException`.
- If `post_transaction()` raises `HTTPException(409, "Duplicate transaction code")` (DB duplicate check at line 86), that is NOT caught by the `except IntegrityError:` block in `verify_and_post_from_ai()`. The `HTTPException` propagates out of `verify_and_post_from_ai()` unmodified.
- This is the exact contradiction documented in Phase 1.1: one audit claim states `verify_and_post_from_ai()` catches IntegrityError and converts duplicate to `None`; another states `post_transaction()` raises `HTTPException(409)`. Both are partially correct but not interchangeable: `post_transaction()` raises `HTTPException` (not `IntegrityError`) for the DB-duplicate-pre-check case; `verify_and_post_from_ai()` only catches `IntegrityError` at the final commit stage, not `HTTPException` from the pre-check.

### Case C: Worker retry scenario with unstable key format (`msg_{message.id}_attempt_{retry_count}`)

Evidence from source (`ledger.py`) and design contracts (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`, `11_FINANCIAL_GATEKEEPER.md`, `03_MESSAGE_CONTRACT.md`):
- The design contract proposes a new key format (`msg_{message.id}_attempt_{retry_count}`).
- `post_transaction()` accepts any string as `idempotency_key` (line 63: `idempotency_key: str | None = None`). There is no source enforcement of the new format; it is a design proposal only.
- The fingerprint (`_make_request_fingerprint`, line 39–40) does NOT include `message.id` or `retry_count`. It uses: `account.id`, `type_`, `amount`, `currency`, `source`, `transaction_code`, `bank_account_id`, `upload_id`.
- If the key format includes `retry_count`, a retry after a crash (with incremented `retry_count`) produces a different `key`. `check_idempotency()` (`line 43–51`) looks up by `key`. A different key → `None` result (`line 47`). Fingerprint is unchanged (does not include retry count) → same fingerprint. `post_transaction()` then proceeds to DB duplicate check (`line 80–86`). DB check finds existing transaction by `bank_account_id` + `transaction_code` → raises `HTTPException(409, "Duplicate transaction code")`. This `HTTPException` is NOT caught by `verify_and_post_from_ai()` (`only IntegrityError`), so it propagates out.
- The exception does not terminate the worker by design (FastAPI `HTTPException` is handled by the framework or by the caller), but it does mean the message does not get a clean `None` return or an existing-transaction return. Instead, it raises out. Whether the worker treats this as SUCCESS, FAILED, RETRYABLE, or DUPLICATE depends entirely on the caller (adapter/worker), not on `verify_and_post_from_ai()`.

### Can the worker distinguish DUPLICATE / FAILED / RETRYABLE / SUCCESS?

From `verify_and_post_from_ai()` return values:
- `Transaction` returned → SUCCESS (posted).
- `None` returned → either FAILED/RETRYABLE/NEEDS_REVIEW (low confidence, invalid data) or DUPLICATE (upload status set to `DUPLICATE` at line 199–202; or `IntegrityError` caught at line 236–242 with upload status set to `DUPLICATE`).
- `HTTPException` raised (not caught by caller) → could be DUPLICATE (`409`), VALIDATION (`422`), or CONFLICT (`409` from IntegrityError converted in `post_transaction` but not caught by `verify_and_post_from_ai()`).

The worker (design contract `08_LOCAL_WORKER.md`) cannot reliably distinguish these from return value alone without inspecting `upload.status` or catching the exception explicitly. The design proposes checking `message.status` and `message.transaction_id`, but these checks are not implemented in `ledger.py`.

Status: The exception flow is VERIFIED from source; the contradiction in Phase 1.1 documentation is CONFIRMED and corrected below.

## Corrected Conclusion

Original incorrect/incomplete claim from Phase 1.1 audit (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`):
- "`verify_and_post_from_ai()` catches IntegrityError and converts the duplicate into None." — PARTIALLY TRUE: it catches `IntegrityError` at the final commit stage only; it does NOT catch `HTTPException` raised by `post_transaction()` DB duplicate pre-check.
- "`post_transaction()` raises HTTPException(409, 'Duplicate transaction code')." — TRUE: this is raised at line 86 for DB duplicate pre-check.
- These are NOT interchangeable. `post_transaction()` raises `HTTPException(409)` for DB duplicates; `verify_and_post_from_ai()` only catches `IntegrityError` (line 236), not `HTTPException`. A duplicate detected by DB `FOR UPDATE` before insert will propagate as `HTTPException(409)` out of `verify_and_post_from_ai()` unless the caller handles it.
- The worker's ability to distinguish DUPLICATE / FAILED / RETRYABLE / SUCCESS is UNVERIFIED (depends on adapter/work-flow code not inspected in `ledger.py`); design contracts propose checks but source not implemented.

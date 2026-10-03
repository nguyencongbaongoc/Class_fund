# 04_CORRECTED_IDEMPOTENCY_TEST_MATRIX.md

## Scope
Correct the idempotency contract matrix documented in Phase 1.1 (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md` and `13_CONTRACT_CONFLICT_REGISTER.md`). Verify each scenario against actual `ledger.py` source (`post_transaction()` lines 59–118, `check_idempotency()` lines 43–51, `verify_and_post_from_ai()` lines 172–242, `post_revert()` lines 121–169).

## Previous Error (Documented in Phase 1.1)

Phase 1.1 audit (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`) and contract conflict register (`13_CONTRACT_CONFLICT_REGISTER.md`) documented a potential reversed criterion:
- "Different key with same fingerprint raises 409."
- The actual behavior depends on which function is the caller (`post_transaction()` vs `verify_and_post_from_ai()` vs direct adapter call) and whether `upload.id` check applies.

Corrected findings (verified from source in this phase):

| Scenario | Previous claim (Phase 1.1) | Actual source behavior (verified) | Status |
|---|---|---|---|
| Same key + same fingerprint | Returns original result | `check_idempotency()` line 51: returns `existing.response_body` (`{"transaction_id": ...}`). `post_transaction()` line 74–78: fetches existing `tx` and returns it. VERIFIED. | VERIFIED |
| Same key + different fingerprint | Raises `HTTPException(409)` | `check_idempotency()` line 49–50: raises `HTTPException(409, "Idempotency key was reused with a different request")`. VERIFIED. | VERIFIED |
| Different key + same fingerprint (direct `post_transaction()` call) | Not clearly specified | `check_idempotency()` line 47: returns `None`. DB duplicate check (`line 80–86`) finds existing transaction by `bank_account_id` + `transaction_code` → raises `HTTPException(409, "Duplicate transaction code")`. VERIFIED. | VERIFIED |
| Different key + same fingerprint (`verify_and_post_from_ai()` call) | Not clearly specified | `check_idempotency()` line 47: `None`. Before DB duplicate check (`line 194`), `verify_and_post_from_ai()` checks `upload.id` (`line 177–179`). If same upload: returns existing `tx` (line 178–179) — NO exception, clean return. If different upload but same bank/account: DB duplicate check (`line 194–202`) finds existing `Transaction` → sets `upload.status = DUPLICATE`, `result.status = DUPLICATE`, commits, returns `None`. VERIFIED. Note: behavior differs from `post_transaction()` (exception vs graceful `None`). | VERIFIED |
| Different key + different fingerprint | Treated as separate operation | `check_idempotency()` returns `None`; DB check does not find duplicate; new transaction created (if no DB conflict from concurrent insert). VERIFIED. | VERIFIED |
| Missing key (`key` is `None`/empty) | Not clearly specified | `check_idempotency()` line 44–45: returns `None`. `post_transaction()` proceeds to DB check (`line 80–86`). If DB allows (no duplicate): creates new transaction. VERIFIED. | VERIFIED |
| Concurrent same-key requests (stable key) | Not clearly specified | DB `IdempotencyKey` unique constraint (`models.py` line 205) prevents duplicate `key` insertion; one succeeds, other receives `IntegrityError`. `post_transaction()` `try/except IntegrityError` (`line 113–117`) converts to `HTTPException(409)`. Concurrent behavior at DB level SCHEMA-VERIFIED; exact concurrent sequence UNVERIFIED (no runtime execution). | SCHEMA-VERIFIED / UNVERIFIED (runtime) |
| Retry after ambiguous commit (transaction may exist; stable key) | Not clearly specified | Stable key (`msg_{message.id}` without retry change): `check_idempotency()` finds existing key → returns existing `transaction_id`. `post_transaction()` returns existing `tx` (`line 74–78`). Clean recovery. VERIFIED (design only; source supports this only if key is stable and unchanged). | VERIFIED (conditional on stable key) |
| Retry after ambiguous commit (unstable key: `retry_count` incremented) | Not clearly specified | Different key (`retry_count` changed): `check_idempotency()` returns `None`. `verify_and_post_from_ai()` checks `upload.id` first (`line 177–179`). If same upload: returns existing `tx` (clean). If different upload but same DB values: DB duplicate check (`line 194–202`) → `upload.status = DUPLICATE`; returns `None`. If called through `post_transaction()` directly: DB duplicate check (`line 80–86`) → raises `HTTPException(409)` (not caught by `verify_and_post_from_ai()` if propagated out). Note: no mechanism in source maps a raised `HTTPException(409)` back to the original `transaction_id` for message linkage (`message.transaction_id`). This is the critical gap. | VERIFIED (gap confirmed) |

## Corrected Contract Statement (Verified from Source)

The previous documentation claim that "Different key with same fingerprint raises 409" must be corrected to:
- It raises `409` ONLY when `post_transaction()` DB duplicate check (`line 80–86`) finds an existing transaction and the caller does not handle it.
- When `verify_and_post_from_ai()` is the caller and the same `upload.id` applies (`line 177–179`), it returns the existing transaction cleanly (no exception).
- When `verify_and_post_from_ai()` is the caller and the upload is different but DB values match (`line 194–202`), it returns `None` gracefully (sets `DUPLICATE` status) — not `409`.
- The exception behavior depends on the caller path, not solely on the key/fingerprint combination. The design contract (`11_FINANCIAL_GATEKEEPER.md`) does not fully distinguish these paths in its idempotency description.

## Impact on Phase 2 Readiness

This matrix correction confirms:
- The idempotency mechanism (`check_idempotency()` + DB `FOR UPDATE` + `IntegrityError` catch) provides at-least-once protection against duplicate transactions, not exactly-once execution.
- Stable retry requires either:
  a) A stable key format (without `retry_count` change) so that retries return existing results cleanly; OR
  b) A `message.transaction_id` pre-check in the adapter/work-flow (design exists, source not implemented) so that retries do not call `verify_and_post_from_ai()` when the message already has a posted transaction.
- Without resolution (Option A or B), retries with incremented `retry_count` will either raise (`post_transaction()` direct) or return `None` (`verify_and_post_from_ai()` with new upload) — neither establishes a clean `message.transaction_id` linkage for retries.
- Status: BLOCKED (resolution required in Phase 2; no source change made in Phase 1.1.1).

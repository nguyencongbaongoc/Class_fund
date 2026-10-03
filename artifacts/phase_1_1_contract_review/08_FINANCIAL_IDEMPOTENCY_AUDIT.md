# 08_FINANCIAL_IDEMPOTENCY_AUDIT.md

## Critical Issue: Idempotency Key Stability Across Retries
Status: BLOCKED — design conflict identified; source code not modified (as required by Phase 1.1 rules); documentation-level recommendation provided.

## Evidence Source (Actual Inspection)
- `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py`: `post_transaction()` lines 59–118; `_make_request_fingerprint()` lines 39–40; `check_idempotency()` lines 43–51; `save_idempotency()` lines 54–57.
- `verify_and_post_from_ai()` lines 172–241: calls `post_transaction()` with `idempotency_key=idempotency_key` (line 225); passes `idempotency_key` through to `post_transaction()`.
- `11_FINANCIAL_GATEKEEPER.md`: Documents proposed new format `msg_{message.id}_attempt_{retry_count}`.
- `08_LOCAL_WORKER.md`: References idempotency format for worker retry.
- `03_MESSAGE_CONTRACT.md`: Defines `message.id` (UUID) and `retry_count`.

## Existing Idempotency Mechanism (Verified Source)
Fingerprint (`_make_request_fingerprint` line 39–40):
```
sha256("|".join([
    account.id, type_.value, str(amount), currency, source.value,
    transaction_code or "", bank_account_id or "", upload_id or "",
]))
```
The fingerprint does NOT include:
- `message.id`
- `retry_count`
- Any reference to the chat message (only `upload.id` via `upload_id` parameter)

Idempotency check (`check_idempotency` line 43–51):
- Looks up `IdempotencyKey` by `key` (line 46: `.where(IdempotencyKey.key == key)`).
- If key found but fingerprint differs (`existing.request_fingerprint != fingerprint`) → raises `HTTPException(409)` (line 49–50).
- If key found and fingerprint matches → returns existing response (`existing.response_body`) (line 51).
- If key not found (`existing` is None) → returns `None`; `post_transaction()` proceeds.

Idempotency save (`save_idempotency` line 54–57):
- Stores `key`, `request_fingerprint`, `response_status`, `response_body` (containing `transaction_id`).

## Failure Scenario Analysis (Evidence-Based)
Scenario described in instruction (documented failure):
1. Worker claims message (`pending` → `processing`).
2. `verify_and_post_from_ai()` succeeds (`post_transaction()` creates `Transaction` and `LedgerEntry`; `idempotency_key` saved with new format).
3. Worker crashes before updating `message.status`.
4. Worker restarts (`reclaim_stale_leases()` resets `processing` to `pending` or `pending` if lease expired).
5. Worker retries message (`message.retry_count` incremented — either by restart logic or by claim logic).
6. Idempotency key format uses `retry_count`: new key string → `check_idempotency()` finds no existing key with this new `key` (line 46 returns None).
7. Fingerprint computed: same `upload_id`, `bank_account_id`, `transaction_code`, `amount`, etc. → fingerprint identical (line 39–40).
8. `post_transaction()` reaches line 74 (`existing_response = check_idempotency(...)`) → `None` (new key).
9. Line 80–86 (`duplicate` DB check): `existing = ... .with_for_update()` finds the previously created transaction (`bank_account_id` + `transaction_code` match) → raises `HTTPException(409, "Duplicate transaction code")`.
10. `verify_and_post_from_ai()` (line 220–241) catches `IntegrityError` (line 236–241): rolls back; updates `upload.status = DUPLICATE`; commits; returns `None`.
11. `message.status` would not be updated to `posted` (no `post_transaction()` success); message remains in retry or fails; `transaction_id` not set; `public_code` not linked to transaction.

Result: No duplicate financial transaction is created (DB unique constraint + `WITH FOR UPDATE` check prevents it); but the message processing fails (`409` from duplicate); worker retries may loop infinitely (if retry logic repeatedly tries the same message with incrementing `retry_count` and same `message.id`); financial posting is blocked correctly; message linkage (`message.transaction_id`) is not established; message remains unposted or enters `failed` after retries.

Conclusion: The proposed new idempotency format (`msg_{message.id}_attempt_{retry_count}`) introduces an unstable key for retries of the same logical message operation. The fingerprint remains stable, but the key changes; the DB `duplicate` check provides the final protection against duplicate transactions, but the retry loop may become unstable (infinite retry with `failed` status or unprocessed message) rather than cleanly returning the existing posted result. The existing `post_transaction()` mechanism relies on the `idempotency_key` to return the existing transaction quickly; with a changing key, the mechanism falls back to the slower `duplicate` check and raises `409`, which is less graceful for message retry.

## Recommendation (Documentation Only — No Source Change Authorized in Phase 1.1)
Documented in this audit (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`) and cross-referenced in `11_FINANCIAL_GATEKEEPER.md` and `08_LOCAL_WORKER.md`.
Recommended stable strategy (for Phase 2 resolution):
- Option A (preferred, requires `post_transaction()` modification — Phase 2): Include `message.id` (or `upload.id` when available) in the fingerprint (modify `_make_request_fingerprint` to include an optional `message_id`). Use a stable idempotency key format: `msg_{message.id}` (without `attempt` or `retry_count`). The fingerprint then includes the stable identifier, making both `key` and `fingerprint` consistent across retries; `check_idempotency()` returns the existing response cleanly; no `409` from duplicate DB check.
- Option B (no `post_transaction()` change; relies on DB constraint): Keep the new key format but document that retries will trigger the `duplicate` DB protection (`409`); the message must be handled by checking `message.transaction_id` before retry (if `message.transaction_id` is set, the message already has a posted transaction; do not retry). This requires the worker to check `message.transaction_id` (or `message.status = 'posted'`) before calling `verify_and_post_from_ai()` — this is a new check (design contract exists in `11` and `12` but source not implemented).
- Option C (immediate, documentation-level fix for Phase 1.1): Confirm in contract that the idempotency format must be stable; document Option A or Option B as the Phase 2 resolution; do not claim `msg_{message.id}_attempt_{retry_count}` as fully verified or implemented.

This audit confirms: the financial gatekeeper (`verify_and_post_from_ai()` + `post_transaction()` + DB unique constraints) remains authoritative and prevents duplicate transactions; the retry/idempotency contract requires resolution before Phase 2; no source modifications made.

Evidence references:
- `ledger.py` lines 39–51 (`fingerprint`, `check_idempotency`), 54–57 (`save_idempotency`), 59–118 (`post_transaction`), 121–169 (`post_revert`), 177–202 (`existing_tx` / `duplicate` checks), 172–241 (`verify_and_post_from_ai`).
- `08_LOCAL_WORKER.md` (`idempotency_key` reference).
- `03_MESSAGE_CONTRACT.md` (`message.id`, `retry_count`).
- `11_FINANCIAL_GATEKEEPER.md` (integration design; preserved gatekeeper contract).

# 07_WORKER_RELIABILITY_REVIEW.md

## Claiming Evidence (Design Only — No Source)
`08_LOCAL_WORKER.md`: `claim_next_message()` SQL contract (`UPDATE ... FOR UPDATE SKIP LOCKED`). `main.py`, `claim.py` not created.
`13_TEST_RESULTS.md`: `test_worker_claim` defined; `test_lease_recovery` defined; both labeled `DESIGNED / UNVERIFIED` (SQL syntax verified, execution not executed).
`02_SUPABASE_SCHEMA.md`: `messages` table includes `claimed_at`, `lease_expires_at`, `worker_id`, `retry_count`.
Actual SQL syntax verification: `UPDATE messages SET ... WHERE id = (SELECT id FROM messages WHERE status='pending' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *` — valid PostgreSQL syntax (verified by manual inspection against `postgresql` docs; no DB execution performed).

## Lease / Recovery Evidence
`08` design: `reclaim_stale_leases()` (`UPDATE ... SET status='pending' ... WHERE status='processing' AND lease_expires_at < now()`).
`13`: `test_lease_recovery` defined but unverified.
Evidence of execution: None (`.coverage` unchanged; no `pytest` result; no process started).

## Retry / Crash Evidence
`03` message contract: `retry_count` increment; `pending` reset for retry.
`08` design: `reset_to_pending()` with `retry_count`, `error_message`; delay (`2 ** retry_count * 60`, max 600s, jitter).
`13`: `test_duplicate_processing` references idempotency key; `test_recalled_before_post` and `test_recalled_after_post` defined; all unverified (design contracts).
`11` (`ledger.py` inspection): Existing retry mechanism not present in `post_transaction()` (only `max_retries` reference is in `VerificationPolicy` settings); retry logic is new contract, not preserved source.

## Critical Reliability Conflicts
1. **Claim execution unverified**: SQL design only; no `UPDATE ... FOR UPDATE SKIP LOCKED` executed against any DB. `BLOCKED / UNVERIFIED`.
2. **Lease expiration execution unverified**: `lease_expires_at` update/reclaim not executed. `BLOCKED / UNVERIFIED`.
3. **Idempotency stability (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`)**: Proposed new key format (`msg_{message.id}_attempt_{retry_count}`) changes with `retry_count`; second attempt (after crash + restart) uses different `retry_count` (if retry count was incremented before crash or after restart); fingerprint changes; existing `IdempotencyKey` table would treat it as new request (if same key reused but fingerprint changed → `IntegrityError` or `409` per `check_idempotency` line 49–50); if `retry_count` changes, either:
   - Key format uses same `message.id` but different `retry_count` → different `key` string → `check_idempotency` sees new key (not duplicate) → new `post_transaction()` call → potential duplicate transaction creation (if fingerprint also differs due to different `retry_count` in fingerprint? Fingerprint in `post_transaction()` uses `upload.id`, `bank_account_id`, `transaction_code`, `amount`, etc. — does NOT include `message.id` or `retry_count` directly). See `08` audit for full analysis.
4. **Crash recovery: retry count ambiguity**: If worker crashes after posting but before updating `message.status`, the restart claims the message again (`pending` or `processing` depending on lease state). If `retry_count` is incremented by the restart logic, the idempotency key format changes. The fingerprint in `post_transaction()` does NOT include `message.id` or `retry_count`, so the fingerprint remains the same; if the same `message.id` is reused but `retry_count` is different, the key string (`msg_{id}_attempt_{rc}`) is different. `check_idempotency` checks the `key` first (line 46: `select(IdempotencyKey).where(IdempotencyKey.key == key)`); if `key` changed, it finds nothing (`None`); then fingerprint is computed; fingerprint does not include `message.id` or `retry_count`; fingerprint is the same; `post_transaction()` then creates a new `Transaction` (new `tx.id`); `DB` `duplicate` check (`bank_account_id` + `transaction_code`) would catch it (line 82–86: `existing = ... .with_for_update()`); but `post_transaction()` would raise `409` before `IdempotencyKey` is saved; the new `Transaction` would NOT be saved (rollback occurs); but the `message.status` would not be updated correctly (no `post_transaction()` success → no `transaction_id` set; message remains unprocessed or retries infinitely). This is a reliability/design issue, not a duplicate financial transaction (DB unique constraint prevents it), but the retry loop may become unstable.
Evidence: `ledger.py` lines 39–57 (`fingerprint`, `check_idempotency`, `save_idempotency`); `08` design (`idempotency_key` format proposal); `11` (`verify_and_post_from_ai()` uses `idempotency_key` parameter).

## Resolution Recommendation (Documentation Only)
- Confirm stable idempotency format: either (a) include `message.id` in fingerprint (not currently done) so fingerprint is stable across retries; OR (b) use a fixed key that excludes `retry_count`; OR (c) rely on DB `duplicate` constraint (`bank_account_id` + `transaction_code`) as final protection (already exists) and treat `IdempotencyKey` as auxiliary (but then `retry_count` changes could cause `409` from same-key-different-fingerprint scenario if `retry_count` is included in fingerprint — currently not included). Recommendation (documented): remove `attempt_{retry_count}` from the proposed format; use a stable key based only on `message.id` (e.g., `msg_{message.id}`) or include `message.id` in the fingerprint (modify `post_transaction()` fingerprint — but this requires source change, which is blocked for Phase 1.1). Therefore, for Phase 1.1 documentation, recommend that the idempotency format uses a stable `message.id`-based key without `retry_count`; note the current design conflict in `08_FINANCIAL_IDEMPOTENCY_AUDIT.md`.

# 05_FINANCIAL_INVARIANT_ASSESSMENT.md

## Existing Financial Authority (Preserved)

Functions preserved (unchanged in source; verified by `read` of `ledger.py` and `git status` confirming zero tracked source modifications):
- `post_transaction()` (`ledger.py` line 59–118)
- `post_revert()` (`ledger.py` line 121–169)
- `verify_and_post_from_ai()` (`ledger.py` line 172–242)
- `calculate_balance()` (`ledger.py` line 19–36)

No function modified during Phase 1.1.1 (verified by `git status` before and after this phase: zero tracked file changes in source; only new artifact files created).

## Financial Guarantees — Evidence-Based Assessment

### 1. No duplicate financial posting
- DB-level: `UniqueConstraint("bank_account_id", "transaction_code", name="uq_bank_transaction_code")` (`models.py` line 179–181). Verified: SCHEMA-VERIFIED.
- DB-level enforcement: confirmed by `post_transaction()` DB duplicate check (`line 80–86`) and `verify_and_post_from_ai()` DB duplicate check (`line 194–202`), plus `IntegrityError` catch (`line 113–117`, `line 236–242`). Verified: IMPLEMENTED.
- Concurrent duplicate prevention: relies on DB unique constraint + `FOR UPDATE` + `IntegrityError` catch. Concurrent behavior SCHEMA-VERIFIED; runtime concurrent execution UNVERIFIED.
- Idempotency-level: `IdempotencyKey` unique key (`models.py` line 205) provides application-level duplicate prevention for the same `idempotency_key`. If key is stable: clean return. If key unstable (`retry_count` change): falls back to DB-level protection. This is a weaker guarantee than exactly-once execution; it is at-least-once processing with idempotent effects (same DB values prevented, but retry path may not return the original transaction cleanly).
- Status: VERIFIED (DB-level); UNVERIFIED (runtime concurrent); BLOCKED (idempotency stability requires Phase 2 resolution for exactly-once retry behavior).

### 2. No unauthorized posting
- `post_transaction()` requires `source`, `transaction_code`, `bank_account_id` validation (`line 67–68`) for AI-posted transactions (`LEDGER_SOURCE.IMAGE`). Verified: IMPLEMENTED.
- `verify_and_post_from_ai()` validates `upload.id` (`line 177`), `upload.status` (`line 180`), confidence (`line 183`), transaction data (`line 188`), campaign/member (`line 204–218`) before calling `post_transaction()`. Verified: IMPLEMENTED.
- `post_transaction()` accepts `actor_id` for audit (`line 102–109`) but does not enforce authorization roles in `post_transaction()` itself; authorization is handled by `post_revert()` (`line 121`: requires `actor_id`; design indicates `OWNER_TREASURER`). Source-level authorization for posting through `verify_and_post_from_ai()` relies on the adapter/work-flow passing a valid `actor_id` (design proposes `actor_id` from session/auth). The authorization mechanism is designed but not fully verified at adapter level. Status: IMPLEMENTED (existing gatekeeper preserved); DESIGNED (message-level authorization endpoint missing); BLOCKED (full authorization mechanism for recall not implemented).

### 3. Stable transaction identity
- Each `post_transaction()` creates a new `Transaction` row with `uuid4_str()` default (`models.py` line 165). Once created, `tx.id` is immutable. Verified: IMPLEMENTED.
- `post_revert()` creates a new `REVERT` transaction (`line 140`) linking to original via `original.id` (not modifying original ID). Verified: IMPLEMENTED.
- Transaction identity is stable; no mutation of `tx.id` possible in source.

### 4. Stable idempotency identity
- `IdempotencyKey` uses `key` (string, unique, `models.py` line 205) as stable identifier. If `key` unchanged: identity stable. If `key` changes (`retry_count` change in proposed format): identity changes. Status: BLOCKED (unstable format; requires Phase 2 resolution).
- `fingerprint` (`_make_request_fingerprint`) is stable for the same transaction parameters (same `upload.id`, `bank_account_id`, `transaction_code`, etc.). Verified: VERIFIED.
- The combination (`key` + `fingerprint`) is only stable when both are stable. With proposed unstable `key`, identity is not stable.

### 5. Exactly-once financial effect vs weaker guarantee
- CLAIMED: The design contracts (`11_FINANCIAL_GATEKEEPER.md`, `08_FINANCIAL_IDEMPOTENCY_AUDIT.md`) imply exactly-once posting through idempotency.
- ACTUAL: The mechanism provides:
  a) At-least-once processing (message may be retried multiple times by worker).
  b) Idempotent effects when `key` is stable (same key → same transaction returned; no new DB row).
  c) At-most-once DB-level protection when `key` is unstable (DB `uq_bank_transaction_code` prevents duplicate DB rows; but retry does not cleanly return the original transaction).
- EXACTLY-ONCE CLAIM: UNVERIFIED / BLOCKED. Source (`ledger.py`) does not provide a mechanism that guarantees exactly one execution of the posting path with exactly one result returned to the caller across retries when the idempotency key changes. The design proposes `message.transaction_id` pre-check but it is not implemented.
- Status: BLOCKED (idempotency stability must be resolved for exactly-once claim to be verified).

### 6. Ledger immutability
- `Transaction` rows are never modified (except `original.status = LedgerStatus.REVERTED` in `post_revert()` at line 156 — this updates the original's status, not deleting or altering the original entry). Verified: IMPLEMENTED.
- `LedgerEntry` is never modified after creation (`post_transaction()` creates new entry; `post_revert()` creates new `REVERT` entry with `original_entry_id` reference). Verified: IMPLEMENTED.
- `AuditLog` records `before`/`after` (`line 102–109`, `line 157–161`) for traceability. Verified: IMPLEMENTED.

### 7. Balance consistency
- `calculate_balance()` (`line 19–36`) derives balance from `LedgerEntry` rows (not mutable state). It applies `CREDIT` (+), `DEBIT` (-), `REVERT` (with note-based reversal direction: `REVERSAL_OF:CREDIT` subtracts; `REVERSAL_OF:DEBIT` adds). Verified: IMPLEMENTED.
- `post_revert()` creates `REVERT` transaction and `REVERT` ledger entry (`line 140–155`). The original `Transaction` status is updated to `REVERTED` (`line 156`). The balance effect of `post_revert()` is consistent with the original entry type (`CREDIT` reversal subtracts; `DEBIT` reversal adds). Verified: IMPLEMENTED.
- No direct mutation of balance variable exists (only derived calculation). Verified: IMPLEMENTED.

### 8. Reversal integrity
- `post_revert()` (`line 121–169`):
  - Locks original `Transaction` and `LedgerEntry` (`line 130–131`).
  - Prevents revert of a `REVERT` (`line 132`).
  - Prevents double-revert (`line 134–138`).
  - Creates new `REVERT` transaction (`line 140`).
  - Creates `REVERT` ledger entry with `original_entry_id` (`line 148–154`).
  - Updates original status (`line 156`).
  - Saves idempotency (`line 162–163`) with fingerprint `revert` + `original.id` + `reason` (`line 123`).
- Fingerprint stability for revert: independent of message retry count (`original.id` + `reason` only). Stable per call with same `reason`; different `reason` creates new fingerprint (by design; appropriate). Verified: IMPLEMENTED.
- Double-revert protection verified by source (`line 134–138`) and existing test (`test_revert_restores_balance_without_deleting_original` at `tests/test_financial_core.py` line 41–55). Status: IMPLEMENTED / TESTED (existing test evidence from Phase 1.1; not executed in this session).

### 9. Retry safety
- Retry safety depends on idempotency stability (`key` format) + worker handling of returned values / exceptions.
- Source (`ledger.py`): provides idempotency mechanism (`check_idempotency()` + `post_transaction()`); provides graceful `None` for duplicate DB check in `verify_and_post_from_ai()` (`line 199–202`); raises `HTTPException` for duplicate DB check in `post_transaction()` (`line 86`).
- Adapter/work-flow behavior (how retries handle `None`, `HTTPException(409)`, or returned `tx`) is not in `ledger.py` source; design contracts (`08_LOCAL_WORKER.md`, `11_FINANCIAL_GATEKEEPER.md`) propose behavior but are not verified by source execution.
- Status: IMPLEMENTED (mechanism preserved); DESIGNED (retry behavior design); BLOCKED (actual retry loop behavior depends on adapter/work-flow; not verified).

### 10. Concurrent worker safety
- `FOR UPDATE` locks (`line 81–84`, `line 130–131`) prevent concurrent modification of existing rows.
- DB unique constraints (`uq_bank_transaction_code`, `IdempotencyKey.key`) prevent concurrent duplicate commits.
- `post_transaction()` `try/except IntegrityError` and `verify_and_post_from_ai()` `try/except IntegrityError` handle concurrent-insert conflicts gracefully (raise or return `None`).
- Concurrent behavior of the full flow (message claim → AI processing → posting → message status update) is not verified at runtime (would require concurrent worker execution). Status: SCHEMA-VERIFIED; UNVERIFIED (runtime concurrent flow).

## Summary Status for Phase 2

- Financial gatekeeper (`verify_and_post_from_ai()`) preserved: VERIFIED.
- No duplicate DB-level transaction: VERIFIED (DB-level); BLOCKED (exact retry behavior unverified).
- Stable transaction identity: VERIFIED.
- Stable idempotency identity: BLOCKED (unstable key format).
- Ledger immutability / balance consistency / reversal integrity: VERIFIED / IMPLEMENTED.
- Exactly-once execution claim: NOT VERIFIED — must not be claimed; weaker guarantee (`at-least-once` + DB-level `at-most-once` protection) is the actual evidence-supported claim.
- Recall/reversal authorization mechanism: DESIGNED (token/hash); BLOCKED (authorization endpoint missing — see `06_RECALL_AND_REVERSAL_CONSISTENCY.md`).

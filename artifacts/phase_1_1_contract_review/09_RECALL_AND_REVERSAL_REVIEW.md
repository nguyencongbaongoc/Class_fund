# 09_RECALL_AND_REVERSAL_REVIEW.md

## Recall / Reversal Contracts (Evidence)
Actual source inspected (`ledger.py` lines 121–169, `post_revert`):
- Original preserved (`Transaction` unchanged; `original.status = LedgerStatus.REVERTED` updated).
- `Reversal` (`REVERT`) `Transaction` created with `type=REVERT`, `transaction_code=f"REV-{original.id}"`, `source=REVERT`, `status=VERIFIED`.
- `Reversal` `LedgerEntry` (`REVERT` type) links to `tx.id`; `original_entry_id` links to original `LedgerEntry.id`.
- Double-revert prevented (`already` check: `original_entry_id == original_entry.id` + `type == REVERT` → `409`).
- Idempotency for revert: fingerprint includes `original.id` + `reason` (line 123); same format applies (same stability concern as `post_transaction`; `retry_count` not included in revert fingerprint — revert fingerprint is independent; stable per call since it uses `original.id` and `reason`, not message retry count).

## Message-Level Recall Contracts (`03`, `12`)
- `recalled` state: terminal; original preserved.
- Before post: `message.status = 'recalled'` check designed (`11` / `12`); source not implemented.
- After post: `post_revert()` created (`11` / `12`); message status updated to `recalled` (design only).
- Recall authorization: `public_code` excluded (`03`); private token (`recall_token_hash`) proposed (`12`); token generation / authorization endpoint not implemented (`BLOCKED`).
- Double-recall prevention: `post_revert()` DB check (`already`) protects at transaction level; `message.status = 'recalled'` protects at message level (design only; no source enforcement for message-level check).

## Contradictions / Gaps (Evidence-Based)
- Phase 0 (`19` audit): Zero authorization mechanism exists (critical finding). Phase 1 (`12`) proposes token strategy; token mechanism remains `DESIGNED` only; authorization endpoint unimplemented.
- Message-level `recalled` state transition requires new source code (`message.status` check before posting; `message.status` update after reversal). Not implemented.
- `public_code` must never authorize recall (design confirms); without implemented token authorization, the authorization mechanism is missing entirely — the design contract is incomplete, not incorrect.
- Financial reversal (`post_revert`) is fully preserved and authoritative; no conflicts with recall design except the missing message-level authorization endpoint.

## Resolution (Documentation — No Source Change)
- Confirm in `12` that authorization endpoint is a required Phase 2 dependency (not Phase 1).
- Confirm in `11` that `message.status` check must be added to `verify_and_post_from_ai()` or worker before calling gatekeeper (contract exists; execution blocked until source modification allowed in Phase 2).
- Confirm in `08` audit that `idempotency_key` format stability requires resolution before retry loops are stable.

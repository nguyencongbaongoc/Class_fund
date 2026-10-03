# 06_RECALL_AND_REVERSAL_CONSISTENCY.md

## Scope
Consistency review of recall/reversal behavior against actual `ledger.py` source (`post_revert()`, `post_transaction()`, `verify_and_post_from_ai()`) and design contracts (`09_RECALL_AND_REVERSAL_REVIEW.md`, `12_RECALL_SAFETY.md`, `03_MESSAGE_CONTRACT.md`, `11_FINANCIAL_GATEKEEPER.md`). Not an implementation phase; no authorization endpoint or message-level recall source implemented.

## Recall Authorization — Source Evidence

### Source (`ledger.py`)
- `post_revert()` (`line 121`) requires `actor_id: str`; no token/hash validation in source.
- `post_transaction()` (`line 63`) accepts `actor_id` as audit parameter (`audit_actor_id`); does not enforce authorization role at posting time (authority comes from adapter/work-flow passing a valid `actor_id`).
- `verify_and_post_from_ai()` (`line 172`) accepts `actor_id: str | None`; does not enforce authorization role.
- No authorization endpoint implementation exists in `ledger.py` or adapter source inspected (adapter source not present in this session; design contracts confirm missing implementation).

### Design (`09_RECALL_AND_REVERSAL_REVIEW.md`, `12_RECALL_SAFETY.md`)
- Design proposes private token (`recall_token_hash`) stored at message insert; authorization endpoint validates hash before allowing recall.
- `public_code` is explicitly excluded from authorization (`03_MESSAGE_CONTRACT.md`, `05_AUTH_RLS_SECURITY_REVIEW.md`). Verified from design contracts.
- Token generation logic is not implemented (`models.py` has `recall_token_hash` design reference; no source creates it in `post_transaction()` or `verify_and_post_from_ai()`).

Status: DESIGNED (token/hash mechanism); BLOCKED (authorization endpoint not implemented; `public_code` authorization correctly excluded by design).

## Recall Before Posting — Source Evidence

### Source (`verify_and_post_from_ai()` line 172–202)
- Checks `upload.status` (`line 180`): if `REJECTED` or `DUPLICATE` → return `None` (line 181–182).
- Checks `upload.id` (`line 177`): if existing transaction exists for upload → return existing transaction (line 178–179).
- Does NOT check `message.status = 'recalled'`. There is no `message.id` parameter passed to `verify_and_post_from_ai()` (`line 172`: parameters are `db`, `upload`, `result`, `account`, `actor_id`, `idempotency_key` — no `message.id`).

### Design (`11_FINANCIAL_GATEKEEPER.md`, `12_RECALL_SAFETY.md`)
- Design proposes passing `message.id` to `verify_and_post_from_ai()` and checking `message.status = 'recalled'` before posting.
- This is a new source change (not implemented in `ledger.py`); blocked for Phase 1.1; required Phase 2 prerequisite.

Status: DESIGNED (design contract defines it); BLOCKED (source not implemented; no `message.id` parameter or `message.status` check in `verify_and_post_from_ai()`).

## Recall After Posting — Source Evidence

### Source (`post_revert()` line 121–169)
- Creates new `Transaction` (`type=REVERT`, `source=REVERT`, `status=VERIFIED`) linking to original (`original.id`, `original.account_id`, `original.bank_account_id`).
- Creates `LedgerEntry` (`type=REVERT`, `original_entry_id=original_entry.id`).
- Updates `original.status = REVERTED` (line 156) — original preserved (not deleted); status updated.
- Prevents double-revert (`line 132`: `original.type == REVERT`; `line 134–138`: checks `original_entry_id` + `REVERT` type; raises `HTTPException(409)`).
- Fingerprint (`line 123`): `revert` + `original.id` + `reason`. Stable per same `original.id` and `reason`; different `reason` creates different fingerprint (appropriate for revert: different reason = different reversal request).
- Idempotency (`line 124`, `line 162–163`): same-key/same-fingerprint returns existing reversal (`line 124–128`); same-key/different-fingerprint raises `HTTPException(409)` (line 124: `check_idempotency()` behavior preserved).

Status: IMPLEMENTED (source unchanged; fully preserved). TESTED (existing `test_revert_restores_balance_without_deleting_original` covers basic revert; not executed in this session; evidence from Phase 1.1).

## Original Transaction Preservation — Source Evidence

### Source (`post_revert()` line 121–169)
- Original `Transaction` row preserved (not deleted); `original.status` updated from `VERIFIED` to `REVERTED` (`line 156`).
- `AuditLog` records `before` (`VERIFIED`) and `after` (`REVERTED` + `reversal_transaction_id`) (`line 157–161`).
- `post_transaction()` never deletes transactions; `post_revert()` never deletes originals. Verified from source.

Status: VERIFIED / IMPLEMENTED.

## Repeated Recall — Source Evidence

### Source (`post_revert()` line 132, 134–138)
- First recall: creates `REVERT`; saves idempotency with fingerprint.
- Second recall with same `original.id` and same `reason`: `check_idempotency()` finds existing key with same fingerprint → returns existing reversal transaction (`line 124–128`). Clean return; no second reversal created.
- Second recall with same `original.id` but different `reason`: `check_idempotency()` raises `HTTPException(409)` (`line 124`: fingerprint mismatch). `post_revert()` does not create a second reversal. The exception propagates; adapter/work-flow must handle it (no source-level graceful `None` for this case — different from `verify_and_post_from_ai()` graceful `None` for DB duplicates). Note: design (`12_RECALL_SAFETY.md`) proposes `message.status = 'recalled'` provides a second layer; source layer only provides DB-level `already` check.

Status: IMPLEMENTED (DB-level double-revert protection verified); DESIGNED (message-level `recalled` state transition not implemented); BLOCKED (authorization endpoint missing prevents full recall flow).

## Cross-Check — Consistency Between Artifacts

Reconciliation performed against:
- `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` (Phase 1.1): confirms `post_revert()` fingerprint independent of retry count; confirms `post_transaction()` fingerprint excludes `message.id`.
- `09_RECALL_AND_REVERSAL_REVIEW.md` (Phase 1.1): confirms authorization mechanism missing; confirms `message.status` check unimplemented; confirms `post_revert()` preserves original.
- `05_AUTH_RLS_SECURITY_REVIEW.md` (Phase 1.1): confirms `public_code` excluded; authorization endpoint unverified.
- `03_MESSAGE_CONTRACT.md`: defines `recalled` terminal state.
- `11_FINANCIAL_GATEKEEPER.md`: proposes `message.id` linkage and `message.status` check.

No contradictions found between these artifacts and actual `ledger.py` source. All design gaps (authorization endpoint, `message.status` check, `message.transaction_id` linkage) are confirmed missing in source. This artifact records the corrected consistency assessment without altering previous evidence.

## Phase 2 Blockers Confirmed by This Audit

- Recall authorization endpoint: BLOCKED (design only; source not implemented).
- `message.status` check before `verify_and_post_from_ai()`: BLOCKED (design only; no source implementation in `ledger.py` or adapter).
- `message.transaction_id` linkage: BLOCKED (design proposes; no DB records with `transaction_id` set verified; adapter/work-flow not verified).
- Stable idempotency format: BLOCKED (design proposes unstable format; source mechanism preserved but design conflict remains).
- No new source changes made; existing `post_revert()` and `post_transaction()` unchanged.

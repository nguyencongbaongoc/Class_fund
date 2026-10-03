# 12_RECALL_SAFETY.md

## Phase 1 Recall Safety Foundation

### Source Evidence (Phase 0)
- 19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md: No secure recall mechanism currently exists; `revertTransaction` in mock has zero authorization; message ID timestamp-based; no recall token; no ownership check; no recall status tracking.
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: Recall mechanism design — `RECALL` creates compensating reversal; original preserved; second recall rejected.
- 18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md: Recall after Qwen processing requires `message_id` linkage; before posting requires state re-check; double-recall prevented by `post_revert()`.
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md: Unauthorized withdrawal risk; recall authorization must use token strategy (not public message_id only); never expose private recall credentials.

### Recall States (Message Lifecycle Integration)
```
PENDING → PROCESSING → POSTED → RECALLED (compensating reversal created)
     ↓                ↓          ↓
     FAILED     AWAITING_ADMIN  (original preserved; status changed to RECALLED)
```
- `RECALLED` is a terminal message state; original message preserved (not deleted).
- Evidence: 13 (message lifecycle includes `recalled`), 19 (status model gap identified), 12 (`messages.status` design).

### Secure Recall Mechanism (Concept — Token Strategy)
- Per-message private recall token generated at message creation (server-side cryptographically secure random; 32 bytes).
- Token stored as hash (`recall_token_hash = SHA-256(token)`) in `messages` table; original token returned to sender only (in message creation response, stored in session/local storage temporarily, not in database as plaintext).
- Recall endpoint (future phase): requires `message.id` + `token` (matched against hash); verifies sender ownership (token match); verifies message state (`status != 'recalled'` already prevented by business logic).
- Evidence: 19 (recall token recommendation: private token per message, hash in DB, token returned only to sender), 16 (security: authorization enforced server-side).

### Recall Before Processing
```python
# Before calling verify_and_post_from_ai()
with Session(db_engine) as db:
    msg = db.execute(select(Messages).where(Messages.id == msg_id).with_for_update())
    if msg.status == 'recalled':
        abort();  # Do not post; no financial impact
```
- Evidence: 19 (race condition protection needed), 23 (before posting re-check), 13 (atomic claim with lease).

### Recall After Posting
- After posting: message `status` remains `recalled`; `transaction_id` preserved.
- `post_revert()` creates new transaction/ledger entry of type `REVERT`; links via `original_entry_id`.
- Original `ledger_entries` entry remains unchanged (immutable); balance corrected by new `REVERT` entry.
- Evidence: 22 (reversal contract: original preserved, audit complete), 11 (compensating reversal, not delete), 04 (reversal logic verified).

### Double-Recall Prevention
- Message `status` checked: if already `recalled`, any second recall attempt rejected.
- `post_revert()` checks existing `original_entry_id` + `REVERT` type: if exists, raises `409` (already reverted).
- Evidence: 11 (existing `post_revert` already prevents double-revert), 16 (security checklist: double-recall prevention required), 22 (reversal contract verified).

### Safety Rules (Phase 1 Confirmed)
- Never delete original `messages`, `transactions`, or `ledger_entries`.
- Recall authorization always server-side (token hash check); frontend display of recall button does NOT grant authorization.
- `public_code` (`CF-...`) is public for identification only; never used as authorization factor.
- Evidence: 16 (security checklist: never use message_id as only authorization), 19 (public code NOT authorization credential), 23 (recall authorization design).

# 11_FINANCIAL_GATEKEEPER.md

## Phase 1 Financial Gatekeeper Contract

### Source Evidence (Phase 0)
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: `verify_and_post_from_ai()` is the critical security gate; must be preserved and reused; extracts verification logic from `VerificationService.verify()`.
- 04_DATABASE_AND_FINANCIAL_INTEGRITY.md: `post_transaction()`, `post_revert()`, `calculate_balance()` verified safe; `IdempotencyKey` table exists; `AuditLog` comprehensive.
- 22_FINANCIAL_GATEKEEPER.md (implied by mission): Target flow: Qwen → Extraction → Verification → Existing ledger gatekeeper → Ledger. Exactly one authoritative posting path.
- 17_HYBRID_INTEGRATION_GAP_ANALYSIS.md: Only missing piece is connection layer; core financial logic sound.

### Existing Gatekeeper (Preserved — No Rewrite)
- `app/services/ledger.py`: `verify_and_post_from_ai()` (line reference preserved in evidence; exact file/line verified in code inspection during audit).
- `post_revert()`: Requires `OWNER_TREASURER` role; prevents double-revert with `original_entry_id` check; creates `REVERT` transaction + ledger entry; preserves original.
- `post_transaction()`: Idempotency key fingerprint; unique constraint `(bank_account_id, transaction_code)`; audit log.
- `calculate_balance()`: Derived from immutable `ledger_entries` (not mutable state).
- Evidence: 11 (reusable components list: 100% reuse), 04 (locking verified with `SELECT ... FOR UPDATE`).

### Integration Contract (Phase 1 — Adapter Only)
```
Worker claims message (pending → processing)
  ↓
Download receipt (if RECEIPT)
  ↓
AI adapter → structured VerificationResult (via ollama_client + existing services)
  ↓
Worker calls verify_and_post_from_ai(
         db,
         upload=upload,
         extraction=extraction_result,
         account=account,
         actor_id=worker_id,
         idempotency_key=f"msg_{message.id}_attempt_{message.retry_count}",
         message_id=message.id  # new linkage for hybrid
     )
  ↓
Result: posted=True/False
         transaction_id=uuid (if posted)
         status='VERIFIED'/'NEEDS_REVIEW'/'REJECTED'
  ↓
Worker updates message status:
         if posted: 'posted', transaction_id=tx.id
         if needs_review: 'awaiting_admin', ai_result=...
         if rejected/failed: 'failed', retry_count++, error_message=...
```
- Evidence: 11 (integration architecture), 13 (message lifecycle), 19 (guest message → transaction linkage), 20 (AI output contract).

### Idempotency Protection
- `idempotency_key` format: `msg_{message.id}_attempt_{message.retry_count}`.
- Database table `idempotency_keys` (existing; verified in `models.py`) stores fingerprint + response body.
- If same message processed again (e.g., worker restart after crash but before DB commit), `check_idempotency()` returns existing response; no second transaction created.
- Evidence: 11 (idempotency key format recommendation), 12 (`IdempotencyKey` table verified), 04 (financial integrity audit).

### Recall Before Posting
- Before calling `verify_and_post_from_ai()`: `SELECT status FROM messages WHERE id = $1 FOR UPDATE`.
- If `status = 'recalled'`: abort; do not call gatekeeper; message remains `recalled`; worker stops processing this message.
- Evidence: 23 (recall safety design), 19 (recall before processing requirement), 11 (message state machine).

### Recall After Posting
- Recall endpoint (future phase) calls `post_revert()` with original transaction.
- Creates new `REVERT` ledger entry (`original_entry_id` links to original); does NOT delete original `transaction` or `ledger_entries`.
- `post_revert()` prevents second reversal (checks existing `original_entry_id` + `REVERT` type).
- Message status updated to `recalled` (not deleted); `transaction_id` preserved.
- Evidence: 22 (reversal contract), 23 (compensating transaction), 04 (reversal logic verified).

### Security Rules (Phase 1 Confirmed)
- Only `OWNER_TREASURER` can trigger `post_revert()` (existing backend enforcement preserved).
- `verify_and_post_from_ai()` validates all inputs before posting; AI output never bypasses validation.
- No second balance calculation; `calculate_balance()` derived from `ledger_entries` remains authoritative.
- Audit log (`audit_logs`) records `LEDGER_POST`, `LEDGER_REVERT`, `MESSAGE_PROCESSED` actions.
- Evidence: 16 (security audit), 22 (gatekeeper contract), 04 (audit log verified).

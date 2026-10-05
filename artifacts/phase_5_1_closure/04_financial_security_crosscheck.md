# Phase 5.1 — Financial Security Invariants Cross-Check

## Findings Summary

**Verdict: All 12 invariants verified intact at source level.** Phase 5 integration does not weaken any financial or security invariant. Backend authorization remains authoritative; frontend is UX-only.

---

## Invariant-by-Invariant Verification

### 1. Ledger Remains Authoritative Financial Source
**Status: ✅ VERIFIED**

**Evidence:**
- AdminDashboardView fetches balance from `adminApi.getStats()` → `/admin/stats` → `calculate_balance()` (ledger.py)
- AdminLedgerView uses `/admin/audit-logs?entity_type=TRANSACTION` → `AuditLog` records of financial actions
- No frontend calculation of balances — all derived from backend authoritative endpoints
- Backend `calculate_balance()` in `services/ledger.py` is single source of truth

### 2. No Fabricated Financial Metrics Displayed
**Status: ✅ VERIFIED**

**Evidence:**
- All dashboard stats come from `/admin/stats` endpoint which queries real DB tables
- AI review queue from `/internal/review` (real extraction records)
- Worker status from `/admin/workers` (real `WorkerStatus` table)
- System health from `/admin/health` (live component checks)
- Queue status from `/admin/queue-status` (real `Message` table counts)
- No mock data in admin views (unlike legacy DashboardView which uses mockDatabase.ts)

### 3. AI Approval Uses Existing Gatekeeper
**Status: ✅ VERIFIED**

**Evidence:**
- Frontend: `adminApi.approveExtraction()` calls `POST /internal/review/{id}/approve`
- Backend: `review.py:179-270` `approve_extraction()` calls `verify_and_post_from_ai()`
- Same function used by worker pipeline (`worker/main.py:181-187`)
- Confidence threshold enforced (0.9 default) — low confidence returns `NEEDS_HUMAN_REVIEW`
- Duplicate detection via `uq_bank_transaction_code` constraint
- Idempotency key generated from message_id + content hash

### 4. Frontend Cannot Independently Post Financial Transactions
**Status: ✅ VERIFIED**

**Evidence:**
- No `POST /fund/credit`, `POST /fund/debit`, `POST /fund/transactions/{id}/revert` calls in frontend
- AdminLedgerView "Nạp thủ công" button only shows toast "Coming soon" (line 95)
- All financial mutations require backend endpoints with `require_roles(Role.OWNER_TREASURER)`
- AI approval is the only path to posting, and it goes through `verify_and_post_from_ai()`

### 5. Idempotency Remains Intact
**Status: ✅ VERIFIED**

**Evidence:**
- All 8 existing idempotency tests pass (`test_idempotency.py`)
- New admin endpoints are read-only — no new idempotency keys needed
- AI review approve/reject use existing review endpoints with existing idempotency logic
- `verify_and_post_from_ai()` maintains idempotency via `message_id` + content hash key
- Worker pipeline unchanged

### 6. Recall-Before-Post Behavior Preserved
**Status: ✅ VERIFIED**

**Evidence:**
- `test_recall_before_post` passes
- Worker checks `message.status == MessageStatus.RECALLED.value` before processing (`worker/main.py:143-148`)
- Recall API marks message `RECALLED` and sets `RecallToken.used_at`
- No transaction created if recalled before processing

### 7. Recall-After-Post Uses Compensating REVERT
**Status: ✅ VERIFIED**

**Evidence:**
- `test_recall_after_post_creates_reversal` passes
- `post_revert()` creates `REVERT` type transaction
- Original transaction marked `status=REVERTED`
- Balance restored to pre-transaction state
- `original_entry_id` links revert to original in `LedgerEntry`

### 8. Original Records Preserved
**Status: ✅ VERIFIED**

**Evidence:**
- `test_revert_restores_balance_without_deleting_original` passes
- Transaction count remains 2 (original + revert) after revert
- Original transaction stays in DB with `LedgerStatus.REVERTED`
- `LedgerEntry` has `original_entry_id` foreign key to original
- Audit log captures both actions

### 9. Double Reversal Impossible
**Status: ✅ VERIFIED**

**Evidence:**
- `test_double_recall_prevented` passes
- `RecallToken.used_at` prevents replay
- Transaction `status=REVERTED` prevents second `post_revert()`
- `LedgerEntry.original_entry_id` chain prevents circular reverts
- Database constraint `uq_bank_transaction_code` prevents duplicate bank tx codes

### 10. Backend Authorization Remains Authoritative
**Status: ✅ VERIFIED**

**Evidence:**
- All `/admin/*` routes: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)`
- Financial mutations: `require_roles(Role.OWNER_TREASURER)` only
- AI review: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)`
- Worker internal: `require_ai_service` (service-to-service)
- JWT validation + revoked token check on every request (`deps.py:16-28`)
- Frontend checks (`currentUser.role === 'TREASURER'`) are UX only — backend enforces

### 11. Service-Role Credentials Not Exposed in Frontend
**Status: ✅ VERIFIED**

**Evidence:**
- Frontend uses JWT access tokens from `localStorage` (user's own token)
- `adminApi.ts` only sends `Authorization: Bearer <user_token>`
- No service-role keys, database URLs, Ollama credentials in frontend source
- Supabase client only used in backend (`services/supabase_client.py`)
- AI/Ollama client only used in backend (`services/ollama_client.py`, `worker/main.py`)

### 12. Phase 3.1/4.1 Contracts Not Broken
**Status: ✅ VERIFIED**

**Evidence:**
- All existing tests pass (24/24 including 4 new admin tests)
- `/fund/*` endpoints unchanged
- `/internal/review/*` endpoints unchanged
- `/internal/ai/*` endpoints unchanged
- `/auth/*` endpoints unchanged
- `/public/*` endpoints unchanged
- Database schema: only additive migration `0005` (pre-existing)
- Worker pipeline logic unchanged
- Financial core logic unchanged

---

## Integration Points Reviewed

### Phase 5 ↔ Phase 3.1 (AI Pipeline)
- Review API reused exactly as-is
- Gatekeeper `verify_and_post_from_ai()` reused
- No changes to extraction, duplicate detection, OCR

### Phase 5 ↔ Phase 4 (Guest Chat)
- No integration points — admin views are separate
- Chat views unchanged

### Phase 5 ↔ Phase 2 (Financial Core)
- Ledger, balance calculation, transactions reused
- Idempotency, revert logic reused
- No modifications to `services/ledger.py`

### Phase 5 ↔ Phase 1 (Contracts)
- All contracts honored
- New admin contracts additive only

---

## Conclusion

All 12 financial security invariants are **verified intact** at source level. Phase 5 adds read-only administrative views and monitoring endpoints without modifying any financial mutation paths, authorization logic, or data integrity mechanisms.

The only caveat is the `TREASURER` vs `OWNER_TREASURER` role naming mismatch (documented in Check A), which is a frontend/backend integration issue for live auth, not a source-level invariant violation.
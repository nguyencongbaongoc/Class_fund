# Phase 5 — Financial Security Invariants Verification

## Non-Negotiable Invariants (All Verified Intact)

### 1. Ledger Remains Authoritative Financial Source
- **Status:** ✅ VERIFIED
- **Evidence:** All admin views fetch balance/transactions from `/fund/balance` and `/fund/transactions` (or `/admin/audit-logs` with entity_type=TRANSACTION). No frontend calculation of balances.
- **Backend:** `calculate_balance()` in `services/ledger.py` is the single source of truth.

### 2. AI Extraction Cannot Independently Post Transactions
- **Status:** ✅ VERIFIED
- **Evidence:** 
  - Review API (`/internal/review`) only allows listing/detail/approve/reject
  - Approval endpoint calls `verify_and_post_from_ai()` which enforces confidence threshold
  - Low confidence (<0.9) returns `NEEDS_HUMAN_REVIEW`, no transaction created
  - Test: `test_ai_low_confidence_does_not_post` passes

### 3. AI Approval Must Use Existing Gatekeeper
- **Status:** ✅ VERIFIED
- **Evidence:** 
  - `POST /internal/review/{id}/approve` calls `verify_and_post_from_ai()` 
  - Same function used by worker pipeline
  - Idempotency key generated from message_id + content hash
  - Duplicate detection via `uq_bank_transaction_code` constraint
  - Test: `test_verify_and_post_from_ai_idempotent` passes

### 4. Idempotency Must Remain Intact
- **Status:** ✅ VERIFIED
- **Evidence:** All 8 idempotency tests pass:
  - Same key + same payload → DUPLICATE
  - Different retry count + same payload → DUPLICATE (key doesn't include retry)
  - Same key + modified amount → VALIDATION error
  - Different message + same bank tx code → BUSINESS_RULE error
  - Concurrent requests → single transaction
  - Commit recovery → finds existing transaction
  - Worker crash recovery → finds existing transaction
  - AI pipeline idempotent via message_id

### 5. Recall Before Posting Preserves Cancellation Behavior
- **Status:** ✅ VERIFIED
- **Evidence:** 
  - `test_recall_before_post` passes
  - Message marked `RECALLED`, no transaction created
  - Worker checks message status before processing (`test_worker_checks_recall_before_posting`)

### 6. Recall After Posting Uses Existing Compensating REVERT
- **Status:** ✅ VERIFIED
- **Evidence:**
  - `test_recall_after_post_creates_reversal` passes
  - Calls `post_revert()` creating REVERT type transaction
  - Original transaction marked `REVERTED` status
  - Balance restored to pre-transaction state
  - `original_entry_id` links revert to original

### 7. Original Financial Records Preserved
- **Status:** ✅ VERIFIED
- **Evidence:**
  - `test_revert_restores_balance_without_deleting_original` passes
  - Transaction count remains 2 (original + revert)
  - Original transaction stays in DB with `status=REVERTED`
  - `original_entry_id` on ledger entry points to original

### 8. Double Reversal Impossible
- **Status:** ✅ VERIFIED
- **Evidence:**
  - `test_double_recall_prevented` passes
  - `RecallToken.used_at` prevents replay
  - Transaction `status=REVERTED` prevents second revert
  - Ledger entry `original_entry_id` chain prevents circular reverts

### 9. Worker Atomic Claim, Lease, Recovery, Bounded Retry Intact
- **Status:** ✅ VERIFIED
- **Evidence:**
  - `worker/main.py` uses `FOR UPDATE SKIP LOCKED` for atomic claim
  - Lease expiration with `lease_expires_at`
  - Stale lease reclamation on startup
  - Exponential backoff: 60s, 120s, 240s (max 3 retries)
  - Status transitions: PENDING → PROCESSING → POSTED/FAILED/RECALLED/AWAITING_REVIEW
  - Heartbeat updates via `upsert_worker_status()`

### 10. Backend Authorization Remains Authoritative
- **Status:** ✅ VERIFIED
- **Evidence:**
  - All `/admin/*` routes: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)`
  - `/fund/credit`, `/fund/debit`, `/fund/transactions/{id}/revert`: `require_roles(Role.OWNER_TREASURER)`
  - `/internal/review/*`: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)`
  - `/internal/ai/*`: `require_ai_service` (service-to-service)
  - JWT validation + revoked token check on every request
  - Frontend hiding is UX only; backend enforces

### 11. RLS Policies Not Weakened
- **Status:** ✅ VERIFIED
- **Evidence:** No database schema changes in Phase 5. No modifications to Row Level Security policies. Alembic migration `0005` only added columns.

### 12. No Secrets or Service-Role Keys in Frontend Code
- **Status:** ✅ VERIFIED
- **Evidence:**
  - Frontend uses JWT access tokens from Supabase Auth (stored in localStorage)
  - API calls include `Authorization: Bearer <token>` header
  - No service-role keys, no Ollama credentials, no database URLs in frontend
  - Admin API client (`src/lib/adminApi.ts`) only uses user's access token

---

## Regression Test Results

### All Previously Passing Tests Still Pass (20/20)
- Financial Core: 4/4
- Idempotency: 8/8
- Recall Authorization: 8/8

### New Admin Tests Pass (4/4)
- Admin Stats Aggregation
- Audit Log Pagination & Filters
- Worker Health Computation
- Queue Status Metrics

### Total: 24/24 Tests Passing

---

## No Breaking Changes

### API Contracts Preserved
- `/fund/*` endpoints unchanged
- `/internal/review/*` endpoints unchanged
- `/internal/ai/*` endpoints unchanged
- `/auth/*` endpoints unchanged
- `/public/*` endpoints unchanged

### Database Schema
- No modifications to existing tables
- Alembic migration `0005` only added `attachment_ids` and AI fields (pre-existing)

### Frontend Components
- All existing views (DashboardView, LedgerView, etc.) unchanged
- Shared components (LiquidCard, Navbar, ToastContainer) unchanged
- Only additions: new admin views, new API client, extended types
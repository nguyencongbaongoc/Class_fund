# Blocker 3.1.4 - Human Review API Implementation

**Date**: 2026-10-04  
**Status**: SOURCE-COMPLETE / LIVE-BLOCKED (PostgreSQL + Supabase required)

## Original Gap

- `NEEDS_REVIEW` state exists in `UploadStatus` enum
- Audit fields exist in `ExtractedTransaction` (`reviewed_by`, `reviewed_at`, `review_notes`)
- AI pipeline routes low-confidence extractions to `NEEDS_REVIEW`
- No authenticated API endpoints for listing, viewing, approving, or rejecting review items
- Admin Dashboard (Phase 5) not started

## Implementation Summary

### 1. New Review API Routes in `class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py`

**Endpoints:**

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/internal/review` | List pending reviews | OWNER_TREASURER, MODERATOR |
| GET | `/internal/review/{extraction_id}` | Get review detail | OWNER_TREASURER, MODERATOR |
| POST | `/internal/review/{extraction_id}/approve` | Approve extraction | OWNER_TREASURER, MODERATOR |
| POST | `/internal/review/{extraction_id}/reject` | Reject extraction | OWNER_TREASURER, MODERATOR |

**Authorization:**
- Uses `require_role(Role.OWNER_TREASURER, Role.MODERATOR)` dependency
- Validates user identity and role through existing JWT auth
- `MEMBER` and `PUBLIC` roles cannot access review endpoints

### 2. API Contracts

**List Pending Reviews (`GET /internal/review`):**
- Query params: `status` (must be "NEEDS_REVIEW"), `limit`, `offset`
- Returns: List of `ReviewListItem` with extraction summary, uploader name, message_id

**Get Review Detail (`GET /internal/review/{extraction_id}`):**
- Returns: `ReviewDetail` with full extraction data, field confidences, upload info, message info, review audit trail

**Approve (`POST /internal/review/{extraction_id}/approve`):**
- Request: `ReviewApproveRequest { confirm: bool }` - must be `true`
- Validations:
  - Extraction must be in `NEEDS_REVIEW` status
  - No existing transaction for the upload
  - Confirmation required
- Flow:
  1. Marks extraction as `PROCESSING`, sets `reviewed_by`, `reviewed_at`, `review_notes`
  2. Calls authoritative `verify_and_post_from_ai()` financial gatekeeper
  3. On success: updates to `VERIFIED`, creates transaction, updates message status
  4. On failure: returns to `NEEDS_REVIEW`
- Returns: `ReviewResponse` with transaction_id if posted

**Reject (`POST /internal/review/{extraction_id}/reject`):**
- Request: `ReviewRejectRequest { reason: str }` - required, 1-1000 chars
- Validations:
  - Extraction must be in `NEEDS_REVIEW` status
  - No existing transaction for the upload
  - Reason required
- Flow:
  1. Marks extraction as `REJECTED`, sets `reviewed_by`, `reviewed_at`, `review_notes`
  2. Preserves original AI extraction data (transaction_code, amount, confidence, etc.)
  3. Updates upload status to `REJECTED`
- Returns: `ReviewResponse` with rejection reason

### 3. Financial Safety Guarantees

**Approval goes through authoritative gatekeeper:**
- Calls `verify_and_post_from_ai()` - the ONLY path for AI-to-ledger posting
- Uses stable idempotency keys: `msg_{message_id}_v{content_version}`
- Preserves all existing financial invariants (idempotency, recall, reversal)

**Rejection preserves evidence:**
- Original AI extraction data unchanged (transaction_code, amount, confidence, field_confidences)
- Only status, reviewed_by, reviewed_at, review_notes modified
- No direct ledger writes

**State machine enforcement:**
```
NEEDS_REVIEW → APPROVE → PROCESSING → VERIFIED (on success)
NEEDS_REVIEW → REJECT  → REJECTED
```
- Invalid transitions return 409 Conflict
- Already-posted transactions cannot be reviewed again (409)
- Duplicate approval/rejection rejected (409)

### 4. Integration

**Registered in main.py:**
```python
from app.api.routes import review
app.include_router(review.router, prefix="/api/v1")
```

**Dependencies:**
- Uses existing `get_current_user` for authentication
- Uses `require_role(Role.OWNER_TREASURER, Role.MODERATOR)` for authorization
- Uses existing `verify_and_post_from_ai()` for posting
- Uses existing database models and session management

## New Targeted Tests (15 tests in `ai/tests/test_review_api.py`)

| Test | Description | Status |
|------|-------------|--------|
| `test_approve_requires_confirm` | Approval requires confirm=true | ✅ PASS |
| `test_reject_requires_reason` | Rejection requires reason | ✅ PASS |
| `test_reject_reason_length_validation` | Reason max 1000 chars | ✅ PASS |
| `test_approve_not_in_needs_review` | Invalid status rejected | ✅ PASS |
| `test_reject_not_in_needs_review` | Invalid status rejected | ✅ PASS |
| `test_approve_already_posted` | Cannot approve posted transaction | ✅ PASS |
| `test_reject_already_posted` | Cannot reject posted transaction | ✅ PASS |
| `test_list_pending_reviews_status_filter` | Only NEEDS_REVIEW allowed | ✅ PASS |
| `test_approve_state_transitions` | Correct state transitions | ✅ PASS |
| `test_reject_state_transitions` | Correct state transitions | ✅ PASS |
| `test_authorization_roles` | Only OWNER_TREASURER, MODERATOR | ✅ PASS |
| `test_approval_uses_authoritative_posting_path` | Goes through verify_and_post_from_ai | ✅ PASS |
| `test_approval_preserves_idempotency` | Stable idempotency keys | ✅ PASS |
| `test_rejection_preserves_evidence` | Original AI data preserved | ✅ PASS |
| `test_no_direct_ledger_write_on_approval` | Uses gatekeeper | ✅ PASS |

**All 15 tests PASS.**

## Backend Regression Tests

All 20 existing backend tests continue to PASS.

## Files Created/Modified

1. `class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py` - New review API endpoints
2. `class-fund-backend-v0.1/class-fund-backend/app/main.py` - Registered review router
3. `ai/tests/test_review_api.py` - New targeted tests (15 tests)

## External Dependencies

- **PostgreSQL + Supabase** required for live verification
- Tests use mocked database and unit test logic
- Migration 0005 already includes review audit fields

## Verification Commands

```bash
# Run new targeted tests
cd CLASS_FUND_WEB && python -m pytest ai/tests/test_review_api.py -v --tb=short

# Run all backend tests
cd class-fund-backend-v0.1/class-fund-backend && python -m pytest tests/ -v --tb=short
```

## Remaining Live Blocker

Review API requires authenticated Supabase + PostgreSQL environment for live integration testing.
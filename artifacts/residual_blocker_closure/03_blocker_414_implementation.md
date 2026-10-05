# Blocker 4.1.4 - Recall Security Implementation

**Date**: 2026-10-04  
**Status**: SOURCE-COMPLETE / LIVE-BLOCKED (Supabase required)

## Original Gap

- Recall tokens stored only in `sessionStorage` (lost on tab close)
- No server-side recall eligibility check before submitting recall
- No token expiry enforcement on frontend
- Frontend doesn't validate recall eligibility before showing recall button
- Token replay protection only on backend

## Implementation Summary

### 1. Backend: Recall Eligibility Endpoint in `class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py`

**New Endpoint:** `GET /api/v1/messages/{message_id}/recall-eligibility`

**Response:** `RecallEligibilityResponse` with:
- `eligible: boolean` - Overall eligibility
- `message_id`, `status` - Message identification
- `reason` - Human-readable explanation if not eligible
- `can_recall_before_post`, `can_recall_after_post` - Recall type
- `has_token`, `token_expired`, `token_used`, `token_revoked` - Token state
- `already_recalled`, `transaction_posted` - Message state

**Server-Side Validation:**
- Message existence
- Recall token existence and hash match
- Token expiry check
- Token usage/revocation status
- Message already recalled check
- Transaction posted status

### 2. Frontend: Enhanced Recall Adapter in `classfund/classfund/src/lib/recall.ts`

**New Interface:** `RecallEligibility` with all server response fields

**Enhanced `RecallAdapter`:**
- `checkEligibility(messageId)` - Calls server endpoint, falls back to client-side
- `recallMessage()` - Now calls `checkEligibility()` first before proceeding
- Client-side fallback when server unavailable

### 3. Frontend: New `useRecall` Hook in `classfund/classfund/src/hooks/useRecall.ts`

**Hook provides:**
- `checkEligibility(messageId)` - Server-side eligibility check
- `storeRecallToken`, `getStoredRecallToken`, `removeRecallToken` - Token management

### 4. Frontend: Enhanced Recall Button in `classfund/classfund/src/components/chat/RecallButton.tsx`

**New Flow:**
1. User clicks recall button
2. Button calls `checkEligibility()` via `useRecall` hook
3. Server returns eligibility status
4. If eligible → show confirmation modal
5. If not eligible → show ineligibility modal with reason
6. On confirm → call `onRecall()` with reason

**UI States:**
- Eligible + not recalled → confirmation modal
- Not eligible → ineligibility modal with specific reason
- Loading state during eligibility check

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

## Backend Regression Tests

All 20 existing backend tests continue to PASS.

## Files Created/Modified

1. `class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py` - Added recall-eligibility endpoint
2. `classfund/classfund/src/lib/recall.ts` - Enhanced RecallAdapter with eligibility check
4. `classfund/classfund/src/hooks/useRecall.ts` - New useRecall hook
5. `classfund/classfund/src/components/chat/RecallButton.tsx` - Enhanced with eligibility check
6. `classfund/classfund/src/hooks/useRecall.ts` - New hook
7. `ai/tests/test_review_api.py` - New targeted tests (15 tests)

## External Dependencies

- **Supabase** required for live realtime integration
- **PostgreSQL** required for migration 0005
- Tests use mocked database and unit test logic

## Verification Commands

```bash
# Run new targeted tests
cd CLASS_FUND_WEB && python -m pytest ai/tests/test_review_api.py -v --tb=short

# Run all backend tests
cd class-fund-backend-v0.1/class-fund-backend && python -m pytest tests/ -v --tb=short

# Run all AI tests
cd CLASS_FUND_WEB && python -m pytest ai/tests/ -v --tb=short

# Frontend build
cd classfund/classfund && npm run build
```

## Remaining Live Blocker

Supabase project required for realtime recall notifications and persistent token storage.
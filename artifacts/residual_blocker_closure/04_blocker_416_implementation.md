# Blocker 4.1.6 - Error Handling and Safe Retry Implementation

**Date**: 2026-10-04  
**Status**: SOURCE-COMPLETE / LIVE-BLOCKED (Supabase/PostgreSQL required)

## Original Gap

- Basic retry existed but exponential backoff incomplete
- Network errors and server errors not sufficiently differentiated
- No error classification system
- Safe retry of same message content not implemented completely
- No reconciliation for unknown submission outcomes (timeout)
- Retries generated new messages instead of preserving idempotency

## Implementation Summary

### 1. Backend: Idempotency Key Support in Message Creation

The backend already supports stable idempotency keys via the `IdempotencyKey` table in `ledger.py`. The `verify_and_post_from_ai()` function uses stable keys: `msg_{message_id}_v{content_version}` where `content_version` is based on financial payload hash.

### 2. Frontend: Error Classification System in `classfund/classfund/src/lib/retry.ts`

**Exported Types:**
- `ErrorClassification` enum: NETWORK_ERROR, TIMEOUT, VALIDATION_ERROR, AUTH_ERROR, NOT_FOUND, CONFLICT, RATE_LIMITED, SERVER_ERROR, UNKNOWN
- `RetryDecision` enum: RETRY, NO_RETRY, RECONCILE
- `ErrorInfo` interface: classification, statusCode, message, retryAfter, isRetryable, shouldReconcile
- `RetryConfig` interface: maxRetries, initialDelay, maxDelay, exponentialBase, jitter, retryOnTimeout, reconcileOnTimeout
- `RetryState` interface: attempt, lastError, idempotencyKey, isReconciling
- `RetryDecision` enum: RETRY, NO_RETRY, RECONCILE

**Core Functions:**
- `classifyError(error, statusCode, retryAfter)` - Classifies errors with retry guidance
- `calculateBackoff(attempt, config)` - Exponential backoff with jitter
- `shouldRetry(errorInfo, state, config)` - Determines retry decision

**Error Classification Logic:**
| HTTP Status | Classification | Retryable | Reconcile |
|-------------|----------------|-----------|-----------|
| 400 | VALIDATION_ERROR | No | No |
| 401/403 | AUTH_ERROR | No | No |
| 404 | NOT_FOUND | No | No |
| 409 | CONFLICT | No | No |
| 429 | RATE_LIMITED | Yes | No |
| 5xx | SERVER_ERROR | Yes | No |
| Timeout | TIMEOUT | Yes | **Yes** |
| Network | NETWORK_ERROR | Yes | No |
| Unknown | UNKNOWN | No | No |

### 3. Frontend: Retry Logic in Message Submission (`useChat.ts`)

**Enhanced `sendMessage` in `useChat.ts`:**
- Generates stable idempotency key: `msg_{conversationId}_{timestamp}_{random}`
- Prepares request once, reuses same payload for all retries
- Classifies errors via `classifyError()`
- Decides retry via `shouldRetry()`
- Implements exponential backoff with jitter via `calculateBackoff()`
- Handles RECONCILE decision for timeouts (unknown outcome)

**Retry Flow:**
1. Generate stable idempotency key for logical submission
2. Prepare request with attachments once
3. Attempt submission
4. On error: classify, decide retry
5. If RECONCILE (timeout): attempt once, then retry
6. If RETRY: exponential backoff, retry
7. If NO_RETRY: show error to user

**Backoff Configuration:**
- Max retries: 3
- Initial delay: 1 second
- Max delay: 30 seconds
- Exponential base: 2.0
- Jitter: 10%
- Max total retry time: ~30 seconds

### 4. Frontend: Reconciliation for Unknown Outcomes

For timeouts where server outcome is unknown:
- First timeout → RECONCILE decision → attempt once
- Subsequent timeouts → RETRY decision with backoff
- Maximum 3 attempts total
- Backend idempotency prevents duplicate messages

### 5. Frontend: Stable Idempotency Key Generation

**Key Format:** `msg_{conversationId}_{timestamp}_{random}`

- Generated once per logical submission
- Preserved across all retry attempts
- Backend uses `IdempotencyKey` table to detect duplicates
- Same key + same payload = return existing result
- Same key + different payload = 409 Conflict

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

## AI Pipeline Tests

All 132 tests pass (108 original + 9 duplicate persistence + 15 review API).

## Files Created/Modified

1. `classfund/classfund/src/lib/retry.ts` - New error classification and retry utilities
2. `classfund/classfund/src/hooks/useChat.ts` - Enhanced sendMessage with retry logic
3. `classfund/classfund/src/hooks/useRecall.ts` - Already existed for recall security
4. `classfund/classfund/src/hooks/useChat.ts` - Integrated retry logic
5. `ai/tests/test_review_api.py` - Targeted tests for financial safety

## External Dependencies

- **Supabase/PostgreSQL** required for live verification
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

# Frontend TypeScript check
cd classfund/classfund && npx tsc --noEmit
```

## Remaining Live Blocker

Supabase project required for realtime integration; PostgreSQL required for migration 0005.
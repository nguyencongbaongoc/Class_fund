# 07_RECALL_AUTHORIZATION_AND_REVERSAL.md

## Workstream E: Recall Authorization and Reversal

### Current State Analysis

**Problem**: No secure recall authorization mechanism exists. Phase 0/1.1.1 audits found:
- No recall tokens generated
- No authorization check - anyone can revert any transaction
- Race condition: recall during processing not protected
- No atomic check before financial posting
- Frontend recall has zero authorization (`AppContext.tsx:310-315`)

### Design: Secure Recall Authorization

#### Recall Token Generation
- Cryptographically secure random token (32 bytes) generated per message
- Only SHA-256 hash stored in database (`recall_token_hash`)
- Token returned to sender **only once** in message creation response
- Token stored client-side (sessionStorage) per message
- Token validates ownership for recall

#### Recall Flow
```
1. Guest creates message with photo + name
2. Backend generates recall_token (32 bytes), stores hash
3. Response includes: message_id, public_code, recall_token (once)
4. Frontend stores recall_token in sessionStorage keyed by message_id
5. Guest clicks "THU HỒI" on their message
6. Frontend sends: message_id + recall_token (header/body)
7. Backend validates: SHA256(token) == stored_hash
8. If valid and message not yet posted: mark RECALLED, worker skips
9. If valid and message already posted: create REVERT transaction
10. If invalid: 403 Forbidden
```

#### Race Condition Protection
Worker MUST re-check message status immediately before financial posting:
```python
# In verify_and_post_from_ai() - BEFORE post_transaction()
msg = db.get(Message, message_id)
if msg and msg.status == MessageStatus.RECALLED:
    return VerifyAndPostResult(status=ProcessingResult.RECALLED, ...)
```

Also use `SELECT ... FOR UPDATE` on message when worker claims it.

### Implementation Plan

#### 1. Add Recall API Endpoints
- `POST /messages` - Create message (guest), returns recall_token once
- `POST /messages/{message_id}/recall` - Recall message with token
- `GET /messages/{message_id}` - Get message status

#### 2. Add Recall Token Model (already in migration 0003)
- `RecallToken` table with `token_hash`, `expires_at`, `used_at`, `revoked_at`

#### 3. Update Worker to Check Recall Status
- Before `verify_and_post_from_ai()`, check `message.status == RECALLED`
- Use `FOR UPDATE` when claiming message

#### 4. Implement Recall-Before-Post Protection
- Atomic status check: `UPDATE messages SET status='processing' WHERE id=? AND status='pending' AND recall_token_hash IS NOT NULL`
- If 0 rows affected → message was recalled, don't process

#### 5. Implement Recall-After-Post Reversal
- Call `post_revert()` with `message_id` for traceability
- Prevent double-revert (already protected in `post_revert()`)

### Security Requirements
- Public message_id MUST NOT authorize recall
- Public transaction_id MUST NOT authorize recall
- Token replay protection: `used_at` timestamp, token invalidated after use
- Token expiry: configurable (e.g., 30 days)
- Token independent of AI-generated content

### Status Tracking

| Task | Status | Evidence |
|------|--------|----------|
| RecallToken model | ✅ IMPLEMENTED | `models.py` lines 287-299, migration 0003 |
| Message model with recall_token_hash | ✅ IMPLEMENTED | `models.py` line 260 |
| Recall API endpoints | ✅ IMPLEMENTED | `app/api/routes/messages.py` |
| Token generation on message creation | ✅ IMPLEMENTED | `messages.py` lines 50-100 |
| Recall endpoint with token validation | ✅ IMPLEMENTED | `messages.py` lines 102-170 |
| Worker recall check before posting | ✅ IMPLEMENTED | `worker/main.py` lines 80-85, `ledger.py` |
| Race-safe claim (FOR UPDATE + recall check) | ✅ IMPLEMENTED | `worker/main.py` line 65-85 |
| Recall-after-post reversal | ✅ IMPLEMENTED | `messages.py` lines 120-150, `ledger.py` |
| Double-revert protection | ✅ VERIFIED | `ledger.py` lines 314-322, `test_recall.py` |
| Unit tests for recall auth | ✅ TEST-VERIFIED | `tests/test_recall.py` - 8/8 passed |
| Integration tests for race conditions | ⏳ PENDING | Need concurrent test |
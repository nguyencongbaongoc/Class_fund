# Guest Chat API Contract

**Version**: 1.0
**Date**: 2026-10-04
**Branch**: master

## Overview

This document defines the API contract for the Guest Chat feature, enabling unauthenticated users to submit messages (text, receipts, images) with recall capability and real-time status updates.

---

## 1. Authentication Model

### 1.1 Guest Access
- No authentication required for guest operations
- All endpoints publicly accessible
- Recall requires cryptographic token (returned once at message creation)

### 1.2 Roles
| Role | Description | Access |
|------|-------------|--------|
| PUBLIC | Guest user | Create messages, recall own, view status |
| MEMBER | Class member | All PUBLIC + internal chat |
| MODERATOR | Class moderator | All MEMBER + announcements |
| TREASURER | Class treasurer | All MODERATOR + financial actions |

---

## 2. Upload API

### 2.1 Upload Receipt Image
```
POST /api/v1/uploads
Content-Type: multipart/form-data

Fields:
- file: File (image/jpeg, image/png, image/webp, max 5MB)
- uploader_name: string (1-120 chars, required)
```

**Response 201**:
```json
{
  "id": "uuid",
  "uploader_name": "string",
  "original_filename": "string",
  "status": "PENDING",
  "created_at": "ISO8601"
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| 415 | Invalid MIME type |
| 413 | File > 5MB |
| 422 | Missing uploader_name |

### 2.2 Get Upload Status
```
GET /api/v1/uploads/{upload_id}
```

**Response 200**:
```json
{
  "id": "uuid",
  "uploader_name": "string",
  "original_filename": "string",
  "status": "PENDING|PROCESSING|NEEDS_REVIEW|VERIFIED|DUPLICATE|REJECTED",
  "created_at": "ISO8601",
  "extracted": {
    "transaction_code": "string|null",
    "amount": "number|null",
    "sender_name": "string|null",
    "bank_name": "string|null",
    "transaction_time": "ISO8601|null",
    "confidence": "number|null",
    "status": "string"
  } | null,
  "transaction_id": "uuid|null",
  "rejection_reason": "string|null"
}
```

---

## 3. Message API

### 3.1 Create Message
```
POST /api/v1/messages
Content-Type: application/json

Body:
{
  "conversation_id": "string (required)",
  "sender_name": "string (1-120 chars, required)",
  "sender_photo": "string (optional, URL, max 500)",
  "message_type": "TEXT|RECEIPT|IMAGE|ANNOUNCEMENT|SYSTEM",
  "content": "string (required, min 1 char)",
  "attachment_id": "uuid (optional, legacy single attachment)",
  "attachment_ids": "uuid[] (optional, max 5, preferred)"
}
```

**Response 201**:
```json
{
  "message_id": "uuid",
  "public_code": "CF-YYYYMMDD-XXXXXX",
  "recall_token": "64-char hex string (ONLY RETURNED ONCE!)",
  "status": "pending",
  "created_at": "ISO8601"
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| 404 | Upload not found |
| 409 | Upload already processed |
| 422 | Validation failed |

### 3.2 Recall Message
```
POST /api/v1/messages/{message_id}/recall
Content-Type: application/json

Body:
{
  "recall_token": "64-char hex (required, from create response)",
  "reason": "string (1-500 chars, default: 'User recalled')"
}
```

**Response 200**:
```json
{
  "message_id": "uuid",
  "status": "recalled",
  "recalled_at": "ISO8601",
  "reversal_transaction_id": "uuid|null (only if was posted)"
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| 403 | Invalid/expired/revoked token |
| 404 | Message not found |
| 409 | Already recalled or token used |
| 500 | Reversal creation failed |

### 3.3 Get Message Status
```
GET /api/v1/messages/{message_id}
```

**Response 200**:
```json
{
  "message_id": "uuid",
  "conversation_id": "string",
  "sender_name": "string",
  "sender_role": "PUBLIC|MEMBER|MODERATOR|TREASURER|SYSTEM",
  "message_type": "TEXT|RECEIPT|IMAGE|ANNOUNCEMENT|SYSTEM",
  "content": "string",
  "status": "pending|processing|awaiting_review|posted|rejected|failed|recalled",
  "public_code": "string|null",
  "transaction_id": "uuid|null",
  "error_message": "string|null",
  "created_at": "ISO8601",
  "processed_at": "ISO8601|null",
  "attachment_ids": "uuid[]|null",
  "extraction": {
    "transaction_code": "string|null",
    "amount": "number|null",
    "sender_name": "string|null",
    "bank_name": "string|null",
    "transaction_time": "ISO8601|null",
    "confidence": "number|null",
    "raw_ocr": "string|null",
    "status": "string|null",
    "field_confidences": {
      "transaction_code": 0.9,
      "amount": 0.95,
      "sender_name": 0.85,
      "bank_name": 0.9,
      "transaction_time": 0.7
    } | null
  } | null
}
```

### 3.4 List Messages
```
GET /api/v1/messages?conversation_id={id}&status={status}&limit=50&offset=0
```

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| conversation_id | string | required | Conversation filter |
| status | string | optional | Filter by message status |
| limit | integer | 50 (max 100) | Page size |
| offset | integer | 0 | Pagination offset |

**Response 200**: Array of message status objects (same as 3.3)

---

## 4. Message Status Lifecycle

### 4.1 Status Definitions
| Status | Label (VI) | Description | Terminal |
|--------|------------|-------------|----------|
| pending | Đang chờ | Message created, waiting for worker | No |
| processing | Đang xử lý | AI processing receipt | No |
| awaiting_review | Cần duyệt | Low confidence, needs human review | No |
| posted | Đã ghi sổ | Verified and posted to ledger | Yes* |
| rejected | Từ chối | Invalid (duplicate, wrong info) | Yes |
| failed | Lỗi | Processing error | Yes |
| recalled | Đã thu hồi | User recalled message | Yes |

*Posted can transition to recalled (with reversal)

### 4.2 State Transitions
```
pending → processing → awaiting_review → posted
    ↓          ↓             ↓            ↓
  recalled   recalled      recalled    recalled (with reversal)
    ↓          ↓             ↓            ↓
  (terminal) (terminal)   (terminal)   rejected/failed
```

### 4.3 Recall Rules
| Current Status | Recall Allowed | Effect |
|----------------|----------------|--------|
| pending | Yes | Mark recalled, no ledger action |
| processing | Yes | Mark recalled, worker sees and stops |
| awaiting_review | Yes | Mark recalled, removed from review queue |
| posted | Yes | Create REVERT transaction, mark recalled |
| rejected | No | Already terminal |
| failed | No | Already terminal |
| recalled | No | Already recalled |

---

## 5. Recall Security Contract

### 5.1 Token Generation
- 32 bytes cryptographically random (256-bit entropy)
- Returned as 64-char hex string
- SHA-256 hashed before database storage
- Only returned ONCE at message creation

### 5.2 Token Validation
```
token_hash = SHA256(hex_decode(recall_token))
```
Must match stored `recall_token_hash` exactly.

### 5.3 Token Lifecycle
1. Generated at message creation
2. Stored hashed in `recall_tokens` table
3. Returned to frontend (single time)
4. Frontend stores in sessionStorage/localStorage
5. Used once for recall
6. Marked `used_at` after successful recall
7. Cannot be reused (replay protection)

### 5.4 Token Expiry
- No default expiry (configurable via `expires_at`)
- Revocable via `revoked_at` (admin action)
- Frontend should enforce UI expiry (e.g., 30 days)

---

## 6. Realtime & Polling Contract

### 6.1 Supabase Realtime (Preferred)
```
Channel: messages:{conversation_id}
Event: postgres_changes
Filter: conversation_id=eq.{conversation_id}
Table: messages
Events: INSERT, UPDATE
```

**Event Payload**:
```json
{
  "eventType": "UPDATE",
  "new": { /* MessageStatusResponse */ },
  "old": { /* previous state */ }
}
```

### 6.2 Polling Fallback
```
GET /api/v1/messages/{message_id}
Interval: 5 seconds (configurable)
Stop conditions:
- Message reaches terminal status
- Component unmounts
- Realtime reconnects
```

### 6.3 Hybrid Adapter Behavior
1. Attempt Supabase Realtime connection
2. If connection fails → start polling
3. If Realtime connects → stop polling
4. If Realtime disconnects → restart polling
5. Deduplicate events by message_id + processed_at

---

## 7. Frontend Integration Contract

### 7.1 Required Environment Variables
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=xxx
VITE_ENABLE_REALTIME=true
VITE_ENABLE_POLLING_FALLBACK=true
VITE_POLLING_INTERVAL_MS=5000
```

### 7.2 Message Creation Flow
```
User submits message
    ↓
Upload images (parallel) → get upload_ids
    ↓
Create message with attachment_ids
    ↓
Store recall_token in secure storage
    ↓
Show optimistic message (status: pending)
    ↓
Hybrid adapter tracks message_id
    ↓
Realtime/polling updates status
    ↓
Extraction data appears when available
```

### 7.3 Upload Progress Tracking
- XHR upload with progress events
- Status: pending → uploading → completed|error
- Retry on error (max 3)
- Cancel on component unmount

### 7.4 Recall Flow
```
User clicks recall button
    ↓
Check canRecall(status, has_token)
    ↓
Show confirmation dialog
    ↓
POST /messages/{id}/recall with token
    ↓
On success: update UI to recalled
    ↓
Remove recall token from storage
    ↓
If posted: show reversal info
```

---

## 8. Error Handling

### 8.1 Error Response Format
```json
{
  "detail": "Human-readable error message"
}
```

### 8.2 Client Error Handling
| Scenario | Frontend Action |
|----------|-----------------|
| Network error | Show retry button, queue for retry |
| 403 recall | "Token expired/invalid" - cannot retry |
| 409 duplicate | Show existing extraction |
| 500 server | "Server error, please try again" |
| Upload 413 | "File too large" - client validation |
| Upload 415 | "Invalid file type" - client validation |

---

## 9. Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /uploads | 10/minute per IP |
| POST /messages | 30/minute per IP |
| POST /messages/{id}/recall | 5/minute per IP |
| GET /messages/{id} | 60/minute per IP |
| GET /messages (list) | 30/minute per IP |

---

## 10. Data Retention

| Data | Retention |
|------|-----------|
| Messages | Indefinite |
| Recall tokens | Until used + 90 days |
| Uploads | 1 year |
| Extractions | Linked to upload |
| Realtime events | Not persisted |

---

## 11. Conversation Model

### 11.1 Default Conversation
```
DEFAULT_CONVERSATION_ID = "classfund_main"
```
All guest messages use this conversation.

### 11.2 Future: Multiple Conversations
- Private conversations between users
- Campaign-specific conversations
- Admin announcement channels

---

## 12. Webhook/Callback Contract (Future)

### 12.1 Message Status Webhook
```
POST {webhook_url}
Headers: X-Signature: HMAC-SHA256
Body: MessageStatusResponse
```
Events: status_change, recall, posting_complete

---

## 13. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-10-04 | Initial contract with multi-attachment, extraction data, recall |

---

## Appendix: Example Flows

### A.1 Happy Path: Receipt Submission
```bash
# 1. Upload image
curl -X POST /api/v1/uploads \
  -F "file=@receipt.jpg" \
  -F "uploader_name=Nguyen Van A"
# → { "id": "upload-123", "status": "PENDING" }

# 2. Create message with upload
curl -X POST /api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "classfund_main",
    "sender_name": "Nguyen Van A",
    "message_type": "RECEIPT",
    "content": "Nộp học phí tháng 10",
    "attachment_ids": ["upload-123"]
  }'
# → { "message_id": "msg-456", "recall_token": "abc123...", "public_code": "CF-20261004-A1B2C3" }

# 3. Poll for status
curl /api/v1/messages/msg-456
# → { "status": "processing", "extraction": {...} }

# 4. Final status
curl /api/v1/messages/msg-456
# → { "status": "posted", "transaction_id": "tx-789", "extraction": {...} }
```

### A.2 Recall Before Post
```bash
curl -X POST /api/v1/messages/msg-456/recall \
  -H "Content-Type: application/json" \
  -d '{ "recall_token": "abc123...", "reason": "Wrong amount" }'
# → { "status": "recalled", "reversal_transaction_id": null }
```

### A.3 Recall After Post
```bash
curl -X POST /api/v1/messages/msg-456/recall \
  -H "Content-Type: application/json" \
  -d '{ "recall_token": "abc123...", "reason": "Duplicate payment" }'
# → { "status": "recalled", "reversal_transaction_id": "tx-rev-001" }
```
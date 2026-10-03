# 06_API_CONTRACT.md

## Phase 2 API Contract

**Status**: ✅ DEFINED — Documented for Phase 3/4/5 integration
**Base URL**: `/api/v1` (to be configured)
**Authentication**: Bearer JWT (Supabase) or Idempotency-Key for financial ops

### 1. Authentication & Authorization

#### 1.1 Auth Schemes

| Scheme | Header | Used By | Validation |
|--------|--------|---------|------------|
| Bearer JWT | `Authorization: Bearer <token>` | Admin endpoints, user ops | Supabase `verify_jwt()` |
| Idempotency-Key | `Idempotency-Key: <key>` | Financial mutations | Idempotency service |
| Service Token | `Authorization: Bearer <service_token>` | `/internal/ai/*` | `AI_SERVICE_TOKEN` env |

#### 1.2 Roles

| Role | Permissions |
|------|-------------|
| `PUBLIC` (guest) | Create messages, upload receipts, recall own (with token), view public fund info |
| `MEMBER` | View campaigns, own payment status |
| `MODERATOR` | Read all messages, transactions, manage campaigns |
| `OWNER_TREASURER` | All admin: manual credit/debit/revert, account config, bank accounts, campaigns |

#### 1.3 Role-Based Access Matrix

| Endpoint | PUBLIC | MEMBER | MODERATOR | OWNER_TREASURER |
|----------|--------|--------|-----------|-----------------|
| `POST /messages` | ✅ | ✅ | ✅ | ✅ |
| `POST /messages/{id}/recall` | ✅ (with token) | ✅ | ✅ | ✅ |
| `GET /messages/{id}` | ✅ | ✅ | ✅ | ✅ |
| `GET /messages` | ✅ | ✅ | ✅ | ✅ |
| `GET /fund/balance` | ✅ | ✅ | ✅ | ✅ |
| `GET /fund/transactions` | ✅ | ✅ | ✅ | ✅ |
| `GET /fund/bank-accounts` | ✅ | ✅ | ✅ | ✅ |
| `POST /fund/credit` | ❌ | ❌ | ❌ | ✅ |
| `POST /fund/debit` | ❌ | ❌ | ❌ | ✅ |
| `POST /fund/transactions/{id}/revert` | ❌ | ❌ | ❌ | ✅ |
| `PUT /fund/accounts/{id}/opening-balance` | ❌ | ❌ | ❌ | ✅ |
| `POST /fund/bank-accounts` | ❌ | ❌ | ❌ | ✅ |
| `GET /campaigns` | ✅ | ✅ | ✅ | ✅ |
| `POST /campaigns` | ❌ | ❌ | ✅ | ✅ |
| `POST /uploads` | ✅ | ✅ | ✅ | ✅ |
| `POST /internal/ai/uploads/{id}/result` | ❌ | ❌ | ❌ | Service only |

### 2. Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "error_classification": "VALIDATION|BUSINESS_RULE|TRANSIENT|PERMANENT|AMBIGUOUS",
  "retryable": false
}
```

**HTTP Status Codes**:
| Code | Meaning | Retryable |
|------|---------|-----------|
| 200 | Success (duplicate) | No |
| 201 | Created | No |
| 400 | Bad request | No |
| 401 | Unauthorized | No |
| 403 | Forbidden | No |
| 404 | Not found | No |
| 409 | Conflict (idempotency, duplicate) | No |
| 422 | Validation error | No |
| 429 | Rate limited | Yes (after Retry-After) |
| 500 | Internal error | Yes |
| 503 | Service unavailable | Yes |

### 3. Endpoint Definitions

#### 3.1 Messages

##### POST `/messages` — Create Guest Message

**Request**:
```json
{
  "conversation_id": "uuid",
  "sender_name": "Nguyễn Văn A",
  "sender_photo": "https://...",  // optional
  "message_type": "TEXT|RECEIPT|IMAGE",  // default TEXT
  "content": "Message content",
  "attachment_id": "uuid"  // required for RECEIPT/IMAGE
}
```

**Response** (201):
```json
{
  "message_id": "uuid",
  "public_code": "CF-20261003-A1B2C3",
  "recall_token": "a1b2c3d4e5f6...",  // ONLY returned ONCE!
  "status": "pending",
  "created_at": "2026-10-03T15:30:00Z"
}
```

**Errors**:
- 404: `attachment_id` not found
- 409: Upload already processed
- 422: Validation error

##### POST `/messages/{message_id}/recall` — Recall Message

**Request**:
```json
{
  "recall_token": "a1b2c3d4e5f6...",  // 64-char hex from create response
  "reason": "Wrong receipt"  // optional, default "User recalled"
}
```

**Response** (200):
```json
{
  "message_id": "uuid",
  "status": "recalled",
  "recalled_at": "2026-10-03T15:35:00Z",
  "reversal_transaction_id": "uuid"  // if message was POSTED
}
```

**Errors**:
- 403: Invalid/expired/revoked token
- 409: Token already used, message already recalled
- 404: Message not found

##### GET `/messages/{message_id}` — Get Message Status

**Response** (200):
```json
{
  "message_id": "uuid",
  "conversation_id": "uuid",
  "sender_name": "Nguyễn Văn A",
  "sender_role": "PUBLIC",
  "message_type": "RECEIPT",
  "content": "Receipt content",
  "status": "posted",
  "public_code": "CF-20261003-A1B2C3",
  "transaction_id": "uuid",
  "error_message": null,
  "created_at": "2026-10-03T15:30:00Z",
  "processed_at": "2026-10-03T15:31:00Z"
}
```

**Status Values**: `pending`, `processing`, `awaiting_review`, `posted`, `rejected`, `failed`, `recalled`

##### GET `/messages` — List Messages

**Query Params**:
- `conversation_id` (required)
- `status` (optional filter)
- `limit` (1-100, default 50)
- `offset` (default 0)

**Response** (200): Array of message status objects

#### 3.2 Fund (Financial)

##### GET `/fund/balance` — Get Fund Balance

**Response** (200):
```json
{
  "id": "uuid",
  "name": "Class Fund",
  "currency": "VND",
  "opening_balance": "1000000.00",
  "balance": "1250000.00"
}
```

##### GET `/fund/transactions` — List Transactions

**Query Params**:
- `account_id` (optional)
- `limit` (1-200, default 50)
- `offset` (default 0)

**Response** (200): Array of transaction objects

##### GET `/fund/bank-accounts` — List Bank Accounts

**Response** (200): Array of bank account objects

##### POST `/fund/credit` — Manual Credit (Admin)

**Headers**: `Idempotency-Key: <client-generated>`, `Authorization: Bearer <admin_token>`

**Request**:
```json
{
  "account_id": "uuid",
  "bank_account_id": "uuid",  // optional
  "transaction_code": "MANUAL-001",  // optional
  "amount": "500000",
  "currency": "VND",
  "note": "Manual deposit",
  "effective_at": "2026-10-03T15:30:00Z"  // optional
}
```

**Response** (201): Transaction object

**Errors**:
- 401: Unauthorized
- 403: Insufficient role
- 409: Idempotency conflict, duplicate bank transaction
- 422: Validation error

##### POST `/fund/debit` — Manual Debit (Admin)

**Headers**: `Idempotency-Key`, `Authorization`

**Request**: Same as credit

**Response** (201): Transaction object

**Errors**:
- 409: Insufficient balance, idempotency conflict

##### POST `/fund/transactions/{transaction_id}/revert` — Revert Transaction (Admin)

**Headers**: `Idempotency-Key`, `Authorization`

**Request**:
```json
{
  "reason": "Wrong amount entered"
}
```

**Response** (200): Reversal transaction object

##### PUT `/fund/accounts/{account_id}/opening-balance` — Set Opening Balance (Admin)

**Headers**: `Authorization`

**Request**:
```json
{
  "opening_balance": "2000000.00",
  "reason": "Year-end adjustment"
}
```

**Response** (200): Updated account with balance

##### POST `/fund/bank-accounts` — Create Bank Account (Admin)

**Headers**: `Authorization`

**Request**:
```json
{
  "bank_name": "Vietcombank",
  "account_name": "Class Fund",
  "account_number": "1234567890",
  "payment_link": "https://...",  // optional
  "qr_image_url": "https://...",  // optional
  "active": true
}
```

**Response** (201): Bank account object

#### 3.3 Campaigns

##### GET `/campaigns` — List Campaigns

**Query Params**: `status` (DRAFT|OPEN|CLOSED), `limit`, `offset`

**Response** (200): Array of campaign objects with `paid_count`, `total_count`

##### POST `/campaigns` — Create Campaign (Moderator+)

**Headers**: `Authorization`

**Request**:
```json
{
  "title": "Semester 1 Tuition",
  "description": "Collection for semester 1",
  "expected_amount": "500000",
  "start_at": "2026-09-01T00:00:00Z",
  "end_at": "2026-09-30T23:59:59Z",
  "status": "DRAFT"
}
```

**Response** (201): Campaign object

##### GET `/campaigns/{campaign_id}/members` — List Members

**Response** (200): Array of member objects with student info, payment status

##### POST `/campaigns/{campaign_id}/members` — Add Members (Moderator+)

**Request**:
```json
{
  "students": [
    {"full_name": "Nguyễn Văn A", "aliases": ["A", "Van A"], "student_code": "SV001", "active": true}
  ]
}
```

**Response** (201): Created members

##### POST `/campaigns/{campaign_id}/import-students` — Bulk Import (Moderator+)

**Request**: Same as add members

#### 3.4 Uploads

##### POST `/uploads` — Upload Receipt

**Content-Type**: `multipart/form-data`

**Form Fields**:
- `file`: Image file (required)
- `uploader_name`: String (required)

**Response** (201):
```json
{
  "id": "uuid",
  "uploader_name": "Nguyễn Văn A",
  "original_filename": "receipt.jpg",
  "status": "pending",
  "created_at": "2026-10-03T15:30:00Z"
}
```

**Errors**:
- 400: Invalid file type/size (TODO: validation)
- 409: Duplicate file (hash match)

##### GET `/uploads/{upload_id}` — Get Upload Status

**Response** (200):
```json
{
  "id": "uuid",
  "uploader_name": "Nguyễn Văn A",
  "original_filename": "receipt.jpg",
  "status": "verified",
  "created_at": "2026-10-03T15:30:00Z",
  "extracted": {
    "transaction_code": "VCB123456",
    "amount": "500000",
    "sender_name": "NGUYEN VAN A",
    "bank_name": "Vietcombank",
    "confidence": "0.98"
  },
  "rejection_reason": null,
  "transaction_id": "uuid"
}
```

#### 3.5 Internal AI (Service-to-Service)

##### POST `/internal/ai/uploads/{upload_id}/result` — Receive AI Extraction Result

**Headers**: `Authorization: Bearer <AI_SERVICE_TOKEN>`, `Idempotency-Key: msg_{message_id}_v{content_version}`

**Request** (`AIResultIn`):
```json
{
  "transaction_code": "VCB123456",
  "amount": "500000",
  "sender_name": "NGUYEN VAN A",
  "bank_name": "Vietcombank",
  "transaction_time": "2026-10-03T10:00:00Z",
  "confidence": "0.98",
  "raw_ocr": "OCR text...",
  "campaign_id": "uuid",  // optional
  "student_id": "uuid",  // optional
  "bank_account_id": "uuid",  // required for credit
  "account_id": "uuid"  // optional
}
```

**Response** (200):
```json
{
  "upload_id": "uuid",
  "status": "verified",
  "transaction_id": "uuid",
  "posted": true,
  "processing_status": "SUCCESS|DUPLICATE|NEEDS_HUMAN_REVIEW|FAILED|AMBIGUOUS|RECALLED",
  "error": "Error message if failed"
}
```

**Processing Status Values**:
- `SUCCESS`: Transaction created
- `DUPLICATE`: Already exists (idempotency or bank tx)
- `NEEDS_HUMAN_REVIEW`: Low confidence, missing fields, campaign mismatch
- `FAILED`: Validation/business rule violation
- `AMBIGUOUS`: Commit status uncertain
- `RECALLED`: Message recalled before processing

#### 3.6 Vision (Service-to-Service)

##### POST `/vision/extract` — Extract Transaction from Image

**Headers**: `Authorization: Bearer <AI_SERVICE_TOKEN>`

**Request**: Multipart with `file` and optional `prompt`

**Response** (200): `AIResultIn` schema

#### 3.7 Health

##### GET `/health` — Health Check

**Response** (200):
```json
{
  "status": "healthy|degraded",
  "database": "ok",
  "supabase": "ok|unreachable",
  "timestamp": "2026-10-03T15:30:00Z"
}
```

### 4. Pagination

**Standard Parameters**:
- `limit`: 1-100 (default 50, max 200 for transactions)
- `offset`: ≥0 (default 0)

**Response Headers** (for list endpoints):
- `X-Total-Count`: Total items
- `X-Page-Count`: Total pages
- `Link`: RFC 5988 pagination links (TODO)

### 5. Idempotency Behavior

| Endpoint | Idempotency-Key Required | Key Format | Duplicate Returns |
|----------|-------------------------|------------|-------------------|
| `POST /fund/credit` | Yes | Client-defined | 200 with existing transaction |
| `POST /fund/debit` | Yes | Client-defined | 200 with existing transaction |
| `POST /fund/revert` | Yes | Client-defined | 200 with existing reversal |
| `POST /internal/ai/...` | Yes | `msg_{message_id}_v{content_version}` | 200 with existing transaction |
| `POST /messages` | No | N/A | N/A (unique per message) |
| `POST /uploads` | No | N/A | 409 on file hash duplicate |

**Key Reuse Rules**:
- Same key + same payload → 200 OK (DUPLICATE)
- Same key + different payload → 409 Conflict (fingerprint mismatch)
- No key → Processed without idempotency (not recommended for financial ops)

### 6. Rate Limiting (TODO Phase 2)

**Planned Limits**:
| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /messages` | 30 | minute |
| `POST /uploads` | 10 | minute |
| `POST /messages/{id}/recall` | 5 | minute |
| `POST /fund/*` | 100 | minute (admin) |
| `/internal/ai/*` | 1000 | minute (service) |

**Response**: 429 with `Retry-After` header

### 7. WebSocket / Realtime (Supabase)

**Channels**:
- `messages:{conversation_id}` — Message create/update
- `worker_status` — Worker online/offline/job changes

**Events**: `INSERT`, `UPDATE`, `DELETE` on respective tables

**Frontend Subscription**:
```javascript
supabase.channel('messages:conv-123')
  .on('postgres_changes', {event: '*', schema: 'public', table: 'messages', filter: 'conversation_id=eq.conv-123'}, handleMessageChange)
  .subscribe()
```

### 8. Versioning

**Strategy**: URL versioning (`/api/v1/...`)
**Current**: v1 (this contract)
**Deprecation**: 6 months notice, parallel run

### 9. OpenAPI Specification

**File**: `openapi.json` (generated from FastAPI)
**Location**: `class-fund-backend-v0.1/class-fund-backend/openapi.json`
**Regenerate**: `python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json`

---

**Contract Status**: ✅ DEFINED — All endpoints documented with request/response schemas, auth requirements, error codes, and idempotency behavior. Ready for Phase 3 (AI), Phase 4 (Frontend), Phase 5 (Admin) integration.
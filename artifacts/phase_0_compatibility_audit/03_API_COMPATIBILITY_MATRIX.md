# PHASE 0 — API COMPATIBILITY MATRIX

## Executive Summary
**Overall: INCOMPATIBLE** — The frontend has **zero API integration**; all data comes from mock state. Backend exposes 33 endpoints across 7 routers. Complete API client layer must be built.

---

## Backend API Endpoints (from openapi.json + route inspection)

| Method | Endpoint | Auth | Request | Response | Router |
|--------|----------|------|---------|----------|--------|
| GET | `/api/v1/health` | None | — | `{}` | health |
| POST | `/api/v1/auth/login` | None | `LoginRequest` | `TokenResponse` | auth |
| POST | `/api/v1/auth/logout` | Bearer | — | `{ok: boolean}` | auth |
| GET | `/api/v1/auth/me` | Bearer | — | `UserOut` | auth |
| GET | `/api/v1/public/fund` | None | — | `{account_id, currency, current_balance, total_income, total_expense}` | public |
| GET | `/api/v1/public/bank-accounts` | None | — | `BankAccount[]` | public |
| GET | `/api/v1/public/campaigns` | None | — | `CampaignOut[]` | public |
| GET | `/api/v1/fund/balance` | Bearer | — | `AccountOut` | fund |
| GET | `/api/v1/fund/transactions` | Bearer | query: account_id, limit, offset | `TransactionOut[]` | fund |
| PUT | `/api/v1/fund/accounts/{account_id}/opening-balance` | Bearer (TREASURER) | `OpeningBalanceIn` | `AccountOut` | fund |
| POST | `/api/v1/fund/bank-accounts` | Bearer (TREASURER) | `BankAccountIn` | `BankAccount` | fund |
| GET | `/api/v1/fund/bank-accounts` | Bearer | — | `BankAccount[]` | fund |
| POST | `/api/v1/fund/credit` | Bearer (TREASURER) + Idempotency-Key | `ManualTransactionIn` | `TransactionOut` | fund |
| POST | `/api/v1/fund/debit` | Bearer (TREASURER) + Idempotency-Key | `ManualTransactionIn` | `TransactionOut` | fund |
| POST | `/api/v1/fund/transactions/{transaction_id}/revert` | Bearer (TREASURER) + Idempotency-Key | `RevertIn` | `TransactionOut` | fund |
| POST | `/api/v1/uploads` | None | multipart: file, uploader_name | `UploadOut` | uploads |
| GET | `/api/v1/uploads/{upload_id}` | None | — | `UploadStatusOut` | uploads |
| GET | `/api/v1/internal/ai/uploads/{upload_id}/file` | AI_SERVICE_KEY | — | File (image) | ai_internal |
| POST | `/api/v1/internal/ai/uploads/{upload_id}/result` | AI_SERVICE_KEY + Idempotency-Key | `AIResultIn` | `{upload_id, status, transaction_id, posted}` | ai_internal |
| POST | `/api/v1/campaigns/students` | Bearer (TREASURER/MODERATOR) | `StudentIn` | `StudentOut` | campaigns |
| POST | `/api/v1/campaigns/students/import` | Bearer (TREASURER/MODERATOR) | `StudentImportIn` | `{created_count, students[]}` | campaigns |
| POST | `/api/v1/campaigns` | Bearer (TREASURER/MODERATOR) | `CampaignIn` | `CampaignOut` | campaigns |
| GET | `/api/v1/campaigns` | None | — | `CampaignOut[]` | campaigns |
| PATCH | `/api/v1/campaigns/{campaign_id}` | Bearer (TREASURER/MODERATOR) | `CampaignIn` | `CampaignOut` | campaigns |
| POST | `/api/v1/campaigns/{campaign_id}/students/{student_id}` | Bearer (TREASURER/MODERATOR) | — | `{id, status}` | campaigns |
| DELETE | `/api/v1/campaigns/{campaign_id}/students/{student_id}` | Bearer (TREASURER/MODERATOR) | — | `{ok: boolean}` | campaigns |
| GET | `/api/v1/campaigns/{campaign_id}/members` | Bearer | — | `{student_id, full_name, status}[]` | campaigns |
| GET | `/api/v1/chat/messages` | Bearer | query: limit, offset | `ChatMessageOut[]` | chat |
| POST | `/api/v1/chat/messages` | Bearer | `ChatMessageIn` | `ChatMessageOut` | chat |

---

## Frontend API Calls: **NONE FOUND**

### Evidence
- Searched all `src/**/*.ts`, `src/**/*.tsx` — zero `fetch`, `axios`, or API client usage
- All data sourced from `AppContext` → `mockDatabase.ts`
- All mutations (`addLedgerEntry`, `revertTransaction`, `sendChatMessage`, etc.) update local React state only

---

## Compatibility Matrix

| Backend Endpoint | Frontend Integration | Status | Notes |
|------------------|---------------------|--------|-------|
| `GET /health` | ❌ None | NOT_IMPLEMENTED | |
| `POST /auth/login` | ❌ None | NOT_IMPLEMENTED | No login UI |
| `POST /auth/logout` | ❌ None | NOT_IMPLEMENTED | No logout |
| `GET /auth/me` | ❌ None | NOT_IMPLEMENTED | No session restoration |
| `GET /public/fund` | ❌ Mock in `PublicFundView` | NOT_IMPLEMENTED | Uses `mockDatabase.balances` |
| `GET /public/bank-accounts` | ❌ Mock in `PublicFundView`/`BankQRView` | NOT_IMPLEMENTED | Uses `MOCK_BANK_ACCOUNT` |
| `GET /public/campaigns` | ❌ Mock in `CampaignView` | NOT_IMPLEMENTED | Uses `mockDatabase.campaign` |
| `GET /fund/balance` | ❌ Mock in `DashboardView` | NOT_IMPLEMENTED | Uses `AppContext.balances` |
| `GET /fund/transactions` | ❌ Mock in `LedgerView` | NOT_IMPLEMENTED | Uses `AppContext.ledgerEntries` |
| `PUT /fund/accounts/.../opening-balance` | ❌ None | NOT_IMPLEMENTED | No UI |
| `POST /fund/bank-accounts` | ❌ None | NOT_IMPLEMENTED | No UI |
| `GET /fund/bank-accounts` | ❌ Mock | NOT_IMPLEMENTED | |
| `POST /fund/credit` | ❌ Mock in `AppContext.addManualExpense` | NOT_IMPLEMENTED | Local state only |
| `POST /fund/debit` | ❌ Mock in `AppContext.addManualExpense` | NOT_IMPLEMENTED | Local state only |
| `POST /fund/transactions/.../revert` | ❌ Mock in `AppContext.revertTransaction` | NOT_IMPLEMENTED | Local state only |
| `POST /uploads` | ❌ Simulated in `UploadReceiptView` | NOT_IMPLEMENTED | `URL.createObjectURL` preview only |
| `GET /uploads/{id}` | ❌ None | NOT_IMPLEMENTED | |
| `GET /internal/ai/uploads/.../file` | ❌ None | NOT_IMPLEMENTED | Worker only |
| `POST /internal/ai/uploads/.../result` | ❌ None | NOT_IMPLEMENTED | Worker only |
| `POST /campaigns/students` | ❌ Mock in `CampaignView` | NOT_IMPLEMENTED | Local `markStudentPaid` |
| `POST /campaigns/students/import` | ❌ None | NOT_IMPLEMENTED | |
| `POST /campaigns` | ❌ Mock `CreateCampaignModal` | NOT_IMPLEMENTED | Local state only |
| `GET /campaigns` | ❌ Mock | NOT_IMPLEMENTED | |
| `PATCH /campaigns/{id}` | ❌ None | NOT_IMPLEMENTED | |
| `POST /campaigns/{id}/students/{student_id}` | ❌ Mock | NOT_IMPLEMENTED | |
| `DELETE /campaigns/{id}/students/{student_id}` | ❌ None | NOT_IMPLEMENTED | |
| `GET /campaigns/{id}/members` | ❌ Mock in `CampaignView` | NOT_IMPLEMENTED | |
| `GET /chat/messages` | ❌ Mock in `ChatView` | NOT_IMPLEMENTED | Uses `AppContext.chatMessages` |
| `POST /chat/messages` | ❌ Mock in `ChatView.handleSend` | NOT_IMPLEMENTED | Local state only |

---

## Data Model Compatibility

### Backend Schemas (Pydantic, snake_case) vs Frontend Types (TypeScript, camelCase)

| Backend Field | Frontend Field | Compatible | Transform Needed |
|---------------|----------------|------------|------------------|
| `transaction_code` | `transaction_code` | ✅ | None (both snake_case in frontend types) |
| `sender_name` | `sender_name` | ✅ | None |
| `uploaded_by` | `uploaded_by` | ✅ | None |
| `created_at` | `created_at` | ✅ | ISO string ↔ ISO string |
| `effective_at` | `effective_at` | ✅ | ISO string ↔ ISO string |
| `opening_balance` | `openingBalance` | ⚠️ | snake_case ↔ camelCase |
| `current_balance` | `currentBalance` | ⚠️ | snake_case ↔ camelCase |
| `total_income` | `totalCredit` | ❌ | Different semantics |
| `total_expense` | `totalDebit` | ❌ | Different semantics |
| `ai_confidence` | `ai_confidence` | ✅ | None |
| `extracted_bank` | `extracted_bank` | ✅ | None |
| `campaign_id` | `campaign_id` | ✅ | None |
| `student_id` | `student_id` | ✅ | None |
| `amount` (Decimal) | `amount` (number) | ⚠️ | Decimal ↔ number (precision) |
| `confidence` (Decimal 0-1) | `confidence` (number 0-100) | ❌ | Scale ×100 |
| `status` (Enum) | `status` (string) | ✅ | Value matches |
| `type` (Enum) | `type` (string) | ✅ | Value matches |
| `source` (Enum) | `source` (string) | ✅ | Value matches |

### Critical Mismatches

1. **Confidence Scale**: Backend `Decimal(0-1)`, Frontend `number(0-100)` — e.g., 0.994 vs 99.4
2. **Amount Type**: Backend `Decimal`, Frontend `number` — VND integers safe but division risky
3. **Date Format**: Backend ISO 8601 with timezone, Frontend `YYYY-MM-DD HH:mm` local
4. **Naming Convention**: Backend API returns snake_case; Frontend types use snake_case (unusual for TS) — actually compatible!
5. **Balance Fields**: Backend `total_income`/`total_expense` vs Frontend `totalCredit`/`totalDebit` — semantic mismatch

---

## Authentication Compatibility

| Aspect | Backend | Frontend | Gap |
|--------|---------|----------|-----|
| **Login** | `POST /auth/login` → JWT | No login UI | Complete |
| **Token Storage** | Client responsibility | No storage | Complete |
| **Authorization Header** | `Authorization: Bearer <jwt>` | No interceptor | Complete |
| **Token Refresh** | Not implemented (60min expiry) | Not implemented | Complete |
| **Logout** | `POST /auth/logout` revokes JTI | No logout UI | Complete |
| **Role Mapping** | `OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC` | Same enum values | ✅ Compatible |
| **CORS** | `http://localhost:3000,5173` | Vite port 3000 | ✅ Compatible |

---

## File Upload Compatibility

| Aspect | Backend | Frontend | Compatible |
|--------|---------|----------|------------|
| **Endpoint** | `POST /uploads` multipart/form-data | `UploadReceiptView` uses `File` + `FormData` | ✅ |
| **Allowed Types** | `image/jpeg`, `image/png`, `image/webp` | `accept="image/*"` | ✅ |
| **Max Size** | 10 MB (configurable) | No client check | ⚠️ |
| **Response** | `UploadOut` (id, uploader_name, filename, status, created_at) | Expects immediate AI result | ❌ |
| **Duplicate Check** | SHA-256 file hash | Simulated client-side | Different layer |

---

## Error Handling Compatibility

| Backend Error Format | Frontend Handling |
|---------------------|-------------------|
| `HTTPException` with `detail` string | No error boundaries |
| 400 Validation Error → `HTTPValidationError` (Pydantic) | No validation display |
| 401 Unauthorized | No redirect to login |
| 403 Forbidden | No UI for insufficient permissions |
| 409 Conflict (duplicate, balance) | No conflict resolution UI |
| 413 Payload Too Large | No file size warning |
| 415 Unsupported Media Type | No file type warning |
| 500 Internal Server Error | No error boundary |

---

## Pagination & Filtering

| Backend | Frontend Expectation |
|---------|---------------------|
| `GET /fund/transactions?limit=50&offset=0` | No pagination UI (shows all mock entries) |
| `GET /chat/messages?limit=50&offset=0` | No pagination (shows all mock messages) |
| No cursor-based pagination | Not needed for current scale |

---

## WebSocket / Realtime

| Backend | Frontend |
|---------|----------|
| No WebSocket endpoints | No WebSocket client |
| Supabase Realtime planned | Supabase Realtime planned |

---

## Classification Summary

| Category | Classification |
|----------|----------------|
| API Contract Coverage | **0/33 endpoints implemented** |
| Authentication Flow | **NOT_IMPLEMENTED** |
| Data Model Mapping | **PARTIALLY_COMPATIBLE** (transformers needed) |
| File Upload | **PARTIALLY_COMPATIBLE** (endpoint compatible, flow different) |
| Error Handling | **NOT_IMPLEMENTED** |
| Realtime | **NOT_IMPLEMENTED** |

---

## Required Frontend API Layer (Minimum)

```typescript
// src/lib/api/client.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) throw new ApiError(res.status, await res.json())
  return res.json()
}

// Typed methods for each endpoint...
```

---

## Confidence Assessment
- **Verified**: Backend endpoints from code + openapi.json; Frontend mock-only from full source scan
- **Partially Verified**: Data model mapping (field-by-field comparison)
- **Assumed**: Vercel deployment will need same CORS updates
- **Not Verified**: Actual network integration, token refresh flow
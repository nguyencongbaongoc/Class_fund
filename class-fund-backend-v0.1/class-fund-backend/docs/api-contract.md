# API contract v0 — frontend ↔ backend ↔ AI

## 1. Financial invariant

Client tuyệt đối không gửi `new_balance`.

Backend tính:

```text
opening_balance + verified CREDIT - verified DEBIT + verified REVERT_SIGN = current_balance
```

## 2. Upload flow

```text
Frontend
  POST /api/v1/uploads (multipart: file + uploader_name)
      ↓
  upload_id + status=PENDING
      ↓
AI service
  GET /api/v1/internal/ai/uploads/{upload_id}/file
  POST /api/v1/internal/ai/uploads/{upload_id}/result
      ↓
Backend validation
  confidence / code / amount / bank / campaign / idempotency / DB uniqueness
      ↓
Ledger transaction
      ↓
Activity event
```

## 3. AI result payload

```json
{
  "transaction_code": "ABC123",
  "amount": 50000,
  "sender_name": "NGUYEN VAN A",
  "bank_name": "Example Bank",
  "transaction_time": "2026-09-27T10:20:00+07:00",
  "confidence": 0.97,
  "raw_ocr": "...",
  "campaign_id": "campaign-uuid-or-null",
  "student_id": "student-uuid-or-null",
  "bank_account_id": "bank-account-uuid",
  "account_id": "fund-account-uuid"
}
```

AI không gửi `ledger_entry`, `balance`, `verified=true` hay `new_balance`.

## 4. Status machine

```text
PENDING -> PROCESSING -> VERIFIED
                      -> NEEDS_REVIEW
                      -> DUPLICATE
                      -> REJECTED
```

`VERIFIED` là điều kiện posting đã qua backend rules. `NEEDS_REVIEW` không được cộng quỹ.

## 5. Financial mutation headers

Manual credit/debit/revert và AI result đều yêu cầu:

```text
Idempotency-Key: <unique-request-key>
```

Retry cùng key + cùng request fingerprint => trả kết quả cũ.

## 6. RBAC

- OWNER_TREASURER: financial mutation, opening balance, bank setup, revert.
- MODERATOR: campaign/student management, moderation UI.
- MEMBER: read authenticated data + chat.
- PUBLIC: public read + receipt upload.

Frontend role UI chỉ là UX; backend vẫn enforce permission.

# AI integration example

AI service không được truy cập database trực tiếp và không được tạo ledger entry.

## 1. Lấy ảnh

```py
import requests

headers = {"X-AI-Service-Key": AI_SERVICE_KEY}
image = requests.get(
    f"{BACKEND}/api/v1/internal/ai/uploads/{upload_id}/file",
    headers=headers,
    timeout=30,
).content
```

## 2. OCR / extraction / matching

AI có thể tạo candidate:

```py
candidate = {
    "transaction_code": "ABC123",
    "amount": 50000,
    "sender_name": "NGUYEN VAN A",
    "bank_name": "Example Bank",
    "transaction_time": "2026-09-27T10:20:00+07:00",
    "confidence": 0.97,
    "raw_ocr": raw_ocr,
    "bank_account_id": bank_account_id,
    "account_id": account_id,
    "campaign_id": campaign_id,
    "student_id": student_id,
}
```

## 3. Gửi candidate về backend

```py
requests.post(
    f"{BACKEND}/api/v1/internal/ai/uploads/{upload_id}/result",
    headers={
        "X-AI-Service-Key": AI_SERVICE_KEY,
        "Idempotency-Key": f"ai-{upload_id}-{model_job_id}",
    },
    json=candidate,
    timeout=30,
)
```

Backend mới quyết định `VERIFIED`, `NEEDS_REVIEW` hoặc `DUPLICATE`.

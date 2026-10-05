# AI Pipeline Contract

**Version**: 1.0
**Date**: 2026-10-04
**Branch**: master

## Overview

This document defines the contract for the AI Pipeline that processes receipt images through OCR/Vision extraction, validation, duplicate detection, and human review before financial posting.

---

## 1. Image Ingestion Contract

### 1.1 Upload Endpoint
```
POST /api/v1/uploads
Content-Type: multipart/form-data

Fields:
- file: binary (image/jpeg, image/png, image/webp)
- uploader_name: string (required, max 120 chars)
```

### 1.2 Validation Rules
| Check | Constraint | Error Code |
|-------|------------|------------|
| MIME Type | image/jpeg, image/png, image/webp | 415 |
| File Size | ≤ 10 MB (configurable) | 413 |
| Filename | Non-empty, sanitized | 422 |
| Image Decoding | Valid image data | 422 |
| Duplicate (SHA-256) | Returns existing upload | 200 (DUPLICATE status) |

### 1.3 Upload Response
```json
{
  "id": "uuid",
  "uploader_name": "string",
  "original_filename": "string",
  "status": "PENDING|DUPLICATE",
  "created_at": "ISO8601"
}
```

---

## 2. Vision Processing Contract

### 2.1 Internal Endpoint
```
POST /internal/vision/process
Headers:
- Idempotency-Key: string (required)
Authorization: Bearer <AI_SERVICE_KEY>

Body:
{
  "upload_id": "uuid",
  "image_data_hex": "hex-encoded image bytes"
}
```

### 2.2 Vision Request Processing Flow
1. Retrieve image from storage (Supabase or local)
2. Compute perceptual hash (pHash) for duplicate detection
3. Call Ollama Vision model (`qwen2.5vl:3b`)
4. If vision fails → OCR fallback → Ollama Text model (`qwen3.5:4b`)
5. Validate output against `VisionExtractionSchema`
6. Store extraction with field confidences
7. Determine processing status

### 2.3 VisionExtractionSchema
```json
{
  "transaction_code": "string|null",
  "amount": "integer|null (VND)",
  "sender_name": "string|null",
  "bank_name": "string|null",
  "transaction_time": "ISO8601|null",
  "confidence": "float [0.0-1.0]",
  "raw_text": "string|null"
}
```

### 2.4 Vision Response
```json
{
  "upload_id": "uuid",
  "status": "PENDING|PROCESSING|NEEDS_REVIEW|VERIFIED|DUPLICATE",
  "extraction": { ... },
  "field_confidences": {
    "transaction_code": 0.9,
    "amount": 0.95,
    "sender_name": 0.85,
    "bank_name": 0.9,
    "transaction_time": 0.7
  },
  "processing_status": "completed|needs_human_review|already_processed|vision_failed",
  "error": "string|null",
  "correlation_id": "string"
}
```

---

## 3. Unified Transaction Schema

### 3.1 ProposedTransaction (Input to Financial Gatekeeper)
```python
class ProposedTransaction:
    upload_id: str
    transaction_code: str
    amount: int  # VND
    sender_name: str
    bank_name: str
    bank_account_id: str  # Matched bank account
    transaction_time: datetime
    confidence: float
    field_confidences: Dict[str, float]
    extraction_method: "vision"|"ocr"|"hybrid"
    source_image_id: str
    currency: "VND"
    campaign_id: Optional[str]
    student_id: Optional[str]
    raw_ocr: Optional[str]
```

### 3.2 Field Confidence Requirements
| Field | Minimum Confidence | Required |
|-------|-------------------|----------|
| transaction_code | 0.7 | Yes |
| amount | 0.7 | Yes |
| sender_name | 0.6 | Yes (for campaign matching) |
| bank_name | 0.6 | Yes |
| transaction_time | 0.5 | No |

---

## 4. Validation Rules

### 4.1 Required Field Validation
```python
def validate_required(extraction: ProposedTransaction) -> List[str]:
    errors = []
    if not extraction.transaction_code:
        errors.append("MISSING_TRANSACTION_CODE")
    if not extraction.amount or extraction.amount <= 0:
        errors.append("MISSING_AMOUNT")
    if not extraction.bank_account_id:
        errors.append("MISSING_BANK_ACCOUNT")
    return errors
```

### 4.2 Cross-Field Consistency
- Amount must be positive integer ≤ 1,000,000,000 VND
- Transaction time must not be > 1 day in future
- Transaction time must not be > 2 years in past
- Bank name must match configured bank_accounts table
- Sender name must match student roster (if campaign)

### 4.3 Confidence Thresholds
| Check | Threshold | Action |
|-------|-----------|--------|
| Overall confidence | < 0.7 | NEEDS_REVIEW |
| Amount confidence | < 0.7 | NEEDS_REVIEW |
| Transaction code confidence | < 0.7 | NEEDS_REVIEW |
| OCR confidence | < 0.5 | NEEDS_REVIEW |

---

## 5. Duplicate Detection Contract

### 5.1 Detection Layers (in order)
1. **File Hash (SHA-256)**: Exact byte-for-byte duplicate
2. **Perceptual Hash (pHash)**: Visual similarity (Hamming distance ≤ 10)
3. **Transaction Identity**: (bank_name, transaction_code) pair
4. **Fuzzy Transaction Reference**: Normalized code similarity

### 5.2 Duplicate Response
```json
{
  "is_duplicate": true,
  "layer": "file_hash|perceptual_hash|transaction_identity|fuzzy",
  "confidence": 1.0,
  "details": { ... },
  "matched_upload_id": "uuid"
}
```

### 5.3 Duplicate Handling
| Layer | Confidence | Action |
|-------|------------|--------|
| file_hash | 1.0 | Mark DUPLICATE, reject |
| perceptual_hash | >0.84 | Mark DUPLICATE, reject |
| transaction_identity | 1.0 | Mark DUPLICATE, reject |
| fuzzy | 0.7-0.9 | Flag as candidate, NEEDS_REVIEW |

---

## 6. Human Review Contract

### 6.1 Review States
```
PENDING → PROCESSING → NEEDS_REVIEW → (APPROVED|REJECTED)
                    ↘ DUPLICATE (terminal)
```

### 6.2 Review Data Structure
```python
class ReviewRecord:
    extraction_id: str
    reviewer_id: str  # User ID
    reviewed_at: datetime
    decision: "APPROVED"|"REJECTED"
    notes: Optional[str]
    modified_fields: Dict[str, Any]  # Fields changed by reviewer
```

### 6.3 Review API (Future)
```
GET    /internal/review/queue          # List pending reviews
GET    /internal/review/{extraction_id} # Get review detail
POST   /internal/review/{extraction_id} # Submit review decision
```

---

## 7. Financial Gatekeeper Contract

### 7.1 Entry Point
```python
verify_and_post_from_ai(
    db: Session,
    upload: Upload,
    extraction: ExtractedTransaction,
    account: Account,
    actor_id: Optional[str],
    idempotency_key: str,
    message_id: Optional[str],
    logical_operation_id: Optional[str],
    attempt_id: Optional[str]
) -> VerifyAndPostResult
```

### 7.2 Idempotency Key Format
```
msg_{message_id}_v{content_version}
```
Where `content_version` = SHA-256(payload)[:8], payload = f"{tx_code}|{amount}|{bank_account_id}"

### 7.3 Result Statuses
| Status | Meaning |
|--------|---------|
| SUCCESS | Posted to ledger |
| DUPLICATE | Already exists, returned existing |
| NEEDS_HUMAN_REVIEW | Below threshold or validation failed |
| FAILED | Permanent error |
| RETRYABLE | Transient error, will retry |
| AMBIGUOUS | Commit may have succeeded |
| RECALLED | Message recalled before posting |

---

## 8. Processing State Machine

### 8.1 Upload States
```mermaid
PENDING → PROCESSING → VERIFIED
    ↓           ↓            ↓
  DUPLICATE  NEEDS_REVIEW  REJECTED
```

### 8.2 Message States
```mermaid
PENDING → PROCESSING → AWAITING_REVIEW → POSTED
    ↓           ↓              ↓            ↓
  RECALLED   RECALLED       RECALLED    RECALLED (with reversal)
    ↓           ↓              ↓            ↓
  (terminal)  (terminal)    (terminal)   REJECTED/FAILED
```

### 8.3 State Transitions
| From | To | Trigger |
|------|-----|---------|
| PENDING | PROCESSING | Worker claims message |
| PROCESSING | NEEDS_REVIEW | Low confidence / validation fail |
| PROCESSING | VERIFIED | High confidence, gatekeeper SUCCESS |
| PROCESSING | DUPLICATE | Duplicate detected |
| NEEDS_REVIEW | VERIFIED | Admin approves |
| NEEDS_REVIEW | REJECTED | Admin rejects |
| ANY | RECALLED | User recalls (before POST) |
| POSTED | RECALLED | User recalls (after POST, creates REVERT) |

---

## 9. Error Handling Contract

### 9.1 Error Categories
| Category | HTTP Code | Retryable |
|----------|-----------|-----------|
| VALIDATION | 422 | No |
| BUSINESS_RULE | 409 | No |
| TRANSIENT | 503 | Yes (exponential backoff) |
| PERMANENT | 500 | No |
| AMBIGUOUS | 500 | Manual intervention |

### 9.2 Ollama Circuit Breaker
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Half-open max calls: 3
- State: CLOSED → OPEN → HALF_OPEN → CLOSED

---

## 10. Monitoring & Observability

### 10.1 Correlation IDs
- Generated at upload: `corr_{uuid[:8]}`
- Propagated through: upload → vision → verification → ledger
- Included in all log entries and API responses

### 10.2 Key Metrics
| Metric | Target |
|--------|--------|
| Vision success rate | > 95% |
| OCR fallback rate | < 10% |
| Average processing time | < 30s |
| Duplicate detection precision | > 99% |
| False positive rate | < 1% |
| Circuit breaker open duration | < 5 min |

---

## 11. Security Contract

### 11.1 Prompt Injection Defense
- All user content (OCR text, vision input) sanitized before model
- Dangerous patterns filtered: ignore previous, disregard, new instructions, system prompt, etc.
- Strict JSON schema validation on model output
- Model never receives authority to call financial functions

### 11.2 Data Flow Security
- Ollama endpoint never exposed publicly
- Service-role Supabase key only on backend
- Recall tokens: 256-bit entropy, SHA-256 hashed in DB
- Idempotency keys include message_id for stable identity

---

## 12. Version Compatibility

| Component | Version |
|-----------|---------|
| OCR Engine | Tesseract 5.x |
| Vision Model | qwen2.5vl:3b |
| Text Model | qwen3.5:4b |
| Extraction Schema | 1.0 |
| Verification Policy | 1.0 |
| Duplicate Detector | 1.0 |

---

## Appendix: Processing Time Budgets

| Stage | Budget |
|-------|--------|
| Image retrieval | 2s |
| Vision inference | 30s |
| OCR fallback | 10s |
| Extraction | 2s |
| Duplicate check | 1s |
| Verification | 5s |
| Ledger posting | 2s |
| **Total (happy path)** | **~42s** |
| **Total (with fallback)** | **~52s** |
# Phase 3.1 Source Gate

**Date**: 2026-10-04  
**Decision**: CLOSED_SOURCE_LEVEL

---

## 1. AI Extraction Pipeline Criteria

### 1.1 Image Validation and Secure Ingestion ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/api/routes/uploads.py:18-49`

```python
@router.post("", response_model=UploadOut, status_code=201)
async def upload_receipt(file: UploadFile = File(...), uploader_name: str = Form(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_MIME:  # image/jpeg, image/png, image/webp
        raise HTTPException(415, "Only JPEG, PNG or WEBP images are accepted")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:  # 10MB default
        raise HTTPException(413, "Image is too large")
    if not uploader_name.strip():
        raise HTTPException(422, "uploader_name is required")
```

**Validation layers**: MIME type (415), file size (413), filename presence (422), SHA-256 deduplication.

---

### 1.2 Ollama Vision Integration ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py`

```python
class OllamaVisionClient:
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client = httpx.Client(timeout=httpx.Timeout(self.config.timeout))
    
    def is_available(self) -> bool:
        response = self.client.get(f"{self.config.base_url}/api/tags", timeout=5)
        return response.status_code == 200
```

**Models configured**: `qwen2.5vl:3b` (vision), `qwen3.5:4b` (text fallback)
**Endpoint**: `POST /internal/vision/process` with `Idempotency-Key` header

---

### 1.3 Text/OCR Fallback Integration ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py:86-107`

```python
if vision_result.error:
    from ai.ocr.service import OCRService
    ocr_service = OCRService()
    try:
        ocr_result = ocr_service.process(image_bytes)
        vision_result = vision_client.extract_with_text_fallback(image_bytes, ocr_result.raw_text, correlation_id)
```

**OCR service**: Multi-strategy preprocessing (default, high_contrast, denoise, sharpen, adaptive_threshold, morphology) with Tesseract engine.

---

### 1.4 Unified Extraction Schema ✅ PASS

**Source**: `ai/contracts.py:90-130` (VerificationResult), `class-fund-backend-v0.1/class-fund-backend/app/models/models.py:146-170` (ExtractedTransaction)

**Fields**: transaction_code, amount, sender_name, bank_name, transaction_time, confidence, field_confidences, extraction_method, source_image_id, currency, raw_ocr, campaign_id, student_id, bank_account_id, account_id

**Field-level confidence**: `field_confidences` JSON column added in migration 0005.

---

### 1.5 Field-Level Confidence ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py:120-127`

```python
field_confidences = {
    "transaction_code": 0.9 if vision_result.transaction_code else 0.0,
    "amount": 0.9 if vision_result.amount else 0.0,
    "sender_name": 0.8 if vision_result.sender_name else 0.0,
    "bank_name": 0.8 if vision_result.bank_name else 0.0,
    "transaction_time": 0.7 if vision_result.transaction_time else 0.0,
}
```

Stored in `ExtractedTransaction.field_confidences` (JSON column, migration 0005).

---

### 1.5 Input Sanitization and Prompt Injection Defense ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py:85-95`

```python
def _sanitize_for_prompt(self, text: str) -> str:
    dangerous_patterns = [
        "ignore previous", "ignore the above", "disregard", "new instructions",
        "system prompt", "you are now", "act as", "pretend to", "roleplay",
        "simulate", "bypass", "override", "jailbreak",
    ]
    sanitized = text
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "[FILTERED]")
    return sanitized[:5000]
```

Also: Strict JSON schema validation (`VisionExtractionSchema`), explicit "ignore instructions" directive in prompts.

---

### 1.6 Validation Before Financial Action ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py:378-421` (`verify_and_post_from_ai`)

```python
def verify_and_post_from_ai(...):
    # Confidence threshold check
    if result.confidence is None or float(result.confidence) < threshold:
        return NEEDS_HUMAN_REVIEW
    # Required fields
    if not result.transaction_code or not result.amount or result.amount <= 0 or not result.bank_account_id:
        return NEEDS_HUMAN_REVIEW
    # Duplicate check with FOR UPDATE
    duplicate = db.execute(select(Transaction).where(...).with_for_update()).scalar_one_or_none()
```

Only this function can post AI-extracted transactions to ledger.

---

### 1.7 Duplicate Detection Integration ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py:72-75`, `ai/duplicate/service.py`

```python
# Vision endpoint computes pHash
perceptual_hash = compute_perceptual_hash(image_bytes)
upload.perceptual_hash = perceptual_hash

# DuplicateDetector.check_all() runs in VerificationService
```

**Three layers**: file_hash (SHA-256), perceptual_hash (pHash), transaction_identity (bank|tx_code)

---

### 1.8 Human Review Routing ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py:402-411`

```python
if vision_result.needs_human_review or vision_result.confidence < 0.7:
    upload.status = UploadStatus.NEEDS_REVIEW
    extraction.status = UploadStatus.NEEDS_REVIEW
    db.commit()
    return VisionProcessResponse(..., processing_status="needs_human_review", ...)
```

Review API endpoints exist at `/internal/review` (see Blocker 3.1.4).

---

## 2. BLOCKER 3.1.3 — Duplicate Detection Persistence

### 2.1 `load_from_database()` Exists ✅ PASS

**Source**: `ai/duplicate/service.py:189-233`

```python
def load_from_database(self, db) -> tuple[bool, Optional[str]]:
    # Loads file hashes, perceptual hashes, transaction identities
    # Returns (success: bool, error_message: Optional[str])
```

---

### 2.2 Worker Startup Integration ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/worker/main.py:35-68`

```python
def startup(self):
    self.reclaim_stale_leases()
    success, error = self._load_duplicate_detection_data()
    if not success:
        self.duplicate_loading_failed = True  # Logs CRITICAL, marks degraded
    else:
        self.duplicate_loading_failed = False
    self.upsert_worker_status("online")
```

**Blocker behavior**: On load failure, `duplicate_loading_failed = True` prevents silent operation.

---

### 2.3 `persist_duplicate_data()` Writes Required Info ✅ PASS

**Source**: `ai/duplicate/service.py:235-254`

```python
def persist_duplicate_data(self, db, image_bytes: bytes, verification: VerificationResult):
    upload = db.execute(select(Upload).where(Upload.id == verification.upload_id)).scalar_one_or_none()
    if upload:
        file_hash = hashlib.sha256(image_bytes).hexdigest()
        phash = self.perceptual_hash_detector.compute_phash(image_bytes)
        upload.file_hash = file_hash
        upload.perceptual_hash = phash
        db.flush()
    self.register(image_bytes, verification)  # Updates in-memory
```

**Called from**: `app/api/routes/vision.py:151-153` after high-confidence extraction.

---

### 2.4 In-Memory/DB Consistency ✅ PASS

**Source**: `ai/duplicate/service.py:224-227`, `253-254`

```python
# load_from_database:
self.file_hash_detector.seen_hashes.update(file_hashes)
self.perceptual_hash_detector.seen_hashes.update(perceptual_hashes)
self.transaction_identity_detector.seen_identities.update(transaction_identities)

# persist_duplicate_data:
self.register(image_bytes, verification)  # Syncs in-memory after DB write
```

---

### 2.5 DB Failure Handling ✅ PASS

**Source**: `ai/duplicate/service.py:232-233`

```python
except Exception as e:
    return False, f"Failed to load duplicate detection data: {e}"
```

**Worker behavior** (`worker/main.py:41-46`): Logs CRITICAL, sets `duplicate_loading_failed = True`, continues in degraded mode.

---

### 2.6 Test Traceability ✅ PASS

**File**: `ai/tests/test_duplicate_persistence.py` (9 tests)

| Test | Criterion |
|------|-----------|
| `test_load_from_empty_database` | Empty DB loads successfully |
| `test_load_persisted_file_hash` | File hashes loaded from uploads |
| `test_load_persisted_perceptual_hash` | pHashes loaded with correct upload_id mapping |
| `test_load_persisted_transaction_identity` | Transaction identities loaded with uppercasing |
| `test_reload_twice_no_duplicates` | Multiple loads don't create duplicates |
| `test_persist_duplicate_data` | Persist and reload works |
| `test_database_failure_handling` | Mock DB failure returns proper error |
| `test_detect_duplicate_after_restart` | Duplicate detected after simulated restart |
| `test_worker_refuses_jobs_when_loading_fails` | Worker handles loading failure |

**All 9 tests PASS** (recorded in test results).

---

## 3. BLOCKER 3.1.4 — Human Review API

### 3.1 Four Endpoints Registered ✅ PASS

**Source**: `class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py`

| Endpoint | Method | Path | Auth |
|----------|--------|------|------|
| List pending | GET | `/internal/review` | OWNER_TREASURER, MODERATOR |
| Get detail | GET | `/internal/review/{extraction_id}` | OWNER_TREASURER, MODERATOR |
| Approve | POST | `/internal/review/{extraction_id}/approve` | OWNER_TREASURER, MODERATOR |
| Reject | POST | `/internal/review/{extraction_id}/reject` | OWNER_TREASURER, MODERATOR |

**Router**: `app/main.py:42` → `app.include_router(review.router, prefix="/api/v1")`

---

### 3.2 Authorization Enforcement ✅ PASS

**Source**: `app/api/routes/review.py:19`

```python
router = APIRouter(prefix="/internal/review", tags=["review-internal"], 
    dependencies=[Depends(require_role(Role.OWNER_TREASURER, Role.MODERATOR))])
```

**Forbidden roles**: MEMBER, PUBLIC (verified in `test_review_api.py::test_authorization_roles`)

---

### 3.3 Invalid Transitions Rejected ✅ PASS

**Source**: `app/api/routes/review.py:135-136, 285-286`

```python
if extraction.status != UploadStatus.NEEDS_REVIEW:
    raise HTTPException(409, f"Extraction is not in NEEDS_REVIEW status (current: {extraction.status.value})")
```

**Test**: `test_review_api.py::test_approve_not_in_needs_review`, `test_reject_not_in_needs_review`

---

### 3.4 Rejection Preserves AI Data ✅ PASS

**Source**: `app/api/routes/review.py:295-301`

```python
extraction.status = UploadStatus.REJECTED
extraction.review_notes = f"Rejected: {body.reason}"
# transaction_code, amount, confidence, field_confidences unchanged
```

**Test**: `test_review_api.py::test_rejection_preserves_evidence` — original_code, original_amount, original_confidence preserved.

---

### 3.5 Approval Uses Authoritative Posting ✅ PASS

**Source**: `app/api/routes/review.py:235-242`

```python
result = verify_and_post_from_ai(
    db, upload, extraction, account=account, actor_id=current_user.id,
    idempotency_key=idempotency_key,
    message_id=message_id,
    logical_operation_id=logical_operation_id,
    attempt_id=attempt_id
)
```

**Test**: `test_review_api.py::test_approval_uses_authoritative_posting_path`

---

### 3.5 Review Decisions Auditable ✅ PASS

**Source**: `app/api/routes/review.py:214-218, 295-301`

```python
# Approve
extraction.reviewed_by = current_user.id
extraction.reviewed_at = datetime.now(timezone.utc)
extraction.review_notes = "Approved by reviewer"

# Reject
extraction.reviewed_by = current_user.id
extraction.reviewed_at = datetime.now(timezone.utc)
extraction.review_notes = f"Rejected: {body.reason}"
```

**Schema**: Migration 0005 adds `reviewed_by`, `reviewed_at`, `review_notes` to `extracted_transactions`.

---

### 3.6 Test Traceability ✅ PASS

**File**: `ai/tests/test_review_api.py` (15 tests)

| Test | Criterion |
|------|-----------|
| `test_approve_requires_confirm` | Confirmation required |
| `test_reject_requires_reason` | Reason required |
| `test_reject_reason_length_validation` | Max 1000 chars |
| `test_approve_not_in_needs_review` | Invalid status rejected |
| `test_reject_not_in_needs_review` | Invalid status rejected |
| `test_approve_already_posted` | Cannot approve posted |
| `test_reject_already_posted` | Cannot reject posted |
| `test_list_pending_reviews_status_filter` | Only NEEDS_REVIEW allowed |
| `test_approve_state_transitions` | Correct transitions |
| `test_reject_state_transitions` | Correct transitions |
| `test_authorization_roles` | Only OWNER_TREASURER, MODERATOR |
| `test_approval_uses_authoritative_posting_path` | Uses verify_and_post_from_ai |
| `test_approval_preserves_idempotency` | Stable idempotency keys |
| `test_rejection_preserves_evidence` | Original AI data preserved |
| `test_no_direct_ledger_write_on_approval` | Uses gatekeeper |

**All 15 tests PASS** (recorded).

---

## 4. Financial Invariant Verification

### 4.1 Gatekeeper Authority ✅ PASS

**Evidence**: `verify_and_post_from_ai()` is the only function that posts AI-extracted transactions. Review API calls this function (line 235-242 in review.py).

**Test**: `test_ai_low_confidence_does_not_post` — low confidence blocked from posting.

---

### 4.2 Idempotency Stability ✅ PASS

**Stable key format**: `msg_{message_id}_v{content_version}` where `content_version = SHA256(payload)[:8]`, payload = `{tx_code}|{amount}|{bank_account_id}`

**Tests**: 7/7 idempotency tests PASS including:
- Same key + same payload → returns existing
- Same key + different payload → 409 Conflict
- Concurrent requests → no double post
- Worker crash recovery → no double post

---

### 4.3 Recall-Before-Post ✅ PASS

**Worker check**: `worker/main.py:143-148`

```python
db.expire(message)
if message.status == MessageStatus.RECALLED.value:
    print(f"Message {message.id} was recalled, skipping")
    return
```

**API check**: `app/api/routes/messages.py:197-199` — 409 if already recalled.

---

### 4.4 Reversal Preserves Original ✅ PASS

**Source**: `app/services/ledger.py:300-375` (`post_revert`)

```python
# Creates REVERT transaction with note: "REVERSAL_OF:{original_type.value};REASON:{reason}"
# Original transaction status → REVERTED (not deleted)
```

**Test**: `test_revert_restores_balance_without_deleting_original`

---

### 4.5 Double Reversal Prevention ✅ PASS

**Source**: `app/services/ledger.py:317-333`

```python
already = db.execute(select(LedgerEntry).where(
    LedgerEntry.original_entry_id == original_entry.id, 
    LedgerEntry.type == LedgerType.REVERT
)).scalar_one_or_none()
if already:
    return FAILED("Transaction has already been reverted")
```

**Test**: `test_double_recall_prevented`

---

### 4.6 Worker Lease & Recovery ✅ PASS

**Atomic claim**: `FOR UPDATE SKIP LOCKED` in `worker/main.py:116-138`
**Stale lease reclaim**: `reclaim_stale_leases()` in `startup()`
**Retry logic**: Exponential backoff (60s, 120s, 240s) after 3 failures → FAILED

---

## Phase 3.1 Source Gate Decision

**Decision**: **CLOSED_SOURCE_LEVEL**

All criteria satisfied with source code evidence and test traceability.
# PHASE 0 — AI / OLLAMA COMPATIBILITY AUDIT

## Executive Summary
**Status: PARTIALLY_COMPATIBLE** — The AI pipeline (OCR, extraction, verification, duplicate detection, matching) is well-architected as a pure Python library with zero HTTP dependencies. However, **Ollama vision models are not integrated** — the pipeline uses Tesseract only. The installed `qwen2.5vl:3b` IS a vision-language model but requires new client code.

---

## 1. OLLAMA ENVIRONMENT VERIFICATION

### Installed Models (Verified via `ollama list`)
```powershell
ollama version is 0.35.0
NAME            ID              SIZE      MODIFIED       
qwen3.5:4b      2a654d98e6fb    3.4 GB    21 minutes ago    
qwen2.5vl:3b    fb90415cde1e    3.2 GB    21 hours ago
```

### Model Analysis

| Model | Type | Vision? | Size | Suitability |
|-------|------|---------|------|-------------|
| `qwen2.5vl:3b` | Vision-Language (vl) | ✅ **YES** | 3.2 GB | **Primary candidate for receipt OCR** |
| `qwen3.5:4b` | Text-only | ❌ No | 3.4 GB | Fallback for text classification |

**Critical Finding**: `qwen2.5vl:3b` **IS a vision-language model** (the "vl" suffix indicates vision-language). The prompt mentioned `ollama3.5:4b` which doesn't exist — the actual model is `qwen3.5:4b` (text-only).

---

## 2. CURRENT AI PIPELINE (Tesseract-Only)

### Architecture (`ai/__init__.py` exports)

```
OCRService (TesseractEngine)
    ↓
ExtractionService (Amount, TransactionCode, Sender, Bank, DateTime extractors)
    ↓
VerificationService (Policy: confidence, required fields, matching, duplicates)
    ↓
VerificationResult (structured output)
```

### OCR Service (`ai/ocr/service.py`)

**Engine**: Tesseract (`pytesseract`) with `vie+eng` languages
**Preprocessing Strategies** (6):
1. `default` — grayscale + resize
2. `high_contrast` — CLAHE
3. `denoise` — Non-local means denoising
4. `sharpen` — Unsharp mask kernel
5. `adaptive_threshold` — Gaussian adaptive threshold
6. `morphology` — Morphological close

**Multi-Strategy**: Tries all strategies, picks highest confidence result
**Output**: `OCRResult` with raw_text, confidence, bounding_boxes, lines, words, engine_version

### Extraction Service (`ai/extraction/service.py`)

**Regex-Based Extractors**:
- **Amount**: VND suffix patterns, "số tiền"/"amount" labels, transfer labels
- **Transaction Code**: Bank-specific patterns (MB, VCB, TCB, BIDV, VPB, ACB, SHB, NAPAS) + generic
- **Sender**: "người gửi"/"sender" labels + Vietnamese name pattern
- **Bank**: Keyword matching for 11 Vietnamese banks + codes
- **DateTime**: Multiple formats (dd/mm/yyyy, yyyy-mm-dd, with/without time)

**Confidence Scoring**: Rule-based with context boosters (e.g., "mã gd" nearby increases tx code confidence)

### Verification Service (`ai/verification/service.py`)

**Policy** (`VerificationPolicy`):
- `min_confidence_threshold`: 0.75
- `require_transaction_code`: True
- `require_amount`: True
- `require_sender_match`: True
- `require_student_match`: True
- `min_ocr_confidence`: 0.5
- `min_extraction_confidence`: 0.6
- `min_matching_confidence`: 0.7

**Risk Flags**:
- `MISSING_TRANSACTION_CODE`, `MISSING_AMOUNT`
- `LOW_IMAGE_QUALITY` (OCR < 0.5)
- `SENDER_MISMATCH` (no student match or low confidence)
- `DUPLICATE_RECEIPT`
- `INCONSISTENT_FIELDS` (extraction confidence < threshold)
- `ABNORMAL_TIMESTAMP` (future >1 day, past >2 years)
- `ABNORMAL_TEXT` (OCR text < 20 chars)

**Status Determination**:
```
DUPLICATE → DUPLICATE
MISSING_TX_CODE + require → NEEDS_REVIEW
MISSING_AMOUNT + require → NEEDS_REVIEW
SENDER_MISMATCH + require → NEEDS_REVIEW
LOW_IMAGE_QUALITY → NEEDS_REVIEW
require_student_match + no match → NEEDS_REVIEW
ABNORMAL_TIMESTAMP → NEEDS_REVIEW
ABNORMAL_TEXT → NEEDS_REVIEW
INCONSISTENT_FIELDS → NEEDS_REVIEW
→ VERIFIED
```

**Confidence Calculation**: Weighted (OCR 20%, Extraction 30%, Matching 30%, Duplicate 20%) minus risk penalties

### Duplicate Detection (`ai/duplicate/service.py`)

**Three Layers**:
1. **File Hash** (SHA-256) — exact duplicate, confidence 1.0
2. **Perceptual Hash** (pHash, DCT-based) — Hamming distance ≤10, confidence 1.0 - distance/64
3. **Transaction Identity** (bank_name + transaction_code) — exact match, confidence 1.0

**In-Memory Only**: `seen_hashes` dicts; `load_existing()` method exists for hydration

### Student Matching (`ai/matching/service.py`)

**Normalization**: Unicode NFD → remove diacritics → lowercase → alphanumeric+space
**Variants**: Reversed name, concatenated, substrings
**Matching**:
1. Exact normalized match (confidence 1.0)
2. Fuzzy (rapidfuzz ratio, threshold 0.8)
3. Alias overlap (SequenceMatcher on variants)

---

## 3. WORKER QUEUE (`ai/worker/queue.py`)

### Celery + Redis Architecture
```python
celery_app = Celery("verification_worker")
broker_url = redis://localhost:6379/0
result_backend = redis://localhost:6379/0
```

**Task**: `process_verification_task(upload_id, image_data_hex, metadata)`
- Updates state: `PROCESSING` → `SUCCESS`/`FAILURE`
- Auto-retry: exponential backoff, max 3 retries
- Timeout: 300s hard, 240s soft

**VerificationTask Base Class**: Lazy-initializes `VerificationService` with empty roster

### Incompatibility with Hybrid Architecture
- ❌ Requires Redis server (not available when PC off)
- ❌ Celery worker must run continuously
- ❌ No Supabase integration
- ✅ Task logic reusable (calls `VerificationService.verify()`)

---

## 4. OLLAMA INTEGRATION GAP

### Current: Zero Ollama Usage
- No `httpx`/`aiohttp` calls to `http://127.0.0.1:11434`
- No vision model integration
- Tesseract is sole OCR engine

### Required: Ollama Vision Client

```python
# NEW: worker/ollama_client.py
import httpx
import base64
from pydantic import BaseModel
from typing import Optional

class OllamaVisionRequest(BaseModel):
    model: str = "qwen2.5vl:3b"
    messages: list[dict]
    format: str = "json"
    options: dict = {"temperature": 0.1}

class OllamaVisionResponse(BaseModel):
    message: dict
    done: bool

async def analyze_receipt(image_bytes: bytes, schema: dict) -> dict:
    """Call Ollama vision model with structured output enforcement."""
    img_b64 = base64.b64encode(image_bytes).decode()
    
    system_prompt = """You are a Vietnamese receipt analyzer.
    Extract: transaction_code, amount (integer VND), sender_name, bank_name, confidence (0-1).
    Return ONLY valid JSON matching the schema."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Analyze this receipt image", "images": [img_b64]}
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/chat",
            json=OllamaVisionRequest(messages=messages).model_dump()
        )
        response.raise_for_status()
        result = OllamaVisionResponse(**response.json())
        return parse_json_from_markdown(result.message.get("content", "{}"))
```

### Integration Points

| Current | With Ollama |
|---------|-------------|
| `OCRService.process()` → `OCRResult` | `OllamaVisionClient.analyze()` → structured dict |
| `ExtractionService.extract_all()` | **Replace** with direct Ollama structured output |
| `VerificationService.verify()` | Keep — validates Ollama output |
| Confidence from Tesseract | Confidence from Ollama + validation |

### Recommended: Hybrid OCR
1. **Primary**: Ollama vision (`qwen2.5vl:3b`) for structured extraction
2. **Fallback**: Tesseract multi-strategy if Ollama fails/times out
3. **Validation**: `VerificationService` validates either source

---

## 5. BACKEND INTEGRATION COMPATIBILITY

### AI → Backend Contract (`app/schemas/schemas.py:97-108`)

```python
class AIResultIn(BaseModel):
    transaction_code: str | None = None
    amount: Decimal | None = None
    sender_name: str | None = None
    bank_name: str | None = None
    transaction_time: datetime | None = None
    confidence: Decimal = Field(ge=0, le=1)
    raw_ocr: str | None = None
    campaign_id: str | None = None
    student_id: str | None = None
    bank_account_id: str | None = None
    account_id: str | None = None
```

### AI VerificationResult → AIResultIn Mapping

| VerificationResult | AIResultIn | Compatible |
|-------------------|------------|------------|
| `transaction_code` | `transaction_code` | ✅ |
| `amount` (int) | `amount` (Decimal) | ✅ |
| `sender_name` | `sender_name` | ✅ |
| `bank_name` | `bank_name` | ✅ |
| `transaction_time` | `transaction_time` | ✅ |
| `confidence` (float 0-1) | `confidence` (Decimal 0-1) | ✅ |
| `evidence["ocr"]` | `raw_ocr` | ✅ |
| `campaign_id` | `campaign_id` | ✅ |
| `student_id` | `student_id` | ✅ |
| `bank_account_id` (from bank match) | `bank_account_id` | ⚠️ Need mapping |
| `account_id` | `account_id` | ⚠️ Worker must provide |

**Gap**: `bank_account_id` requires matching extracted bank name to `bank_accounts` table.

---

## 6. CONFIDENCE THRESHOLD ALIGNMENT

| Component | Threshold | Configurable |
|-----------|-----------|--------------|
| Backend `AI_CONFIDENCE_THRESHOLD` | 0.90 | `.env` |
| AI `VerificationPolicy.min_confidence_threshold` | 0.75 | Code |
| AI `min_ocr_confidence` | 0.5 | Code |
| AI `min_extraction_confidence` | 0.6 | Code |

**Misalignment**: Backend requires 0.90, AI policy defaults to 0.75.
**Fix**: Align AI policy to 0.90 or make configurable via env.

---

## 6. VIETNAMESE RECEIPT HANDLING

### Current Capabilities
- Tesseract `vie+eng` language pack
- Vietnamese bank name keywords (11 banks)
- Vietnamese sender name patterns (with diacritics)
- Vietnamese date formats (dd/mm/yyyy)
- Amount patterns with VND/đ suffixes

### Ollama `qwen2.5vl:3b` Capabilities (Unverified)
- ✅ Vision-language model
- ✅ Multilingual (Chinese/English focus, Vietnamese unknown)
- ⚠️ Vietnamese receipt accuracy **untested**
- ⚠️ Structured output reliability **untested**
- ⚠️ Timeout behavior **untested**

### Required Validation
```python
# Test with 20+ real Vietnamese receipts
test_cases = [
    "vietcombank_receipt.jpg",
    "mbbank_receipt.jpg", 
    "techcombank_receipt.jpg",
    # ... various banks, amounts, formats
]

for img_path in test_cases:
    result = await ollama_client.analyze_receipt(img_path)
    verify_fields(result)
    measure_confidence_calibration()
```

---

## 7. COMPATIBILITY MATRIX

| Component | Current | Ollama-Ready | Effort |
|-----------|---------|--------------|--------|
| OCR Engine | Tesseract | Replace/Wrap | Medium |
| Extraction | Regex | Replace (Ollama structured) | Medium |
| Verification | Policy-based | Keep (validates Ollama) | None |
| Duplicate Detection | 3-layer in-memory | Persist to Supabase | Medium |
| Student Matching | RapidFuzz | Keep | None |
| Worker Queue | Celery/Redis | Replace with Supabase polling | High |
| Backend Contract | `AIResultIn` | Compatible | None |
| Confidence Threshold | 0.75 vs 0.90 | Align config | Low |

---

## 8. OLLAMA MODEL COMPATIBILITY VERDICT

| Model | Available | Vision | Structured Output | Vietnamese | Verdict |
|-------|-----------|--------|-------------------|------------|---------|
| `qwen2.5vl:3b` | ✅ Yes | ✅ Yes | ✅ Via `format=json` | ⚠️ Unknown | **USE WITH VALIDATION** |
| `qwen3.5:4b` | ✅ Yes | ❌ No | ✅ Good | ✅ Good | Text fallback only |

**Critical**: Do not assume `qwen2.5vl:3b` works for Vietnamese receipts without empirical testing.

---

## 9. REQUIRED NEW CODE FOR OLLAMA INTEGRATION

### Priority 1: Worker Core
1. `worker/ollama_client.py` — Async client with timeout, retry, JSON schema enforcement
2. `worker/vision_extractor.py` — Wraps Ollama, falls back to Tesseract
3. `worker/supabase_storage.py` — Download receipt from Supabase Storage
4. `worker/duplicate_persister.py` — Persist hashes to Supabase

### Priority 2: Pipeline Integration
1. Modify `VerificationService.verify()` to accept pre-extracted data (from Ollama)
2. Add `OllamaExtractionSource` to evidence tracking
3. Align confidence thresholds (0.90)

### Priority 3: Testing
1. Vietnamese receipt test suite (50+ images)
2. Confidence calibration curves
3. Failure mode analysis (blur, glare, partial receipt)

---

## 10. SECURITY CONSIDERATIONS

### Ollama Attack Surface
- **Local only**: `127.0.0.1:11434` — no network exposure
- **No authentication** on Ollama API — relies on localhost binding
- **Model manipulation**: Not applicable (read-only inference)

### AI Output Validation (Defense in Depth)
1. **Structured output enforcement** — `format=json` + schema validation
2. **Confidence threshold** — Backend enforces 0.90
3. **Required fields** — Backend validates transaction_code, amount, bank_account_id
4. **Duplicate check** — Backend unique constraint
5. **Campaign validation** — Amount must match, student unpaid
6. **Admin review** — Low confidence → human review

---

## 11. CONFIDENCE ASSESSMENT

- **Verified**: AI pipeline code, Tesseract integration, verification logic, duplicate detection, matching, worker queue structure
- **Verified**: Ollama models installed (`qwen2.5vl:3b` vision, `qwen3.5:4b` text)
- **Partially Verified**: Ollama API compatibility (standard `/api/chat` with `images` and `format=json`)
- **Assumed**: `qwen2.5vl:3b` Vietnamese receipt capability
- **Not Verified**: Actual vision model accuracy, structured output reliability, timeout behavior, Vietnamese language quality
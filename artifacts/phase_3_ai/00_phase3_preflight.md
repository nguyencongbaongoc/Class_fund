# 00_PHASE3_PREFLIGHT.md

## Phase 3 AI Pipeline — Preflight Baseline Assessment

**Date**: 2026-10-03  
**Agent**: Ngọc (AI Engineer)  
**Branch**: phase-3-ai  
**Repository**: CLASS_FUND_WEB / class-fund-backend-v0.1

---

## 1. Executive Summary

This document establishes the **actual baseline** for Phase 3 AI Pipeline implementation by auditing:
- Current Ollama client implementation (`app/services/ollama_client.py`)
- Current AI pipeline in `ai/` package (Tesseract-based)
- Backend vision endpoint (`app/api/routes/vision.py`)
- Phase 1.2 completion report and remaining gaps
- Contract compatibility with Phase 2

**Verdict**: Significant implementation exists but **not production-ready**. Key gaps:
- Ollama vision integration implemented but **UNVERIFIED** (no accuracy measurement)
- AI pipeline still Tesseract-primary; Ollama is alternative path
- No unified extraction schema versioned across both pipelines
- Confidence thresholds misaligned (AI: 0.75, Backend: 0.90)
- No evaluation dataset or measured metrics
- Duplicate detection in-memory only, not persisted

---

## 2. Current State Inventory

### 2.1 Ollama Vision Client (`app/services/ollama_client.py`)

| Aspect | Status | Details |
|--------|--------|---------|
| **Config** | ✅ Implemented | `OllamaConfig` with env vars: base_url, vision_model, text_model, timeout, retries |
| **Model Availability Check** | ✅ Implemented | `is_available()`, `list_models()` |
| **Vision Extraction** | ✅ Implemented | `extract_from_image()` with JSON schema validation |
| **Text Fallback** | ✅ Implemented | `extract_with_text_fallback()` using OCR text |
| **Structured Output** | ✅ Implemented | `VisionExtractionSchema` (Pydantic) |
| **Retry Logic** | ✅ Implemented | 3 retries with exponential backoff |
| **Timeout** | ✅ Implemented | 60s default, configurable |
| **Error Handling** | ✅ Implemented | Returns `VisionResult` with error, needs_human_review |
| **Global Instance** | ✅ Implemented | `get_vision_client()` singleton |

**Fields Extracted**: `transaction_code`, `amount`, `sender_name`, `bank_name`, `transaction_time`, `confidence`, `raw_text`, `needs_human_review`

**Confidence Threshold**: Hardcoded 0.7 for human review trigger

**Gap**: No field-level confidence, no schema versioning, no model metadata in output

### 2.2 Vision Endpoint (`app/api/routes/vision.py`)

| Aspect | Status | Details |
|--------|--------|---------|
| **Endpoint** | ✅ Implemented | `POST /internal/vision/process` |
| **Auth** | ✅ Implemented | `require_ai_service` dependency |
| **Idempotency** | ✅ Implemented | `Idempotency-Key` header required |
| **Image Retrieval** | ✅ Implemented | Supabase + local storage fallback |
| **Vision Processing** | ✅ Implemented | Calls `get_vision_client().extract_from_image()` |
| **Extraction Persistence** | ✅ Implemented | Creates/updates `ExtractedTransaction` |
| **Low Confidence Handling** | ✅ Implemented | Marks `NEEDS_REVIEW` if confidence < 0.7 |
| **Verification Integration** | ✅ Implemented | Calls `verify_and_post_from_ai()` for high confidence |

**Gap**: Uses hardcoded 0.7 threshold instead of configurable policy; no field-level validation before verification

### 2.3 AI Pipeline (`ai/` package) — Tesseract-Based

| Component | File | Status |
|-----------|------|--------|
| **OCR Service** | `ai/ocr/service.py` | ✅ Multi-strategy Tesseract (6 strategies) |
| **Extraction Service** | `ai/extraction/service.py` | ✅ Regex extractors (Amount, TxCode, Sender, Bank, DateTime) |
| **Verification Service** | `ai/verification/service.py` | ✅ Policy-based with risk flags |
| **Duplicate Detection** | `ai/duplicate/service.py` | ✅ 3-layer (file hash, pHash, transaction identity) |
| **Student Matching** | `ai/matching/service.py` | ✅ RapidFuzz + alias variants |
| **Worker Queue** | `ai/worker/queue.py` | ✅ Celery/Redis (incompatible with hybrid) |

**Contracts** (`ai/contracts.py`): Pydantic models for all intermediate types

**Gap**: This pipeline is **not connected** to backend vision endpoint; separate code paths

### 2.4 Backend Financial Gatekeeper (`app/services/ledger.py`)

| Function | Status | Key Behavior |
|----------|--------|--------------|
| `verify_and_post_from_ai()` | ✅ Preserved | Enforces confidence ≥ threshold (0.90 from settings) |
| `post_transaction()` | ✅ Preserved | Idempotency + duplicate prevention |
| `post_revert()` | ✅ Preserved | Authorization via recall tokens |

**Confidence Threshold**: Backend reads `ai_confidence_threshold` from settings (default 0.90)

**Gap**: AI pipeline uses 0.75; Ollama client uses 0.7 — **three different thresholds**

### 2.5 Phase 1.2 Completion Artifacts Review

From `17_PHASE_1_2_FINAL_REPORT.md` and `16_REMAINING_GAPS_AND_EXTERNAL_DEPENDENCIES.md`:

| Workstream G (Vision Adapter) | Status |
|-------------------------------|--------|
| Ollama client | ✅ IMPLEMENTED |
| Vision extraction | ✅ IMPLEMENTED |
| Text fallback | ✅ IMPLEMENTED |
| JSON schema validation | ✅ IMPLEMENTED |
| Vision endpoint | ✅ IMPLEMENTED |
| Human review trigger | ✅ IMPLEMENTED |
| Offline handling | ✅ IMPLEMENTED |
| **Unit tests** | ⏳ PENDING |
| **Model accuracy verification** | ⏳ UNVERIFIED |

**Critical**: Vision adapter marked **UNVERIFIED** for accuracy — no measured dataset exists

---

## 3. Contract Compatibility Analysis

### 3.1 Backend ↔ AI Contract (`app/schemas/schemas.py`)

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

### 3.2 Ollama VisionResult → AIResultIn Mapping

| VisionResult | AIResultIn | Compatible |
|--------------|------------|------------|
| `transaction_code` | `transaction_code` | ✅ |
| `amount` (int) | `amount` (Decimal) | ✅ |
| `sender_name` | `sender_name` | ✅ |
| `bank_name` | `bank_name` | ✅ |
| `transaction_time` (str) | `transaction_time` (datetime) | ⚠️ Parse needed |
| `confidence` (float) | `confidence` (Decimal) | ✅ |
| `raw_text` | `raw_ocr` | ✅ |
| — | `campaign_id` | ❌ Not in vision output |
| — | `student_id` | ❌ Not in vision output |
| — | `bank_account_id` | ❌ Requires bank→account mapping |
| — | `account_id` | ❌ Worker must provide |

### 3.3 AI Pipeline VerificationResult → AIResultIn Mapping

| VerificationResult | AIResultIn | Compatible |
|--------------------|------------|------------|
| `transaction_code` | `transaction_code` | ✅ |
| `amount` (int) | `amount` (Decimal) | ✅ |
| `sender_name` | `sender_name` | ✅ |
| `bank_name` | `bank_name` | ✅ |
| `transaction_time` (datetime) | `transaction_time` (datetime) | ✅ |
| `confidence` (float) | `confidence` (Decimal) | ✅ |
| `evidence["ocr"]` | `raw_ocr` | ✅ |
| `student_id` | `student_id` | ✅ |
| — | `campaign_id` | ❌ Not in result |
| — | `bank_account_id` | ❌ Need mapping |
| — | `account_id` | ❌ Worker provides |

---

## 4. Gap Analysis for Phase 3 Scope

### 4.1 Must Implement (Phase 3 Responsibility)

| Gap | Priority | Description |
|-----|----------|-------------|
| **Unified Extraction Schema** | P0 | Single versioned schema for both Ollama and Tesseract outputs |
| **Field-Level Confidence** | P0 | Per-field confidence scores, not just overall |
| **Configurable Confidence Thresholds** | P0 | Align AI (0.75), Ollama (0.7), Backend (0.90) via single config |
| **Schema Versioning** | P0 | `schema_version` in all outputs for forward compatibility |
| **Image Ingestion Validation** | P0 | MIME, size, dimensions, corruption, blur, orientation, duplicate hash |
| **Ollama Model Management** | P0 | Health checks, model listing, warmup, fallback routing |
| **Evaluation Dataset** | P0 | Ground truth dataset for accuracy measurement |
| **Comprehensive Test Suite** | P0 | All test cases from Phase 3 spec §7 |
| **Persisted Duplicate Detection** | P1 | Supabase persistence for hash/identity databases |
| **Human Review Queue Integration** | P1 | Structured handoff to human review workflow |
| **Prompt Injection Defense** | P1 | Sanitize/validate model outputs |
| **Model Metadata in Output** | P1 | Model name, version, processing time in every result |

### 4.2 Out of Phase 3 Scope (Phase 2/4/5)

| Item | Owner |
|------|-------|
| Financial ledger posting | Minh (Phase 2) |
| Transaction posting API | Minh (Phase 2) |
| Persistent worker deployment | Minh (Phase 2) |
| Guest Chat UI | Hải (Phase 4) |
| Admin Dashboard | Hải (Phase 5) |
| Supabase RLS enforcement | Phase 2 |
| End-to-end integration | Phase 6+ |

---

## 5. Environment Verification

### 5.1 Ollama Models (Verified Installed)

```powershell
ollama list
NAME            ID              SIZE      MODIFIED       
qwen3.5:4b      2a654d98e6fb    3.4 GB    21 minutes ago    
qwen2.5vl:3b    fb90415cde1e    3.2 GB    21 hours ago
```

- `qwen2.5vl:3b` — Vision-Language model (3.2 GB) — **Primary for receipt OCR**
- `qwen3.5:4b` — Text-only model (3.4 GB) — Fallback for text classification

### 5.2 Ollama Endpoint

- Default: `http://127.0.0.1:11434`
- Not exposed to Internet (security requirement)
- No authentication on local endpoint

### 5.3 Backend Test Status

```bash
cd class-fund-backend-v0.1/class-fund-backend
python -m pytest tests/ -v
# 20 passed, 1 warning in 1.21s
```

All financial core, idempotency, and recall tests pass.

### 5.4 AI Package Tests

```bash
cd CLASS_FUND_WEB
python -m pytest ai/tests/ -v
```

Need to verify current test status.

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ollama vision model accuracy unknown for Vietnamese receipts | High | High | Build evaluation dataset; measure before production |
| Confidence threshold misalignment causes false accepts/rejects | High | High | Unify to single configurable threshold (0.90) |
| Tesseract and Ollama produce different field sets | Medium | Medium | Define unified schema with all fields; null for missing |
| Duplicate detection in-memory only — lost on restart | Medium | High | Persist to Supabase in Phase 3 |
| No prompt injection defense on vision model | Medium | High | Output schema validation; sanitize raw_text |
| Schema evolution breaks Phase 2/4 integration | Low | High | Versioned schema; backward compatibility tests |

---

## 7. Phase 3 Entry Confirmation

**Baseline Confirmed**: 
- ✅ Ollama client implemented and tested for availability
- ✅ Vision endpoint implemented with idempotency
- ✅ AI pipeline (Tesseract) fully functional with tests
- ✅ Financial gatekeeper preserved and tested
- ❌ **No unified schema** — must create
- ❌ **No evaluation dataset** — must create
- ❌ **No measured accuracy** — must measure
- ❌ **Threshold misalignment** — must fix

**Ready to proceed** with Phase 3 implementation on `phase-3-ai` branch.

---

## 8. Files to Create/Modify (Phase 3 Scope)

### New Files (AI Pipeline Core)
- `ai/schema/v1/extraction_schema.py` — Unified versioned schema
- `ai/schema/v1/__init__.py`
- `ai/ingestion/image_validator.py` — Image quality validation
- `ai/ingestion/__init__.py`
- `ai/ollama/manager.py` — Model management, health checks
- `ai/ollama/__init__.py`
- `ai/verification/engine.py` — Unified verification engine
- `ai/evaluation/dataset.py` — Evaluation dataset loader
- `ai/evaluation/runner.py` — Evaluation runner
- `ai/evaluation/__init__.py`

### Modified Files
- `ai/contracts.py` — Align with unified schema
- `ai/verification/service.py` — Use unified schema, configurable thresholds
- `ai/extraction/service.py` — Output unified schema
- `app/services/ollama_client.py` — Output unified schema, field confidence
- `app/api/routes/vision.py` — Use unified threshold config

### Test Files
- `ai/tests/test_image_ingestion.py`
- `ai/tests/test_ollama_integration.py`
- `ai/tests/test_unified_schema.py`
- `ai/tests/test_verification_engine.py`
- `ai/tests/test_evaluation.py`

### Artifact Files (This Directory)
- All 14 artifacts listed in todo list

---

## 9. Commit Hash Baseline

```bash
# To be filled after first commit on phase-3-ai branch
git log --oneline -1
```

---

*End of Preflight Assessment*
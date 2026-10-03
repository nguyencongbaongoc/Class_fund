# 14_PHASE3_HANDOFF.md

## Phase 3 AI Pipeline — Handoff Document

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Branch**: phase-3-ai  
**Status**: DESIGN COMPLETE — IMPLEMENTATION PENDING

---

## 1. Phase 3 Summary

### 1.1 Scope Delivered

Phase 3 designed the complete AI pipeline for receipt processing:

| Component | Status | Artifact |
|-----------|--------|----------|
| Image Ingestion Pipeline | ✅ Designed | `02_image_ingestion.md` |
| Ollama Model Configuration | ✅ Designed | `03_ollama_model_configuration.md` |
| OCR Pipeline (Tesseract Fallback) | ✅ Designed | `04_ocr_pipeline.md` |
| Unified Extraction Schema v1.0.0 | ✅ Designed | `05_extraction_schema.md` |
| Verification Engine | ✅ Designed | `06_verification_engine.md` |
| Confidence Scoring & Human Review | ✅ Designed | `07_confidence_and_human_review.md` |
| Duplicate Candidate Detection | ✅ Designed | `08_duplicate_candidate_detection.md` |
| Evaluation Dataset Design | ✅ Designed | `09_evaluation_dataset.md` |
| Evaluation Results Template | ✅ Created | `10_evaluation_results.md` |
| Test Plan | ✅ Created | `11_test_plan.md` |
| Test Results Template | ✅ Created | `12_test_results.md` |
| Model Limitations | ✅ Documented | `13_model_limitations.md` |

### 1.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Unified schema for all paths** | Single contract for Ollama Vision, Ollama Text, Tesseract |
| **Field-level confidence** | Enables granular thresholding and calibration |
| **AI proposes, Backend decides** | Financial gatekeeper preserved (Phase 2) |
| **Four-layer duplicate detection** | Defense in depth: file hash, pHash, tx identity, fuzzy |
| **Configurable thresholds** | Single source of truth, env-overrideable |
| **Calibration from evaluation data** | Confidence scores reflect actual accuracy |
| **Prompt injection detection** | Defense in depth for model output |
| **Supabase-persisted duplicate state** | Survives worker restarts, works across workers |
| **Async Ollama client with circuit breaker** | Resilience to model/server failures |
| **Tesseract multi-strategy fallback** | Graceful degradation when Ollama unavailable |

---

## 2. Files Created/Modified

### 2.1 New Artifacts (14 files in `artifacts/phase_3_ai/`)

```
artifacts/phase_3_ai/
├── 00_phase3_preflight.md           # Baseline assessment
├── 01_ai_architecture.md            # Overall architecture
├── 02_image_ingestion.md            # Image validation & hashing
├── 03_ollama_model_configuration.md # Ollama client & management
├── 04_ocr_pipeline.md               # Tesseract + regex fallback
├── 05_extraction_schema.md          # Unified schema v1.0.0
├── 06_verification_engine.md        # Validation & risk flags
├── 07_confidence_and_human_review.md # Confidence & review queue
├── 08_duplicate_candidate_detection.md # 4-layer duplicate detection
├── 09_evaluation_dataset.md         # Dataset design (500 receipts)
├── 10_evaluation_results.md         # Results template
├── 11_test_plan.md                  # Comprehensive test plan
├── 12_test_results.md               # Results template
├── 13_model_limitations.md          # Honest limitations
└── 14_phase3_handoff.md             # This document
```

### 2.2 New Implementation Files (to be created)

```
ai/
├── schema/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── extraction_schema.py     # UnifiedExtractionResult, FieldConfidence, etc.
│   │   ├── json_schema.json         # JSON Schema for external consumers
│   │   └── migration.py             # Version migration utilities
│   └── __init__.py                  # Re-exports v1 as current
├── ingestion/
│   ├── __init__.py
│   ├── image_validator.py           # ImageIngestionService
│   ├── validators/
│   ├── hashing.py                   # File hash + pHash
│   ├── normalization.py             # Orientation, color space
│   └── config.py                    # IngestionConfig
├── ollama/
│   ├── __init__.py
│   ├── config.py                    # OllamaConfig
│   ├── manager.py                   # OllamaModelManager
│   ├── circuit_breaker.py           # CircuitBreaker
│   ├── prompts.py                   # Prompt templates
│   ├── schemas.py                   # VisionExtractionSchema, OllamaExtraction
│   ├── client.py                    # Low-level HTTP client
│   └── errors.py                    # Exception hierarchy
├── pipeline/
│   ├── __init__.py
│   ├── ocr_pipeline.py              # Orchestrates OCR + Extraction + Adapter
│   ├── schema_adapter.py            # Legacy → Unified mapping
│   └── config.py                    # OCRPipelineConfig
├── verification/
│   ├── engine.py                    # UnifiedVerificationEngine
│   ├── policy.py                    # VerificationPolicy, RiskFlag, VerificationStatus
│   ├── validators/
│   ├── confidence.py                # Confidence calculation
│   ├── status.py                    # Status determination
│   └── __init__.py
├── confidence/
│   ├── __init__.py
│   ├── calculator.py                # Overall confidence calculation
│   ├── calibration.py               # Calibration curves
│   ├── thresholds.py                # ConfidenceThresholds
│   ├── routing.py                   # RoutingDecision logic
│   └── explanation.py               # ConfidenceExplanation
├── duplicate/
│   ├── __init__.py
│   ├── detector.py                  # DuplicateCandidateDetector
│   ├── file_hash.py                 # FileHashDetector
│   ├── perceptual_hash.py           # PerceptualHashDetector
│   ├── transaction_identity.py      # TransactionIdentityDetector
│   ├── fuzzy.py                     # FuzzyTransactionDetector
│   ├── config.py                    # DuplicateDetectorConfig
│   └── models.py                    # DuplicateCandidate, DuplicateLayer
├── review/
│   ├── __init__.py
│   ├── queue.py                     # HumanReviewQueue
│   ├── contracts.py                 # ReviewRequest, ReviewDecision
│   ├── summary.py                   # ExtractionSummary, RiskSummary
│   └── ui_data.py                   # ReviewImageData, FieldReviewItem
└── evaluation/
    ├── __init__.py
    ├── dataset.py                   # GroundTruth, DatasetLoader
    ├── metrics.py                   # Metric computation
    ├── calibration.py               # Calibration fitting
    ├── runner.py                    # EvaluationRunner
    ├── reporter.py                  # Report generation
    ├── regression.py                # Regression detection
    └── synthetic.py                 # Synthetic data generation
```

### 2.3 Existing Files to Modify

| File | Changes Needed |
|------|----------------|
| `ai/contracts.py` | Align with unified schema v1; add schema_version |
| `ai/verification/service.py` | Replace with UnifiedVerificationEngine; use configurable thresholds |
| `ai/extraction/service.py` | Output UnifiedExtractionResult via schema adapter |
| `ai/ocr/service.py` | Keep as-is; used by OCRPipeline |
| `app/services/ollama_client.py` | Replace with OllamaModelManager; output unified schema |
| `app/api/routes/vision.py` | Use unified thresholds; return unified schema |
| `app/schemas/schemas.py` | Verify AIResultIn compatibility (no changes needed) |

---

## 3. Model Names & Versions

| Model | Name | Version/Digest | Purpose |
|-------|------|----------------|---------|
| Vision | `qwen2.5vl:3b` | sha256:fb90415cde1e... | Primary receipt OCR |
| Text Fallback | `qwen3.5:4b` | sha256:2a654d98e6fb... | Text classification fallback |
| OCR Engine | Tesseract | 5.x | Fallback OCR |
| Language Pack | `vie+eng` | - | Vietnamese + English |

---

## 4. Extraction Schema Version

**Schema Version**: `1.0.0`

Key features:
- All fields optional with `FieldConfidence` wrapper
- Per-field confidence + evidence + source attribution
- Model metadata for traceability
- Explicit null semantics (not detected / unreadable / not applicable)
- Flat `field_confidence` map for easy thresholding
- `needs_human_review` flag computed from thresholds

---

## 5. API Contract Dependencies

### 5.1 Backend Contract (Phase 2) — `app/schemas/schemas.py:AIResultIn`

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

**Mapping from UnifiedExtractionResult**: Implemented in `to_ai_result_in()` function (see `05_extraction_schema.md`)

### 5.2 Human Review Contract (Phase 4/5)

```python
class HumanReviewRequest(BaseModel):
    review_id: UUID
    upload_id: UUID
    verification_result: VerificationResult
    image_url: str
    priority: Literal["high", "normal", "low"]
    # ... see 07_confidence_and_human_review.md
```

### 5.3 Vision API Endpoint (Phase 2) — `app/api/routes/vision.py`

```
POST /internal/vision/process
Headers: Idempotency-Key
Body: { upload_id, image_data_hex }
Response: VisionProcessResponse
```

---

## 6. Evaluation Dataset

| Metric | Status |
|--------|--------|
| **Size** | 500 real Vietnamese receipts (design target) |
| **Split** | Train: 350, Val: 75, Test: 75 |
| **Stratification** | 12 banks × 6 amount ranges × 4 quality × 4 formats |
| **Ground Truth** | 2x annotation + verification |
| **Collection** | ❌ NOT STARTED |
| **Annotations** | ❌ NOT STARTED |
| **Calibration Curves** | ❌ NOT FITTED |
| **Test Set Metrics** | ❌ NOT MEASURED |
| **Regression Baseline** | ❌ NOT ESTABLISHED |

**Critical**: Phase 3 cannot be declared COMPLETE until evaluation dataset is collected and metrics meet targets.

---

## 7. Metrics Targets (Required for Phase 3 Complete)

### 7.1 Accuracy Targets (Ollama Vision Path)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Amount Exact Match | ≥95% | Test set (75 samples) |
| Transaction Code Exact Match | ≥90% | Test set |
| Transaction Date Exact Match | ≥90% | Test set |
| Bank Name Match | ≥95% | Test set |
| Sender Name F1 | ≥85% | Test set |
| Full Record Accuracy | ≥80% | Test set |
| ECE (Calibration) | <0.05 | Test set |
| Invalid Document AUC | ≥0.95 | Test set |

### 7.2 Accuracy Targets (Tesseract Fallback)

| Metric | Target |
|--------|--------|
| Amount Exact Match | ≥85% |
| Transaction Code Exact Match | ≥80% |
| Full Record Accuracy | ≥65% |

### 7.3 Routing Targets

| Metric | Target |
|--------|--------|
| Human Review Recall | ≥95% |
| Human Review Precision | ≥60% |
| False Positive Rate | ≤20% |
| Auto-Verify Rate | Maximize (subject to above) |

### 7.4 Performance Targets

| Operation | P95 Target |
|-----------|------------|
| Image Ingestion | <500ms |
| Ollama Vision | <10s |
| Tesseract OCR | <5s |
| Verification | <100ms |
| Duplicate Check | <100ms |
| Total (Ollama) | <15s |
| Total (Tesseract) | <10s |

---

## 8. Test Results

| Test Suite | Status |
|------------|--------|
| Unit Tests | ❌ NOT RUN |
| Integration Tests | ❌ NOT RUN |
| Contract Tests | ❌ NOT RUN |
| Security Tests | ❌ NOT RUN |
| Performance Tests | ❌ NOT RUN |
| Chaos Tests | ❌ NOT RUN |
| Evaluation Tests | ❌ NOT RUN (needs dataset) |

---

## 9. Known Failure Modes

See `13_model_limitations.md` for complete catalog. Key highlights:

| Category | Top Failure Modes |
|----------|-------------------|
| **Ollama Vision** | Amount decimal/comma confusion; tx_code partial; Vietnamese diacritics; stamp occlusion |
| **Tesseract** | Vietnamese diacritics; table structure; handwritten text; low resolution |
| **Regex Extraction** | Amount format ambiguity; new bank formats; name line breaks |
| **Confidence** | No calibration; heuristic risk penalties; single confidence from Ollama |
| **Duplicate** | pHash threshold arbitrary; fuzzy layer not implemented; requires tx_code |
| **Student Matching** | Name variations; middle names; nicknames; OCR errors |

---

## 10. Interfaces Phase 2/4/5 Need

### 10.1 Phase 2 (Backend - Minh) Needs From Phase 3

| Interface | Provided By | Status |
|-----------|-------------|--------|
| `AIResultIn` schema | Unchanged (compatible) | ✅ Ready |
| `VisionProcessResponse` | `app/api/routes/vision.py` | ✅ Ready |
| Unified thresholds config | `ai/confidence/thresholds.py` | 🔄 To implement |
| Duplicate candidate evidence | In `AIResultIn.evidence` | 🔄 To implement |
| Human review queue integration | `ai/review/queue.py` | 🔄 To implement |

### 10.2 Phase 4 (Guest Chat - Hải) Needs From Phase 3

| Interface | Provided By | Status |
|-----------|-------------|--------|
| Image upload validation | `ai/ingestion/image_validator.py` | 🔄 To implement |
| Human review request format | `ai/review/contracts.py` | ✅ Designed |
| Review decision callback | `ai/review/queue.py` | 🔄 To implement |

### 10.3 Phase 5 (Admin Dashboard - Hải) Needs From Phase 3

| Interface | Provided By | Status |
|-----------|-------------|--------|
| Review queue metrics | `ai/review/queue.get_metrics()` | 🔄 To implement |
| Reviewer workload | `ai/review/queue` | 🔄 To implement |
| Extraction summary UI data | `ai/review/ui_data.py` | ✅ Designed |

---

## 11. Configuration Required

### 11.1 Environment Variables (New)

```bash
# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_VISION_MODEL=qwen2.5vl:3b
OLLAMA_TEXT_MODEL=qwen3.5:4b
OLLAMA_TIMEOUT=60
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=1.0
OLLAMA_TEMPERATURE=0.1
OLLAMA_TOP_P=0.9
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_PREDICT=1024
OLLAMA_KEEP_ALIVE=5m
OLLAMA_HEALTH_CHECK_INTERVAL=30
OLLAMA_WARMUP_ON_START=true
OLLAMA_CIRCUIT_BREAKER_THRESHOLD=5
OLLAMA_CIRCUIT_BREAKER_TIMEOUT=60

# Ingestion
AI_INGESTION_MAX_FILE_SIZE_MB=10
AI_INGESTION_MIN_BLUR_SCORE=100.0
AI_INGESTION_MAX_DIMENSION=4000

# Thresholds (single source of truth)
AI_AUTO_VERIFY_THRESHOLD=0.90
AI_HUMAN_REVIEW_THRESHOLD=0.70
AI_MIN_AMOUNT_CONFIDENCE=0.85
AI_MIN_TX_CODE_CONFIDENCE=0.80
AI_MIN_SENDER_CONFIDENCE=0.70
AI_MIN_BANK_CONFIDENCE=0.75
AI_MIN_DATE_CONFIDENCE=0.70
AI_MIN_OCR_CONFIDENCE=0.50
AI_MIN_STUDENT_MATCH=0.80

# Duplicate
AI_PHASH_THRESHOLD=10
AI_FUZZY_THRESHOLD=0.85
AI_FUZZY_LOOKBACK_DAYS=30
```

### 11.2 Backend Must Also Use These Thresholds

The backend `ai_confidence_threshold` setting (currently 0.90) must align with `AI_AUTO_VERIFY_THRESHOLD`. Recommend single config file shared between AI and Backend.

---

## 12. Remaining Work for Phase 3 Complete

| Task | Priority | Owner | Blocked By |
|------|----------|-------|------------|
| Collect 500 real Vietnamese receipts | P0 | Ngọc | Volunteer participants |
| Annotate ground truth (2x + verify) | P0 | Ngọc | Dataset collected |
| Implement all new `ai/` modules | P0 | Ngọc | Design complete |
| Replace `ollama_client.py` with `OllamaModelManager` | P0 | Ngọc | Ollama module done |
| Replace `vision.py` with unified thresholds | P0 | Ngọc | Thresholds module done |
| Run evaluation on test set | P0 | Ngọc | Dataset + implementation done |
| Fit calibration curves | P0 | Ngọc | Evaluation done |
| Establish regression baseline | P0 | Ngọc | Evaluation done |
| Run full test suite | P0 | Ngọc | Implementation done |
| CI/CD pipeline for evaluation | P1 | Ngọc | Tests passing |
| Document any API changes for Phase 2/4 | P1 | Ngọc | Implementation done |

---

## 13. Commit Hash

```bash
# To be filled after implementation commits
git log --oneline -1
# Branch: phase-3-ai
```

---

## 14. Phase 3 Status Declaration

### Current Status: **DESIGN COMPLETE — IMPLEMENTATION PENDING**

| Acceptance Criterion | Status |
|---------------------|--------|
| Image ingestion works | 🔄 Designed |
| Ollama adapter handles timeout/model unavailable | 🔄 Designed |
| Extraction output follows schema | 🔄 Designed |
| Field-level validation exists | 🔄 Designed |
| Confidence & human review work | 🔄 Designed |
| AI has no ledger write authority | ✅ Enforced by architecture |
| Duplicate detection is proposal only | ✅ Enforced by architecture |
| Evaluation metrics honest | ❌ Needs dataset |
| Tests pass | ❌ Not run |
| Contract compatible with Phase 2 | ✅ Verified |

### Declaration Options

When implementation and evaluation are complete, Phase 3 will be declared as one of:

- **PHASE_3_COMPLETE** — All acceptance criteria met with evidence
- **PHASE_3_PARTIAL** — Core pipeline works but some metrics below target
- **PHASE_3_BLOCKED** — External dependency (e.g., no evaluation data) prevents completion

---

## 15. Handoff Checklist

- [ ] All 14 artifacts created in `artifacts/phase_3_ai/`
- [ ] Implementation files created in `ai/` and `app/`
- [ ] Evaluation dataset collected (500 receipts)
- [ ] Ground truth annotated and verified
- [ ] Evaluation run on test set
- [ ] Calibration curves fitted and applied
- [ ] All tests passing (unit, integration, contract, security, performance)
- [ ] Regression baseline established
- [ ] CI/CD pipeline configured
- [ ] Phase 2/4/5 notified of interface changes
- [ ] Model limitations communicated to stakeholders
- [ ] Phase 3 status declared (COMPLETE/PARTIAL/BLOCKED)

---

## 16. Next Steps for Integration Team

1. **Review this handoff** and all 14 artifacts
2. **Confirm API contracts** with Phase 2 (Minh) and Phase 4/5 (Hải)
3. **Allocate resources** for dataset collection (500 receipts)
4. **Schedule implementation sprints** for `ai/` modules
5. **Set up evaluation infrastructure** (Supabase tables, CI/CD)
6. **Agree on shared threshold config** between AI and Backend

---

*End of Phase 3 Handoff Document*
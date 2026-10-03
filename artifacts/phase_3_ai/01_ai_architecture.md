# 01_AI_ARCHITECTURE.md

## Phase 3 AI Pipeline — Architecture Design

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 3 AI PIPELINE ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   GUEST      │    │   IMAGE      │    │   EXTRACTION │    │ VERIFI-  │  │
│  │   CHAT       │───▶│   INGESTION  │───▶│   ENGINE     │───▶│ CATION   │  │
│  │   (Phase 4)  │    │   (VALIDATE) │    │  (OLLAMA/    │    │ ENGINE   │  │
│  └──────────────┘    └──────────────┘    │   TESSERACT) │    └────┬─────┘  │
│                                          └──────────────┘         │        │
│                                                 │                  │        │
│                                                 ▼                  ▼        │
│                                          ┌──────────────┐    ┌──────────┐  │
│                                          │ UNIFIED      │    │ HUMAN    │  │
│                                          │ SCHEMA v1    │    │ REVIEW   │  │
│                                          │ (VERSIONED)  │    │ QUEUE    │  │
│                                          └──────────────┘    └──────────┘  │
│                                                 │                  ▲        │
│                                                 ▼                  │        │
│                                          ┌──────────────┐    ┌──────────┐  │
│                                          │ DUPLICATE    │    │ BACKEND  │  │
│                                          │ CANDIDATE    │    │ GATEKEEPER│  │
│                                          │ DETECTION    │    │ (Phase 2)│  │
│                                          └──────────────┘    └──────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Design Principles

1. **Single Source of Truth**: One versioned extraction schema for all paths
2. **Defense in Depth**: AI proposes, Backend decides (financial gatekeeper)
3. **Observable Confidence**: Field-level + overall confidence with calibration
4. **Graceful Degradation**: Ollama → Tesseract fallback, Human review fallback
5. **No Financial Authority**: AI never writes ledger; only produces structured proposals
6. **Auditability**: Every decision traceable with evidence and model metadata

### 1.2 Component Boundaries

| Component | Responsibility | NOT Responsible For |
|-----------|---------------|---------------------|
| **Image Ingestion** | Validate, normalize, hash images | OCR, extraction, business logic |
| **Extraction Engine** | OCR + structured extraction | Validation, duplicate check, posting |
| **Verification Engine** | Field validation, risk flags, confidence | Ledger posting, financial decisions |
| **Duplicate Detection** | Candidate identification only | Final duplicate decision (Backend) |
| **Human Review Queue** | Structured handoff for low confidence | UI, assignment, resolution (Phase 4/5) |

---

## 2. Data Flow Specification

### 2.1 Primary Path (Ollama Vision)

```
Guest Chat Upload
       │
       ▼
┌──────────────────┐
│ Image Ingestion  │◄── Validates: MIME, size, dimensions, corruption, blur
│ Service          │     Generates: file_hash, perceptual_hash
└────────┬─────────┘
         │ ValidatedImage {bytes, metadata, hashes}
         ▼
┌──────────────────┐
│ Extraction       │◄── Routes to Ollama vision (primary) or Tesseract (fallback)
│ Router           │     Returns: UnifiedExtractionResult v1
└────────┬─────────┘
         │ UnifiedExtractionResult
         ▼
┌──────────────────┐
│ Verification     │◄── Validates fields, computes risk flags, scores confidence
│ Engine           │     Returns: VerificationResult v1
└────────┬─────────┘
         │ VerificationResult
         ▼
┌──────────────────┐
│ Duplicate        │◄── Checks: file_hash, pHash, transaction_identity
│ Candidate        │     Returns: DuplicateCandidate[] (proposals only)
│ Detector         │
└────────┬─────────┘
         │ VerificationResult + DuplicateCandidates
         ▼
┌──────────────────┐
│ Confidence       │◄── If confidence ≥ threshold AND no blocking flags → AUTO_VERIFY
│ Router           │     If confidence < threshold OR blocking flags → HUMAN_REVIEW
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
AUTO      HUMAN
VERIFY    REVIEW
    │         │
    ▼         ▼
Backend   Review
Gatekeeper Queue
(Phase 2) (Phase 4)
```

### 2.2 Fallback Path (Tesseract + Regex)

```
Image Ingestion
       │
       ▼
┌──────────────────┐
│ Tesseract OCR    │──▶ Multi-strategy (6 strategies) → best OCRResult
│ Service          │
└────────┬─────────┘
         │ OCRResult
         ▼
┌──────────────────┐
│ Regex Extraction │──▶ Amount, TxCode, Sender, Bank, DateTime extractors
│ Service          │     Returns: ExtractionResult (legacy)
└────────┬─────────┘
         │ ExtractionResult
         ▼
┌──────────────────┐
│ Schema Adapter   │──▶ Maps legacy → UnifiedExtractionResult v1
│                  │     (fills field_confidence from extractor evidence)
└────────┬─────────┘
         │ UnifiedExtractionResult v1
         ▼
[Continues to Verification Engine - same as primary path]
```

---

## 3. Component Specifications

### 3.1 Image Ingestion Service

**Location**: `ai/ingestion/image_validator.py`

```python
class ImageIngestionService:
    def validate_and_normalize(self, image_bytes: bytes, filename: str) -> ValidatedImage:
        """
        1. MIME type detection (python-magic, not client-provided)
        2. File size limits (config: max_mb)
        3. Dimension limits (min/max width/height)
        4. Corruption check (PIL verify)
        5. Orientation detection (EXIF)
        6. Blur detection (Laplacian variance)
        7. Resolution check (min DPI equivalent)
        8. Duplicate hash computation (SHA-256 + pHash)
        9. Returns ValidatedImage with all metadata
        """
```

**Configuration**:
```python
@dataclass
class IngestionConfig:
    allowed_mime_types: list[str] = ["image/jpeg", "image/png", "image/webp", "image/heic"]
    max_file_size_mb: int = 10
    min_dimensions: tuple[int, int] = (400, 300)
    max_dimensions: tuple[int, int] = (4000, 4000)
    min_blur_score: float = 100.0  # Laplacian variance threshold
    min_resolution_dpi: int = 72
```

### 3.2 Extraction Engine (Unified Interface)

**Location**: `ai/extraction/engine.py`

```python
class ExtractionEngine:
    def __init__(self, ollama_manager: OllamaModelManager, 
                 tesseract_service: OCRService,
                 config: ExtractionConfig):
        pass
    
    def extract(self, validated_image: ValidatedImage) -> UnifiedExtractionResult:
        """
        1. Try Ollama vision first (if available and enabled)
        2. On failure/timeout/low_confidence → fallback to Tesseract
        3. Normalize both outputs to UnifiedExtractionResult v1
        4. Include model_metadata (model, version, processing_time, fallback_used)
        """
```

**ExtractionConfig**:
```python
@dataclass
class ExtractionConfig:
    prefer_ollama: bool = True
    ollama_timeout_s: float = 60.0
    tesseract_fallback: bool = True
    require_transaction_code: bool = True
    require_amount: bool = True
```

### 3.3 Ollama Model Manager

**Location**: `ai/ollama/manager.py`

```python
class OllamaModelManager:
    def __init__(self, config: OllamaManagerConfig):
        pass
    
    async def health_check(self) -> ModelHealthStatus:
        """Check server + model availability"""
    
    async def warmup(self) -> None:
        """Preload models to avoid cold start latency"""
    
    def get_vision_model(self) -> str:
        """Return configured vision model name"""
    
    def get_text_model(self) -> str:
        """Return configured text model name"""
    
    async def extract_vision(self, image_bytes: bytes) -> OllamaExtraction:
        """Call vision model with structured output"""
    
    async def extract_text_fallback(self, ocr_text: str) -> OllamaExtraction:
        """Call text model with OCR text"""
```

### 3.4 Unified Verification Engine

**Location**: `ai/verification/engine.py`

```python
class UnifiedVerificationEngine:
    def __init__(self, policy: VerificationPolicy, 
                 duplicate_detector: DuplicateCandidateDetector,
                 student_matcher: MatchingService):
        pass
    
    def verify(self, extraction: UnifiedExtractionResult, 
               validated_image: ValidatedImage) -> VerificationResult:
        """
        1. Field-level validation (required fields, formats, ranges)
        2. Risk flag analysis (8 risk types)
        3. Duplicate candidate detection
        4. Student matching (if sender extracted)
        5. Confidence calculation (weighted + penalties)
        6. Status determination (VERIFIED / NEEDS_REVIEW / DUPLICATE)
        7. Returns VerificationResult v1 with full evidence
        """
```

### 3.5 Duplicate Candidate Detector

**Location**: `ai/duplicate/detector.py`

```python
class DuplicateCandidateDetector:
    def __init__(self, supabase_client: SupabaseClient):
        pass
    
    def check_candidates(self, validated_image: ValidatedImage,
                         verification: VerificationResult) -> list[DuplicateCandidate]:
        """
        Layer 1: File hash (exact) - SHA-256
        Layer 2: Perceptual hash (near-duplicate) - pHash Hamming distance
        Layer 3: Transaction identity (bank + tx_code) - exact
        Layer 4: Amount + date + sender fuzzy match - configurable threshold
        
        Returns: DuplicateCandidate[] with layer, confidence, matched_upload_id
        NOTE: Only proposes candidates; final decision by Backend
        """
    
    def register(self, validated_image: ValidatedImage, 
                 verification: VerificationResult) -> None:
        """Persist hashes/identities to Supabase for future checks"""
```

---

## 4. Unified Schema (v1.0.0)

**Location**: `ai/schema/v1/extraction_schema.py`

### 4.1 Core Types

```python
class FieldConfidence(BaseModel):
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: ExtractionEvidence
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    normalized: Any | None = None  # e.g., amount normalized to integer VND

class UnifiedExtractionResult(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    extraction_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Core fields with per-field confidence
    amount: FieldConfidence | None = None
    currency: FieldConfidence = Field(default_factory=lambda: FieldConfidence(value="VND", confidence=1.0))
    transaction_code: FieldConfidence | None = None
    transaction_date: FieldConfidence | None = None
    transaction_time: FieldConfidence | None = None
    transaction_type: FieldConfidence | None = None
    bank_name: FieldConfidence | None = None
    bank_code: FieldConfidence | None = None
    account_number_masked: FieldConfidence | None = None
    sender_name: FieldConfidence | None = None
    receiver_name: FieldConfidence | None = None
    description: FieldConfidence | None = None
    
    # Metadata
    source_image_id: UUID
    raw_ocr_text: str
    model_metadata: ModelMetadata
    warnings: list[str] = []
    needs_human_review: bool = False
    field_confidence: dict[str, float] = {}  # Flat map for easy thresholding
```

### 4.2 Model Metadata

```python
class ModelMetadata(BaseModel):
    primary_model: str  # e.g., "qwen2.5vl:3b"
    fallback_model: str | None = None
    fallback_used: bool = False
    ollama_version: str | None = None
    processing_time_ms: int
    ollama_latency_ms: int | None = None
    tesseract_latency_ms: int | None = None
    preprocess_strategy: str | None = None
```

### 4.3 Verification Result (v1)

```python
class VerificationResult(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    verification_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Extracted fields (from UnifiedExtractionResult)
    transaction_code: str | None = None
    amount: int | None = None
    sender_name: str | None = None
    bank_name: str | None = None
    transaction_time: datetime | None = None
    student_id: str | None = None
    
    # Confidence & Status
    confidence: float = Field(ge=0.0, le=1.0)
    status: VerificationStatus
    
    # Risk & Evidence
    risk_flags: list[RiskFlag] = []
    duplicate_candidates: list[DuplicateCandidate] = []
    field_confidence: dict[str, float] = {}
    evidence: dict[str, Any] = {}
    
    # Model traceability
    model_metadata: ModelMetadata
    processing_time_ms: int
```

---

## 5. Configuration Management

### 5.1 Single Source of Truth for Thresholds

```python
# ai/config/thresholds.py
class ThresholdConfig:
    # Overall confidence for auto-verify (aligned with backend)
    AUTO_VERIFY_THRESHOLD: float = 0.90
    
    # Human review trigger
    HUMAN_REVIEW_THRESHOLD: float = 0.70
    
    # Per-field minimums
    MIN_FIELD_CONFIDENCE: dict[str, float] = {
        "amount": 0.85,
        "transaction_code": 0.80,
        "sender_name": 0.70,
        "bank_name": 0.75,
        "transaction_time": 0.70,
    }
    
    # OCR quality
    MIN_OCR_CONFIDENCE: float = 0.50
    
    # Student matching
    MIN_STUDENT_MATCH_CONFIDENCE: float = 0.80
    
    # Duplicate detection
    PHASH_HAMMING_THRESHOLD: int = 10
    FUZZY_DUPLICATE_THRESHOLD: float = 0.85
```

**Environment Override**:
```bash
AI_AUTO_VERIFY_THRESHOLD=0.90
AI_HUMAN_REVIEW_THRESHOLD=0.70
AI_MIN_AMOUNT_CONFIDENCE=0.85
# etc.
```

### 5.2 Configuration Loading Priority

1. Environment variables (highest)
2. Config file (`ai/config.yaml`)
3. Code defaults (lowest)

---

## 6. Integration Contracts

### 6.1 Phase 2 Backend Contract (AIResultIn)

```python
# Must match app/schemas/schemas.py exactly
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

### 6.2 Phase 4 Human Review Contract

```python
class HumanReviewRequest(BaseModel):
    review_id: UUID
    upload_id: UUID
    verification_result: VerificationResult
    image_url: str  # Presigned URL to Supabase Storage
    priority: Literal["high", "normal", "low"]
    created_at: datetime
    deadline: datetime | None = None  # SLA
```

### 6.3 Phase 4/5 Admin Dashboard Contract

```python
class ReviewDecision(BaseModel):
    review_id: UUID
    decision: Literal["approve", "reject", "request_more_info"]
    reviewer_id: str
    corrected_fields: dict[str, Any] | None = None
    notes: str | None = None
    decided_at: datetime
```

---

## 7. Error Handling & Resilience

### 7.1 Failure Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **VALIDATION** | Bad image, missing fields | Return NEEDS_REVIEW with details |
| **TRANSIENT** | Ollama timeout, network blip | Retry with backoff; fallback to Tesseract |
| **MODEL_UNAVAILABLE** | Model not loaded, OOM | Fallback to Tesseract; alert |
| **SCHEMA_VIOLATION** | Model output doesn't match schema | Treat as extraction failure; fallback |
| **LOW_CONFIDENCE** | All fields < threshold | Route to human review |
| **DUPLICATE_CANDIDATE** | Potential duplicate detected | Flag in result; don't block |

### 7.2 Circuit Breaker for Ollama

```python
class OllamaCircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_s: int = 60
    half_open_max_calls: int = 3
    
    # States: CLOSED → OPEN → HALF_OPEN → CLOSED
```

---

## 8. Observability

### 8.1 Structured Logging

Every pipeline stage logs:
```json
{
  "stage": "extraction|verification|duplicate_check",
  "extraction_id": "uuid",
  "model": "qwen2.5vl:3b",
  "latency_ms": 1234,
  "confidence": 0.92,
  "status": "success|fallback|error",
  "fallback_used": false,
  "error_type": null
}
```

### 8.2 Metrics to Emit

- `ai_extraction_total` (counter by model, status)
- `ai_extraction_latency_ms` (histogram)
- `ai_confidence_distribution` (histogram by field)
- `ai_human_review_rate` (gauge)
- `ai_duplicate_candidate_rate` (gauge)
- `ai_fallback_rate` (gauge)

---

## 9. Security Considerations

1. **No External Calls**: Ollama only on `127.0.0.1:11434`
2. **Output Validation**: All model outputs validated against Pydantic schema
3. **Prompt Injection Defense**: 
   - Strict JSON schema enforcement via `format=json`
   - Sanitize `raw_ocr_text` before logging/storage
   - Limit `raw_ocr_text` length in stored evidence
4. **Image Handling**: No persistent storage of raw images in AI service; use Supabase Storage with TTL
5. **Rate Limiting**: Per-upload-id rate limiting at API gateway level

---

## 10. Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   API Gateway   │────▶│  Vision Worker  │  (Phase 3 - this pipeline)
│   (FastAPI)     │     │  (Supabase      │
│                 │     │   polling)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │ VerificationResult    │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Backend        │     │  Supabase       │
│  Gatekeeper     │     │  Storage + DB   │
│  (Phase 2)      │     │  (hashes,       │
│                 │     │   review queue) │
└─────────────────┘     └─────────────────┘
```

- **Vision Worker**: Stateless, horizontal scaling via Supabase polling lease
- **No Redis**: Uses Supabase for queue state (aligned with Phase 1.2 worker)
- **Shared Config**: Thresholds loaded from env vars shared with backend

---

## 11. Versioning Strategy

| Artifact | Versioning |
|----------|------------|
| Extraction Schema | Semantic (MAJOR.MINOR.PATCH) in `schema_version` field |
| Verification Policy | Config version in `verification_policy_version` |
| Model | Ollama model tag (e.g., `qwen2.5vl:3b`) |
| API Contract | Backward compatible; additive fields only |

**Breaking Changes**: Require new `schema_version` and parallel support for N-1 version.

---

*End of Architecture Design*
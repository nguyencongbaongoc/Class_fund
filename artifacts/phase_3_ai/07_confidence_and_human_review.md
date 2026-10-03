# 07_CONFIDENCE_AND_HUMAN_REVIEW.md

## Phase 3 AI Pipeline — Confidence Scoring & Human Review

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This document specifies the confidence scoring methodology, calibration procedures, and human review integration for the AI pipeline. The confidence system must be:

- **Calibrated**: Confidence scores reflect actual accuracy (not just model self-reporting)
- **Explainable**: Every score traceable to evidence
- **Actionable**: Clear thresholds for auto-verify vs human review
- **Auditable**: Full trail for compliance

---

## 2. Confidence Architecture

### 2.1 Three-Level Confidence

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIDENCE HIERARCHY                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LEVEL 1: FIELD CONFIDENCE (Per-field)                      │
│  ─────────────────────────────────                          │
│  amount.confidence          → 0.92                          │
│  transaction_code.confidence → 0.87                         │
│  sender_name.confidence     → 0.78                          │
│  bank_name.confidence       → 0.91                          │
│  transaction_date.confidence → 0.83                        │
│                                                              │
│  LEVEL 2: COMPONENT CONFIDENCE (Weighted groups)            │
│  ─────────────────────────────────                          │
│  OCR Confidence             → 0.85 (Tesseract avg word conf)│
│  Extraction Confidence      → 0.86 (weighted field avg)     │
│  Matching Confidence        → 0.90 (student match score)    │
│  Duplicate Confidence       → 0.95 (1.0 - max dup score)    │
│  Consistency Confidence     → 0.92 (1.0 - mismatch penalty) │
│                                                              │
│  LEVEL 3: OVERALL CONFIDENCE (Final calibrated)             │
│  ─────────────────────────────────                          │
│  Overall Confidence         → 0.87                          │
│  Status                     → VERIFIED (≥0.90) / REVIEW      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Confidence Flow

```
Raw Model Output
       │
       ▼
┌──────────────────┐
│ Field Confidence │  (Ollama: model self-report + schema validation
│ Assignment       │   Tesseract: rule-based + evidence confidence)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Component        │  (Weighted aggregation per component)
│ Aggregation      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Risk Penalty     │  (Subtract penalties for risk flags)
│ Application      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Calibration      │  (Apply isotonic regression / Platt scaling
│ Mapping          │   from evaluation dataset)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Threshold        │  (Compare to AUTO_VERIFY / HUMAN_REVIEW
│ Routing          │   thresholds)
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
AUTO      HUMAN
VERIFY    REVIEW
```

---

## 3. Field Confidence Sources

### 3.1 Ollama Vision Model

```python
# Model returns confidence in JSON response
# We validate and calibrate:

def get_ollama_field_confidence(extracted_field: dict, model_confidence: float) -> float:
    """
    Ollama returns overall confidence. We distribute to fields
    based on presence and clarity.
    """
    if not extracted_field or extracted_field.get("value") is None:
        return 0.0
    
    # Base: model's overall confidence
    base = model_confidence
    
    # Boost if field has clear evidence
    if extracted_field.get("evidence"):
        base += 0.05
    
    # Penalty if value looks suspicious
    value = str(extracted_field.get("value", ""))
    if looks_suspicious(value):
        base -= 0.15
    
    return clamp(base, 0.0, 1.0)
```

### 3.2 Tesseract + Regex Extraction

```python
# Each extractor returns evidence.confidence (rule-based)
# See ai/extraction/service.py for current implementation

# Amount: 0.6-0.95 based on pattern specificity
# Tx Code: 0.7-0.95 based on bank prefix match
# Sender: 0.5-0.9 based on label vs pattern match
# Bank: 0.85-0.95 based on keyword match
# DateTime: 0.7-0.9 based on format + context
```

### 3.3 Field Confidence Normalization

```python
def normalize_field_confidence(
    raw_confidence: float,
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"],
    field_name: str
) -> float:
    """
    Apply source-specific calibration to make confidences comparable.
    """
    # Source calibration factors (from evaluation)
    calibration = {
        "ollama_vision": {
            "amount": 0.95,
            "transaction_code": 0.92,
            "sender_name": 0.88,
            "bank_name": 0.93,
            "transaction_date": 0.85,
        },
        "ollama_text": {
            "amount": 0.90,
            "transaction_code": 0.85,
            "sender_name": 0.80,
            "bank_name": 0.88,
            "transaction_date": 0.75,
        },
        "tesseract_regex": {
            "amount": 0.85,
            "transaction_code": 0.80,
            "sender_name": 0.70,
            "bank_name": 0.85,
            "transaction_date": 0.75,
        }
    }
    
    factor = calibration.get(source, {}).get(field_name, 1.0)
    return clamp(raw_confidence * factor, 0.0, 1.0)
```

---

## 4. Component Confidence Calculation

### 4.1 Extraction Component

```python
def calculate_extraction_confidence(extraction: UnifiedExtractionResult) -> float:
    """Weighted average of field confidences."""
    weights = {
        "amount": 0.30,
        "transaction_code": 0.25,
        "sender_name": 0.15,
        "bank_name": 0.15,
        "transaction_date": 0.10,
        "transaction_time": 0.05,
    }
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for field_name, weight in weights.items():
        field_obj = getattr(extraction, field_name, None)
        if field_obj and field_obj.confidence > 0:
            weighted_sum += field_obj.confidence * weight
            total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

### 4.2 OCR Component

```python
def calculate_ocr_confidence(extraction: UnifiedExtractionResult) -> float:
    """Extract OCR confidence from model metadata."""
    meta = extraction.model_metadata
    
    if meta.primary_model == "tesseract":
        # Tesseract stores avg word confidence in metadata
        return meta.get("tesseract_avg_confidence", 0.5)
    else:
        # Ollama doesn't provide per-word confidence
        # Use proxy: text length / expected length
        text_len = len(extraction.raw_ocr_text)
        expected = 200  # Typical receipt text length
        return min(1.0, text_len / expected) * 0.8  # Conservative
```

### 4.3 Matching Component

```python
def calculate_matching_confidence(match: Optional[StudentMatch]) -> float:
    """Student matching confidence."""
    if not match:
        return 0.0
    return match.confidence  # Already 0-1 from rapidfuzz
```

### 4.4 Duplicate Component

```python
def calculate_duplicate_confidence(candidates: list[DuplicateCandidate]) -> float:
    """Duplicate confidence: 1.0 = no duplicates, lower = more likely duplicate."""
    if not candidates:
        return 1.0
    
    max_dup_conf = max(c.confidence for c in candidates)
    return 1.0 - max_dup_conf
```

### 4.5 Consistency Component

```python
def calculate_consistency_confidence(risk_flags: list[RiskFlag]) -> float:
    """Consistency: 1.0 = no mismatches, lower = more inconsistencies."""
    mismatch_flags = [
        RiskFlag.INCONSISTENT_FIELDS,
        RiskFlag.AMOUNT_MISMATCH,
        RiskFlag.DATE_MISMATCH,
        RiskFlag.SENDER_MISMATCH,
        RiskFlag.BANK_MISMATCH,
    ]
    
    mismatch_count = sum(1 for f in risk_flags if f in mismatch_flags)
    penalty = min(mismatch_count * 0.1, 0.5)
    return max(0.0, 1.0 - penalty)
```

---

## 5. Overall Confidence Calculation

```python
def calculate_overall_confidence(
    extraction: UnifiedExtractionResult,
    match: Optional[StudentMatch],
    duplicate_candidates: list[DuplicateCandidate],
    risk_flags: list[RiskFlag],
    policy: VerificationPolicy
) -> float:
    """Calculate final calibrated confidence."""
    
    # Component confidences
    components = {
        "ocr": calculate_ocr_confidence(extraction),
        "extraction": calculate_extraction_confidence(extraction),
        "matching": calculate_matching_confidence(match),
        "duplicate": calculate_duplicate_confidence(duplicate_candidates),
        "consistency": calculate_consistency_confidence(risk_flags),
    }
    
    # Weighted combination
    weights = policy.confidence_weights
    confidence = sum(
        components[k] * weights.get(k, 0.0) 
        for k in components
    )
    
    # Risk penalties
    penalty = min(
        len(risk_flags) * policy.risk_penalty_per_flag,
        policy.max_risk_penalty
    )
    confidence = max(0.0, confidence - penalty)
    
    # Calibration mapping (from evaluation dataset)
    confidence = apply_calibration(confidence)
    
    return round(confidence, 4)
```

### 5.1 Calibration Mapping

```python
# Calibration curve learned from evaluation dataset
# Maps raw confidence → calibrated probability of correctness

CALIBRATION_CURVE = [
    # (raw_confidence, calibrated_accuracy)
    (0.0, 0.0),
    (0.1, 0.05),
    (0.2, 0.12),
    (0.3, 0.22),
    (0.4, 0.35),
    (0.5, 0.48),
    (0.6, 0.60),
    (0.7, 0.72),
    (0.8, 0.83),
    (0.85, 0.88),
    (0.9, 0.93),
    (0.95, 0.96),
    (1.0, 1.0),
]

def apply_calibration(raw_confidence: float) -> float:
    """Apply piecewise linear calibration."""
    for i in range(len(CALIBRATION_CURVE) - 1):
        x1, y1 = CALIBRATION_CURVE[i]
        x2, y2 = CALIBRATION_CURVE[i + 1]
        if x1 <= raw_confidence <= x2:
            # Linear interpolation
            t = (raw_confidence - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return raw_confidence
```

---

## 6. Threshold Configuration

### 6.1 Threshold Definitions

```python
@dataclass
class ConfidenceThresholds:
    # Auto-verify: High confidence, all checks pass
    AUTO_VERIFY: float = 0.90
    
    # Human review: Below auto-verify, above reject
    HUMAN_REVIEW: float = 0.70
    
    # Per-field minimums for auto-verify
    FIELD_MINIMUMS: dict[str, float] = field(default_factory=lambda: {
        "amount": 0.85,
        "transaction_code": 0.80,
        "sender_name": 0.70,
        "bank_name": 0.75,
        "transaction_date": 0.70,
    })
    
    # OCR quality floor
    MIN_OCR_CONFIDENCE: float = 0.50
    
    # Student matching
    MIN_STUDENT_MATCH: float = 0.80
```

### 6.2 Routing Logic

```python
def route_by_confidence(
    verification: VerificationResult,
    thresholds: ConfidenceThresholds
) -> RoutingDecision:
    """Determine routing based on confidence and risk flags."""
    
    # Check field minimums first
    field_failures = []
    for field, min_conf in thresholds.FIELD_MINIMUMS.items():
        actual = verification.field_confidence.get(field, 0.0)
        if actual < min_conf:
            field_failures.append(f"{field}: {actual:.2f} < {min_conf}")
    
    # Blocking risk flags
    blocking_flags = {
        RiskFlag.MISSING_TRANSACTION_CODE,
        RiskFlag.MISSING_AMOUNT,
        RiskFlag.MISSING_SENDER,
        RiskFlag.LOW_IMAGE_QUALITY,
        RiskFlag.ABNORMAL_AMOUNT,
        RiskFlag.ABNORMAL_TIMESTAMP,
        RiskFlag.PROMPT_INJECTION_DETECTED,
    }
    has_blocking = any(f in blocking_flags for f in verification.risk_flags)
    
    # Decision
    if verification.status == VerificationStatus.DUPLICATE:
        return RoutingDecision.DUPLICATE
    
    if verification.status == VerificationStatus.INVALID:
        return RoutingDecision.REJECT
    
    if has_blocking or field_failures or verification.confidence < thresholds.HUMAN_REVIEW:
        return RoutingDecision.HUMAN_REVIEW
    
    if verification.confidence >= thresholds.AUTO_VERIFY:
        return RoutingDecision.AUTO_VERIFY
    
    # In between → human review
    return RoutingDecision.HUMAN_REVIEW
```

---

## 7. Human Review Integration

### 7.1 Review Queue Contract

```python
class HumanReviewRequest(BaseModel):
    """Payload sent to human review queue (Phase 4/5)."""
    review_id: UUID = Field(default_factory=uuid4)
    upload_id: UUID
    verification_result: VerificationResult
    image_url: str                          # Presigned Supabase Storage URL
    priority: Literal["high", "normal", "low"] = "normal"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sla_deadline: Optional[datetime] = None # e.g., +24h for normal
    
    # Context for reviewer
    extraction_summary: ExtractionSummary
    risk_summary: RiskSummary
    
    # Pre-filled suggestions from AI
    suggested_corrections: dict[str, Any] = Field(default_factory=dict)

class ExtractionSummary(BaseModel):
    """Human-readable summary for reviewer."""
    amount: str | None = None
    transaction_code: str | None = None
    sender: str | None = None
    bank: str | None = None
    date: str | None = None
    overall_confidence: float
    model_used: str

class RiskSummary(BaseModel):
    """Risk flags explained for human."""
    flags: list[RiskFlagExplanation] = Field(default_factory=list)
    blocking: bool = False

class RiskFlagExplanation(BaseModel):
    flag: RiskFlag
    message: str
    severity: Literal["blocking", "warning", "info"]
    field: str | None = None
```

### 7.2 Review Decision Contract

```python
class ReviewDecision(BaseModel):
    """Decision from human reviewer."""
    review_id: UUID
    decision: Literal["approve", "reject", "correct"]
    reviewer_id: str
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    
    # If correcting
    corrected_fields: dict[str, Any] = Field(default_factory=dict)
    
    # If rejecting
    rejection_reason: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None
```

### 7.3 Review Queue Implementation

```python
class HumanReviewQueue:
    def __init__(self, supabase: SupabaseClient):
        self.supabase = supabase
    
    async def enqueue(self, request: HumanReviewRequest) -> str:
        """Add review request to queue."""
        # Store in Supabase review_queue table
        # Return queue position
        pass
    
    async def get_next(self, reviewer_id: str) -> Optional[HumanReviewRequest]:
        """Get next review for reviewer (priority + FIFO)."""
        pass
    
    async def submit_decision(self, decision: ReviewDecision) -> None:
        """Record decision, trigger backend processing."""
        # Update review_queue status
        # If approve → call backend verify_and_post
        # If correct → re-run verification with corrections
        # If reject → mark upload REJECTED
        pass
    
    async def get_metrics(self) -> ReviewQueueMetrics:
        """Queue depth, avg wait time, reviewer workload."""
        pass
```

---

## 8. Reviewer UI Data Requirements

### 8.1 Image Display

```python
class ReviewImageData(BaseModel):
    """Data needed for reviewer image viewer."""
    original_url: str                    # Presigned URL
    annotated_url: Optional[str] = None  # With bounding boxes (future)
    zoom_levels: list[float] = [0.5, 1.0, 2.0, 4.0]
    rotation: int = 0                    # Current rotation
```

### 8.2 Field Review Widget

```python
class FieldReviewItem(BaseModel):
    """Single field for reviewer to verify/correct."""
    field_name: str
    label: str                            # Human label: "Số tiền"
    ai_value: str | None                  # AI extracted value
    ai_confidence: float                  # 0-1
    ai_evidence: ExtractionEvidence | None
    is_required: bool
    current_value: str | None = None      # Reviewer's edit
    validation_error: str | None = None   # Real-time validation
```

### 8.3 Risk Flag Display

```python
class RiskFlagDisplay(BaseModel):
    """Risk flag formatted for reviewer."""
    flag: RiskFlag
    title: str                            # "Thiếu mã giao dịch"
    description: str                      # "Không tìm thấy mã GD trên biên lai"
    severity: Literal["blocking", "warning", "info"]
    related_fields: list[str]
    suggested_action: str                 # "Kiểm tra vùng mã GD, nhập thủ công"
```

---

## 9. Confidence Calibration Process

### 9.1 Calibration Dataset Requirements

- Minimum 500 labeled receipts (ground truth)
- Balanced across: banks, amounts, image qualities, languages
- Split: 70% train, 15% val, 15% test

### 9.2 Calibration Procedure

```python
def calibrate_confidence(
    predictions: list[float],   # Raw confidence scores
    labels: list[bool]          # Ground truth: correct/incorrect
) -> Callable[[float], float]:
    """
    Fit isotonic regression or Platt scaling.
    Returns calibration function.
    """
    from sklearn.isotonic import IsotonicRegression
    import numpy as np
    
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(predictions, labels)
    
    def calibrate(x: float) -> float:
        return float(ir.predict(np.array([x]))[0])
    
    return calibrate
```

### 9.3 Calibration Monitoring

- Track calibration drift monthly
- Re-calibrate when dataset grows >20%
- Alert if ECE (Expected Calibration Error) > 0.05

---

## 10. Confidence Explanation for Audit

```python
class ConfidenceExplanation(BaseModel):
    """Full explanation for audit trail."""
    overall: float
    components: dict[str, float]
    weights: dict[str, float]
    field_breakdown: dict[str, FieldBreakdown]
    risk_penalties: list[RiskPenalty]
    calibration_applied: bool
    calibration_version: str

class FieldBreakdown(BaseModel):
    raw_confidence: float
    normalized_confidence: float
    weight: float
    contribution: float
    evidence: ExtractionEvidence | None

class RiskPenalty(BaseModel):
    flag: RiskFlag
    penalty: float
    reason: str
```

---

## 11. Testing Requirements

### 11.1 Calibration Tests

| Test | Expected |
|------|----------|
| Perfect predictions (1.0) → calibrated ≈ 1.0 | ✓ |
| Random predictions (0.5) → calibrated ≈ accuracy | ✓ |
| Monotonicity: higher raw → higher calibrated | ✓ |
| ECE on test set < 0.05 | ✓ |

### 11.2 Routing Tests

| Scenario | Expected Route |
|----------|----------------|
| Confidence 0.95, no flags | AUTO_VERIFY |
| Confidence 0.85, no flags | HUMAN_REVIEW |
| Confidence 0.95, missing tx_code | HUMAN_REVIEW |
| Confidence 0.95, duplicate | DUPLICATE |
| Confidence 0.30, blurry | HUMAN_REVIEW |
| Confidence 0.95, prompt injection | HUMAN_REVIEW |

### 11.3 Human Review Integration Tests

| Test | Description |
|------|-------------|
| Enqueue → dequeue → approve → backend post | Full flow |
| Enqueue → correct fields → re-verify → auto-verify | Correction flow |
| Enqueue → reject → upload marked rejected | Rejection flow |
| SLA deadline exceeded → escalation | Escalation flow |
| Reviewer workload balancing | Fair distribution |

---

## 12. Metrics & Monitoring

| Metric | Type | Description |
|--------|------|-------------|
| `confidence_distribution` | Histogram | Overall confidence by status |
| `confidence_calibration_ece` | Gauge | Expected Calibration Error |
| `auto_verify_rate` | Gauge | % routed to auto-verify |
| `human_review_rate` | Gauge | % routed to human review |
| `human_review_agreement` | Gauge | % reviewer agrees with AI |
| `review_queue_depth` | Gauge | Pending reviews |
| `review_avg_wait_time` | Histogram | Time to first review |
| `review_correction_rate` | Gauge | % reviews with corrections |

---

## 13. Implementation Location

```
ai/
├── confidence/
│   ├── __init__.py
│   ├── calculator.py           # Overall confidence calculation
│   ├── calibration.py          # Calibration curves
│   ├── thresholds.py           # ConfidenceThresholds
│   ├── routing.py              # RoutingDecision logic
│   └── explanation.py          # ConfidenceExplanation
├── review/
│   ├── __init__.py
│   ├── queue.py                # HumanReviewQueue
│   ├── contracts.py            # ReviewRequest, ReviewDecision
│   ├── summary.py              # ExtractionSummary, RiskSummary
│   └── ui_data.py              # ReviewImageData, FieldReviewItem
```

---

## 14. Migration from Current System

| Current | New |
|---------|-----|
| Single `confidence` float | Field-level + component + overall |
| Hardcoded 0.7 threshold | Configurable thresholds (0.90/0.70) |
| No calibration | Calibration curve from eval data |
| No field minimums | Per-field minimums |
| No risk penalties | Structured risk penalties |
| No prompt injection detection | Added |
| No human review queue contract | Full contract for Phase 4/5 |
| No confidence explanation | Audit-ready explanation |

---

*End of Confidence Scoring & Human Review Design*
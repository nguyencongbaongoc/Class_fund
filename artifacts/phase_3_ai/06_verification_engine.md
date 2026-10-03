# 06_VERIFICATION_ENGINE.md

## Phase 3 AI Pipeline — Verification Engine Design

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

The Verification Engine is the **core validation layer** that:
1. Validates extracted fields against business rules
2. Computes risk flags
3. Calculates calibrated confidence scores
4. Determines processing status (VERIFIED / NEEDS_REVIEW / DUPLICATE)
5. Produces evidence for audit trail

**Critical**: The verification engine does NOT make financial decisions. It produces structured proposals for the Backend Financial Gatekeeper (Phase 2).

---

## 2. Input/Output Contracts

### 2.1 Input

```python
class VerificationInput(BaseModel):
    extraction: UnifiedExtractionResult          # From extraction engine
    validated_image: ValidatedImage              # From image ingestion
    student_roster: list[StudentRecord]          # For sender matching
    campaign_context: CampaignContext | None     # Optional campaign info
```

### 2.2 Output

```python
class VerificationResult(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    verification_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Extracted fields (copied from extraction for convenience)
    transaction_code: Optional[str] = None
    amount: Optional[int] = None
    sender_name: Optional[str] = None
    bank_name: Optional[str] = None
    transaction_time: Optional[datetime] = None
    transaction_type: Optional[str] = None
    bank_code: Optional[str] = None
    account_number_masked: Optional[str] = None
    receiver_name: Optional[str] = None
    description: Optional[str] = None
    student_id: Optional[str] = None
    
    # Confidence & Status
    confidence: float = Field(ge=0.0, le=1.0)
    status: VerificationStatus
    
    # Risk Analysis
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    risk_details: dict[str, Any] = Field(default_factory=dict)
    
    # Duplicate Detection
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list)
    
    # Evidence & Traceability
    field_confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    model_metadata: ModelMetadata
    
    # Processing Info
    processing_time_ms: int
    verification_policy_version: str = "1.0.0"
```

### 2.3 Status Enum

```python
class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"           # High confidence, all checks passed
    NEEDS_REVIEW = "NEEDS_REVIEW"   # Low confidence or risk flags
    DUPLICATE = "DUPLICATE"         # Duplicate candidate detected
    INVALID = "INVALID"             # Fundamentally invalid (not a receipt, etc.)
```

### 2.4 Risk Flags

```python
class RiskFlag(StrEnum):
    # Missing critical fields
    MISSING_TRANSACTION_CODE = "MISSING_TRANSACTION_CODE"
    MISSING_AMOUNT = "MISSING_AMOUNT"
    MISSING_SENDER = "MISSING_SENDER"
    MISSING_BANK = "MISSING_BANK"
    MISSING_TRANSACTION_DATE = "MISSING_TRANSACTION_DATE"
    
    # Quality issues
    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"
    LOW_FIELD_CONFIDENCE = "LOW_FIELD_CONFIDENCE"
    
    # Data inconsistency
    INCONSISTENT_FIELDS = "INCONSISTENT_FIELDS"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    SENDER_MISMATCH = "SENDER_MISMATCH"
    BANK_MISMATCH = "BANK_MISMATCH"
    
    # Anomalies
    ABNORMAL_AMOUNT = "ABNORMAL_AMOUNT"
    ABNORMAL_TIMESTAMP = "ABNORMAL_TIMESTAMP"
    ABNORMAL_TEXT = "ABNORMAL_TEXT"
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"
    
    # Duplicates
    DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    
    # Campaign-specific
    CAMPAIGN_AMOUNT_MISMATCH = "CAMPAIGN_AMOUNT_MISMATCH"
    CAMPAIGN_STUDENT_NOT_FOUND = "CAMPAIGN_STUDENT_NOT_FOUND"
    CAMPAIGN_ALREADY_PAID = "CAMPAIGN_ALREADY_PAID"
    
    # Security
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
```

---

## 3. Verification Policy (Configurable)

```python
@dataclass
class VerificationPolicy:
    # Overall thresholds
    auto_verify_threshold: float = 0.90          # Overall confidence for auto-verify
    human_review_threshold: float = 0.70         # Below this → NEEDS_REVIEW
    
    # Field-level minimums
    min_field_confidence: dict[str, float] = field(default_factory=lambda: {
        "amount": 0.85,
        "transaction_code": 0.80,
        "sender_name": 0.70,
        "bank_name": 0.75,
        "transaction_date": 0.70,
        "transaction_time": 0.60,
    })
    
    # Required fields for auto-verify
    required_fields: list[str] = field(default_factory=lambda: [
        "amount", "transaction_code", "sender_name", "bank_name", "transaction_date"
    ])
    
    # OCR quality
    min_ocr_confidence: float = 0.50
    
    # Student matching
    min_student_match_confidence: float = 0.80
    require_student_match: bool = True
    
    # Amount validation
    min_amount: int = 1000                       # 1,000 VND
    max_amount: int = 1_000_000_000              # 1B VND
    allow_zero_amount: bool = False
    
    # Date validation
    max_future_days: int = 1                     # Allow 1 day in future (timezone)
    max_past_years: int = 2                      # Reject > 2 years old
    
    # Duplicate detection
    phash_hamming_threshold: int = 10
    fuzzy_duplicate_threshold: float = 0.85
    
    # Campaign validation
    require_campaign_match: bool = False         # Only if campaign_id present
    
    # Confidence weights
    confidence_weights: dict[str, float] = field(default_factory=lambda: {
        "ocr": 0.15,
        "extraction": 0.30,
        "matching": 0.25,
        "duplicate": 0.15,
        "consistency": 0.15,
    })
    
    # Risk penalties
    risk_penalty_per_flag: float = 0.05
    max_risk_penalty: float = 0.30
```

---

## 4. Verification Steps

### Step 1: Field Presence Validation

```python
def validate_field_presence(
    extraction: UnifiedExtractionResult,
    policy: VerificationPolicy
) -> list[RiskFlag]:
    """Check all required fields are present with minimum confidence."""
    flags = []
    
    for field_name in policy.required_fields:
        field_obj = getattr(extraction, field_name, None)
        min_conf = policy.min_field_confidence.get(field_name, 0.5)
        
        if not field_obj or not field_obj.value:
            flags.append(RiskFlag(f"MISSING_{field_name.upper()}"))
        elif field_obj.confidence < min_conf:
            flags.append(RiskFlag(f"LOW_FIELD_CONFIDENCE"))  # Generic, detail in risk_details
    
    return flags
```

### Step 2: Field Format & Range Validation

```python
def validate_field_formats(
    extraction: UnifiedExtractionResult,
    policy: VerificationPolicy
) -> list[RiskFlag]:
    """Validate field formats, ranges, and consistency."""
    flags = []
    
    # Amount validation
    if extraction.amount and extraction.amount.value:
        amount = extraction.amount.value
        if amount < policy.min_amount or amount > policy.max_amount:
            flags.append(RiskFlag.ABNORMAL_AMOUNT)
        if amount == 0 and not policy.allow_zero_amount:
            flags.append(RiskFlag.ABNORMAL_AMOUNT)
    
    # Transaction code format
    if extraction.transaction_code and extraction.transaction_code.value:
        tc = extraction.transaction_code.value
        if len(tc) < 8 or len(tc) > 30:
            flags.append(RiskFlag.SUSPICIOUS_PATTERN)
        if not re.search(r'\d', tc):
            flags.append(RiskFlag.SUSPICIOUS_PATTERN)
    
    # Date validation
    if extraction.transaction_date and extraction.transaction_date.value:
        dt = extraction.transaction_date.value
        now = datetime.utcnow()
        if dt > now + timedelta(days=policy.max_future_days):
            flags.append(RiskFlag.ABNORMAL_TIMESTAMP)
        if dt < now - timedelta(days=365 * policy.max_past_years):
            flags.append(RiskFlag.ABNORMAL_TIMESTAMP)
    
    # Sender name validation
    if extraction.sender_name and extraction.sender_name.value:
        name = extraction.sender_name.value
        if len(name) < 3 or len(name) > 100:
            flags.append(RiskFlag.SUSPICIOUS_PATTERN)
        # Check for obvious non-names
        if re.match(r'^[\d\s\.\-_]+$', name):
            flags.append(RiskFlag.SUSPICIOUS_PATTERN)
    
    return flags
```

### Step 3: Cross-Field Consistency Validation

```python
def validate_cross_field_consistency(
    extraction: UnifiedExtractionResult,
    policy: VerificationPolicy
) -> list[RiskFlag]:
    """Check consistency between related fields."""
    flags = []
    
    # Bank name + code consistency
    if extraction.bank_name and extraction.bank_code:
        if extraction.bank_name.value and extraction.bank_code.value:
            expected_code = BankField.BANK_CODES.get(extraction.bank_name.value)
            if expected_code and expected_code != extraction.bank_code.value:
                flags.append(RiskFlag.BANK_MISMATCH)
    
    # Amount consistency (if multiple amount sources)
    # This would be populated by extraction engine if multiple candidates
    
    # Date + time consistency
    if extraction.transaction_date and extraction.transaction_time:
        if extraction.transaction_date.value and extraction.transaction_time.value:
            date_part = extraction.transaction_date.value.date()
            time_part = extraction.transaction_time.value.time()
            combined = datetime.combine(date_part, time_part)
            # Check if they're consistent (within same day)
            if extraction.transaction_date.value.date() != combined.date():
                flags.append(RiskFlag.DATE_MISMATCH)
    
    return flags
```

### Step 4: OCR Quality Assessment

```python
def assess_ocr_quality(
    extraction: UnifiedExtractionResult,
    validated_image: ValidatedImage,
    policy: VerificationPolicy
) -> list[RiskFlag]:
    """Assess OCR/image quality."""
    flags = []
    
    # Overall OCR confidence
    if extraction.model_metadata:
        # Check if Tesseract was used and its confidence
        if "tesseract" in extraction.model_metadata.primary_model.lower():
            # Would need OCR confidence from metadata
            pass
    
    # Blur score from ingestion
    if validated_image.blur_score < 100:
        flags.append(RiskFlag.LOW_IMAGE_QUALITY)
    
    # Raw text length
    if len(extraction.raw_ocr_text.strip()) < 20:
        flags.append(RiskFlag.ABNORMAL_TEXT)
    
    return flags
```

### Step 5: Student Matching (if sender present)

```python
def match_sender_to_student(
    extraction: UnifiedExtractionResult,
    student_roster: list[StudentRecord],
    policy: VerificationPolicy
) -> tuple[Optional[StudentMatch], list[RiskFlag]]:
    """Match extracted sender to student roster."""
    flags = []
    
    if not extraction.sender_name or not extraction.sender_name.value:
        if policy.require_student_match:
            flags.append(RiskFlag.MISSING_SENDER)
        return None, flags
    
    # Use existing MatchingService
    matcher = StudentMatcher(student_roster)
    sender_extraction = SenderExtraction(
        name=extraction.sender_name.value,
        confidence=extraction.sender_name.confidence,
        evidence=extraction.sender_name.evidence
    )
    
    match = matcher.match(sender_extraction)
    
    if match is None:
        if policy.require_student_match:
            flags.append(RiskFlag.SENDER_MISMATCH)
    elif match.confidence < policy.min_student_match_confidence:
        flags.append(RiskFlag.SENDER_MISMATCH)
    
    return match, flags
```

### Step 6: Campaign Validation (if campaign context)

```python
def validate_campaign_context(
    extraction: UnifiedExtractionResult,
    match: Optional[StudentMatch],
    campaign_context: CampaignContext | None,
    policy: VerificationPolicy
) -> list[RiskFlag]:
    """Validate against campaign requirements."""
    flags = []
    
    if not campaign_context:
        return flags
    
    # Amount must match campaign expected amount
    if extraction.amount and extraction.amount.value:
        if extraction.amount.value != campaign_context.expected_amount:
            flags.append(RiskFlag.CAMPAIGN_AMOUNT_MISMATCH)
    
    # Student must be in campaign and unpaid
    if match and match.student_id:
        member = campaign_context.get_member(match.student_id)
        if not member:
            flags.append(RiskFlag.CAMPAIGN_STUDENT_NOT_FOUND)
        elif member.status == "PAID":
            flags.append(RiskFlag.CAMPAIGN_ALREADY_PAID)
    elif policy.require_campaign_match:
        flags.append(RiskFlag.CAMPAIGN_STUDENT_NOT_FOUND)
    
    return flags
```

### Step 7: Duplicate Candidate Detection

```python
def detect_duplicate_candidates(
    validated_image: ValidatedImage,
    extraction: UnifiedExtractionResult,
    duplicate_detector: DuplicateCandidateDetector,
    policy: VerificationPolicy
) -> list[DuplicateCandidate]:
    """Run all duplicate detection layers."""
    candidates = duplicate_detector.check_candidates(
        validated_image, extraction
    )
    
    # Filter by confidence threshold
    return [c for c in candidates if c.confidence >= policy.fuzzy_duplicate_threshold]
```

### Step 8: Confidence Calculation

```python
def calculate_confidence(
    extraction: UnifiedExtractionResult,
    validated_image: ValidatedImage,
    match: Optional[StudentMatch],
    duplicate_candidates: list[DuplicateCandidate],
    risk_flags: list[RiskFlag],
    policy: VerificationPolicy
) -> float:
    """Calculate calibrated overall confidence."""
    
    # Component confidences
    ocr_conf = extraction.model_metadata.get("ocr_confidence", 0.5)
    
    extraction_confs = [
        f.confidence for f in [
            extraction.amount, extraction.transaction_code,
            extraction.sender_name, extraction.bank_name,
            extraction.transaction_date
        ] if f and f.confidence > 0
    ]
    extraction_conf = sum(extraction_confs) / len(extraction_confs) if extraction_confs else 0.0
    
    matching_conf = match.confidence if match else 0.0
    
    duplicate_conf = 1.0
    if duplicate_candidates:
        duplicate_conf = 1.0 - max(c.confidence for c in duplicate_candidates)
    
    consistency_conf = 1.0 - (len([f for f in risk_flags if "MISMATCH" in f or "INCONSISTENT" in f]) * 0.1)
    consistency_conf = max(0.0, consistency_conf)
    
    # Weighted combination
    weights = policy.confidence_weights
    confidence = (
        weights["ocr"] * ocr_conf +
        weights["extraction"] * extraction_conf +
        weights["matching"] * matching_conf +
        weights["duplicate"] * duplicate_conf +
        weights["consistency"] * consistency_conf
    )
    
    # Risk penalties
    penalty = min(len(risk_flags) * policy.risk_penalty_per_flag, policy.max_risk_penalty)
    confidence = max(0.0, confidence - penalty)
    
    return round(confidence, 4)
```

### Step 9: Status Determination

```python
def determine_status(
    confidence: float,
    risk_flags: list[RiskFlag],
    duplicate_candidates: list[DuplicateCandidate],
    policy: VerificationPolicy
) -> VerificationStatus:
    """Determine final verification status."""
    
    # Duplicate takes precedence
    if duplicate_candidates:
        return VerificationStatus.DUPLICATE
    
    # Invalid document (fundamentally not a receipt)
    if RiskFlag.ABNORMAL_TEXT in risk_flags and RiskFlag.LOW_IMAGE_QUALITY in risk_flags:
        return VerificationStatus.INVALID
    
    # Blocking risk flags
    blocking_flags = {
        RiskFlag.MISSING_TRANSACTION_CODE,
        RiskFlag.MISSING_AMOUNT,
        RiskFlag.MISSING_SENDER,
        RiskFlag.MISSING_BANK,
        RiskFlag.LOW_IMAGE_QUALITY,
        RiskFlag.ABNORMAL_AMOUNT,
        RiskFlag.ABNORMAL_TIMESTAMP,
        RiskFlag.SUSPICIOUS_PATTERN,
        RiskFlag.PROMPT_INJECTION_DETECTED,
    }
    
    if any(f in blocking_flags for f in risk_flags):
        return VerificationStatus.NEEDS_REVIEW
    
    # Student match required but missing/low
    if policy.require_student_match and RiskFlag.SENDER_MISMATCH in risk_flags:
        return VerificationStatus.NEEDS_REVIEW
    
    # Campaign validation failed
    if RiskFlag.CAMPAIGN_AMOUNT_MISMATCH in risk_flags:
        return VerificationStatus.NEEDS_REVIEW
    if RiskFlag.CAMPAIGN_STUDENT_NOT_FOUND in risk_flags:
        return VerificationStatus.NEEDS_REVIEW
    if RiskFlag.CAMPAIGN_ALREADY_PAID in risk_flags:
        return VerificationStatus.NEEDS_REVIEW
    
    # Confidence thresholds
    if confidence < policy.human_review_threshold:
        return VerificationStatus.NEEDS_REVIEW
    
    if confidence >= policy.auto_verify_threshold:
        return VerificationStatus.VERIFIED
    
    # Between thresholds → review
    return VerificationStatus.NEEDS_REVIEW
```

---

## 5. Complete Verification Engine

```python
class UnifiedVerificationEngine:
    def __init__(
        self,
        policy: VerificationPolicy,
        duplicate_detector: DuplicateCandidateDetector,
        student_matcher: MatchingService,
    ):
        self.policy = policy
        self.duplicate_detector = duplicate_detector
        self.student_matcher = student_matcher
    
    def verify(
        self,
        extraction: UnifiedExtractionResult,
        validated_image: ValidatedImage,
        student_roster: list[StudentRecord],
        campaign_context: CampaignContext | None = None,
    ) -> VerificationResult:
        start_time = time.perf_counter()
        
        # Step 1: Field presence
        risk_flags = self.validate_field_presence(extraction, self.policy)
        
        # Step 2: Format validation
        risk_flags.extend(self.validate_field_formats(extraction, self.policy))
        
        # Step 3: Cross-field consistency
        risk_flags.extend(self.validate_cross_field_consistency(extraction, self.policy))
        
        # Step 4: OCR quality
        risk_flags.extend(self.assess_ocr_quality(extraction, validated_image, self.policy))
        
        # Step 5: Student matching
        match, match_flags = self.match_sender_to_student(
            extraction, student_roster, self.policy
        )
        risk_flags.extend(match_flags)
        
        # Step 6: Campaign validation
        if campaign_context:
            risk_flags.extend(self.validate_campaign_context(
                extraction, match, campaign_context, self.policy
            ))
        
        # Step 7: Duplicate detection
        duplicate_candidates = self.detect_duplicate_candidates(
            validated_image, extraction, self.duplicate_detector, self.policy
        )
        if duplicate_candidates:
            risk_flags.append(RiskFlag.DUPLICATE_RECEIPT)
        
        # Step 8: Confidence calculation
        confidence = self.calculate_confidence(
            extraction, validated_image, match,
            duplicate_candidates, risk_flags, self.policy
        )
        
        # Step 9: Status determination
        status = self.determine_status(
            confidence, risk_flags, duplicate_candidates, self.policy
        )
        
        # Build evidence
        evidence = {
            "extraction": extraction.model_dump(),
            "validated_image": {
                "file_hash": validated_image.file_hash,
                "perceptual_hash": validated_image.perceptual_hash,
                "blur_score": validated_image.blur_score,
                "dimensions": f"{validated_image.width}x{validated_image.height}",
            },
            "student_match": match.model_dump() if match else None,
            "duplicate_candidates": [c.model_dump() for c in duplicate_candidates],
            "risk_details": self._build_risk_details(risk_flags, extraction),
        }
        
        processing_time = int((time.perf_counter() - start_time) * 1000)
        
        return VerificationResult(
            transaction_code=extraction.transaction_code.value if extraction.transaction_code else None,
            amount=extraction.amount.value if extraction.amount else None,
            sender_name=extraction.sender_name.value if extraction.sender_name else None,
            bank_name=extraction.bank_name.value if extraction.bank_name else None,
            transaction_time=extraction.transaction_date.value if extraction.transaction_date else None,
            transaction_type=extraction.transaction_type.value if extraction.transaction_type else None,
            bank_code=extraction.bank_code.value if extraction.bank_code else None,
            account_number_masked=extraction.account_number_masked.value if extraction.account_number_masked else None,
            receiver_name=extraction.receiver_name.value if extraction.receiver_name else None,
            description=extraction.description.value if extraction.description else None,
            student_id=match.student_id if match else None,
            confidence=confidence,
            status=status,
            risk_flags=risk_flags,
            risk_details=self._build_risk_details(risk_flags, extraction),
            duplicate_candidates=duplicate_candidates,
            field_confidence=extraction.field_confidence,
            evidence=evidence,
            model_metadata=extraction.model_metadata,
            processing_time_ms=processing_time,
        )
```

---

## 6. Prompt Injection Detection

```python
def detect_prompt_injection(extraction: UnifiedExtractionResult) -> bool:
    """Detect potential prompt injection in extracted text."""
    suspicious_patterns = [
        r"ignore.*instruction",
        r"disregard.*above",
        r"system.*prompt",
        r"you are",
        r"act as",
        r"pretend",
        r"roleplay",
        r"<.*>",  # HTML/XML tags
        r"```",   # Code blocks
        r"json\s*{",  # JSON in raw text
    ]
    
    text = extraction.raw_ocr_text.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check individual fields
    for field_name in ["sender_name", "description", "bank_name"]:
        field_obj = getattr(extraction, field_name, None)
        if field_obj and field_obj.raw_text:
            for pattern in suspicious_patterns:
                if re.search(pattern, field_obj.raw_text, re.IGNORECASE):
                    return True
    
    return False
```

---

## 7. Integration with Backend Gatekeeper

### 7.1 Output Mapping to AIResultIn

```python
def to_backend_contract(verification: VerificationResult) -> AIResultIn:
    """Map VerificationResult to backend AIResultIn."""
    from decimal import Decimal
    
    return AIResultIn(
        transaction_code=verification.transaction_code,
        amount=Decimal(str(verification.amount)) if verification.amount else None,
        sender_name=verification.sender_name,
        bank_name=verification.bank_name,
        transaction_time=verification.transaction_time,
        confidence=Decimal(str(verification.confidence)),
        raw_ocr=verification.evidence.get("extraction", {}).get("raw_ocr_text"),
        campaign_id=None,           # Worker fills
        student_id=verification.student_id,
        bank_account_id=None,       # Worker fills (bank_name → account mapping)
        account_id=None,            # Worker fills
    )
```

### 7.2 Status Mapping

| VerificationStatus | Backend Action |
|-------------------|----------------|
| VERIFIED | Auto-post via `verify_and_post_from_ai` |
| NEEDS_REVIEW | Queue for human review |
| DUPLICATE | Reject as duplicate |
| INVALID | Reject as invalid document |

---

## 8. Testing Requirements

### 8.1 Unit Tests

| Test | Description |
|------|-------------|
| Field presence validation | Missing required fields flagged |
| Field format validation | Invalid amounts, codes, dates flagged |
| Cross-field consistency | Bank name/code mismatch detected |
| OCR quality assessment | Blur, low text length flagged |
| Student matching | Exact, fuzzy, alias matches work |
| Campaign validation | Amount mismatch, student not found, already paid |
| Duplicate detection | All 3 layers + fuzzy |
| Confidence calculation | Weighted average + penalties |
| Status determination | All status transitions |
| Prompt injection detection | Common patterns detected |

### 8.2 Integration Tests

| Test | Description |
|------|-------------|
| Valid receipt → VERIFIED | End-to-end happy path |
| Missing amount → NEEDS_REVIEW | Required field missing |
| Low confidence → NEEDS_REVIEW | Below threshold |
| Duplicate image → DUPLICATE | Exact file hash match |
| Near-duplicate image → DUPLICATE | pHash match |
| Campaign amount mismatch → NEEDS_REVIEW | Amount ≠ expected |
| Blurry image → NEEDS_REVIEW | Blur score low |
| Prompt injection → NEEDS_REVIEW + flag | Injection detected |

---

## 9. Monitoring & Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `verification_total` | Counter | status |
| `verification_latency_ms` | Histogram | - |
| `verification_confidence` | Histogram | status |
| `verification_risk_flags` | Counter | flag |
| `verification_field_confidence` | Histogram | field |
| `verification_student_match_rate` | Gauge | - |

---

## 10. Implementation Location

```
ai/
├── verification/
│   ├── engine.py              # UnifiedVerificationEngine
│   ├── policy.py              # VerificationPolicy, RiskFlag, VerificationStatus
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── field_presence.py
│   │   ├── field_format.py
│   │   ├── cross_field.py
│   │   ├── ocr_quality.py
│   │   └── prompt_injection.py
│   ├── confidence.py          # Confidence calculation
│   ├── status.py              # Status determination
│   └── __init__.py
```

---

## 11. Migration from Current VerificationService

| Current (`ai/verification/service.py`) | New |
|----------------------------------------|-----|
| `VerificationPolicy` (hardcoded) | Configurable `VerificationPolicy` |
| `RiskFlag` (8 flags) | Extended `RiskFlag` (20+ flags) |
| `VerificationResult` (legacy) | `VerificationResult` v1 with schema_version |
| Single confidence | Field-level + overall confidence |
| In-memory duplicate detector | Persisted `DuplicateCandidateDetector` |
| Student matching integrated | Separate `MatchingService` dependency |
| No prompt injection detection | Added |
| No model metadata in output | Full `ModelMetadata` included |

---

*End of Verification Engine Design*
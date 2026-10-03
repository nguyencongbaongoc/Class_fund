# 05_EXTRACTION_SCHEMA.md

## Phase 3 AI Pipeline — Unified Extraction Schema v1.0.0

**Version**: 1.0.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This document defines the **single, versioned schema** for all AI extraction outputs. Both the Ollama Vision path and the Tesseract OCR path must produce output conforming to this schema. The schema includes:

- **Field-level confidence** for every extracted field
- **Evidence tracking** linking each field to source text
- **Model metadata** for traceability and debugging
- **Explicit null handling** distinguishing missing vs unknown vs not detected
- **Schema versioning** for forward compatibility

---

## 2. Core Design Principles

1. **No Implicit Values**: Every field is `Optional` with explicit `None` for missing
2. **Three-State Null**: `null` = not detected, `"unknown"` = detected but unreadable, omitted = not applicable
3. **Evidence Required**: Every non-null field must have `ExtractionEvidence`
4. **Source Attribution**: Every field knows its extraction source (ollama_vision, ollama_text, tesseract_regex)
5. **Normalized + Raw**: Both normalized value and raw extracted text preserved
6. **Versioned**: `schema_version` field mandatory for all outputs

---

## 3. Schema Definitions

### 3.1 Extraction Evidence

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

class ExtractionEvidence(BaseModel):
    """
    Evidence linking an extracted field to its source in the image/text.
    """
    value: str                                    # Raw extracted text span
    confidence: float = Field(ge=0.0, le=1.0)    # Confidence in THIS field
    source_text: str                              # Surrounding context (50-100 chars)
    source_span: tuple[int, int]                  # Character offset in raw OCR text
    rule: Optional[str] = None                    # Extraction rule name (e.g., "vnd_suffix", "bank_keyword")
    model_source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
```

### 3.2 Field Confidence Wrapper

```python
class FieldConfidence(BaseModel):
    """
    Wrapper for any extracted field with confidence and evidence.
    Generic over the value type.
    """
    value: Optional[str] = None                   # Normalized value as string
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    normalized: Optional[object] = None           # Type-specific normalized value
    raw_value: Optional[str] = None               # Exact raw text before normalization
    
    model_config = {"arbitrary_types_allowed": True}
```

### 3.3 Amount Field

```python
class AmountField(BaseModel):
    """Monetary amount in VND."""
    value: Optional[int] = None                   # Integer VND (e.g., 500000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    currency: str = "VND"
    raw_text: Optional[str] = None                # Raw text like "500.000 VND"
    
    @property
    def is_valid(self) -> bool:
        return self.value is not None and self.value > 0
```

### 3.4 Transaction Code Field

```python
class TransactionCodeField(BaseModel):
    """Bank transaction reference code."""
    value: Optional[str] = None                   # e.g., "FT26277123456789"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    bank_pattern: Optional[str] = None            # Which bank pattern matched (MB, VCB, GENERIC, etc.)
    raw_text: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        return self.value is not None and len(self.value) >= 8
```

### 3.5 Date/Time Fields

```python
class DateTimeField(BaseModel):
    """Date and/or time field with parsed datetime."""
    value: Optional[datetime] = None              # Parsed datetime (UTC)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    raw_text: Optional[str] = None                # Raw text like "25/12/2024 14:30:00"
    format_detected: Optional[str] = None         # Format pattern: "dd/mm/yyyy hh:mm:ss"
    timezone: str = "UTC"
    
    @property
    def date_only(self) -> Optional[datetime]:
        if self.value:
            return self.value.replace(hour=0, minute=0, second=0, microsecond=0)
        return None
    
    @property
    def time_only(self) -> Optional[str]:
        if self.value:
            return self.value.strftime("%H:%M:%S")
        return None
```

### 3.6 Sender/Receiver Fields

```python
class PartyField(BaseModel):
    """Sender or receiver name."""
    value: Optional[str] = None                   # Normalized name (uppercase)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    raw_text: Optional[str] = None                # Raw extracted text
    candidates: list[str] = []                    # Alternative candidates
```

### 3.7 Bank Fields

```python
class BankField(BaseModel):
    """Bank identification."""
    value: Optional[str] = None                   # Standardized bank name
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    code: Optional[str] = None                    # Bank code (VCB, TCB, MB, etc.)
    raw_text: Optional[str] = None
    
    # Standard Vietnamese bank codes
    BANK_CODES = {
        "Vietcombank": "VCB",
        "Techcombank": "TCB",
        "BIDV": "BIDV",
        "MBBank": "MB",
        "VPBank": "VPB",
        "ACB": "ACB",
        "SHB": "SHB",
        "Sacombank": "STB",
        "VietinBank": "ICB",
        "Agribank": "VBA",
        "SeABank": "SEA",
        "NAPAS": "NAPAS",
    }
```

### 3.8 Transaction Type

```python
class TransactionTypeField(BaseModel):
    """Transaction type classification."""
    value: Optional[Literal["CREDIT", "DEBIT", "TRANSFER", "PAYMENT", "WITHDRAWAL", "DEPOSIT"]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    raw_text: Optional[str] = None
```

### 3.9 Account Number (Masked)

```python
class AccountNumberField(BaseModel):
    """Masked account number for display."""
    value: Optional[str] = None                   # e.g., "****1234"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    raw_text: Optional[str] = None
    mask_pattern: str = "****"                    # Masking pattern used
```

### 3.10 Description Field

```python
class DescriptionField(BaseModel):
    """Transaction description/memo."""
    value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Optional[ExtractionEvidence] = None
    source: Literal["ollama_vision", "ollama_text", "tesseract_regex"]
    raw_text: Optional[str] = None
```

---

## 4. Unified Extraction Result (Main Output)

```python
class UnifiedExtractionResult(BaseModel):
    """
    Complete extraction result conforming to schema version 1.0.0.
    This is the SINGLE output type for both Ollama and Tesseract paths.
    """
    # Schema versioning (MANDATORY)
    schema_version: Literal["1.0.0"] = "1.0.0"
    
    # Identification
    extraction_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Source image reference
    source_image_id: UUID
    source_image_hash: str                        # SHA-256 of original image
    
    # Core extracted fields (all optional with field-level confidence)
    amount: Optional[AmountField] = None
    transaction_code: Optional[TransactionCodeField] = None
    transaction_date: Optional[DateTimeField] = None
    transaction_time: Optional[DateTimeField] = None
    transaction_type: Optional[TransactionTypeField] = None
    bank_name: Optional[BankField] = None
    bank_code: Optional[BankField] = None
    account_number_masked: Optional[AccountNumberField] = None
    sender_name: Optional[PartyField] = None
    receiver_name: Optional[PartyField] = None
    description: Optional[DescriptionField] = None
    
    # Raw OCR text for reference and debugging
    raw_ocr_text: str
    
    # Model metadata for traceability
    model_metadata: "ModelMetadata"
    
    # Processing warnings (non-blocking)
    warnings: list[str] = Field(default_factory=list)
    
    # Human review flag
    needs_human_review: bool = False
    
    # Flat field confidence map for easy thresholding
    field_confidence: dict[str, float] = Field(default_factory=dict)
    
    # Overall confidence (weighted aggregate)
    confidence: float = Field(ge=0.0, le=1.0)
    
    def model_post_init(self, __context):
        """Auto-populate field_confidence map."""
        self.field_confidence = {}
        for field_name in [
            "amount", "transaction_code", "transaction_date", "transaction_time",
            "transaction_type", "bank_name", "bank_code", "account_number_masked",
            "sender_name", "receiver_name", "description"
        ]:
            field_obj = getattr(self, field_name, None)
            if field_obj and field_obj.confidence > 0:
                self.field_confidence[field_name] = field_obj.confidence
    
    def get_field_confidence(self, field_name: str) -> float:
        """Get confidence for a specific field."""
        return self.field_confidence.get(field_name, 0.0)
    
    def has_required_fields(self, required: list[str]) -> bool:
        """Check if all required fields are present with minimum confidence."""
        min_confidence = {
            "amount": 0.85,
            "transaction_code": 0.80,
            "sender_name": 0.70,
            "bank_name": 0.75,
            "transaction_date": 0.70,
        }
        for field in required:
            conf = self.get_field_confidence(field)
            if conf < min_confidence.get(field, 0.5):
                return False
            if not getattr(self, field, None) or not getattr(self, field).value:
                return False
        return True
```

---

## 5. Model Metadata

```python
class ModelMetadata(BaseModel):
    """
    Metadata about the model(s) used for extraction.
    Enables traceability, debugging, and model comparison.
    """
    # Primary model used
    primary_model: str                          # e.g., "qwen2.5vl:3b" or "tesseract"
    primary_model_version: Optional[str] = None # Model digest/tag
    
    # Fallback information
    fallback_model: Optional[str] = None        # e.g., "qwen3.5:4b" or "tesseract"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None       # "timeout", "error", "low_confidence", "unavailable"
    
    # Ollama specific
    ollama_version: Optional[str] = None        # Ollama server version
    ollama_latency_ms: Optional[int] = None     # Model inference time
    
    # Tesseract specific
    tesseract_version: Optional[str] = None     # Tesseract version
    tesseract_latency_ms: Optional[int] = None
    
    # Preprocessing
    preprocess_strategy: Optional[str] = None   # Strategy used (for Tesseract)
    strategies_tried: list[str] = []            # All strategies attempted
    
    # Timing
    processing_time_ms: int                     # Total pipeline time
    image_ingestion_ms: Optional[int] = None
    extraction_ms: Optional[int] = None
    verification_ms: Optional[int] = None
    
    # Image properties
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_blur_score: Optional[float] = None
```

---

## 6. Null Value Semantics

### 6.1 Three States

| State | Representation | Meaning |
|-------|----------------|---------|
| **Not Detected** | `field: null` or field absent | Field not found in image/text |
| **Detected but Unreadable** | `field.value: "unknown"` | Field region found but text illegible |
| **Not Applicable** | Field omitted from output | Field doesn't apply to this document type |

### 6.2 Implementation

```python
# In extraction code:
# NOT DETECTED - field simply not found
amount = None

# DETECTED BUT UNREADABLE - found region but can't read
amount = AmountField(
    value=None,
    confidence=0.0,
    evidence=ExtractionEvidence(
        value="[illegible]",
        confidence=0.0,
        source_text="... Số tiền: [illegible] ...",
        source_span=(100, 120),
        rule="amount_region_found",
        model_source="ollama_vision"
    ),
    source="ollama_vision",
    raw_text="[illegible]"
)
```

---

## 7. Normalization Rules

### 7.1 Amount Normalization

| Input | Normalized Output |
|-------|-------------------|
| "500.000 VND" | 500000 |
| "500,000đ" | 500000 |
| "500 000 VNĐ" | 500000 |
| "+500000" | 500000 |
| "1.000.000" | 1000000 |
| "1,000,000" | 1000000 |

**Algorithm**: Remove all non-digits except leading `+`, parse as int, validate range (1 - 1,000,000,000)

### 7.2 Date/Time Normalization

| Input Format | Parsed Output |
|--------------|---------------|
| "25/12/2024" | 2024-12-25T00:00:00Z |
| "25/12/2024 14:30" | 2024-12-25T14:30:00Z |
| "2024-12-25" | 2024-12-25T00:00:00Z |
| "2024-12-25T14:30:00" | 2024-12-25T14:30:00Z |
| "14:30:00" | Today at 14:30:00Z |
| "25-12-2024" | 2024-12-25T00:00:00Z |
| "25.12.2024" | 2024-12-25T00:00:00Z |

### 7.3 Bank Name Normalization

| Input | Normalized Name | Code |
|-------|-----------------|------|
| "VIETCOMBANK" | "Vietcombank" | VCB |
| "Vietcom Bank" | "Vietcombank" | VCB |
| "VCB" | "Vietcombank" | VCB |
| "TECHCOMBANK" | "Techcombank" | TCB |
| "MB BANK" | "MBBank" | MB |
| "MBVCB" | "MBBank" | MB |

### 7.4 Transaction Code Normalization

- Uppercase all letters
- Remove spaces
- Preserve exact alphanumeric sequence
- Do NOT add/remove characters

### 7.5 Name Normalization

- Uppercase
- Remove special characters (keep Vietnamese diacritics)
- Collapse multiple spaces
- Trim

---

## 8. Confidence Calculation

### 8.1 Per-Field Confidence Sources

| Source | Confidence Basis |
|--------|------------------|
| **Ollama Vision** | Model's self-reported confidence (validated) |
| **Ollama Text** | Model's self-reported confidence |
| **Tesseract Regex** | Rule-based: pattern specificity + context boosters |

### 8.2 Overall Confidence (Weighted)

```python
WEIGHTS = {
    "amount": 0.30,
    "transaction_code": 0.25,
    "sender_name": 0.15,
    "bank_name": 0.15,
    "transaction_date": 0.10,
    "transaction_time": 0.05,
}

def calculate_overall_confidence(fields: dict[str, FieldConfidence]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for field_name, weight in WEIGHTS.items():
        if field_name in fields and fields[field_name].confidence > 0:
            weighted_sum += fields[field_name].confidence * weight
            total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

### 8.3 Confidence Penalties

Apply penalties to overall confidence for risk flags:

| Risk Flag | Penalty |
|-----------|---------|
| Missing required field | -0.15 per field |
| Low OCR quality | -0.10 |
| Inconsistent fields | -0.10 |
| Abnormal timestamp | -0.05 |
| Duplicate candidate | -0.20 |
| Prompt injection detected | -0.30 |

---

## 9. Schema Evolution

### 9.1 Versioning Rules

- **PATCH** (1.0.1): Add optional fields, fix validation bugs
- **MINOR** (1.1.0): Add new optional fields, new enum values
- **MAJOR** (2.0.0): Remove fields, change types, change required fields

### 9.2 Backward Compatibility

- Consumers MUST handle missing optional fields gracefully
- Producers SHOULD populate all known fields
- `schema_version` allows consumers to detect version

### 9.3 Migration Path

```python
def migrate_to_v1_0_0(old_result: dict) -> UnifiedExtractionResult:
    """Migrate from legacy format to v1.0.0."""
    # Add schema_version
    # Wrap fields in FieldConfidence
    # Add model_metadata
    # Compute field_confidence map
    pass
```

---

## 10. JSON Schema (for API Contracts)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UnifiedExtractionResult",
  "version": "1.0.0",
  "type": "object",
  "required": ["schema_version", "extraction_id", "timestamp", "source_image_id", "raw_ocr_text", "model_metadata", "confidence"],
  "properties": {
    "schema_version": {"const": "1.0.0"},
    "extraction_id": {"type": "string", "format": "uuid"},
    "timestamp": {"type": "string", "format": "date-time"},
    "source_image_id": {"type": "string", "format": "uuid"},
    "source_image_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "amount": {"$ref": "#/$defs/AmountField"},
    "transaction_code": {"$ref": "#/$defs/TransactionCodeField"},
    "transaction_date": {"$ref": "#/$defs/DateTimeField"},
    "transaction_time": {"$ref": "#/$defs/DateTimeField"},
    "transaction_type": {"$ref": "#/$defs/TransactionTypeField"},
    "bank_name": {"$ref": "#/$defs/BankField"},
    "bank_code": {"$ref": "#/$defs/BankField"},
    "account_number_masked": {"$ref": "#/$defs/AccountNumberField"},
    "sender_name": {"$ref": "#/$defs/PartyField"},
    "receiver_name": {"$ref": "#/$defs/PartyField"},
    "description": {"$ref": "#/$defs/DescriptionField"},
    "raw_ocr_text": {"type": "string"},
    "model_metadata": {"$ref": "#/$defs/ModelMetadata"},
    "warnings": {"type": "array", "items": {"type": "string"}},
    "needs_human_review": {"type": "boolean"},
    "field_confidence": {"type": "object", "additionalProperties": {"type": "number"}},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  },
  "$defs": {
    "AmountField": { ... },
    "TransactionCodeField": { ... },
    "DateTimeField": { ... },
    "PartyField": { ... },
    "BankField": { ... },
    "TransactionTypeField": { ... },
    "AccountNumberField": { ... },
    "DescriptionField": { ... },
    "ExtractionEvidence": { ... },
    "ModelMetadata": { ... }
  }
}
```

---

## 11. Mapping to Backend Contract (AIResultIn)

```python
def to_ai_result_in(unified: UnifiedExtractionResult) -> AIResultIn:
    """Convert UnifiedExtractionResult to backend AIResultIn contract."""
    from decimal import Decimal
    
    return AIResultIn(
        transaction_code=unified.transaction_code.value if unified.transaction_code else None,
        amount=Decimal(unified.amount.value) if unified.amount and unified.amount.value else None,
        sender_name=unified.sender_name.value if unified.sender_name else None,
        bank_name=unified.bank_name.value if unified.bank_name else None,
        transaction_time=unified.transaction_date.value if unified.transaction_date else None,
        confidence=Decimal(str(unified.confidence)),
        raw_ocr=unified.raw_ocr_text,
        campaign_id=None,                    # Filled by worker if applicable
        student_id=None,                     # Filled by worker after matching
        bank_account_id=None,                # Filled by worker (bank_name → account mapping)
        account_id=None,                     # Filled by worker (default account)
    )
```

---

## 12. Implementation Location

```
ai/
├── schema/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── extraction_schema.py      # All classes above
│   │   ├── json_schema.json          # JSON Schema for external consumers
│   │   └── migration.py              # Version migration utilities
│   └── __init__.py                   # Re-exports v1 as current
```

---

## 13. Validation Rules

### 13.1 Required for Auto-Verify

```python
REQUIRED_FOR_AUTO_VERIFY = [
    "amount",
    "transaction_code",
    "sender_name",
    "bank_name",
    "transaction_date",
]

MIN_FIELD_CONFIDENCE = {
    "amount": 0.85,
    "transaction_code": 0.80,
    "sender_name": 0.70,
    "bank_name": 0.75,
    "transaction_date": 0.70,
}
```

### 13.2 Validation Function

```python
def validate_for_auto_verify(result: UnifiedExtractionResult) -> tuple[bool, list[str]]:
    """Check if result meets auto-verify criteria."""
    errors = []
    
    for field in REQUIRED_FOR_AUTO_VERIFY:
        field_obj = getattr(result, field)
        min_conf = MIN_FIELD_CONFIDENCE[field]
        
        if not field_obj or not field_obj.value:
            errors.append(f"Missing required field: {field}")
        elif field_obj.confidence < min_conf:
            errors.append(f"Low confidence for {field}: {field_obj.confidence} < {min_conf}")
    
    if result.confidence < 0.90:
        errors.append(f"Overall confidence {result.confidence} < 0.90")
    
    return len(errors) == 0, errors
```

---

*End of Unified Extraction Schema v1.0.0*
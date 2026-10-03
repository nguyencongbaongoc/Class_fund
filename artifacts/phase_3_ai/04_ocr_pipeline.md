# 04_OCR_PIPELINE.md

## Phase 3 AI Pipeline — OCR Pipeline Design

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

The OCR Pipeline is the **fallback extraction path** when Ollama vision model is unavailable, fails, or returns low confidence. It uses Tesseract OCR with multi-strategy preprocessing followed by regex-based field extraction.

### 1.1 Design Goals

- **Reliability**: Deterministic, no external dependencies
- **Vietnamese Support**: `vie+eng` language pack for diacritics
- **Multi-Strategy**: 6 preprocessing strategies, pick best result
- **Structured Output**: Normalized to UnifiedExtractionResult v1
- **Field-Level Confidence**: Per-field confidence from extraction evidence

### 1.2 Position in Pipeline

```
Image Ingestion
       │
       ▼
┌──────────────────┐
│ Ollama Vision    │──▶ Primary (if available)
│ (Primary)        │
└────────┬─────────┘
         │ Fallback conditions:
         │ - Ollama unavailable
         │ - Vision model missing
         │ - Timeout/Error
         │ - Low confidence (< 0.3)
         │ - JSON parse failure
         ▼
┌──────────────────┐
│ Tesseract OCR    │──▶ Fallback
│ + Regex Extract  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Schema Adapter   │──▶ Maps to UnifiedExtractionResult v1
└────────┬─────────┘
         │
         ▼
[Verification Engine - same as primary path]
```

---

## 2. Tesseract OCR Service (Existing)

### 2.1 Current Implementation (`ai/ocr/service.py`)

The existing implementation provides:

- **Engine**: Tesseract via `pytesseract` with `vie+eng` languages
- **Preprocessing**: 6 strategies (default, high_contrast, denoise, sharpen, adaptive_threshold, morphology)
- **Multi-Strategy**: Tries all, picks highest confidence
- **Output**: `OCRResult` with raw_text, confidence, bounding_boxes, lines, words

### 2.2 Configuration

```python
@dataclass
class TesseractConfig:
    language: str = "vie+eng"
    config: str = "--oem 3 --psm 6"  # LSTM OCR, uniform block
    min_confidence: float = 0.3      # Minimum avg word confidence
    dpi: int = 300                   # Target DPI for preprocessing
```

### 2.3 Preprocessing Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `default` | Grayscale + resize | Baseline |
| `high_contrast` | CLAHE enhancement | Low contrast receipts |
| `denoise` | Non-local means denoising | Noisy/grainy images |
| `sharpen` | Unsharp mask kernel | Blurry text |
| `adaptive_threshold` | Gaussian adaptive threshold | Uneven lighting |
| `morphology` | Morphological close | Broken characters |

---

## 3. Regex-Based Extraction (Existing)

### 3.1 Current Implementation (`ai/extraction/service.py`)

Five specialized extractors with rule-based confidence:

| Extractor | Patterns | Confidence Basis |
|-----------|----------|------------------|
| **Amount** | VND suffix, "số tiền", "chuyển", standalone | Label proximity, context |
| **Transaction Code** | Bank-specific (MB, VCB, TCB, BIDV, VPB, ACB, SHB, NAPAS) + generic | Bank prefix match |
| **Sender** | "người gửi", "chủ tài khoản" labels + Vietnamese name pattern | Label match + name validity |
| **Bank** | 11 Vietnamese bank keywords + codes | Keyword match + context |
| **DateTime** | dd/mm/yyyy, yyyy-mm-dd, with/without time | Format + context keywords |

### 3.2 Extraction Evidence

Each field returns `ExtractionEvidence`:
```python
class ExtractionEvidence(BaseModel):
    value: str
    confidence: float
    source_text: str
    source_span: tuple[int, int]
    rule: str
```

---

## 4. Unified Schema Adapter

### 4.1 Mapping Legacy → Unified Schema

The legacy `ExtractionResult` must be mapped to `UnifiedExtractionResult v1` with field-level confidence.

```python
class SchemaAdapter:
    """Adapts legacy Tesseract+Regex output to UnifiedExtractionResult v1."""
    
    def adapt(
        self, 
        ocr_result: OCRResult,
        extraction_result: ExtractionResult,
        validated_image: ValidatedImage,
        model_metadata: ModelMetadata
    ) -> UnifiedExtractionResult:
        """
        1. Convert each extracted field to FieldConfidence
        2. Use extractor evidence.confidence as field confidence
        3. Set source = "tesseract_regex"
        4. Normalize values (amount → int VND, datetime → ISO)
        5. Compute overall confidence from field confidences
        6. Determine needs_human_review from thresholds
        """
```

### 4.2 Field Mapping Details

| Legacy Field | Unified Field | Normalization |
|--------------|---------------|---------------|
| `amount.amount` (int) | `amount.value` | Already int VND |
| `amount.confidence` | `amount.confidence` | Direct mapping |
| `amount.evidence` | `amount.evidence` | Direct mapping |
| `transaction_code.code` | `transaction_code.value` | Uppercase, trim |
| `transaction_code.confidence` | `transaction_code.confidence` | Direct |
| `sender.name` | `sender_name.value` | Uppercase, clean |
| `sender.confidence` | `sender_name.confidence` | Direct |
| `bank.name` | `bank_name.value` | Standardized name |
| `bank.code` | `bank_code.value` | Bank code (VCB, TCB, etc.) |
| `bank.confidence` | `bank_name.confidence` | Direct |
| `datetime.timestamp` | `transaction_date.value` + `transaction_time.value` | Split date/time |
| `datetime.confidence` | Both fields get same confidence | Direct |

### 4.3 Confidence Aggregation

```python
def compute_overall_confidence(field_confidences: dict[str, float]) -> float:
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
    
    for field, weight in weights.items():
        if field in field_confidences:
            weighted_sum += field_confidences[field] * weight
            total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

---

## 5. OCR Pipeline Service

### 5.1 Interface

```python
@dataclass
class OCRPipelineConfig:
    tesseract_config: TesseractConfig
    extraction_config: ExtractionConfig  # For regex extractors
    min_overall_confidence: float = 0.4  # Below this = human review
    min_ocr_confidence: float = 0.3      # Below this = human review

class OCRPipeline:
    def __init__(self, config: OCRPipelineConfig):
        self.ocr_service = OCRService([TesseractEngine()])
        self.extraction_service = ExtractionService()
        self.schema_adapter = SchemaAdapter()
        self.config = config
    
    def process(self, validated_image: ValidatedImage) -> UnifiedExtractionResult:
        """
        1. Run Tesseract multi-strategy OCR
        2. Run regex extraction on best OCR result
        3. Adapt to UnifiedExtractionResult v1
        4. Add model_metadata (tesseract version, strategies tried)
        5. Return unified result
        """
```

### 5.2 Processing Flow

```python
def process(self, validated_image: ValidatedImage) -> UnifiedExtractionResult:
    start_time = time.perf_counter()
    
    # Use normalized bytes if available (resized, rotated)
    image_bytes = validated_image.normalized_bytes or validated_image.image_bytes
    
    # Step 1: OCR
    ocr_result = self.ocr_service.process(
        image_bytes,
        preprocess_strategy="default",
        try_multiple=True  # Try all 6 strategies
    )
    
    # Step 2: Extraction
    extraction_result = self.extraction_service.extract_all(ocr_result)
    
    # Step 3: Build model metadata
    model_metadata = ModelMetadata(
        primary_model="tesseract",
        fallback_model=None,
        fallback_used=False,
        ollama_version=None,
        processing_time_ms=int((time.perf_counter() - start_time) * 1000),
        ollama_latency_ms=None,
        tesseract_latency_ms=ocr_result.processing_time_ms,
        preprocess_strategy="multi_strategy"
    )
    
    # Step 4: Adapt to unified schema
    unified = self.schema_adapter.adapt(
        ocr_result=ocr_result,
        extraction_result=extraction_result,
        validated_image=validated_image,
        model_metadata=model_metadata
    )
    
    # Step 5: Determine human review need
    unified.needs_human_review = (
        unified.confidence < self.config.min_overall_confidence or
        ocr_result.confidence < self.config.min_ocr_confidence or
        not unified.amount or
        not unified.transaction_code
    )
    
    return unified
```

---

## 6. Vietnamese Language Considerations

### 6.1 Tesseract Language Pack

```bash
# Verify Vietnamese language pack installed
tesseract --list-langs | grep vie
```

Required: `tesseract-ocr-vie` package (Vietnamese language data)

### 6.2 Diacritics Handling

- Tesseract `vie+eng` handles: àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ
- Regex patterns in extractors include full Vietnamese character ranges
- Normalization: NFD → remove diacritics for matching, preserve original for display

### 6.3 Common Vietnamese Receipt Patterns

| Field | Vietnamese Keywords | Example |
|-------|---------------------|---------|
| Amount | "Số tiền", "Sotien", "Amount", "Chuyển", "Gui" | "500.000 VND" |
| Tx Code | "Mã GD", "Mã giao dịch", "Transaction code", "Ref" | "FT26277123456789" |
| Sender | "Người gửi", "Sender", "Chủ tài khoản" | "NGUYEN VAN A" |
| Bank | "Vietcombank", "Techcombank", "BIDV", "MBBank"... | "Vietcombank" |
| Date | "Ngày", "Date", "Thời gian" | "25/12/2024 14:30" |

---

## 7. Performance Optimization

### 7.1 Parallel Strategy Execution

```python
async def process_parallel(self, image_bytes: bytes) -> OCRResult:
    """Run all preprocessing strategies in parallel."""
    import asyncio
    
    strategies = list(self.ocr_service.preprocessor.strategies.keys())
    
    async def run_strategy(strategy: str):
        preprocessed = self.ocr_service.preprocessor.preprocess(
            self.ocr_service._load_image(image_bytes), strategy
        )
        return self.ocr_service._run_ocr(preprocessed.image)
    
    tasks = [run_strategy(s) for s in strategies]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Pick best valid result
    valid_results = [r for r in results if isinstance(r, OCRResult)]
    return max(valid_results, key=lambda r: r.confidence) if valid_results else OCRResult(...)
```

### 7.2 Caching

- Cache preprocessed images by hash for retry scenarios
- Cache Tesseract engine initialization (already singleton)

### 7.3 Resource Limits

```python
# Prevent OOM on large images
MAX_IMAGE_PIXELS = 20_000_000  # 20MP limit for OCR
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
```

---

## 8. Quality Metrics & Calibration

### 8.1 Confidence Calibration

Tesseract confidence (0-100 per word) → normalized 0-1:
- Word-level: `conf / 100.0`
- Line-level: Average of word confidences
- Overall: Average of line confidences (current implementation)

**Issue**: Tesseract confidence is often overconfident on garbage text.
**Fix**: Apply calibration curve based on evaluation dataset.

### 8.2 Field Confidence Calibration

Regex extractor confidence is rule-based (0.6-0.95). Need empirical calibration:
- Collect ground truth dataset
- Measure actual accuracy per confidence bucket
- Apply isotonic regression or Platt scaling

---

## 9. Testing Requirements

### 9.1 Unit Tests

| Test | Description |
|------|-------------|
| Tesseract engine init | Loads with vie+eng |
| Preprocessing strategies | All 6 strategies produce output |
| Multi-strategy selection | Picks highest confidence |
| Amount extraction | VND patterns, labels, standalone |
| Tx code extraction | Bank-specific + generic patterns |
| Sender extraction | Labels + name pattern |
| Bank extraction | 11 bank keywords |
| DateTime extraction | Multiple formats |
| Schema adapter | Legacy → unified mapping |
| Confidence aggregation | Weighted average correct |

### 9.2 Integration Tests

| Test | Description |
|------|-------------|
| Valid receipt image | End-to-end → unified result |
| Blurry image | Low confidence → needs_review=true |
| Rotated image | EXIF auto-rotate → correct OCR |
| Low contrast | High contrast strategy wins |
| No text image | Low OCR confidence → needs_review |
| Vietnamese diacritics | Correctly recognized |

### 9.3 Regression Tests

- Compare output against golden master for 20+ test images
- Ensure confidence scores don't regress
- Verify field extraction completeness

---

## 10. Error Handling

```python
class OCRPipelineError(Exception):
    pass

class OCRDecodingError(OCRPipelineError):
    """Cannot decode image."""

class TesseractNotFoundError(OCRPipelineError):
    """Tesseract binary not in PATH."""

class TesseractLanguageError(OCRPipelineError):
    """Language pack not installed."""

class ExtractionError(OCRPipelineError):
    """Regex extraction failed."""

def process(self, validated_image: ValidatedImage) -> UnifiedExtractionResult:
    try:
        return self._process_internal(validated_image)
    except OCRDecodingError:
        # Image corrupted - should have been caught in ingestion
        return UnifiedExtractionResult(
            ...,
            confidence=0.0,
            needs_human_review=True,
            warnings=["OCR_DECODING_FAILED"]
        )
    except TesseractNotFoundError:
        return UnifiedExtractionResult(
            ...,
            confidence=0.0,
            needs_human_review=True,
            warnings=["TESSERACT_NOT_AVAILABLE"]
        )
    except Exception as e:
        logger.error(f"OCR pipeline unexpected error: {e}")
        return UnifiedExtractionResult(
            ...,
            confidence=0.0,
            needs_human_review=True,
            warnings=[f"OCR_PIPELINE_ERROR: {type(e).__name__}"]
        )
```

---

## 11. Monitoring

### 11.1 Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `ocr_requests_total` | Counter | status (success, fallback, error) |
| `ocr_latency_ms` | Histogram | strategy |
| `ocr_confidence` | Histogram | overall |
| `ocr_field_confidence` | Histogram | field (amount, tx_code, sender, bank, datetime) |
| `ocr_strategy_selected` | Counter | strategy |
| `ocr_fallback_rate` | Gauge | - |

### 11.2 Alerts

- Tesseract not available → PagerDuty
- Average confidence < 0.4 for 1h → Warning
- Fallback rate > 50% → Warning (Ollama issues)

---

## 12. Implementation Location

```
ai/
├── ocr/
│   ├── service.py              # Existing - keep
│   └── __init__.py
├── extraction/
│   ├── service.py              # Existing - keep
│   └── __init__.py
├── pipeline/
│   ├── __init__.py
│   ├── ocr_pipeline.py         # NEW - Orchestrates OCR + Extraction + Adapter
│   ├── schema_adapter.py       # NEW - Legacy → Unified mapping
│   └── config.py               # OCRPipelineConfig
```

---

## 13. Migration Notes

### From Current Architecture

| Current | New |
|---------|-----|
| `OCRService.process()` → `OCRResult` | `OCRPipeline.process()` → `UnifiedExtractionResult` |
| `ExtractionService.extract_all()` → `ExtractionResult` | Internal to `OCRPipeline` |
| `VerificationService.verify()` takes `OCRResult` | `VerificationEngine.verify()` takes `UnifiedExtractionResult` |
| Confidence: single float | Confidence: per-field + overall |

### Backward Compatibility

- Keep `OCRService`, `ExtractionService` for existing tests
- Add `OCRPipeline` as new unified entry point
- `VerificationEngine` accepts both (with adapter) during transition

---

*End of OCR Pipeline Design*
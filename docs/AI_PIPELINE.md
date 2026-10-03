# AI Processing Pipeline

## Overview

This document describes the complete image-to-verification pipeline implemented in the AI system.

## Pipeline Stages

### Stage 1: Image Input & Validation

**Input**: Raw image bytes (JPEG, PNG, WebP)

**Validation**:
- MIME type verification via content inspection
- File size limit (configurable, default 10MB)
- Image decode verification

**Output**: Validated `np.ndarray` (OpenCV format)

### Stage 2: Preprocessing

**Strategies** (tried in order, best confidence wins):

1. **Default**: Grayscale + resize if needed
2. **High Contrast**: CLAHE (Contrast Limited Adaptive Histogram Equalization)
3. **Denoise**: Non-local means denoising
4. **Sharpen**: Unsharp masking kernel
5. **Adaptive Threshold**: Gaussian adaptive binarization
6. **Morphology**: Morphological closing

**Configuration**:
- Minimum height: 1000px (upscale with cubic interpolation)
- Strategy selection: Automatic (best confidence) or manual

**Output**: Preprocessed `np.ndarray` (grayscale)

### Stage 3: OCR Recognition

**Engine**: Tesseract 5.x with `vie+eng` language pack

**Configuration**:
- OEM 3 (LSTM only)
- PSM 6 (Single uniform block of text)
- Custom config via `TESSERACT_CONFIG` env var

**Output**: `OCRResult` containing:
- `raw_text`: Full extracted text
- `confidence`: Average word confidence (0-1)
- `bounding_boxes`: Per-word position + confidence
- `lines`: Text split by newlines
- `words`: Word-level details
- `engine`: "tesseract"
- `engine_version`: Tesseract version string
- `processing_time_ms`: OCR latency

### Stage 4: Transaction Extraction

**Extractors** (independent, parallelizable):

#### AmountExtractor
- Patterns: VND suffix, labeled amounts, transfer labels, standalone
- Normalization: Remove separators, parse as integer VND
- Exclusion: Phone numbers, account numbers, balances
- Priority: Transaction amount > balance > other

#### TransactionCodeExtractor
- Bank-specific patterns: MB, VCB, TCB, BIDV, VPB, ACB, SHB, NAPAS
- Generic patterns: FT, REF, TRX, TXN, GD, MAGD, MA GD
- Validation: Min 8 chars, contains digits

#### SenderExtractor
- Label-based: "Người gửi", "Sender", "Chủ tài khoản"
- Pattern-based: Vietnamese name detection (2-5 words, 2+ chars each)
- Candidate ranking: Label matches > pattern matches

#### BankExtractor
- Keyword matching: 11 major Vietnamese banks + NAPAS
- Aliases: Short names, Vietnamese names, English names
- Output: Canonical name + bank code

#### DateTimeExtractor
- Formats: DD/MM/YYYY HH:MM:SS, YYYY-MM-DD HH:MM:SS, DD/MM/YYYY, YYYY-MM-DD, HH:MM:SS
- Context boost: Near "ngày", "giờ", "time", "date"
- Timezone: UTC (assumed if not specified)

**Output**: `ExtractionResult` with all 5 fields + raw evidence

### Stage 5: Student Matching

**Normalization**:
1. Unicode NFD decomposition
2. Diacritic removal (Mn category)
3. Lowercase
4. Non-alphanumeric removal (keep spaces)
5. Whitespace collapse

**Matching Strategies** (in order):
1. **Exact**: Normalized sender == normalized roster name/alias/code
2. **Fuzzy**: RapidFuzz ratio ≥ 80%, returns top 5 candidates
3. **Alias**: Variant overlap (name permutations, substrings)

**Output**: `StudentMatch` with:
- `student_id`: Matched student
- `confidence`: Match score (0-1)
- `matched_name`: Roster name matched
- `candidate_list`: Top matches with scores
- `match_method`: "exact" | "fuzzy_high" | "fuzzy" | "alias"

### Stage 6: Duplicate Detection

**Layer 1: File Hash**
- SHA-256 of raw image bytes
- Exact duplicate detection
- Confidence: 1.0

**Layer 2: Perceptual Hash (pHash)**
- DCT-based 64-bit hash
- Hamming distance ≤ 10 (configurable)
- Resistant to: resize, compression, minor crop, screenshot
- Confidence: 1 - (distance/64)

**Layer 3: Transaction Identity**
- Key: `{bank_name}|{transaction_code}`
- Same transaction code at same bank = duplicate
- Confidence: 1.0

**Layer 4: Database (Backend)**
- Unique constraint on (bank, transaction_code)
- Final authority - AI layer is advisory

**Output**: List of `DuplicateCheckResult` per layer

### Stage 7: Verification & Risk Analysis

**Risk Flags** (auto-detected):
- `MISSING_TRANSACTION_CODE`: No txn code extracted
- `MISSING_AMOUNT`: No amount extracted
- `LOW_IMAGE_QUALITY`: OCR confidence < 0.5
- `SENDER_MISMATCH`: No student match or low match confidence
- `ABNORMAL_TIMESTAMP`: Future >1 day or past >2 years
- `ABNORMAL_TEXT`: OCR text < 20 chars
- `DUPLICATE_RECEIPT`: Any duplicate layer triggered
- `INCONSISTENT_FIELDS`: Extraction confidence < 0.6

**Decision Policy**:
```
if DUPLICATE:                    → DUPLICATE
elif MISSING_TRANSACTION_CODE:     → NEEDS_REVIEW
elif MISSING_AMOUNT:               → NEEDS_REVIEW
elif SENDER_MISMATCH:              → NEEDS_REVIEW
elif LOW_IMAGE_QUALITY:            → NEEDS_REVIEW
elif ABNORMAL_TIMESTAMP:           → NEEDS_REVIEW
elif ABNORMAL_TEXT:                → NEEDS_REVIEW
elif INCONSISTENT_FIELDS:          → NEEDS_REVIEW
else:                              → VERIFIED
```

**Confidence Calculation** (weighted):
- OCR: 20%
- Extraction: 30% (average of all extracted fields)
- Matching: 30% (0 if no match)
- Duplicate: 20% (0 if duplicate, 1 if clean)
- Risk penalty: -5% per flag (max -30%)

### Stage 8: Result Assembly

**Output**: `VerificationResult` with:
- All extracted fields
- Status + confidence
- Risk flags
- Version metadata
- Full evidence for audit
- Processing time

## Data Flow Diagram

```
┌─────────────┐
│  Upload     │
│  Image      │
└──────┬──────┘
       ▼
┌─────────────┐     ┌──────────────────┐
│ Validate &  │────▶│  Preprocess      │
│ Load Image  │     │  (6 strategies)  │
└─────────────┘     └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  OCR (Tesseract) │
                    └────────┬─────────┘
                             ▼
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐ ┌───────────┐ ┌────────────┐
       │  Amount    │ │ Txn Code  │ │  Sender    │
       │ Extractor  │ │ Extractor │ │ Extractor  │
       └─────┬──────┘ └─────┬─────┘ └─────┬──────┘
             ▼              ▼              ▼
       ┌────────────┐ ┌───────────┐ ┌────────────┐
       │   Bank     │ │ DateTime  │ │  Matching  │
       │ Extractor  │ │ Extractor │ │  Service   │
       └─────┬──────┘ └─────┬─────┘ └─────┬──────┘
             ▼              ▼              ▼
       ┌──────────────────────────────────────┐
       │      Duplicate Detection (3 layers)  │
       └──────────────────┬───────────────────┘
                          ▼
       ┌──────────────────────────────────────┐
       │      Verification & Risk Analysis    │
       └──────────────────┬───────────────────┘
                          ▼
              ┌───────────────────────┐
              │  VerificationResult   │
              │  (JSON Contract)      │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │    Backend API        │
              │  (Minh's service)     │
              └───────────────────────┘
```

## Configuration

### VerificationPolicy (tunable)

```python
VerificationPolicy(
    min_confidence_threshold=0.75,      # Overall minimum
    require_transaction_code=True,       # Hard requirement
    require_amount=True,                 # Hard requirement
    require_sender_match=True,           # Hard requirement
    require_student_match=True,          # Hard requirement
    min_ocr_confidence=0.5,              # OCR quality gate
    min_extraction_confidence=0.6,       # Per-field minimum
    min_matching_confidence=0.7,         # Student match minimum
)
```

### DuplicateDetector (tunable)

```python
DuplicateDetector(
    phash_threshold=10,    # Hamming distance (0-64, lower = stricter)
)
```

## Error Handling

| Stage | Failure Mode | Result |
|-------|--------------|--------|
| Load | Invalid image | REJECTED + ABNORMAL_TEXT |
| Preprocess | All strategies fail | REJECTED + LOW_IMAGE_QUALITY |
| OCR | Engine error | REJECTED + LOW_IMAGE_QUALITY |
| Extraction | All fields missing | NEEDS_REVIEW + flags |
| Matching | No roster | NEEDS_REVIEW + SENDER_MISMATCH |
| Duplicate | DB unavailable | Log warning, continue |
| Verification | Policy error | REJECTED |

## Monitoring & Observability

**Structured Logs** (per upload):
- `upload_id`: Correlation ID
- `job_id`: Worker job ID
- `stage`: Current pipeline stage
- `attempt`: Retry attempt number
- `processing_time_ms`: Per-stage timing

**Metrics to Track**:
- OCR latency (p50, p95, p99)
- Extraction success rate per field
- Matching accuracy (verified vs reviewed)
- Duplicate detection rate per layer
- End-to-end latency
- Queue depth & throughput
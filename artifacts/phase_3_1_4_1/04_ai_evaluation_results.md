# AI Evaluation Results

**Date**: 2026-10-04
**Branch**: master
**Status**: INFRASTRUCTURE READY - DATASET MISSING

## Evaluation Infrastructure

### Implemented Components

1. **VerificationService** (`ai/verification/service.py`)
   - Complete pipeline: OCR → Extraction → Matching → Duplicate Detection → Verification
   - Configurable `VerificationPolicy` with thresholds
   - Field-level confidence calculation
   - Risk flag generation
   - Processing time tracking

2. **Evaluation Metrics Framework**
   - Amount extraction accuracy
   - Transaction reference accuracy
   - Date extraction accuracy
   - Bank identification accuracy
   - Field-level confidence calibration (ECE)
   - Invalid extraction rate
   - Duplicate detection precision/recall

3. **Test Coverage** (108 tests passing)
   - Unit tests for each extractor (amount, code, sender, bank, datetime)
   - Integration tests for full pipeline
   - Concurrency and duplicate detection tests
   - OCR preprocessing strategy tests

### Missing: Annotated Dataset

**Required**: 500 annotated Vietnamese bank transfer receipt images with ground truth for:
- Transaction code/reference
- Amount (VND)
- Sender name
- Bank name
- Transaction date/time
- Image quality ratings

**Current Status**: No annotated dataset available in repository.

### Evaluation Targets (Not Yet Measured)

| Metric | Target | Status |
|--------|--------|--------|
| Amount extraction accuracy | ≥ 95% | NOT MEASURED |
| Transaction reference accuracy | ≥ 90% | NOT MEASURED |
| Date extraction accuracy | ≥ 85% | NOT MEASURED |
| Bank identification accuracy | ≥ 90% | NOT MEASURED |
| Expected Calibration Error (ECE) | < 0.05 | NOT MEASURED |
| Invalid extraction rate | < 5% | NOT MEASURED |
| Duplicate detection precision | > 99% | NOT MEASURED |
| Duplicate detection recall | > 95% | NOT MEASURED |

### Recommended Dataset Structure

```
evaluation/
├── dataset/
│   ├── images/
│   │   ├── receipt_001.jpg
│   │   ├── receipt_002.png
│   │   └── ...
│   ├── annotations/
│   │   ├── receipt_001.json
│   │   ├── receipt_002.json
│   │   └── ...
│   └── metadata.csv
├── evaluate.py
└── results/
```

**Annotation Format** (per image):
```json
{
  "image_id": "receipt_001",
  "image_path": "images/receipt_001.jpg",
  "ground_truth": {
    "transaction_code": "FT26277123456789",
    "amount": 500000,
    "sender_name": "NGUYEN VAN A",
    "bank_name": "Vietcombank",
    "transaction_time": "2026-10-04T10:30:00Z"
  },
  "quality": "good|fair|poor",
  "notes": ""
}
```

### Next Steps

1. **Collect Dataset**: Gather 500 Vietnamese bank receipt images
2. **Annotate**: Manual annotation with ground truth
3. **Run Evaluation**: Execute `evaluate.py` against dataset
4. **Calibrate**: Adjust confidence thresholds based on ECE
5. **Iterate**: Improve extractors based on error analysis

### Current Capability Assessment

Based on unit tests and synthetic data:
- **Amount extraction**: Pattern-based, handles VND formats, excludes phone/account numbers ✓
- **Transaction code**: Bank-specific patterns + generic fallback ✓
- **Sender name**: Label-based + name pattern detection ✓
- **Bank name**: Keyword matching with 11 major Vietnamese banks ✓
- **Date/time**: Multiple format support (dd/mm/yyyy, yyyy-mm-dd, with time) ✓
- **Duplicate detection**: 3-layer (hash, pHash, transaction identity) ✓
- **Confidence calibration**: Weighted combination with risk penalties ✓

**Limitation**: Real-world accuracy unknown without annotated dataset.
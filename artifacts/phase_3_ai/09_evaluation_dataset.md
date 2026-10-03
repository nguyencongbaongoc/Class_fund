# 09_EVALUATION_DATASET.md

## Phase 3 AI Pipeline — Evaluation Dataset Design

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This document specifies the design, construction, and maintenance of the evaluation dataset for measuring AI pipeline accuracy. The dataset is **critical** — without measured accuracy, the pipeline is **UNVERIFIED** per Phase 1.2 completion criteria.

### 1.1 Evaluation Goals

1. **Measure true accuracy** of both Ollama Vision and Tesseract paths
2. **Calibrate confidence scores** to reflect actual correctness probability
3. **Identify failure modes** by bank, image quality, amount range, etc.
4. **Track regression** across model versions
5. **Establish production thresholds** with statistical confidence

### 1.2 Key Principle: No Synthetic Accuracy Claims

> **NEVER** report synthetic accuracy as production accuracy.
> 
> Synthetic data (generated receipts) can be used for **development testing** only.
> Production accuracy claims **MUST** come from real Vietnamese receipt images with verified ground truth.

---

## 2. Dataset Requirements

### 2.1 Minimum Size

| Split | Size | Purpose |
|-------|------|---------|
| **Train** | 350 | Model selection, threshold tuning, calibration fitting |
| **Validation** | 75 | Hyperparameter tuning, early stopping |
| **Test** | 75 | Final accuracy reporting, regression detection |
| **Total** | **500** | **Minimum for statistical significance** |

### 2.2 Diversity Requirements (Stratified Sampling)

The dataset MUST cover:

| Dimension | Categories | Min Samples Each |
|-----------|------------|------------------|
| **Bank** | Vietcombank, Techcombank, BIDV, MBBank, VPBank, ACB, SHB, Sacombank, VietinBank, Agribank, SeABank, NAPAS | 20 |
| **Amount Range** | <100K, 100K-500K, 500K-1M, 1M-5M, 5M-20M, >20M | 30 |
| **Image Quality** | Sharp, slight blur, moderate blur, low light, glare, rotated | 40 |
| **Format** | JPEG, PNG, WebP, HEIC | 50 |
| **Language** | Vietnamese, English, Mixed | 50 |
| **Receipt Type** | Transfer, QR payment, ATM deposit, counter deposit | 40 |
| **Device** | Mobile photo, scanner, screenshot | 50 |

### 2.3 Ground Truth Format

```python
@dataclass
class GroundTruth:
    # Identification
    sample_id: str                          # Unique identifier
    image_path: str                         # Relative path in dataset
    image_hash: str                         # SHA-256 for deduplication
    
    # Core fields (ALL REQUIRED)
    amount: int                             # Integer VND
    transaction_code: str                   # Exact as on receipt
    sender_name: str                        # Normalized uppercase
    bank_name: str                          # Standardized name
    transaction_datetime: datetime          # UTC, parsed from receipt
    
    # Optional fields
    transaction_type: Optional[str] = None  # CREDIT/DEBIT/TRANSFER/etc.
    receiver_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    description: Optional[str] = None
    
    # Metadata
    bank_code: str                          # VCB, TCB, MB, etc.
    image_quality: Literal["excellent", "good", "fair", "poor"]
    blur_score: float                       # Laplacian variance
    format: str                             # jpeg, png, webp, heic
    source_device: str                      # mobile, scanner, screenshot
    
    # Annotations
    annotated_by: str                       # Annotator ID
    annotated_at: datetime
    verified_by: Optional[str] = None       # Second verifier
    notes: str = ""                         # Any special notes
```

### 2.4 Dataset Manifest

```yaml
# dataset/manifest.yaml
version: "1.0.0"
created: "2026-10-03"
total_samples: 500
splits:
  train: 350
  val: 75
  test: 75
checksums:
  train: "sha256:..."
  val: "sha256:..."
  test: "sha256:..."
distribution:
  banks:
    Vietcombank: 45
    Techcombank: 42
    BIDV: 40
    MBBank: 43
    VPBank: 38
    ACB: 35
    SHB: 35
    Sacombank: 32
    VietinBank: 30
    Agribank: 28
    SeABank: 25
    NAPAS: 20
  amount_ranges:
    "<100K": 50
    "100K-500K": 120
    "500K-1M": 100
    "1M-5M": 130
    "5M-20M": 70
    ">20M": 30
  quality:
    "excellent": 150
    "good": 180
    "fair": 120
    "poor": 50
```

---

## 3. Data Collection Procedure

### 3.1 Source Channels

1. **Internal Test Transactions**: Team members make real transfers
2. **Volunteer Contributors**: Class fund participants (with consent)
3. **Public Test Images**: Anonymized receipts from public sources
4. **Synthetic Generation**: For development ONLY (clearly labeled)

### 3.2 Image Capture Standards

```python
CAPTURE_STANDARDS = {
    "resolution": "≥ 1200px on shortest side",
    "lighting": "Even, no flash glare on text areas",
    "angle": "Perpendicular to receipt (±15°)",
    "background": "Contrasting, non-reflective",
    "format": "Original format (no re-compression)",
    "naming": "{bank}_{amount}_{quality}_{sequential}.{ext}",
}
```

### 3.3 Annotation Process

1. **Primary Annotation**: Two independent annotators per image
2. **Discrepancy Resolution**: Third senior annotator resolves conflicts
3. **Verification**: Random 10% sample verified by lead engineer
4. **Tooling**: Custom annotation UI with field validation

### 3.4 Quality Control

```python
def validate_ground_truth(gt: GroundTruth) -> list[str]:
    """Validate ground truth entry."""
    errors = []
    
    # Amount must be positive integer
    if gt.amount <= 0:
        errors.append("Amount must be positive")
    
    # Transaction code format
    if not gt.transaction_code or len(gt.transaction_code) < 8:
        errors.append("Invalid transaction code")
    
    # Datetime must be recent (within 2 years)
    if gt.transaction_datetime < datetime.utcnow() - timedelta(days=730):
        errors.append("Transaction date too old")
    
    # Bank code must match name
    expected_code = BANK_CODES.get(gt.bank_name)
    if expected_code and expected_code != gt.bank_code:
        errors.append(f"Bank code mismatch: {gt.bank_name} != {gt.bank_code}")
    
    return errors
```

---

## 4. Dataset Structure

```
dataset/
├── manifest.yaml              # Dataset metadata & checksums
├── ground_truth.csv           # All annotations (train+val+test)
├── ground_truth.jsonl         # JSON Lines for programmatic access
├── splits/
│   ├── train.txt              # Sample IDs for train
│   ├── val.txt                # Sample IDs for validation
│   └── test.txt               # Sample IDs for test
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── annotations/
│   ├── train.jsonl
│   ├── val.jsonl
│   └── test.jsonl
├── synthetic/                 # Clearly separated synthetic data
│   ├── manifest.yaml
│   └── images/
└── scripts/
    ├── evaluate.py            # Main evaluation script
    ├── calibrate.py           # Calibration fitting
    ├── visualize.py           # Error analysis visualizations
    └── collect.py             # Data collection helpers
```

---

## 5. Evaluation Metrics

### 5.1 Primary Metrics (Per-Field)

| Metric | Definition | Target |
|--------|------------|--------|
| **Amount Exact Match** | % samples where predicted amount == ground truth | ≥ 95% |
| **Transaction Code Exact Match** | % samples where predicted code == ground truth | ≥ 90% |
| **Date Exact Match** | % samples where predicted date == ground truth | ≥ 90% |
| **Bank Name Match** | % samples where predicted bank == ground truth | ≥ 95% |
| **Sender Name F1** | F1 score on sender name (token-level) | ≥ 85% |
| **Full Record Accuracy** | % samples where ALL fields correct | ≥ 80% |

### 5.2 Confidence Calibration Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **ECE (Expected Calibration Error)** | Σ |accuracy(bin) - confidence(bin)| × P(bin) | < 0.05 |
| **MCE (Maximum Calibration Error)** | max |accuracy(bin) - confidence(bin)| | < 0.10 |
| **Reliability Diagram** | Visual: accuracy vs confidence per bin | Monotonic |

### 5.3 Detection Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Invalid Document Detection** | AUC-ROC for detecting non-receipts | ≥ 0.95 |
| **Human Review Recall** | % of actual errors routed to review | ≥ 95% |
| **Human Review Precision** | % of review items that are actual errors | ≥ 60% |
| **False Positive Rate** | % correct samples sent to review | ≤ 20% |

### 5.4 Per-Slice Metrics (Required)

Report metrics **separately** for each slice:

```python
REQUIRED_SLICES = [
    "bank",
    "amount_range",
    "image_quality",
    "format",
    "source_device",
    "receipt_type",
]
```

---

## 6. Evaluation Procedure

### 6.1 Running Evaluation

```python
# scripts/evaluate.py

async def run_evaluation(
    model: Literal["ollama_vision", "tesseract", "both"],
    split: Literal["train", "val", "test"],
    output_dir: Path,
) -> EvaluationReport:
    """
    1. Load split samples
    2. Run pipeline on each image
    3. Compare predictions to ground truth
    4. Compute all metrics
    5. Generate report
    """
    pass
```

### 6.2 Comparison Protocol

```python
def compare_extraction(
    prediction: UnifiedExtractionResult,
    ground_truth: GroundTruth,
) -> FieldComparison:
    """Compare single prediction to ground truth."""
    
    results = {}
    
    # Amount
    pred_amt = prediction.amount.value if prediction.amount else None
    results["amount"] = {
        "correct": pred_amt == ground_truth.amount,
        "predicted": pred_amt,
        "actual": ground_truth.amount,
        "confidence": prediction.amount.confidence if prediction.amount else 0.0,
    }
    
    # Transaction code
    pred_code = prediction.transaction_code.value if prediction.transaction_code else None
    results["transaction_code"] = {
        "correct": pred_code == ground_truth.transaction_code,
        "predicted": pred_code,
        "actual": ground_truth.transaction_code,
        "confidence": prediction.transaction_code.confidence if prediction.transaction_code else 0.0,
    }
    
    # ... similar for other fields
    
    return FieldComparison(fields=results)
```

### 6.3 Statistical Significance

```python
def confidence_interval(accuracy: float, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    import scipy.stats as stats
    
    z = stats.norm.ppf((1 + confidence) / 2)
    p = accuracy
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    return (centre - half_width, centre + half_width)

# Example: 95% accuracy on 75 samples → CI = [87.2%, 98.1%]
```

---

## 7. Calibration Fitting

### 7.1 Data Collection

```python
def collect_calibration_data(split: Literal["train", "val"]) -> tuple[list[float], list[bool]]:
    """Collect (confidence, correct) pairs for calibration."""
    predictions = []
    labels = []
    
    for sample_id in load_split(split):
        gt = load_ground_truth(sample_id)
        pred = run_pipeline(gt.image_path)
        
        # Overall confidence vs full record correctness
        predictions.append(pred.confidence)
        labels.append(is_fully_correct(pred, gt))
        
        # Per-field calibration data
        for field in ["amount", "transaction_code", "sender_name", "bank_name", "transaction_date"]:
            field_pred = getattr(pred, field)
            if field_pred:
                predictions.append(field_pred.confidence)
                field_gt = getattr(gt, field)
                labels.append(field_pred.value == field_gt)
    
    return predictions, labels
```

### 7.2 Calibration Models

```python
def fit_calibration_models(
    predictions: list[float],
    labels: list[bool],
) -> dict[str, Callable[[float], float]]:
    """Fit calibration curves for overall and per-field."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    import numpy as np
    
    # Overall confidence calibration (isotonic regression)
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(predictions, labels)
    
    def overall_calibrate(x: float) -> float:
        return float(ir.predict(np.array([x]))[0])
    
    # Per-field calibration (if enough data per field)
    # ... similar for each field
    
    return {
        "overall": overall_calibrate,
        # "amount": amount_calibrate,
        # ...
    }
```

---

## 8. Regression Detection

### 8.1 Baseline Metrics (to establish)

| Metric | Baseline (Test Set) | Regression Threshold |
|--------|---------------------|---------------------|
| Amount Exact Match | TBD | < -2% absolute |
| Transaction Code Match | TBD | < -3% absolute |
| Full Record Accuracy | TBD | < -3% absolute |
| ECE | TBD | > 0.05 |
| Invalid Doc AUC | TBD | < -0.02 |

### 8.2 Regression Test Protocol

```python
def check_regression(current: EvaluationReport, baseline: EvaluationReport) -> RegressionReport:
    """Compare current metrics to baseline."""
    alerts = []
    
    for metric in ["amount_exact", "tx_code_exact", "full_record", "ece"]:
        current_val = getattr(current, metric)
        baseline_val = getattr(baseline, metric)
        
        if metric == "ece":
            # Higher is worse
            if current_val > baseline_val + 0.02:
                alerts.append(f"ECE regression: {baseline_val:.4f} → {current_val:.4f}")
        else:
            # Higher is better
            if current_val < baseline_val - 0.02:
                alerts.append(f"{metric} regression: {baseline_val:.4f} → {current_val:.4f}")
    
    return RegressionReport(alerts=alerts, passed=len(alerts) == 0)
```

---

## 9. Synthetic Data (Development Only)

### 9.1 Purpose

- Unit test development
- Pipeline integration testing
- CI/CD smoke tests
- **NOT for accuracy reporting**

### 9.2 Generation

```python
# scripts/generate_synthetic.py

def generate_synthetic_receipt(
    bank: str,
    amount: int,
    template: str = "standard",
) -> tuple[bytes, GroundTruth]:
    """
    Generate synthetic receipt image using templates.
    Returns image bytes and ground truth.
    """
    # Use template images + text overlay
    # Clearly mark as synthetic in metadata
    pass
```

### 9.3 Synthetic Manifest

```yaml
# dataset/synthetic/manifest.yaml
version: "1.0.0"
type: "synthetic"
purpose: "development_testing_only"
warning: "DO NOT USE FOR PRODUCTION ACCURACY CLAIMS"
samples: 1000
```

---

## 10. Data Privacy & Ethics

### 10.1 PII Handling

- **Sender names**: Real names from volunteers with consent
- **Account numbers**: ALWAYS masked in ground truth (only last 4 digits)
- **Transaction codes**: Real codes (not PII)
- **Images**: Stored encrypted at rest

### 10.2 Consent & Retention

```python
DATA_POLICY = {
    "consent_required": True,
    "retention_days": 365,
    "anonymization": "sender_name hashed after annotation",
    "access_control": "engineers only, audit logged",
    "deletion_on_request": True,
}
```

---

## 11. Continuous Evaluation

### 11.1 Scheduled Runs

```yaml
# .github/workflows/evaluation.yml
schedule:
  - cron: "0 2 * * 0"  # Weekly Sunday 2 AM
  - cron: "0 2 1 * *"  # Monthly 1st 2 AM
```

### 11.2 Trigger Conditions

- New model version deployed
- Threshold config changed
- Manual trigger

### 11.3 Report Artifacts

```
evaluation_runs/
├── 2026-10-03_ollama_vision/
│   ├── metrics.json
│   ├── calibration_curves.json
│   ├── error_analysis.html
│   ├── confusion_matrices.png
│   └── regression_report.md
```

---

## 12. Implementation Location

```
ai/
├── evaluation/
│   ├── __init__.py
│   ├── dataset.py             # GroundTruth, DatasetLoader
│   ├── metrics.py             # Metric computation
│   ├── calibration.py         # Calibration fitting
│   ├── runner.py              # EvaluationRunner
│   ├── reporter.py            # Report generation
│   ├── regression.py          # Regression detection
│   └── synthetic.py           # Synthetic data generation
├── scripts/
│   ├── collect_data.py        # Data collection helpers
│   ├── annotate.py            # Annotation tool
│   └── validate_gt.py         # Ground truth validation
```

---

## 13. Deliverables Checklist

| Deliverable | Status | Due |
|-------------|--------|-----|
| Dataset collection (500 real receipts) | ⏳ PENDING | Phase 3 |
| Ground truth annotations (2x + verification) | ⏳ PENDING | Phase 3 |
| Manifest with checksums | ⏳ PENDING | Phase 3 |
| Evaluation scripts | ⏳ PENDING | Phase 3 |
| Calibration curves (train) | ⏳ PENDING | Phase 3 |
| Test set metrics (held out) | ⏳ PENDING | Phase 3 |
| Regression baseline | ⏳ PENDING | Phase 3 |
| CI/CD integration | ⏳ PENDING | Phase 3 |

---

## 14. Acceptance Criteria for Phase 3 Complete

Phase 3 **CANNOT** be declared COMPLETE without:

- [ ] **500 real Vietnamese receipt images** with verified ground truth
- [ ] **Test set metrics** published with confidence intervals
- [ ] **Calibration curves** fitted and applied
- [ ] **ECE < 0.05** on test set
- [ ] **Per-slice metrics** reported for all required slices
- [ ] **Failure mode analysis** documented
- [ ] **Regression baseline** established
- [ ] **CI/CD pipeline** runs evaluation on every model change

---

*End of Evaluation Dataset Design*
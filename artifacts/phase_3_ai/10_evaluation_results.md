# 10_EVALUATION_RESULTS.md

## Phase 3 AI Pipeline — Evaluation Results Template

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: TEMPLATE — TO BE FILLED AFTER EVALUATION

---

## 1. Overview

This document template will be populated after running the evaluation on the test dataset. All metrics must be computed on the **held-out test set** (75 samples) that was never used for training, threshold tuning, or calibration.

**Critical**: Results from synthetic data, training set, or validation set **MUST NOT** be reported as production accuracy.

---

## 2. Test Set Composition

| Dimension | Distribution | Notes |
|-----------|--------------|-------|
| **Total Samples** | 75 | |
| **Banks** | | |
| Vietcombank | X | |
| Techcombank | X | |
| BIDV | X | |
| MBBank | X | |
| VPBank | X | |
| ACB | X | |
| SHB | X | |
| Sacombank | X | |
| VietinBank | X | |
| Agribank | X | |
| SeABank | X | |
| NAPAS | X | |
| **Amount Ranges** | | |
| <100K | X | |
| 100K-500K | X | |
| 500K-1M | X | |
| 1M-5M | X | |
| 5M-20M | X | |
| >20M | X | |
| **Quality** | | |
| Excellent | X | |
| Good | X | |
| Fair | X | |
| Poor | X | |
| **Format** | | |
| JPEG | X | |
| PNG | X | |
| WebP | X | |
| HEIC | X | |

---

## 3. Primary Metrics (Ollama Vision Path)

### 3.1 Per-Field Exact Match Accuracy

| Field | Correct | Total | Accuracy | 95% CI | Target |
|-------|---------|-------|----------|--------|--------|
| Amount | X | 75 | X% | [X%, X%] | ≥95% |
| Transaction Code | X | 75 | X% | [X%, X%] | ≥90% |
| Transaction Date | X | 75 | X% | [X%, X%] | ≥90% |
| Bank Name | X | 75 | X% | [X%, X%] | ≥95% |
| Sender Name (F1) | - | - | X% | [X%, X%] | ≥85% |

### 3.2 Full Record Accuracy

| Metric | Value | 95% CI | Target |
|--------|-------|--------|--------|
| All Fields Correct | X% | [X%, X%] | ≥80% |
| Amount + TxCode + Date Correct | X% | [X%, X%] | ≥85% |

### 3.3 Confidence Calibration

| Metric | Value | Target |
|--------|-------|--------|
| ECE (Expected Calibration Error) | X.XXXX | < 0.05 |
| MCE (Maximum Calibration Error) | X.XXXX | < 0.10 |
| Brier Score | X.XXXX | - |

### 3.4 Detection Metrics

| Metric | Value | 95% CI | Target |
|--------|-------|--------|--------|
| Invalid Document AUC-ROC | X.XXXX | [X, X] | ≥0.95 |
| Human Review Recall | X% | [X%, X%] | ≥95% |
| Human Review Precision | X% | [X%, X%] | ≥60% |
| False Positive Rate (Review) | X% | [X%, X%] | ≤20% |

---

## 4. Primary Metrics (Tesseract Fallback Path)

### 4.1 Per-Field Exact Match Accuracy

| Field | Correct | Total | Accuracy | 95% CI | Target |
|-------|---------|-------|----------|--------|--------|
| Amount | X | 75 | X% | [X%, X%] | ≥85% |
| Transaction Code | X | 75 | X% | [X%, X%] | ≥80% |
| Transaction Date | X | 75 | X% | [X%, X%] | ≥80% |
| Bank Name | X | 75 | X% | [X%, X%] | ≥90% |
| Sender Name (F1) | - | - | X% | [X%, X%] | ≥75% |

### 4.2 Full Record Accuracy

| Metric | Value | 95% CI | Target |
|--------|-------|--------|--------|
| All Fields Correct | X% | [X%, X%] | ≥65% |
| Amount + TxCode + Date Correct | X% | [X%, X%] | ≥70% |

---

## 5. Per-Slice Analysis (Required)

### 5.1 By Bank

| Bank | Amount Acc | TxCode Acc | Date Acc | Bank Acc | Full Record | N |
|------|------------|------------|----------|----------|-------------|---|
| Vietcombank | X% | X% | X% | X% | X% | X |
| Techcombank | X% | X% | X% | X% | X% | X |
| BIDV | X% | X% | X% | X% | X% | X |
| MBBank | X% | X% | X% | X% | X% | X |
| VPBank | X% | X% | X% | X% | X% | X |
| ACB | X% | X% | X% | X% | X% | X |
| SHB | X% | X% | X% | X% | X% | X |
| Sacombank | X% | X% | X% | X% | X% | X |
| VietinBank | X% | X% | X% | X% | X% | X |
| Agribank | X% | X% | X% | X% | X% | X |
| SeABank | X% | X% | X% | X% | X% | X |
| NAPAS | X% | X% | X% | X% | X% | X |

### 5.2 By Amount Range

| Range | Amount Acc | TxCode Acc | Date Acc | Full Record | N |
|-------|------------|------------|----------|-------------|---|
| <100K | X% | X% | X% | X% | X |
| 100K-500K | X% | X% | X% | X% | X |
| 500K-1M | X% | X% | X% | X% | X |
| 1M-5M | X% | X% | X% | X% | X |
| 5M-20M | X% | X% | X% | X% | X |
| >20M | X% | X% | X% | X% | X |

### 5.3 By Image Quality

| Quality | Amount Acc | TxCode Acc | OCR Conf | Full Record | N |
|---------|------------|------------|----------|-------------|---|
| Excellent | X% | X% | X.XX | X% | X |
| Good | X% | X% | X.XX | X% | X |
| Fair | X% | X% | X.XX | X% | X |
| Poor | X% | X% | X.XX | X% | X |

### 5.4 By Format

| Format | Amount Acc | TxCode Acc | Full Record | N |
|--------|------------|------------|-------------|---|
| JPEG | X% | X% | X% | X |
| PNG | X% | X% | X% | X |
| WebP | X% | X% | X% | X |
| HEIC | X% | X% | X% | X |

---

## 6. Failure Mode Analysis

### 6.1 Top Failure Categories

| Failure Mode | Count | % of Errors | Example |
|--------------|-------|-------------|---------|
| Amount misread (comma/decimal) | X | X% | "500.000" → 500 |
| Transaction code partial | X | X% | Missing prefix |
| Sender name truncated | X | X% | "NGUYEN VAN" vs "NGUYEN VAN A" |
| Bank misclassification | X | X% | VPBank → Vietcombank |
| Date format error | X | X% | dd/mm vs mm/dd |
| Low confidence correct | X | X% | Correct but < threshold |
| High confidence wrong | X | X% | Wrong but > threshold |

### 6.2 Confusion Matrix (Amount Ranges)

```
Predicted →
           <100K  100K-500K  500K-1M  1M-5M  5M-20M  >20M
Actual ↓
<100K        X        X        X      X       X      X
100K-500K    X        X        X      X       X      X
500K-1M      X        X        X      X       X      X
1M-5M        X        X        X      X       X      X
5M-20M       X        X        X      X       X      X
>20M         X        X        X      X       X      X
```

### 6.3 Confidence vs Accuracy (Reliability Diagram Data)

| Confidence Bin | Avg Confidence | Accuracy | Count |
|----------------|----------------|----------|-------|
| [0.0, 0.1) | X.XX | X% | X |
| [0.1, 0.2) | X.XX | X% | X |
| [0.2, 0.3) | X.XX | X% | X |
| [0.3, 0.4) | X.XX | X% | X |
| [0.4, 0.5) | X.XX | X% | X |
| [0.5, 0.6) | X.XX | X% | X |
| [0.6, 0.7) | X.XX | X% | X |
| [0.7, 0.8) | X.XX | X% | X |
| [0.8, 0.9) | X.XX | X% | X |
| [0.9, 1.0] | X.XX | X% | X |

---

## 7. Routing Performance

| Route | Count | % | Correct | Incorrect |
|-------|-------|---|---------|-----------|
| AUTO_VERIFY | X | X% | X | X |
| HUMAN_REVIEW | X | X% | X | X |
| DUPLICATE | X | X% | X | X |
| INVALID | X | X% | X | X |

### 7.1 Human Review Outcomes

| Outcome | Count | % of Reviews |
|---------|-------|--------------|
| Reviewer Approved (AI correct) | X | X% |
| Reviewer Corrected (AI wrong) | X | X% |
| Reviewer Rejected (Invalid) | X | X% |
| Reviewer Unsure → Escalated | X | X% |

---

## 8. Latency & Resource Metrics

| Metric | Ollama Vision | Tesseract Fallback |
|--------|---------------|-------------------|
| P50 Latency | X ms | X ms |
| P95 Latency | X ms | X ms |
| P99 Latency | X ms | X ms |
| Avg Memory | X MB | X MB |
| Peak Memory | X MB | X MB |
| GPU Memory (Ollama) | X MB | N/A |
| Fallback Rate | X% | - |

---

## 9. Comparison: Ollama vs Tesseract

| Metric | Ollama Vision | Tesseract | Winner |
|--------|---------------|-----------|--------|
| Amount Accuracy | X% | X% | - |
| TxCode Accuracy | X% | X% | - |
| Date Accuracy | X% | X% | - |
| Bank Accuracy | X% | X% | - |
| Full Record | X% | X% | - |
| Latency (P95) | X ms | X ms | - |
| Fallback Rate | X% | N/A | - |

---

## 10. Regression Check (vs Baseline)

| Metric | Baseline | Current | Delta | Status |
|--------|----------|---------|-------|--------|
| Amount Exact Match | X% | X% | X% | ✓/✗ |
| TxCode Exact Match | X% | X% | X% | ✓/✗ |
| Full Record Accuracy | X% | X% | X% | ✓/✗ |
| ECE | X.XXXX | X.XXXX | X.XXXX | ✓/✗ |
| Invalid Doc AUC | X.XXXX | X.XXXX | X.XXXX | ✓/✗ |

---

## 11. Artifacts Generated

```
evaluation_runs/2026-10-03_ollama_qwen2.5vl_3b/
├── metrics.json                 # All metrics in machine-readable format
├── metrics_test_set.csv         # Per-sample results
├── calibration_curves.json      # Calibration mappings
├── reliability_diagram.png      # Visualization
├── confusion_matrices.png       # Per-field confusion matrices
├── per_slice_metrics.csv        # Slice breakdown
├── failure_analysis.md          # Top failures with examples
├── routing_analysis.csv         # Routing decisions
├── regression_report.md         # vs baseline
└── evaluation_report.md         # This document (filled)
```

---

## 12. Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| AI Engineer (Ngọc) | | | ☐ |
| Backend Lead (Minh) | | | ☐ |
| QA Lead | | | ☐ |

---

## 13. Notes & Caveats

1. **Sample Size**: 75 test samples gives ~11% margin of error at 95% CI for 80% accuracy
2. **Confidence Intervals**: Wilson score intervals used for binomial proportions
3. **Calibration**: Fitted on train set (350), applied to test set (75)
4. **Thresholds**: Auto-verify 0.90, Human review 0.70 (from config)
5. **Known Limitations**: See `13_model_limitations.md`

---

*End of Evaluation Results Template — TO BE FILLED AFTER TESTING*
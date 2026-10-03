# 13_MODEL_LIMITATIONS.md

## Phase 3 AI Pipeline — Model Limitations & Known Failure Modes

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This document honestly documents the **known limitations, failure modes, and uncertainty areas** of the AI pipeline. Transparency about limitations is required for Phase 3 completion — we must not claim capabilities we haven't measured.

> **Principle**: "If you haven't measured it, you don't know it works."

---

## 2. Ollama Vision Model (qwen2.5vl:3b) Limitations

### 2.1 Unverified Capabilities

| Capability | Status | Evidence |
|------------|--------|----------|
| Vietnamese receipt OCR accuracy | ❌ **UNVERIFIED** | No evaluation dataset exists |
| Structured JSON output reliability | ❌ **UNVERIFIED** | No systematic testing |
| Vietnamese language understanding | ⚠️ **PARTIAL** | Model trained primarily on Chinese/English |
| Handwritten text recognition | ❌ **UNVERIFIED** | Receipts often have handwritten notes |
| Stamp/seal recognition | ❌ **UNVERIFIED** | Critical for Vietnamese receipts |
| QR code reading | ❌ **UNVERIFIED** | Many receipts have QR codes |
| Multi-receipt images | ❌ **UNVERIFIED** | Users may upload multiple receipts |

### 2.2 Known Vision Model Weaknesses (from literature)

| Weakness | Impact | Mitigation |
|----------|--------|------------|
| Small text (<12pt) | Misses transaction codes, amounts | Preprocess: upscale image |
| Low contrast / glare | Misses fields | Preprocess: CLAHE, denoise |
| Perspective distortion | Misreads aligned fields | Preprocess: perspective correction |
| Handwritten annotations | Confuses model | Mask handwritten regions |
| Stamps/seals overlapping text | Occludes critical fields | Detect and exclude regions |
| Non-standard receipt formats | Fails on unfamiliar layouts | Fallback to Tesseract |

### 2.3 Model-Specific Issues

```python
KNOWN_QWEN25VL_ISSUES = {
    "json_format_reliability": "Occasionally outputs markdown code fences instead of pure JSON",
    "confidence_calibration": "Self-reported confidence often overconfident (typical for LLMs)",
    "vietnamese_diacritics": "May normalize or drop diacritics in names",
    "amount_formatting": "May output '500,000' instead of integer 500000",
    "date_format_inconsistency": "May use dd/mm/yyyy or mm/dd/yyyy inconsistently",
    "timeout_behavior": "No streaming; full timeout before any response",
    "memory_usage": "~3.2GB VRAM + system RAM; OOM risk on small GPUs",
}
```

---

## 3. Tesseract OCR Limitations

### 3.1 Known Weaknesses

| Weakness | Impact | Current Mitigation |
|----------|--------|-------------------|
| Vietnamese diacritics | Low accuracy on ạ, ắ, ặ, ử, etc. | vie+eng langpack; multi-strategy |
| Table/column structure | Loses spatial relationships | Not used for layout analysis |
| Handwritten text | Near-zero accuracy | Not handled |
| Low resolution (<300 DPI) | Character confusion | Upscale in preprocessing |
| Glare/reflections | Noise in text regions | CLAHE, denoise strategies |
| Skewed/rotated text | Poor recognition | EXIF auto-rotate only |

### 3.2 Regex Extraction Limitations

| Limitation | Example Failure |
|------------|-----------------|
| Amount: Comma vs decimal ambiguity | "500.000" → 500 (Vietnam uses . as thousands) |
| Amount: No VND suffix | "Chuyển 500000" → may miss if no label |
| TxCode: New bank formats | New bank not in patterns → generic only |
| Sender: Name split across lines | "NGUYEN\nVAN A" → may not match |
| Bank: Abbreviations | "VCB" → works, but "Vietcom Bank" → may miss |
| Date: Ambiguous formats | "01/02/2024" → Jan 2 or Feb 1? |

---

## 4. Unified Pipeline Limitations

### 4.1 Confidence System Limitations

| Limitation | Impact |
|------------|--------|
| No field-level confidence from Ollama | Model returns single confidence; we distribute heuristically |
| Calibration requires 500+ labeled samples | Not yet collected |
| Risk penalties are heuristic | Not learned from data |
| Thresholds are fixed | Not adaptive per bank/quality |

### 4.2 Duplicate Detection Limitations

| Limitation | Impact |
|------------|--------|
| pHash: 10 Hamming threshold arbitrary | May miss near-duplicates or false positive |
| Fuzzy layer not implemented | Expensive; deferred |
| Transaction identity requires tx_code | Missing tx_code = no Layer 3 detection |
| In-memory only (current) | Lost on restart; Supabase persistence designed but not tested |

### 4.3 Student Matching Limitations

| Limitation | Impact |
|------------|--------|
| Vietnamese name variations | "Nguyễn Văn A" vs "Nguyen Van A" vs "A Nguyen" |
| Middle name handling | "Thị" often omitted in receipts |
| Nicknames/aliases | Not in roster |
| OCR errors in names | "NGUYEN VAN A" → "NGUYEN VAN 4" |

---

## 5. Data & Training Limitations

### 5.1 Evaluation Dataset

| Gap | Status | Required For |
|-----|--------|--------------|
| 500 real Vietnamese receipts | ❌ NOT COLLECTED | Phase 3 completion |
| Ground truth annotations (2x + verification) | ❌ NOT DONE | Accuracy measurement |
| Stratified by bank/amount/quality | ❌ NOT DONE | Per-slice metrics |
| Calibration curves | ❌ NOT FITTED | Confidence calibration |
| Regression baseline | ❌ NOT ESTABLISHED | Regression detection |

### 5.2 Synthetic Data Limitations

```python
SYNTHETIC_DATA_LIMITATIONS = {
    "visual_fidelity": "Templates lack real-world noise, compression, lighting",
    "layout_diversity": "Limited to known receipt formats",
    "text_rendering": "Perfect text → overestimates OCR accuracy",
    "vietnamese_realism": "May not capture real Vietnamese receipt quirks",
    "usage": "DEVELOPMENT ONLY — never report as production accuracy",
}
```

---

## 6. Operational Limitations

### 6.1 Infrastructure Dependencies

| Dependency | Risk | Mitigation |
|------------|------|------------|
| Ollama server (localhost) | Single point of failure | Health checks, circuit breaker, Tesseract fallback |
| GPU memory | OOM on concurrent requests | Queue requests, limit concurrency |
| Model loading time | Cold start ~10-30s | Warmup on startup, keep_alive=5m |
| Supabase for duplicate persistence | Network latency | Local cache, async writes |

### 6.2 Scalability Limits

| Limit | Current | Target |
|-------|---------|--------|
| Concurrent requests per worker | 1 (sequential) | 4 (async) |
| Images per minute | ~10 | >30 |
| Max image size | 10MB / 4000px | Configurable |
| Memory per worker | ~2GB | <2GB |

---

## 7. Security & Privacy Limitations

### 7.1 Current Gaps

| Gap | Risk | Status |
|-----|------|--------|
| No malware scanning on uploads | Malicious files | Deferred to Phase 2 |
| No rate limiting on vision endpoint | DoS via large images | Deferred to Phase 2 |
| PII in logs (sender names) | Privacy leak | Partial: not in structured logs |
| Image retention in Supabase | Storage growth | TTL policy not implemented |
| Prompt injection detection | Basic pattern matching | Implemented but not comprehensive |

### 7.2 Model Security

| Concern | Assessment |
|---------|------------|
| Model extraction attacks | Low risk (local only, no API exposure) |
| Data poisoning | Not applicable (pre-trained, frozen) |
| Adversarial images | Possible; no defense implemented |
| Output injection | Mitigated by JSON schema enforcement |

---

## 8. Compliance & Audit Limitations

| Requirement | Current Status | Gap |
|-------------|----------------|-----|
| Decision audit trail | Structured logs + evidence | Human review decisions not yet linked |
| Model version tracking | Model name in metadata | Model digest not enforced |
| Data lineage | Image hash → extraction → verification | Complete |
| Reproducibility | Deterministic Tesseract; Ollama non-deterministic | Temperature=0.1 helps but not guaranteed |

---

## 9. Failure Mode Catalog

### 9.1 Critical Failures (Block Auto-Verify)

| Failure Mode | Trigger | Detection | Fallback |
|--------------|---------|-----------|----------|
| Amount misread by 10x | Decimal/comma confusion | Range check (amount > 1B) | Human review |
| Transaction code missing | Blurry/cropped image | Required field check | Human review |
| Wrong bank identified | Similar logos | Cross-check with tx_code prefix | Human review |
| Date in future | OCR error | >1 day future check | Human review |
| Duplicate not detected | New image, same tx | Layer 3 (tx identity) | Backend DB constraint |

### 9.2 Degraded Performance (Auto-Verify but Wrong)

| Failure Mode | Likelihood | Detection Difficulty |
|--------------|------------|---------------------|
| Amount off by ±1000 | Medium | Low (no cross-check) |
| Sender name typo | High | Medium (student match catches) |
| Bank code vs name mismatch | Low | High (consistency check) |
| Time wrong by hours | Medium | Low (no reference) |

### 9.3 Silent Failures (Auto-Verify, Looks Correct, Is Wrong)

| Failure Mode | Why Silent | Mitigation |
|--------------|------------|------------|
| Correct amount, wrong sender | Sender matches another student | Student match confidence threshold |
| Correct tx_code, different bank | Bank misread but code valid | Bank name/code consistency check |
| Future date within 1 day | Timezone edge case | Max future days = 1 |

---

## 10. Honest Accuracy Estimates (Pre-Evaluation)

Based on architecture analysis and literature, **before evaluation**:

| Component | Estimated Accuracy | Confidence |
|-----------|-------------------|------------|
| Ollama Amount | 85-95% | LOW (unverified) |
| Ollama TxCode | 80-90% | LOW (unverified) |
| Ollama Date | 80-90% | LOW (unverified) |
| Ollama Bank | 90-95% | LOW (unverified) |
| Ollama Sender | 70-85% | LOW (unverified) |
| Tesseract Amount | 75-85% | MEDIUM (known from literature) |
| Tesseract TxCode | 70-80% | MEDIUM |
| Tesseract Date | 70-80% | MEDIUM |
| Tesseract Bank | 85-90% | MEDIUM |
| Tesseract Sender | 60-75% | MEDIUM |
| Student Matching | 85-95% | HIGH (existing tests) |
| Duplicate Detection | 95-99% | HIGH (deterministic) |

> **These are ESTIMATES ONLY. Do not report as measured accuracy.**

---

## 11. Required Measurements Before Production

| Measurement | Method | Success Criteria |
|-------------|--------|------------------|
| Amount exact match | Evaluation dataset | ≥95% (Ollama), ≥85% (Tesseract) |
| TxCode exact match | Evaluation dataset | ≥90% (Ollama), ≥80% (Tesseract) |
| Full record accuracy | Evaluation dataset | ≥80% (Ollama), ≥65% (Tesseract) |
| ECE calibration | Evaluation dataset | <0.05 |
| Invalid doc AUC | Evaluation dataset | ≥0.95 |
| Human review recall | Evaluation dataset | ≥95% |
| Per-slice parity | Evaluation dataset | No slice >10% below average |
| Latency P95 | Load test | <15s (Ollama), <10s (Tesseract) |
| Fallback rate | Production monitoring | <20% |

---

## 12. Recommended Improvements (Post-Phase 3)

### 12.1 Short Term (Phase 3.x)

1. **Collect evaluation dataset** (500 receipts)
2. **Run evaluation** and calibrate confidence
3. **Implement fuzzy duplicate layer**
4. **Add perspective correction** preprocessing
5. **Improve Vietnamese diacritics** in Tesseract (train custom model?)

### 12.2 Medium Term (Phase 4+)

1. **Fine-tune vision model** on Vietnamese receipts
2. **Add layout analysis** (table detection)
3. **Implement active learning** from human reviews
4. **Add ensemble** (Ollama + Tesseract + heuristic)
5. **Real-time monitoring** dashboard

### 12.3 Long Term (Phase 6+)

1. **Custom Vietnamese receipt model** (fine-tuned Qwen or similar)
2. **Multi-modal** (image + text from bank APIs)
3. **Continuous learning** pipeline
4. **A/B testing** framework for model versions

---

## 13. Summary: What We Know vs Don't Know

| Category | Known (Verified) | Unknown (Unverified) |
|----------|------------------|----------------------|
| **Architecture** | ✅ Design complete | ❌ Production performance |
| **Code** | ✅ Implemented | ❌ Battle-tested |
| **Tesseract OCR** | ✅ Unit tests pass | ❌ Vietnamese accuracy |
| **Regex Extraction** | ✅ Unit tests pass | ❌ Real-world coverage |
| **Verification Logic** | ✅ Unit tests pass | ❌ Threshold calibration |
| **Duplicate Detection** | ✅ Unit tests pass | ❌ Supabase persistence |
| **Ollama Vision** | ✅ Client works | ❌ Accuracy, reliability, calibration |
| **Confidence System** | ✅ Design complete | ❌ Calibration curves |
| **Human Review Flow** | ✅ Contracts defined | ❌ Integration with Phase 4/5 |
| **Evaluation** | ✅ Plan complete | ❌ Dataset, metrics, baseline |

---

## 14. Sign-off on Limitations

By acknowledging these limitations, the team confirms:

- [ ] No synthetic accuracy claims will be made
- [ ] Evaluation dataset will be collected before production
- [ ] Thresholds will be calibrated on real data
- [ ] Failure modes will be monitored in production
- [ ] Limitations will be communicated to stakeholders

| Role | Name | Date | Acknowledged |
|------|------|------|--------------|
| AI Engineer (Ngọc) | | | ☐ |
| Backend Lead (Minh) | | | ☐ |
| Tech Lead | | | ☐ |

---

*End of Model Limitations Documentation*
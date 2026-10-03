# AI Verification Result Contract

## Overview

This document defines the canonical contract for AI verification results produced by Ngọc (the AI system) and consumed by Minh's backend.

## VerificationResult Schema

```json
{
  "upload_id": "string (UUID)",
  "transaction_code": "string | null",
  "amount": "integer | null",
  "sender_name": "string | null",
  "bank_name": "string | null",
  "transaction_time": "string (ISO 8601) | null",
  "student_id": "string | null",
  "confidence": "float (0.0 - 1.0)",
  "status": "enum",
  "risk_flags": "array[string]",
  "ocr_version": "string",
  "extractor_version": "string",
  "matcher_version": "string",
  "preprocessor_version": "string",
  "verification_policy_version": "string",
  "evidence": "object",
  "duplicate_checks": "array[DuplicateCheckResult]",
  "created_at": "string (ISO 8601)",
  "processing_time_ms": "integer"
}
```

## Field Definitions

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `upload_id` | UUID | Unique identifier for the upload |
| `confidence` | float | Overall confidence score (0.0-1.0) |
| `status` | enum | Verification status (see below) |
| `ocr_version` | string | OCR engine version |
| `extractor_version` | string | Extraction rules version |
| `matcher_version` | string | Student matching version |
| `created_at` | ISO 8601 | Result creation timestamp |
| `processing_time_ms` | integer | Total processing time |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_code` | string | Bank transaction reference code |
| `amount` | integer | Transaction amount in VND (smallest unit) |
| `sender_name` | string | Extracted sender name |
| `bank_name` | string | Detected bank name |
| `transaction_time` | ISO 8601 | Transaction timestamp |
| `student_id` | string | Matched student ID from roster |
| `risk_flags` | array | List of risk indicators |
| `evidence` | object | Raw extraction evidence |
| `duplicate_checks` | array | Duplicate detection results |

## Status Enum

| Status | Description | Backend Action |
|--------|-------------|----------------|
| `PENDING` | Job queued, not yet processed | Wait |
| `PROCESSING` | Currently being processed | Wait |
| `NEEDS_REVIEW` | Low confidence or missing fields | Manual review required |
| `VERIFIED` | All checks passed | Post to ledger (after backend re-check) |
| `REJECTED` | Clearly invalid/fraudulent | Reject |
| `DUPLICATE` | Duplicate detected | Skip (already processed) |

## Risk Flags Enum

| Flag | Description |
|------|-------------|
| `MISSING_TRANSACTION_CODE` | No transaction code extracted |
| `MISSING_AMOUNT` | No amount extracted |
| `ABNORMAL_TEXT` | OCR text too short or abnormal |
| `ABNORMAL_TIMESTAMP` | Transaction time in future or too far past |
| `SENDER_MISMATCH` | Sender not matched to any student |
| `LOW_IMAGE_QUALITY` | OCR confidence below threshold |
| `DUPLICATE_RECEIPT` | Duplicate image detected |
| `INCONSISTENT_FIELDS` | Extracted fields have low confidence |

## DuplicateCheckResult Schema

```json
{
  "is_duplicate": "boolean",
  "layer": "string",
  "confidence": "float",
  "details": "object",
  "matched_upload_id": "string | null"
}
```

### Layers

| Layer | Description |
|-------|-------------|
| `file_hash` | SHA-256 exact file match |
| `perceptual_hash` | pHash near-duplicate match |
| `transaction_identity` | Same bank + transaction code |

## Evidence Object

Contains raw extraction data for audit:

```json
{
  "ocr": { "raw_text": "...", "confidence": 0.9, "lines": [...], ... },
  "extraction": {
    "amount": { "value": "50000", "confidence": 0.95, "source_text": "50.000 VND", "rule": "vnd_suffix" },
    "transaction_code": { ... },
    "sender": { ... },
    "bank": { ... },
    "datetime": { ... }
  },
  "matching": { "student_id": "...", "confidence": 0.94, "method": "exact", "candidates": [...] },
  "duplicate_checks": [...]
}
```

## Backend Integration

### Endpoint Expectation

POST `/api/v1/verification-results`

Request body: `VerificationResult`

### Backend Responsibilities

1. **Re-verify** all critical fields before ledger posting
2. **Enforce** database unique constraints (transaction_code + bank)
3. **Handle** idempotency (same upload_id processed multiple times)
4. **Audit** all results with version fields

### Response

```json
{
  "accepted": true,
  "ledger_entry_id": "uuid | null",
  "message": "string"
}
```

## Versioning

All version fields follow semantic versioning (MAJOR.MINOR.PATCH).

Breaking changes to extraction logic → MAJOR version bump
New patterns/rules added → MINOR version bump
Bug fixes → PATCH version bump

## Error Handling

If AI service fails to produce result:
- Status: `REJECTED`
- Confidence: 0.0
- Risk flags: Include error reason
- Evidence: Include error details

## Example: Successful Verification

```json
{
  "upload_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "transaction_code": "FT1234567890",
  "amount": 50000,
  "sender_name": "NGUYEN VAN AN",
  "bank_name": "MB Bank",
  "transaction_time": "2024-12-25T14:30:00Z",
  "student_id": "student-1",
  "confidence": 0.94,
  "status": "VERIFIED",
  "risk_flags": [],
  "ocr_version": "1.0.0",
  "extractor_version": "1.0.0",
  "matcher_version": "1.0.0",
  "preprocessor_version": "1.0.0",
  "verification_policy_version": "1.0.0",
  "evidence": { ... },
  "duplicate_checks": [
    { "is_duplicate": false, "layer": "file_hash", "confidence": 1.0, "details": {...} },
    { "is_duplicate": false, "layer": "perceptual_hash", "confidence": 1.0, "details": {...} },
    { "is_duplicate": false, "layer": "transaction_identity", "confidence": 1.0, "details": {...} }
  ],
  "created_at": "2024-12-25T14:30:05Z",
  "processing_time_ms": 2340
}
```

## Example: Needs Review

```json
{
  "upload_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
  "transaction_code": null,
  "amount": 50000,
  "sender_name": "NGUYEN VAN AN",
  "bank_name": "MB Bank",
  "transaction_time": "2024-12-25T14:30:00Z",
  "student_id": "student-1",
  "confidence": 0.65,
  "status": "NEEDS_REVIEW",
  "risk_flags": ["MISSING_TRANSACTION_CODE"],
  "ocr_version": "1.0.0",
  "extractor_version": "1.0.0",
  "matcher_version": "1.0.0",
  "preprocessor_version": "1.0.0",
  "verification_policy_version": "1.0.0",
  "evidence": { ... },
  "duplicate_checks": [...],
  "created_at": "2024-12-25T14:30:05Z",
  "processing_time_ms": 2100
}
```
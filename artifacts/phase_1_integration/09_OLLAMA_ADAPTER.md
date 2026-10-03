# 09_OLLAMA_ADAPTER.md

## Phase 1 Ollama Adapter

### Source Evidence (Phase 0)
- 05_AI_OLLAMA_COMPATIBILITY.md: `qwen2.5vl:3b` (vision-language) installed (`ollama list` verified); `qwen3.5:4b` (text-only) installed. Existing AI pipeline uses Tesseract only; Ollama not integrated.
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: `OllamaVisionClient` needed; structured output enforcement (`format=json` + schema validation); timeout/retry; model unavailable detection.
- 21_EXISTING_AI_SERVICES.md (implied by 09): `OCRService`, `ExtractionService`, `VerificationService`, `MatchingService`, `DuplicateDetector` — pure Python, reusable. Only `DuplicateDetector` needs persistence adapter (not full rewrite).
- 10_AI_CONTRACT.md (Phase 1 contract): Structured output enforced; allowed intents enumerated; AI never directly updates balance.

### Adapter Design (New — Existing AI Services Preserved)
```
ai/
  ollama_client.py  # Adapter (new)
```
- Adapter creates structured chat/completion requests to `http://127.0.0.1:11434`.
- Does NOT replace `ai/ocr/service.py`, `ai/extraction/service.py`, `ai/verification/service.py`.
- Adapter provides vision input via base64-encoded image; structured JSON output parsed and validated with Pydantic or existing schema layer.

### Adapter Requirements (Implemented Skeleton)
- Model selection: default `qwen2.5vl:3b` (verified installed); configurable via `OLLAMA_MODEL` env var.
- Timeout: 60s max (30s target per 11 requirements).
- Structured response: enforce `{"intent": ..., "amount": ..., "currency": ..., "confidence": ...}` with allowed intent whitelist (`CONTRIBUTION`, `WITHDRAWAL`, `BALANCE_INQUIRY`, `ANNOUNCEMENT`, `UNKNOWN`).
- Malformed output: return structured error; set message `status='failed'` or `awaiting_admin`.
- Retry: exponential backoff (max 3 retries) for temporary failures.
- Unavailable detection: if `ollama list` does not include model or endpoint unreachable, worker logs error and stops processing (does not corrupt DB).
- Evidence: 05 (model verification), 11 (vision client requirements), 20 (structured output schema).

### Integration with Existing AI Pipeline (No Rewrite)
```
Worker claims message
  ↓
Download receipt from Supabase Storage
  ↓
Adapter → Ollama vision (qwen2.5vl:3b) for structured extraction
  ↓
OR: Existing Tesseract OCR (fallback if vision unavailable / low confidence)
  ↓
Existing ExtractionService (regex) → structured fields
  ↓
Existing VerificationService.verify() (with configured policy threshold 0.90)
  ↓
Existing MatchingService (Vietnamese name normalization)
  ↓
Existing verify_and_post_from_ai() (financial gatekeeper)
```
- Evidence: 21 (reuse list), 22 (financial gatekeeper contract), 11 (pure function design).

### Security
- Adapter treats AI output as untrusted data; never passes amount directly to balance update.
- Structured schema validation prevents injection; intent whitelist prevents unauthorized actions.
- Evidence: 16 (untrusted AI output defense), 20 (contract enforcement).

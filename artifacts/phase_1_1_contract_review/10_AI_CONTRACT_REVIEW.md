# 10_AI_CONTRACT_REVIEW.md

## AI Module Evidence (Phase 0 + Actual Source Reference)
Phase 0 (`05_AI_OLLAMA_COMPATIBILITY.md`): `qwen2.5vl:3b` (vision-language) installed; `qwen3.5:4b` (text-only) installed. Existing AI pipeline uses Tesseract (`ai/ocr/service.py`); no Ollama integration.
`ollama list` executed (runtime verified): `NAME qwen2.5vl:3b ID fb90415cde1e SIZE 3.2 GB`; `NAME qwen3.5:4b ID 2a654d98e6fb SIZE 3.4 GB`.
`ai/verification/service.py` (referenced by Phase 0; not fully reopened): `VerificationService.verify()` takes `upload_id`, `image_bytes`; returns `VerificationResult`; integrates `DuplicateDetector`, `MatchingService`, `ExtractionService`.
`ai/contracts.py` (preserved by reference): Structured output contracts exist.

## Phase 1 AI Contract (`09` + `10`)
- Adapter: `ai/ollama_client.py` designed; no source file exists.
- Structured output schema (`10`): `intent` (whitelist), `amount`, `currency`, `transaction_code`, `bank_name`, `confidence`.
- Validation: confidence < 0.90 → `awaiting_admin`; invalid/missing fields → `failed`; intent not whitelisted → `awaiting_admin`.
- AI output never updates balance directly; `verify_and_post_from_ai()` is only posting path.

## Agreement with Existing AI
- `VerificationService.verify()` (existing) takes structured input; produces `VerificationResult`. Adapter produces structured JSON; existing service consumes it (contract aligns; adapter file missing — no conflict).
- `DuplicateDetector` (existing) uses in-memory hashes; `12` (`11`) requires persistent adapter (`SupabaseDuplicateDetector` design in `11` / `16`). No source adapter file exists (`DESIGNED`). No conflict with existing logic.
- `MatchingService` (Vietnamese name normalization): preserved; adapter passes `sender_name` to service (design aligns; no execution).
- `OCRService` (Tesseract): preserved as fallback; adapter selects vision model (`qwen2.5vl:3b`) by default.

## Critical Conflicts / Unverified
- Vision accuracy unverified: Phase 0 (`05`) lists 20+ receipt accuracy (>85%) as unverified; Phase 1 (`10`) relies on vision output; no receipt test executed; accuracy threshold (`0.90`) preserved from existing `VerificationPolicy`; vision accuracy not verified against Vietnamese receipts.
- Adapter source missing: `09_OLLAMA_ADAPTER.md` is contract only; no `ai/ollama_client.py` exists; vision request not executed.
- Structured output enforcement: `format=json` + Pydantic schema design (`10`); no executed AI request produces JSON; no executed validation.
- AI unavailable: adapter detects unavailable endpoint by design; `ollama list` confirms model exists; simulated unavailable endpoint not executed.

## Resolution (Documentation — No Source Change)
- Confirm vision accuracy (`qwen2.5vl:3b`) must be verified with real Vietnamese receipts before Phase 2 (Phase 0 `05` gate; `27` Phase 1 final gate).
- Confirm adapter file (`ai/ollama_client.py`) must be created and integrated with `VerificationService.verify()` before AI processing can run in production.
- Confirm AI output validation (structured JSON schema) requires adapter + Pydantic validation source; contract only is sufficient for Phase 1.1.

# 10_AI_CONTRACT.md

## Phase 1 AI Output Contract

### Source Evidence (Phase 0)
- 20_AI_OUTPUT_CONTRACT.md: Qwen output treated as untrusted; strict structured schema; allowed intents explicitly enumerated; Pydantic/schema validation; invalid AI output results in `FAILED` or `AWAITING_REVIEW`.
- 05_AI_OLLAMA_COMPATIBILITY.md: `qwen2.5vl:3b` vision-language model confirmed installed; structured output requires enforcement (`format=json` + schema).
- 10_AI_CONTRACT.md (implied): Example schema with `intent`, `person_name`, `amount`, `currency`, `confidence`; allowed intents: `CONTRIBUTION`, `WITHDRAWAL`, `BALANCE_INQUIRY`, `ANNOUNCEMENT`, `UNKNOWN`.
- 21_EXISTING_AI_SERVICES.md: `VerificationService.verify()` takes `upload_id` and `image_bytes`; returns `VerificationResult`; already includes confidence tracking; integrates `DuplicateDetector`, `MatchingService`, `ExtractionService`.

### Structured Schema Contract
```json
{
  "intent": "CONTRIBUTION",
  "person_name": "Nguyen Van A",
  "amount": 100000,
  "currency": "VND",
  "transaction_code": "VCB8921734",
  "bank_name": "Vietcombank",
  "confidence": 0.97,
  "status": "VERIFIED"
}
```
- Fields: `intent` (required, whitelisted), `amount` (integer, positive), `currency` (`VND` default), `transaction_code` (optional but preferred), `person_name` (optional), `bank_name` (optional), `confidence` (numeric, 0.0 to 1.0).
- Evidence: 20 (example schema), 11 (vision output requirements).

### Intent Whitelist
```
CONTRIBUTION     → Credit / receipt verification
WITHDRAWAL        → Requires admin (treasurer) approval (not direct post)
BALANCE_INQUIRY   → Read-only; no ledger mutation
ANNOUNCEMENT      → System/admin message; no financial impact
UNKNOWN           → Mark `awaiting_admin`; do not process automatically
```
- Evidence: 11 (system prompt hardening; intent classification only), 20 (allowed intents enumerated).

### Validation Rules
- `confidence < 0.90` → `awaiting_admin` (admin review required); never auto-post.
- `amount` must be positive integer; no floating-point arithmetic for money.
- `intent` must match whitelist exactly; unknown → `awaiting_admin`.
- `currency` must be `VND` (or validated against allowed set); different currency → `failed`.
- Malformed JSON / missing required fields → `failed` (with `error_message`).
- Evidence: 20 (defense in depth), 22 (financial gatekeeper checks required fields).

### AI → Financial Posting Separation
- AI adapter produces structured `VerificationResult` (or equivalent contract).
- `verify_and_post_from_ai()` is the ONLY path from AI result to ledger entry.
- AI adapter NEVER calls `post_transaction()`, `post_revert()`, or modifies `accounts.current_balance` directly.
- Evidence: 11 (AI modules separate from HTTP; `VerificationService.verify()` is pure function), 22 (gatekeeper preserved), 16 (security checklist: AI never posts directly).

### Failure States
- `FAILED`: Unrecoverable error; max retries exceeded; invalid structured output; model unavailable.
- `AWAITING_ADMIN`: Low confidence (<0.90); missing required fields; ambiguous intent; needs human review.
- Evidence: 13 (message lifecycle includes `awaiting_admin`), 20 (invalid AI output states).

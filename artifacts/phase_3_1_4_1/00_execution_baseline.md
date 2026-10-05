# Phase 3.1 + 4.1 Execution Baseline

**Date**: 2026-10-04
**Branch**: master
**Commit**: f7ac634 - Merge Phase 3 AI Pipeline + Phase 4 Guest Chat

## Git Status
- Current branch: `master`
- No uncommitted changes to source code
- Untracked: `artifacts/master_consolidation/`, `artifacts/phase_2_merge_resolution/`

## Backend Structure

### class-fund-backend-v0.1/class-fund-backend/
- **API Routes**: `/uploads`, `/messages`, `/chat`, `/internal/vision`, `/fund`, `/campaigns`, `/auth`, `/health`, `/public`, `/ai_internal`
- **Models**: 20 SQLAlchemy models including Upload, Message, Transaction, ExtractedTransaction, Account, Student, Campaign, LedgerEntry, etc.
- **Schemas**: Pydantic schemas for request/response validation
- **Services**: ledger.py (financial gatekeeper), ollama_client.py, supabase_client.py, audit.py, activity.py
- **Worker**: Persistent worker with atomic claim, lease handling, retry logic
- **Migrations**: 4 migrations (0001-0004)

### ai/ package (local AI pipeline)
- **ocr/service.py**: Multi-strategy preprocessing + Tesseract OCR
- **extraction/service.py**: Rule-based extraction for amount, transaction_code, sender, bank, datetime
- **verification/service.py**: Orchestrates OCR → Extraction → Matching → Duplicate Detection → Verification
- **duplicate/service.py**: 3-layer duplicate detection (file hash, perceptual hash, transaction identity)
- **matching/service.py**: Vietnamese name matching with fuzzy logic
- **contracts.py**: Pydantic contracts for all AI pipeline data structures

## Frontend Structure

### classfund/classfund/
- **Pages**: GuestChatPage.tsx (main guest chat interface)
- **Components**: MessageComposer, ImageUploadArea, MessageList, MessageItem, StatusBadge, RecallButton, SenderNameInput, PublicCodeDisplay, EmptyState
- **Hooks**: useChat.ts (orchestrates realtime + polling + upload + recall)
- **Lib**: api.ts, polling.ts, realtime.ts, recall.ts, upload.ts
- **Types**: chat.ts (comprehensive TypeScript types)

## Test Results

### Backend (class-fund-backend-v0.1)
- **20/20 tests PASS**
  - test_financial_core.py: 4 tests
  - test_idempotency.py: 7 tests
  - test_recall.py: 9 tests

### AI Pipeline (ai/)
- **108/108 tests PASS**
  - test_contracts.py: 12 tests
  - test_duplicate.py: 12 tests
  - test_extraction.py: 15 tests
  - test_integration.py: 5 tests
  - test_matching.py: 11 tests
  - test_ocr.py: 11 tests
  - test_verification.py: 12 tests

### Frontend
- **TypeScript strict check: PASS** (no errors)
- **Production build: SUCCESS** (Vite build completed)

## Current Blocker Inventory

### Phase 3.1 - AI Pipeline Blockers

1. **Ollama Vision Integration Not Fully Wired**
   - `ollama_client.py` exists but vision endpoint in `vision.py` calls it without proper timeout/circuit breaker
   - No connection pooling or health checks for Ollama
   - Vision model output validation is minimal

2. **Unified Transaction Schema Gap**
   - `ai/contracts.py` has `VerificationResult` but backend uses `ExtractedTransaction` model
   - Two separate schemas not fully aligned
   - Field-level confidence not propagated to database model

3. **Duplicate Detection - Database Layer Missing**
   - `ai/duplicate/service.py` is in-memory only
   - No database-backed duplicate detection for production
   - Perceptual hash not stored in Upload model consistently

4. **Human Review State Machine**
   - `UploadStatus.NEEDS_REVIEW` exists but transition logic split between vision.py and ledger.py
   - No explicit API for admin review actions

5. **Prompt Injection Defense**
   - No input sanitization for OCR text before sending to Ollama
   - Vision prompt is static, no defense against embedded instructions

6. **Evaluation Infrastructure**
   - No evaluation harness for annotated Vietnamese receipts
   - No measurement of accuracy targets (95% amount, 90% ref, ECE < 0.05)

### Phase 4.1 - Guest Chat Blockers

1. **API Contract Mismatch**
   - Frontend `MessageCreateRequest` uses `attachment_ids` (array) but backend `MessageCreate` uses `attachment_id` (single string)
   - Frontend sends `message_type` as 'TEXT'|'RECEIPT'|'IMAGE'|'ANNOUNCEMENT' but backend expects different pattern

2. **Realtime/Polling Integration Gaps**
   - Hybrid adapter created but Supabase credentials not configured for local dev
   - Polling fallback doesn't handle message deduplication properly
   - No connection state persistence across refreshes

3. **Upload Flow Integration**
   - Frontend uploads to `/api/v1/uploads` but backend expects form data with `uploader_name`
   - Upload status polling not implemented in frontend
   - No handling for upload duplicate detection response

4. **Recall Security**
   - Recall tokens stored in `sessionStorage` (client-side only)
   - No token expiry enforcement on frontend
   - Frontend doesn't validate recall eligibility before showing button

5. **Message Status Synchronization**
   - Optimistic updates but no conflict resolution with server state
   - Processing status not displayed with extraction results
   - No display for low-confidence extraction requiring review

## External Dependencies Status

- **Supabase**: Not configured (no SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY in env)
- **Ollama**: Local service expected at http://127.0.0.1:11434 with models qwen2.5vl:3b and qwen3.5:4b
- **PostgreSQL**: Expected at localhost:5432 (configured in DATABASE_URL)
- **Tesseract OCR**: Required for ai/ocr/service.py (system dependency)

## Financial Invariants Verification

All Phase 2 tests pass, confirming:
- ✅ Idempotency with stable keys
- ✅ Recall before post prevention
- ✅ Reversal preserves original transaction
- ✅ Worker lease and recovery
- ✅ No AI bypass of financial gatekeeper
- ✅ No service-role key in frontend
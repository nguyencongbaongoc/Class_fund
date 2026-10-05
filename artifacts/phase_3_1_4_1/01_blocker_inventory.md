# Phase 3.1 + 4.1 Blocker Inventory

**Generated**: 2026-10-04
**Based on**: Baseline inspection of master branch

---

## Phase 3.1 - AI Pipeline Blockers

### BLOCKER-3.1.1: Ollama Vision Integration Incomplete
**Severity**: HIGH
**Location**: `class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py`, `app/api/routes/vision.py`

**Issues**:
1. No circuit breaker pattern - Ollama failures can block worker indefinitely
2. No connection pooling - new httpx.Client per request
3. Vision endpoint doesn't handle Ollama unavailability gracefully
4. No request/response correlation IDs for tracing
5. Timeout configuration not validated against model inference time
6. Text fallback model (`qwen3.5:4b`) not integrated in vision endpoint

**Required Fixes**:
- Add circuit breaker with configurable failure threshold
- Add connection pooling for httpx client
- Implement graceful degradation (OCR-only mode when Ollama unavailable)
- Add structured logging with correlation IDs
- Integrate text fallback in vision processing pipeline

---

### BLOCKER-3.1.2: Dual Schema Divergence (ai/contracts.py vs Backend Models)
**Severity**: HIGH
**Location**: `ai/contracts.py` vs `class-fund-backend-v0.1/class-fund-backend/app/models/models.py`

**Issues**:
1. `VerificationResult` (ai) vs `ExtractedTransaction` (backend) - overlapping but incompatible
2. Field-level confidence in `ExtractionEvidence` (ai) but single `confidence` Decimal in backend
3. `VerificationResult` has `risk_flags`, `duplicate_checks`, `evidence` - not in backend
4. Backend `ExtractedTransaction` missing: `currency`, `extraction_method`, `source_image_identifier`
5. No unified schema for "proposed transaction" passed to financial gatekeeper

**Required Fixes**:
- Create unified `ProposedTransaction` schema in backend
- Migrate `ExtractedTransaction` to store field-level confidence as JSON
- Add missing fields to backend model
- Ensure single source of truth for extraction data structure

---

### BLOCKER-3.1.3: Duplicate Detection - In-Memory Only
**Severity**: HIGH
**Location**: `ai/duplicate/service.py`

**Issues**:
1. `DuplicateDetector` uses in-memory sets/dicts - lost on restart
2. Perceptual hash not persisted to `Upload.perceptual_hash` column
3. No database-backed duplicate queries for production scale
4. Worker cannot detect duplicates across restarts
5. No fuzzy matching for transaction reference variations

**Required Fixes**:
- Persist perceptual hashes to database on upload
- Add database indexes for duplicate detection queries
- Implement `DuplicateDetector.load_from_database()` for worker startup
- Add transaction reference normalization for fuzzy matching

---

### BLOCKER-3.1.4: Human Review State Machine Fragmented
**Severity**: MEDIUM
**Location**: `app/api/routes/vision.py`, `app/services/ledger.py`, `app/models/models.py`

**Issues**:
1. `UploadStatus.NEEDS_REVIEW` set in vision.py (line 79, 115) AND ledger.py (line 403, 413)
2. No API endpoint for admin to approve/reject reviewed items
3. No notification mechanism for review queue
4. Reviewer identity not tracked
5. No SLA or escalation for stuck review items

**Required Fixes**:
- Consolidate review state transitions in single service
- Add `/internal/review` API endpoints
- Track `reviewed_by`, `reviewed_at`, `review_notes`
- Add review queue monitoring

---

### BLOCKER-3.1.5: Prompt Injection Vulnerability
**Severity**: HIGH
**Location**: `app/services/ollama_client.py` (line 77-95), `ai/extraction/service.py`

**Issues**:
1. Vision prompt is static - no defense against instructions embedded in receipt images
2. OCR text passed directly to text fallback model without sanitization
3. No validation that model output matches expected schema before parsing
4. Model could return extra fields or malicious JSON structures

**Required Fixes**:
- Add prompt injection detection in OCR text (look for instruction-like patterns)
- Strict JSON schema validation with `pydantic` before processing
- Strip/escape control characters from OCR text
- Limit model output tokens and structure

---

### BLOCKER-3.1.6: No Evaluation Infrastructure
**Severity**: MEDIUM
**Location**: N/A - Missing entirely

**Issues**:
1. No test dataset of annotated Vietnamese receipts
2. No evaluation harness to measure:
   - Amount extraction accuracy
   - Transaction reference accuracy
   - Date extraction accuracy
   - Bank identification accuracy
   - Field-level confidence calibration (ECE)
   - Invalid extraction rate
   - Duplicate detection precision/recall

**Required Fixes**:
- Create evaluation dataset structure (even if empty initially)
- Implement evaluation runner that uses `VerificationService`
- Add metrics calculation (accuracy, precision, recall, ECE)
- Document dataset requirements (500 annotated samples target)

---

## Phase 4.1 - Guest Chat Blockers

### BLOCKER-4.1.1: API Contract Mismatch - Message Creation
**Severity**: CRITICAL
**Location**: 
- Frontend: `src/types/chat.ts` line 55-62 (`MessageCreateRequest.attachment_ids: string[]`)
- Backend: `app/api/routes/messages.py` line 24-30 (`MessageCreate.attachment_id: Optional[str]`)

**Issues**:
1. Frontend sends array `attachment_ids`, backend expects single `attachment_id`
2. Frontend `message_type` includes 'RECEIPT', 'ANNOUNCEMENT' - backend only validates 'TEXT'|'RECEIPT'|'IMAGE'
3. Backend doesn't validate `attachment_ids` array - only checks first item

**Required Fixes**:
- Align frontend/backend: support multiple attachments OR single attachment consistently
- Update backend to accept `attachment_ids` array
- Add validation for all message types

---

### BLOCKER-4.1.2: Upload Flow Integration Broken
**Severity**: CRITICAL
**Location**: 
- Frontend: `src/lib/api.ts` line 42-52 (`uploadReceipt`)
- Backend: `app/api/routes/uploads.py` line 18-49

**Issues**:
1. Frontend `uploadReceipt` sends `file` + `uploader_name` - MATCHES ✓
2. Backend returns `UploadOut` with `id`, `uploader_name`, `original_filename`, `status`, `created_at`
3. Frontend expects `UploadResponse` with same fields - MATCHES ✓
4. **BUT**: Frontend `useChat.ts` line 328-335 calls `uploadAdapter.uploadFile()` which uses `apiClient.uploadReceipt()`
5. **MISSING**: Frontend doesn't poll for upload processing status
6. **MISSING**: No handling of `DUPLICATE` upload status response
7. **MISSING**: No correlation between upload and message creation

**Required Fixes**:
- Add upload status polling in frontend
- Handle duplicate upload response (show existing extraction)
- Link upload ID to message creation properly
- Show extraction results in message UI

---

### BLOCKER-4.1.3: Realtime/Polling - Supabase Credentials Missing
**Severity**: HIGH
**Location**: `src/hooks/useChat.ts` line 81-83, `src/lib/realtime.ts` line 27-34

**Issues**:
1. `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` not in frontend `.env`
2. Hybrid adapter falls back to polling immediately
3. Polling adapter makes individual `/messages/{id}` requests - inefficient
4. No deduplication of realtime + polling events
5. Connection state not persisted across page refresh

**Required Fixes**:
- Document required Supabase environment variables
- Optimize polling to batch message status requests
- Add event deduplication in hybrid adapter
- Persist connection state in localStorage

---

### BLOCKER-4.1.4: Recall Security - Client-Side Only Token Storage
**Severity**: HIGH
**Location**: `src/lib/recall.ts` line 139-176 (`createSessionStorageRecallConfig`)

**Issues**:
1. Recall tokens stored only in `sessionStorage` - lost on tab close
2. No token expiry enforcement on frontend
3. Frontend shows recall button based on `canRecall()` which only checks local state
4. No server-side validation of recall eligibility before showing UI
5. Token replay protection only on backend - frontend doesn't prevent double-click

**Required Fixes**:
- Add token expiry display and enforcement
- Store tokens in more persistent storage (localStorage with encryption)
- Add server-side recall eligibility check endpoint
- Disable recall button during pending recall

---

### BLOCKER-4.1.5: Message Status Display Incomplete
**Severity**: MEDIUM
**Location**: `src/components/chat/MessageItem.tsx`, `src/components/chat/StatusBadge.tsx`

**Issues**:
1. `MessageItem` doesn't display extraction results (amount, transaction_code, bank, confidence)
2. No UI for "awaiting_review" state with extraction preview
3. No display of `rejection_reason` from upload status
4. Low-confidence results not visually distinguished
5. Duplicate candidate vs confirmed duplicate not differentiated

**Required Fixes**:
- Add extraction result display in MessageItem for RECEIPT/IMAGE messages
- Create `ExtractionResultDisplay` component
- Visual indicators for confidence levels (high/medium/low)
- Distinct UI for duplicate candidate vs confirmed duplicate

---

### BLOCKER-4.1.6: Error Handling and Retry Gaps
**Severity**: MEDIUM
**Location**: `src/hooks/useChat.ts`, `src/components/chat/ImageUploadArea.tsx`

**Issues**:
1. Upload retry doesn't preserve file reference correctly
2. Message send failure doesn't offer retry with same content
3. Network errors not differentiated from server errors
4. No exponential backoff for polling/realtime reconnection
5. Toast notifications for errors but no persistent error state

**Required Fixes**:
- Improve upload retry with file blob preservation
- Add message send retry with optimistic update rollback
- Categorize errors (network, validation, server, auth)
- Add retry with backoff for connection failures

---

## Cross-Cutting Blockers

### BLOCKER-X.1: Environment Configuration
**Severity**: HIGH
**Location**: `.env` files (missing)

**Issues**:
1. No `.env.example` for frontend with all required variables
2. Backend `.env.example` missing Ollama and Supabase vars
3. No documentation of required external services

**Required Fixes**:
- Create comprehensive `.env.example` files
- Document all required external services
- Add validation on startup for required config

---

### BLOCKER-X.2: Database Migration for Phase 3.1 Fields
**Severity**: MEDIUM
**Location**: `alembic/versions/` (only 0001-0004 exist)

**Issues**:
1. `Upload.perceptual_hash` column exists but not populated
2. `ExtractedTransaction` missing field-level confidence columns
3. No `reviewed_by`, `reviewed_at` columns for audit trail
4. No `extraction_method` column to track OCR vs Vision vs Hybrid

**Required Fixes**:
- Create migration 0005 for AI pipeline fields
- Create migration 0006 for review audit fields
- Ensure migrations are reversible

---

## Blocker Priority Matrix

| ID | Component | Severity | Effort | Dependencies |
|----|-----------|----------|--------|--------------|
| BLOCKER-4.1.1 | API Contract | CRITICAL | Low | None |
| BLOCKER-4.1.2 | Upload Flow | CRITICAL | Medium | BLOCKER-4.1.1 |
| BLOCKER-3.1.1 | Ollama Integration | HIGH | Medium | None |
| BLOCKER-3.1.2 | Schema Unification | HIGH | High | BLOCKER-3.1.3 |
| BLOCKER-3.1.3 | Duplicate Detection | HIGH | Medium | BLOCKER-X.2 |
| BLOCKER-3.1.5 | Prompt Injection | HIGH | Low | None |
| BLOCKER-4.1.3 | Realtime Config | HIGH | Low | External (Supabase) |
| BLOCKER-4.1.4 | Recall Security | HIGH | Medium | None |
| BLOCKER-3.1.4 | Review State Machine | MEDIUM | Medium | BLOCKER-3.1.2 |
| BLOCKER-4.1.5 | Status Display | MEDIUM | Medium | BLOCKER-3.1.2 |
| BLOCKER-4.1.6 | Error Handling | MEDIUM | Low | None |
| BLOCKER-3.1.6 | Evaluation Infra | MEDIUM | High | Dataset |
| BLOCKER-X.1 | Env Config | HIGH | Low | None |
| BLOCKER-X.2 | Migrations | MEDIUM | Low | BLOCKER-3.1.2, 3.1.3 |

---

## Resolution Order (Recommended)

1. **BLOCKER-X.1** - Environment configuration (enables all other work)
2. **BLOCKER-4.1.1** - API contract alignment (unblocks frontend/backend integration)
3. **BLOCKER-4.1.2** - Upload flow integration (core user journey)
4. **BLOCKER-3.1.5** - Prompt injection defense (security)
5. **BLOCKER-3.1.1** - Ollama integration hardening (reliability)
6. **BLOCKER-3.1.3** - Duplicate detection persistence (data integrity)
7. **BLOCKER-3.1.2** - Schema unification (architectural consistency)
8. **BLOCKER-X.2** - Database migrations (schema changes)
9. **BLOCKER-3.1.4** - Review state machine (workflow completion)
10. **BLOCKER-4.1.4** - Recall security hardening (security)
11. **BLOCKER-4.1.3** - Realtime/polling optimization (UX)
12. **BLOCKER-4.1.5** - Status display (UX)
13. **BLOCKER-4.1.6** - Error handling (robustness)
14. **BLOCKER-3.1.6** - Evaluation infrastructure (quality assurance)
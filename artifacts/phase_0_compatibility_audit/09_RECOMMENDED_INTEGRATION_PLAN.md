# PHASE 0 — RECOMMENDED INTEGRATION PLAN

## Executive Summary
**Status: PARTIALLY_COMPATIBLE → REQUIRES 4-5 WEEK IMPLEMENTATION** — The smallest safe integration path preserves existing backend logic and AI pipeline, adds Supabase integration layer, builds a lightweight local polling worker, and connects the frontend to realtime cloud data.

---

## 1. OVERALL STRATEGY

### Design Principles
1. **No destructive rewrites** — Reuse `ledger.py`, AI modules, frontend UI
2. **Smallest safe path** — Add missing integration only; don't redesign working parts
3. **Defense in depth** — RLS (database) + Backend validation (service) + Idempotency (request) + Audit (trail)
4. **Responsibility boundaries preserved** — Minh (DB/auth/ledger), Ngọc (AI/worker), Hải (UI/realtime)
5. **Offline resilience** — Cloud accepts messages; worker processes when online

---

## 2. PHASE BREAKDOWN

### Phase 0.5: Foundation (Week 1) — Minh
**Deliverable**: Supabase project with schema, auth, RLS, storage, realtime

**Tasks**:
1. Create Supabase project (database, auth, storage, realtime enabled)
2. Add `user_roles`, `messages`, `worker_status`, `message_receipts` tables
3. Generate Alembic revisions (not `create_all`)
4. Apply migrations to Supabase
5. Write `supabase/rls_policies.sql` (all 15 tables + new ones)
6. Enable Realtime publications (`ALTER PUBLICATION`)
7. Create Storage bucket `receipts` with RLS policies
8. Configure CORS for Vercel domain (future)
9. Seed admin user (OWNER_TREASURER) via Supabase Auth Admin API
10. Store `SERVICE_ROLE_KEY` securely (Windows Credential Manager template)

**Success Criteria**:
- `supabase` connection works from Windows PC
- `SELECT * FROM accounts` works with anon key
- `SELECT * FROM user_roles WHERE user_id = auth.uid()` returns role
- RLS blocks unauthorized INSERT/UPDATE
- Storage upload works with `ANON_KEY`

### Phase 1: AI/Worker Integration (Week 2-3) — Ngọc
**Deliverable**: Local worker processes messages end-to-end

**Tasks**:
1. Create `worker/` package (new directory)
2. `worker/main.py`: Polling loop (`FOR UPDATE SKIP LOCKED` claim)
3. `worker/claim.py`: Atomic claim with lease expiration
4. `worker/storage.py`: Download receipt from Supabase Storage
5. `worker/ollama_client.py`: Vision client (`qwen2.5vl:3b`) with structured output
6. `worker/duplicate_persister.py`: Load/Save hashes to Supabase
7. `worker/heartbeat.py`: `worker_status` updates every 10s
8. `worker/recovery.py`: Reclaim expired leases on startup
9. Modify `ai/duplicate/service.py`: Use `SupabaseDuplicateDetector`
10. Align `VerificationPolicy.min_confidence_threshold` to 0.90
11. Add timeout/retry (10 min max, exponential backoff)
12. Test with 10 real Vietnamese receipts

**Success Criteria**:
- Worker claims `pending` message within 5 seconds of poll
- Ollama returns structured JSON with `transaction_code`, `amount`, `sender_name`
- `verify_and_post_from_ai()` posts to Supabase DB
- `worker_status` shows `online`/`processing`
- Duplicate detection works across restarts
- Lease expiration recovers stale messages

### Phase 2: Frontend Integration (Week 3-4) — Hải
**Deliverable**: Frontend talks to Supabase, realtime updates work

**Tasks**:
1. Create `src/lib/supabase.ts` (Supabase client with `ANON_KEY`)
2. Create `src/lib/auth/` — Login/logout, session management, role fetch from `user_roles`
3. Create `src/lib/api/` — Typed clients for mutations (use Supabase directly for read, backend for AI/post if needed)
4. Create `src/hooks/useRealtimeMessages.ts` (subscribe to `messages` table)
5. Create `src/hooks/useWorkerStatus.ts` (subscribe to `worker_status`)
6. Create `src/lib/adapters.ts` — Snake_case ↔ camelCase, Decimal ↔ number
7. Replace `AppContext` mock state:
   - Remove mock `MOCK_USERS` role switching
   - Replace `ledgerEntries` with `useRealtimeLedger()`
   - Replace `chatMessages` with `useRealtimeMessages()`
   - Replace `campaign` with `useCampaign()` hook
8. Update `UploadReceiptView`: Actual `POST /uploads` (or direct Supabase Storage upload + DB insert)
9. Add message status badges (`pending`, `processing`, `awaiting_admin`, `processed`, `recalled`)
10. Add `public_code` generation/display (`CF-YYYYMMDD-{uuid}`)
11. Add `THU HỒI` button (only for own messages, only if `status != 'recalled'`)
12. Add admin review modal (`awaiting_admin` messages)
13. Create `vercel.json` with SPA rewrites
14. Configure `.env` templates for Vercel

**Success Criteria**:
- User can log in (Supabase Auth)
- User sees realtime message updates
- User sees message status change
- User can upload receipt (to Storage)
- User sees `CF-...` code next to message
- User can click `THU HỒI` and sees reversal in ledger
- Admin can review `awaiting_admin` messages

### Phase 3: Hardening & Testing (Week 4-5) — All
**Deliverable**: Production-ready hybrid system

**Tasks**:
1. Rate limiting (`pg_cron` or middleware): 30 msg/min per user
2. Offline message queue (IndexedDB): Store pending, sync on reconnect
3. Security: RLS test matrix (anon/member/admin/service role)
4. Security: Recall authorization (token check on every attempt)
5. Security: Double-recall prevention (idempotency on reversal endpoint)
6. Security: Worker claims only pending messages (race test with 2 workers)
7. AI: Structured output enforcement (`format=json`, schema validation)
8. AI: Timeout/retry testing (simulate slow Ollama)
9. Integration: End-to-end test (guest → message → AI → ledger → realtime → recall → reversal)
10. Vercel deploy to preview domain
11. Load testing (100 concurrent chat users, 10 receipt uploads/min)
12. Documentation (`README`, `docs/` updates)

---

## 3. CRITICAL GATES BEFORE IMPLEMENTATION

### Gate 1: Ollama Vision (Blocks Phase 1)
- [ ] `qwen2.5vl:3b` extracts `transaction_code`, `amount`, `sender_name`, `bank_name` from 20+ real Vietnamese bank receipts
- [ ] Accuracy ≥ 85% at 0.90 confidence threshold
- [ ] Timeout < 30s average, < 60s max
- [ ] JSON output valid 95%+ of time

**If FAILS**: Fallback to Tesseract-only pipeline; increase admin review rate; lower confidence threshold; document limitations.

### Gate 2: RLS Security (Blocks Phase 1)
- [ ] All 15 tables have RLS enabled
- [ ] Policies tested: anon (read public), member (read own conversation, insert own message), treasurer (full fund access), moderator (campaign/student access), service role (full, worker only)
- [ ] No unauthorized INSERT/UPDATE/DELETE succeeds
- [ ] `FOR UPDATE SKIP LOCKED` claim works under 2-worker concurrency

**If FAILS**: Simplify permissions (fewer roles); use backend API gateway instead of direct Supabase mutations; add application-level authorization middleware.

### Gate 3: Integration End-to-End (Blocks Phase 2)
- [ ] Guest sends chat message
- [ ] Message stored in `messages` (Supabase)
- [ ] Realtime updates frontend
- [ ] Worker claims `pending` message
- [ ] Ollama processes receipt
- [ ] Backend validates and posts to `transactions`
- [ ] Ledger updates
- [ ] Realtime updates `ledger_entries`
- [ ] User sees `VERIFIED` status
- [ ] User clicks `THU HỒI`
- [ ] System creates reversal (not delete)
- [ ] Balance corrected
- [ ] Realtime updates balance
- [ ] Original message remains with `recalled` status
- [ ] Second recall attempt rejected

---

## 4. IMPLEMENTATION SEQUENCE (WEEK BY WEEK)

### Week 1: Foundation
**Mon-Tue** (Minh):
- Create Supabase project, configure auth
- Run migrations, create new tables
- Write RLS policies SQL

**Wed-Thu** (Minh):
- Create Storage bucket `receipts`
- Configure CORS for future Vercel domain
- Seed admin user

**Fri** (All):
- Weekly check: Supabase connection from Windows
- Review RLS test results
- Confirm `SERVICE_ROLE_KEY` storage plan

### Week 2: AI/Worker Core
**Mon-Tue** (Ngọc):
- Build `worker/main.py` (polling loop)
- Build `worker/claim.py` (atomic claim)
- Build `worker/storage.py` (Supabase download)

**Wed-Thu** (Ngọc):
- Build `worker/ollama_client.py` (vision model)
- Build `worker/duplicate_persister.py` (DB persistence)
- Integrate `VerificationService`
- Test claim + AI + backend post

**Fri** (Ngọc + Minh):
- End-to-end: message → claim → AI → ledger
- Test duplicate detection across restarts
- Test lease expiration recovery

### Week 3: AI Refinement + Frontend Auth
**Mon-Tue** (Ngọc):
- Structured output enforcement (JSON schema)
- Timeout/retry testing
- Test 50 receipts; calibrate confidence

**Wed-Fri** (Hải):
- `src/lib/supabase.ts`
- `src/lib/auth/` (login/logout/session)
- `src/lib/api/` (typed clients)
- `vercel.json`

### Week 4: Frontend Realtime + Integration
**Mon-Tue** (Hải):
- Replace `AppContext` mock state
- `useRealtimeMessages`, `useWorkerStatus`
- Data adapters (snake_case ↔ camelCase)
- `upload` endpoint (Supabase Storage + DB)

**Wed-Thu** (Hải + Ngọc):
- Message status badges (`pending`, `processing`, `awaiting_admin`, etc.)
- Recall button with token mechanism
- Admin review modal
- Integration testing

**Fri** (All):
- End-to-end full flow
- Security: RLS + recall token + double-recall
- Load: concurrent users, upload rate

### Week 5: Hardening + Deploy
**Mon-Wed** (All):
- Rate limiting (`pg_cron`)
- Offline queue (`IndexedDB`)
- Error boundaries
- Documentation (`README`, `docs/`, runbooks)

**Thu** (Minh + Hải):
- Final security audit: RLS matrix, penetration test (manual)
- Vercel deploy (preview)

**Fri** (All):
- Load testing
- Final review
- Approval gate confirmation
- **STOP** — Await user approval for any further work

---

## 5. MINIMUM CODE TO ADD (ESTIMATE)

### Minh (Backend/DB) — ~600 lines
`
├── supabase/rls_policies.sql              (~150 lines SQL)
├── supabase/migrations/                  (~100 lines Alembic revisions)
├── supabase/realtime_publications.sql    (~20 lines SQL)
├── worker/heartbeat.py                   (~50 lines)
├── worker/recovery.py                    (~80 lines)
└── .env.template updates                  (~20 lines)
`

### Ngọc (AI/Worker) — ~900 lines
`
├── worker/
│   ├── main.py                            (~100)
│   ├── claim.py                           (~80)
│   ├── heartbeat.py                      (~50)
│   ├── storage.py                         (~60)
│   ├── ollama_client.py                  (~120)
│   ├── vision_extractor.py               (~100)
│   ├── duplicate_persister.py            (~70)
│   └── retry_logic.py                    (~80)
├── ai/
│   ├── duplicate/service.py              (+adapter, ~50)
│   ├── worker/queue.py                  (+poll mode, ~80)
│   └── contracts.py                      (no changes needed)
```

### Hải (Frontend) — ~1,200 lines
`
├── src/lib/
│   ├── supabase.ts                       (~30)
│   ├── auth/                             (~200 total)
│   │   ├── AuthContext.tsx              (~60)
│   │   ├── LoginPage.tsx                 (~80)
│   │   ├── useSession.ts                 (~60)
│   ├── api/
│   │   ├── client.ts                     (~80)
│   │   └── mutations.ts                  (~100)
│   └── adapters.ts                       (~60)
├── src/hooks/
│   ├── useRealtimeMessages.ts           (~100)
│   ├── useWorkerStatus.ts               (~60)
│   ├── useCampaign.ts                   (~50)
│   └── useLedger.ts                     (~50)
├── src/views/
│   ├── ChatView.tsx                      (+realtime + badges, ~150)
│   ├── UploadReceiptView.tsx            (+real storage, ~50)
│   ├── LedgerView.tsx                   (+realtime, ~30)
│   ├── DashboardView.tsx                (+realtime, ~30)
│   ├── CampaignView.tsx                 (+realtime, ~20)
│   └── PublicFundView.tsx               (+realtime, ~20)
└── vercel.json                          (~20)
`

**Total New**: ~2,700 lines (no rewrites of core logic)

---

## 6. SMALL SAFETY CHECKLIST (Before Any Phase 1 Work)

### Before Code Changes
- [ ] User confirms `qwen2.5vl:3b` is acceptable AI model
- [ ] User confirms Supabase as cloud layer (not alternative like Firebase)
- [ ] User confirms Vercel for frontend hosting
- [ ] User confirms Windows PC as worker host
- [ ] User approves responsibility split (Minh/Ngọc/Hải)
- [ ] User approves 4-5 week timeline

### Before First Commit
- [ ] `git init` or commit current audit artifacts
- [ ] `.env` never committed (verification only)
- [ ] `SERVICE_ROLE_KEY` never committed
- [ ] No secrets in any file

---

## 7. WHAT ALREADY WORKS (Can Be Reused Immediately)

### Backend Financial Engine (Minh)
- `post_transaction()` — safe, idempotent, audit complete
- `post_revert()` — safe, preserves original, audit complete
- `calculate_balance()` — derived from immutable ledger
- `verify_and_post_from_ai()` — validates AI before posting (critical security gate)

### AI Pipeline (Ngọc)
- `OCRService` with 6 preprocessing strategies
- `ExtractionService` with 5 regex extractors
- `VerificationService` with configurable policy
- `DuplicateDetector` with 3-layer detection
- `MatchingService` with Vietnamese name normalization

### Frontend Design (Hải)
- Complete Liquid Glass design system
- 8 fully-functional view components
- Responsive layout (mobile + desktop)
- Mock state management covers all needed data structures
- TypeScript interfaces align with backend schemas

---

## 8. FINAL RECOMMENDATION STATEMENT

**RECOMMEND INTEGRATION PATH**: **Option D — Refactor Only Integration Components**

Justification:
- Existing backend logic is sound (financial integrity verified by tests and code inspection)
- Existing AI pipeline is well-structured (pure Python library, reusable)
- Existing frontend is production-quality (design, interaction, state management)
- Only missing piece is **connection layer** (Supabase, Realtime, Auth, Worker)

**No component requires replacement** — only adapters and new integration code.

**The smallest safe path is 4-5 weeks with three parallel tracks** (DB/Auth, AI/Worker, Frontend/Realtine) converging in Week 4 for integration testing.

---

## 9. CONFIRMATION: NO IMPLEMENTATION YET

**CONFIRMED**: This report and all Phase 0 audit work (original + addendums A and B) contains:
- Zero code modifications to existing source files
- Zero database modifications
- Zero package installations/upgrades
- Zero configuration file changes
- Zero user account creation
- Zero financial transactions submitted
- Zero production service deployments
- Zero changes to Ollama models

**STOP HERE** — Await user approval before Phase 1 implementation.

---

## 10. NEXT ACTIONS (For User Review)

1. Read `11_HYBRID_ARCHITECTURE_COMPATIBILITY.md`
2. Read `18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md`
3. Confirm `qwen2.5vl:3b` acceptable for Vietnamese receipt OCR
4. Confirm Supabase + Vercel + Windows worker architecture
5. Confirm 4-5 week timeline acceptable
6. Confirm responsibility split (Minh/Ngọc/Hải)
7. Confirm critical risk acceptance (guest authorization, AI accuracy, security)
8. Give explicit approval: "Proceed to Phase 1" or specify modifications

**No work should begin until explicit approval received.**
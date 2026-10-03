# PHASE 0 ADDENDUM — HYBRID INTEGRATION GAP ANALYSIS

## Executive Summary
**Status: SIGNIFICANT GAPS REQUIRE IMPLEMENTATION** — The existing three components (Backend, Frontend, AI) have solid foundations but lack the integration layer for hybrid deployment. This report maps exact gaps and the minimal implementation path.

---

## 1. COMPONENT REUSE MATRIX

### Backend (Minh) — `class-fund-backend-v0.1/class-fund-backend`

| Module | Reuse | Adapt | Replace | Notes |
|--------|-------|-------|---------|-------|
| `ledger.py` | ✅ 100% | | | Pure functions, no HTTP deps |
| `models.py` | ✅ 100% | | | SQLAlchemy models work with Supabase |
| `schemas.py` | ✅ 100% | | | Pydantic v2 compatible |
| `verify_and_post_from_ai()` | ✅ 100% | | | Core financial gatekeeper |
| `audit.py`, `activity.py` | ✅ 100% | | | Simple helpers |
| `ai_internal.py` (routes) | | ✅ | | Convert to direct function calls |
| `auth.py`, `deps.py` | | ✅ | | Replace with Supabase Auth |
| `fund.py`, `campaigns.py` | | ✅ | | Frontend calls Supabase directly |
| `uploads.py` | | ✅ | | Frontend → Supabase Storage |
| `public.py`, `chat.py` | | ✅ | | Frontend → Supabase client |
| `main.py` (FastAPI app) | | | ✅ | Worker runs without HTTP server |

### Frontend (Hải) — `classfund/classfund`

| Module | Reuse | Adapt | Replace | Notes |
|--------|-------|-------|---------|-------|
| All Views (`*.tsx`) | ✅ 90% | | | UI logic solid; replace data source |
| `AppContext.tsx` | | ✅ | | Replace mock with API/Realtime hooks |
| `mockDatabase.ts` | | | ✅ | Remove; use dev mock only |
| Types (`types/index.ts`) | ✅ 100% | | | Align with backend schemas |
| Components (`components/`) | ✅ 100% | | | Design system complete |
| `vite.config.ts` | ✅ 100% | | | Add Vercel config |
| API Client | | | ✅ | **NEW**: `src/lib/api/` |
| Auth Integration | | | ✅ | **NEW**: `src/lib/auth/` |
| Realtime Hooks | | | ✅ | **NEW**: `src/hooks/useRealtime*` |

### AI (Ngọc) — `ai/`

| Module | Reuse | Adapt | Replace | Notes |
|--------|-------|-------|---------|-------|
| `ocr/service.py` | ✅ 100% | | | Tesseract + preprocessing |
| `extraction/service.py` | ✅ 100% | | | Regex extractors |
| `verification/service.py` | ✅ 100% | | | Policy orchestration |
| `matching/service.py` | ✅ 100% | | | Student matching |
| `duplicate/service.py` | | ✅ | | Persist hashes to Supabase |
| `worker/queue.py` (Celery) | | | ✅ | Replace with Supabase polling |
| Ollama integration | | | ✅ | **NEW**: Vision model client |

---

## 2. INTEGRATION CONTRACTS (SHARED INTERFACES)

### Contract 1: Message Schema (Frontend ↔ Worker ↔ Backend)

```typescript
// src/types/message.ts (NEW - shared)
interface Message {
  id: string;                    // UUID
  conversation_id: string;       // UUID
  sender_id: string;             // UUID (auth.uid())
  content: string;
  message_type: 'TEXT' | 'RECEIPT' | 'ANNOUNCEMENT' | 'SYSTEM' | 'AI_INTENT';
  status: 'pending' | 'processing' | 'awaiting_admin' | 'processed' | 'failed';
  ai_intent?: 'CONTRIBUTION' | 'WITHDRAWAL' | 'BALANCE_INQUIRY' | 'UNKNOWN';
  ai_result?: {
    transaction_code: string;
    amount: number;
    sender_name: string;
    bank_name: string;
    confidence: number;
    storage_path?: string;       // Supabase Storage path
  };
  ai_confidence?: number;
  transaction_id?: string;       // UUID from transactions table
  error_message?: string;
  is_pinned?: boolean;
  created_at: string;            // ISO 8601
  processed_at?: string;
}
```

### Contract 2: AI Verification Result (Worker → Backend)

```python
# ai/contracts.py (EXISTING - VerificationResult)
class VerificationResult(BaseModel):
    upload_id: UUID
    transaction_code: str | None
    amount: int | None
    sender_name: str | None
    bank_name: str | None
    transaction_time: datetime | None
    student_id: str | None
    confidence: float  # 0-1
    status: VerificationStatus  # PENDING, PROCESSING, NEEDS_REVIEW, VERIFIED, REJECTED, DUPLICATE
    risk_flags: list[RiskFlag]
    evidence: dict
    duplicate_checks: list[DuplicateCheckResult]
    processing_time_ms: int
```

**Worker calls**: `verify_and_post_from_ai(db, upload, extraction, account, actor_id, idempotency_key)`

### Contract 3: Financial Ledger (Backend ↔ Frontend via Supabase)

```typescript
// LedgerEntry from Supabase (snake_case)
interface LedgerEntry {
  id: string;
  transaction_id: string;
  type: 'CREDIT' | 'DEBIT' | 'REVERT';
  amount: number;           // integer VND
  currency: 'VND';
  transaction_code: string | null;
  source: 'IMAGE' | 'MANUAL' | 'REVERT';
  status: 'VERIFIED' | 'REVERTED';
  upload_id: string | null;
  created_by: string | null;
  created_at: string;       // ISO 8601
  effective_at: string;
  original_entry_id: string | null;  // for REVERT
  note: string | null;
}
```

### Contract 4: Worker Status (Worker → Frontend via Realtime)

```sql
-- worker_status table
worker_id uuid PRIMARY KEY,
status varchar(20),           -- 'online', 'offline', 'processing'
model_name varchar(100),
last_heartbeat timestamptz,
last_processed_at timestamptz,
current_job_id uuid REFERENCES messages(id),
metadata jsonb
```

---

## 3. GAP ANALYSIS BY RESPONSIBILITY AREA

### Minh (Backend, Database, Auth, Financial Integrity)

| Gap | Current | Required | Effort |
|-----|---------|----------|--------|
| Supabase DB connection | Local PostgreSQL | `DATABASE_URL` = Supabase pooler | Low |
| Alembic migrations | `create_all()` | Proper migration files | Medium |
| RLS policies | None | Full policy set for all tables | High |
| Supabase Auth integration | Custom JWT | `user_roles` table + RLS helpers | High |
| Service-role key usage | N/A | Worker uses service role | Low |
| Storage integration | Local filesystem | Supabase Storage bucket | Medium |
| Realtime publications | None | `ALTER PUBLICATION` for 6 tables | Low |
| Audit log immutability | App-level | RLS: no DELETE policy | Low |
| Idempotency key enforcement | Backend only | Also in worker calls | Low |

### Ngọc (AI, OCR, Extraction, Verification, Duplicate Detection)

| Gap | Current | Required | Effort |
|-----|---------|----------|--------|
| Ollama vision client | None | `httpx` client for `qwen2.5vl:3b` | Medium |
| Structured output | Regex only | JSON schema enforcement | Medium |
| Duplicate persistence | In-memory | Supabase `uploads` + `transactions` | Medium |
| Worker integration | Celery/Redis | Supabase polling loop | High |
| Receipt download | Local file | Supabase Storage download | Low |
| Confidence threshold | 0.90 config | Align with backend `AI_CONFIDENCE_THRESHOLD` | Low |
| Vietnamese receipt handling | Tesseract vie+eng | Test Ollama vision accuracy | Unknown |
| Timeout/retry | Celery config | Custom in polling loop | Medium |

### Hải (Frontend, UI/UX, Chat, Public Pages)

| Gap | Current | Required | Effort |
|-----|---------|----------|--------|
| API client layer | None | `src/lib/api/` with typed fetch | High |
| Supabase Auth UI | Mock `switchRole()` | Login page, session management | High |
| Realtime subscriptions | None | `useRealtimeMessages`, `useWorkerStatus` | Medium |
| Data transformation | Mock direct use | Snake_case ↔ camelCase adapters | Medium |
| Error boundaries | None | React error boundaries + toast | Low |
| Offline queue | None | IndexedDB for pending messages | Medium |
| Vercel deployment | Vite config only | `vercel.json`, env vars | Low |
| Public fund page | Mock data | Real Supabase queries | Low |
| Campaign/roster | Mock data | Real Supabase queries | Low |

---

## 4. MINIMUM VIABLE INTEGRATION PATH

### Phase 0.5: Foundation (Week 1-2)
**Goal**: Supabase project + schema + auth working

| Task | Owner | Deliverable |
|------|-------|-------------|
| Create Supabase project | Minh | Project URL, keys |
| Run Alembic migrations on Supabase | Minh | Schema deployed |
| Create RLS policies SQL | Minh | `supabase/rls_policies.sql` |
| Enable Realtime publications | Minh | 6 tables published |
| Create Storage bucket `receipts` | Minh | Bucket + policies |
| Create `user_roles` table | Minh | Table + admin seed |
| Create `messages` + `worker_status` tables | Minh | Migration file |
| Test Supabase Auth (email/password) | Minh/Hải | Working login |

### Phase 1: Worker Core (Week 2-3)
**Goal**: Local worker processes messages end-to-end

| Task | Owner | Deliverable |
|------|-------|-------------|
| Supabase polling worker skeleton | Ngọc | `worker/main.py` |
| Atomic claim with `FOR UPDATE SKIP LOCKED` | Ngọc | `worker/claim.py` |
| Supabase Storage download | Ngọc | `worker/storage.py` |
| Ollama vision client | Ngọc | `worker/ollama_client.py` |
| Integrate `VerificationService` | Ngọc | Zero changes needed |
| Call `verify_and_post_from_ai()` | Ngọc | Pass idempotency key |
| Persist duplicate hashes | Ngọc | Update `DuplicateDetector` |
| Worker heartbeat + status table | Ngọc | `worker/heartbeat.py` |
| Lease expiration on startup | Ngọc | Reclaim stale messages |
| Test with real receipt image | Ngọc/MinH | End-to-end flow |

### Phase 2: Frontend Integration (Week 3-4)
**Goal**: Frontend talks to Supabase, realtime works

| Task | Owner | Deliverable |
|------|-------|-------------|
| Supabase client setup | Hải | `src/lib/supabase.ts` |
| Auth context + login page | Hải | `src/context/AuthContext.tsx` |
| API client for mutations | Hải | `src/lib/api/mutations.ts` |
| Realtime message hook | Hải | `src/hooks/useRealtimeMessages.ts` |
| Replace `AppContext` mock data | Hải | Use hooks + API |
| Snake_case ↔ camelCase adapter | Hải | `src/lib/adapters.ts` |
| Worker status indicator | Hải | `src/hooks/useWorkerStatus.ts` |
| Admin review modal | Hải | For `awaiting_admin` messages |
| Vercel deploy config | Hải | `vercel.json`, env vars |
| Deploy to Vercel preview | Hải | Working preview URL |

### Phase 3: Polish & Hardening (Week 4-5)
**Goal**: Production-ready hybrid system

| Task | Owner | Deliverable |
|------|-------|-------------|
| Rate limiting (pg_cron) | Minh | Message/upload rate limits |
| MFA for admin accounts | Minh | Supabase Auth MFA |
| Service role key rotation | Minh | Documented procedure |
| AI prompt hardening | Ngọc | System prompt + JSON schema |
| Comprehensive error handling | All | User-facing error toasts |
| Offline message queue | Hải | IndexedDB + sync on reconnect |
| Load testing | All | 100 concurrent users |
| Security audit | All | RLS test matrix, pen test |
| Documentation | All | README, API docs, runbooks |

---

## 5. DEPENDENCY ORDER (CRITICAL PATH)

```
1. Supabase Project + Schema (Minh)
   ↓
2. RLS Policies + Realtime + Storage (Minh)
   ↓
3. Worker: Polling + Claim + Ollama (Ngọc)  ← CAN START AFTER #1
   ↓
4. Worker: VerificationService + Ledger Posting (Ngọc)  ← NEEDS #2 (DB)
   ↓
5. Frontend: Auth + API Client (Hải)  ← NEEDS #2 (Auth)
   ↓
6. Frontend: Realtime + Data Adapters (Hải)  ← NEEDS #3 (Worker produces data)
   ↓
7. Integration Testing (All)
   ↓
8. Vercel Deploy + Worker Install (All)
```

**Critical Path**: Minh's Supabase setup → Ngọc's worker → Hải's frontend integration

---

## 6. SHARED ARTIFACTS TO CREATE

| Artifact | Location | Owners |
|----------|----------|--------|
| `message.ts` types | `shared/types/` or duplicated | All |
| `VerificationResult` contract | `ai/contracts.py` (existing) | Ngọc → Minh |
| `supabase/rls_policies.sql` | `supabase/` | Minh |
| `supabase/migrations/` | `supabase/migrations/` | Minh |
| `worker/` package | `worker/` | Ngọc |
| `src/lib/api/` | `classfund/src/lib/api/` | Hải |
| `src/hooks/useRealtime*` | `classfund/src/hooks/` | Hải |
| `.env.example` files | Each project root | All |

---

## 7. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ollama vision accuracy low | High | High | Fallback to Tesseract; admin review threshold |
| Supabase RLS blocks legitimate queries | Medium | High | Thorough policy testing matrix |
| Worker crashes silently | Medium | High | Heartbeat alerting; auto-restart (systemd/NSSM) |
| Message loss during worker offline | Low | High | Supabase retains `pending` messages |
| Duplicate credits from retry | Low | Critical | Idempotency keys at every layer |
| Vercel cold starts delay realtime | Low | Medium | Keep Supabase connection warm |
| Schema migration conflicts | Medium | High | Single migration file; review before apply |
| Vietnamese OCR accuracy | High | Medium | Test 50+ real receipts; tune confidence |
| Supabase connection limits | Low | High | Worker pool_size=2; PgBouncer config |

---

## 8. ESTIMATED EFFORT SUMMARY

| Area | New Code | Modified Code | Config/Infra | Total |
|------|----------|---------------|--------------|-------|
| Backend/DB (Minh) | ~200 lines | ~100 lines | High | 40 hrs |
| AI/Worker (Ngọc) | ~800 lines | ~200 lines | Medium | 60 hrs |
| Frontend (Hải) | ~1500 lines | ~500 lines | Low | 80 hrs |
| **Total** | **~2500 lines** | **~800 lines** | | **~180 hrs** |

---

## 9. GO/NO-GO CRITERIA

### Go to Phase 1 Implementation If:
- [ ] Supabase project created and accessible
- [ ] Alembic migration runs cleanly on Supabase
- [ ] RLS policies tested against all 4 roles
- [ ] Worker can connect to Supabase and claim message
- [ ] Ollama `qwen2.5vl:3b` returns structured JSON for test receipt
- [ ] Frontend can authenticate with Supabase Auth
- [ ] Realtime subscription receives `INSERT` events

### No-Go (Blockers):
- Supabase connection fails from Windows PC
- Ollama vision model cannot extract transaction codes reliably
- RLS policies cannot express required permissions
- Financial integrity tests fail with Supabase DB

---

## 10. CONFIDENCE ASSESSMENT

- **Verified**: All existing code capabilities, Supabase feature support
- **Partially Verified**: Integration patterns (standard architectures)
- **Assumed**: Ollama vision model accuracy, Supabase performance at scale
- **Not Verified**: End-to-end integration, production load, security audit
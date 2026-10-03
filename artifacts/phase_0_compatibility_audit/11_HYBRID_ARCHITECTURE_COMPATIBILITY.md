# PHASE 0 ADDENDUM — HYBRID ARCHITECTURE COMPATIBILITY AUDIT

## Target Architecture Summary
- **Cloud**: Vercel Frontend + Supabase (PostgreSQL, Auth, Realtime, Storage)
- **Local**: Python worker on Windows + Ollama at `127.0.0.1:11434`
- **Flow**: User → Vercel → Supabase → Local Worker (polls/claims) → AI → Backend Validation → Ledger → Supabase Realtime → Frontend
- **Requirement**: System must accept messages while local PC is OFF; worker resumes on restart

---

## 1. FRONTEND DEPLOYABILITY TO VERCEL

### Status: **COMPATIBLE WITH REMEDIATION**

| Finding | Evidence | Impact | Remediation |
|---------|----------|--------|-------------|
| **No API base URL configuration** | `vite.config.ts` only has dev server config; no `import.meta.env.VITE_API_URL` or similar in any source file | Frontend cannot be deployed to Vercel without knowing backend URL | Add `VITE_API_BASE_URL` env var, create `src/lib/api/client.ts` with base URL from env |
| **No authentication flow** | `AppContext.tsx` uses `switchRole()` with mock users only; no login form, token storage, or interceptors | Cannot integrate with Supabase Auth | Implement login page, token storage (localStorage/cookie), Axios/fetch interceptor for Authorization header |
| **Hardcoded mock data** | All views read from `mockDatabase.ts` via `AppContext` | Zero real data in production | Replace mock data with API calls; keep mock as dev fallback |
| **CORS compatible** | Backend allows `http://localhost:3000`; frontend runs on 3000 | ✅ Compatible for local dev | Vercel domain must be added to backend CORS |
| **Build output** | `vite build` outputs to `dist/` — standard for Vercel | ✅ Compatible | Configure Vercel build command: `bun run build` |
| **Static assets** | `ASSET_PATHS` uses local `/src/assets/` and external URLs | ✅ Compatible | Local assets copied to `dist/` by Vite |
| **No server-side rendering** | Pure SPA with Vite + React 19 | ✅ Compatible | Vercel SPA fallback needed (`vercel.json` with rewrites) |

### Missing for Vercel Deployment
1. `vercel.json` with SPA rewrite rules
2. Environment variables: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
3. API client layer (`src/lib/api/`)
4. Authentication integration with Supabase Auth
5. Realtime subscription hooks (`src/hooks/useRealtime.ts`)

---

## 2. FRONTEND ASSUMPTIONS ABOUT LOCAL BACKEND

### Status: **INCOMPATIBLE (Assumes Local Backend)**

| Assumption | Evidence | Conflict with Hybrid |
|------------|----------|---------------------|
| **All mutations are local** | `AppContext.addLedgerEntry()`, `revertTransaction()`, `addManualExpense()` modify local state only | Must become API calls to Supabase/cloud |
| **No network layer** | Zero `fetch`/`axios` calls in 20+ source files | Must add complete API client |
| **Role switching is UI-only** | `switchRole()` cycles mock users | Must map to real Supabase Auth roles |
| **Real-time via local state** | Chat, ledger, campaign updates are immediate local mutations | Must subscribe to Supabase Realtime |
| **File upload simulated** | `UploadReceiptView` uses `URL.createObjectURL()` preview only | Must upload to Supabase Storage or backend |
| **No error boundaries** | No try/catch for network errors | Must add error handling for cloud failures |
| **No offline support** | Assumes always online | Must handle offline queue for messages |

---

## 3. BACKEND AS WORKER (NO PUBLIC EXPOSURE)

### Status: **PARTIALLY COMPATIBLE**

| Component | Can Run as Worker? | Evidence | Changes Needed |
|-----------|-------------------|----------|----------------|
| **FastAPI app** | ❌ No — designed as HTTP server | `main.py` creates FastAPI with routers, CORS, lifespan | Extract business logic (ledger, verification) into pure functions/classes |
| **Database session** | ✅ Yes — `get_db()` yields SQLAlchemy session | `session.py:11-16` — standard session factory | Point `DATABASE_URL` to Supabase PostgreSQL |
| **Ledger service** | ✅ Yes — pure Python functions | `ledger.py` — no HTTP dependencies | No changes needed |
| **Auth/Deps** | ❌ No — `get_current_user` requires HTTP request | `deps.py:16-28` — FastAPI `Depends` on `OAuth2PasswordBearer` | Replace with service-role key or worker identity |
| **AI Internal Endpoint** | ❌ No — HTTP endpoint | `ai_internal.py:13` — `@router.post("/uploads/{id}/result")` | Convert to direct function call `verify_and_post_from_ai()` |
| **Upload file serving** | ❌ No — `FileResponse` | `ai_internal.py:16-21` — `GET /uploads/{id}/file` | Worker reads from Supabase Storage directly |
| **Public endpoints** | ❌ No — public API | `public.py`, `chat.py`, etc. | Not needed for worker; frontend calls Supabase directly |
| **Alembic migrations** | ✅ Yes — CLI tool | `alembic/` — standard migrations | Run against Supabase |

### Worker Architecture Required
```
Local Worker Process:
├── Poll Supabase for pending messages (status='pending')
├── Claim atomically (UPDATE ... SET status='processing', worker_id=..., claimed_at=now WHERE id=... RETURNING *)
├── Download receipt from Supabase Storage
├── Run AI pipeline (OCR → Extraction → Verification)
├── Call verify_and_post_from_ai() with Supabase DB session
├── Update message status (processed/failed/awaiting_admin)
├── Emit Realtime event via Supabase (or DB trigger)
└── Heartbeat to worker_status table
```

---

## 4. DATABASE MIGRATION TO SUPABASE

### Status: **COMPATIBLE WITH ADAPTERS**

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **PostgreSQL** | ✅ Compatible | `DATABASE_URL` uses `postgresql+psycopg`; Supabase is PostgreSQL 15+ |
| **SQLAlchemy 2.x** | ✅ Compatible | `pyproject.toml`: `sqlalchemy>=2.0,<3.0` |
| **Alembic migrations** | ✅ Compatible | `alembic/versions/0001_initial.py` uses `Base.metadata.create_all` |
| **UUID primary keys** | ✅ Compatible | All models use `String(36)` UUID strings |
| **Decimal money** | ✅ Compatible | `Numeric(18,2)` for amounts — maps to PostgreSQL `numeric` |
| **Foreign keys** | ✅ Compatible | All FKs defined in models |
| **Unique constraints** | ✅ Compatible | `UNIQUE(bank_account_id, transaction_code)`, `UNIQUE(upload_id)`, etc. |
| **Indexes** | ✅ Compatible | Defined on status, FK columns |
| **JSON columns** | ✅ Compatible | `audit_logs.before_data/after_data`, `students.aliases`, `idempotency_keys.response_body` |
| **Timezone-aware timestamps** | ✅ Compatible | `DateTime(timezone=True)` with `utcnow()` default |

### Required Adapters/Changes
1. **Connection pooling** — Supabase uses PgBouncer (transaction mode); SQLAlchemy `pool_pre_ping=True` works but pool size must be small
2. **Row Level Security (RLS)** — Supabase requires RLS policies; current schema has none
3. **Realtime publications** — Must add `ALTER PUBLICATION supabase_realtime ADD TABLE messages, transactions, ...`
4. **Auth integration** — Supabase Auth uses `auth.users`; current `users` table must be mapped or replaced
5. **Storage** — Receipt images currently in local `./storage/uploads`; must use Supabase Storage bucket

---

## 5. AI MODULES SEPARATION FROM HTTP

### Status: **COMPATIBLE — Already Decoupled**

| AI Module | HTTP Dependent? | Evidence | Reusable as Library |
|-----------|-----------------|----------|---------------------|
| **OCR Service** | ❌ No | `ai/ocr/service.py` — pure Python, takes `image_bytes` | ✅ Yes |
| **Extraction Service** | ❌ No | `ai/extraction/service.py` — regex on OCR text | ✅ Yes |
| **Verification Service** | ❌ No | `ai/verification/service.py` — orchestrates OCR+Extraction+Matching+Duplicate | ✅ Yes |
| **Duplicate Detector** | ❌ No | `ai/duplicate/service.py` — in-memory hash sets | ⚠️ Needs persistent backend (Supabase) |
| **Matching Service** | ❌ No | `ai/matching/service.py` — takes roster list | ✅ Yes |
| **Worker Queue** | ⚠️ Yes — Celery/Redis | `ai/worker/queue.py` — Celery app, Redis broker | Replace with Supabase polling |

### Key Finding
The AI pipeline (`VerificationService.verify()`) is **already a pure function** taking `upload_id` and `image_bytes`, returning `VerificationResult`. It has **zero HTTP dependencies**. This is ideal for worker integration.

### Gap: Duplicate Detector Persistence
Current `DuplicateDetector` uses in-memory sets (`seen_hashes`, `seen_identities`). For hybrid worker:
- Must load existing hashes from Supabase on startup (`load_existing()` method exists)
- Must persist new hashes to Supabase after each verification
- Current `register()` only updates in-memory — needs DB write

---

## 6. WORKER RECOVERY AFTER RESTART

### Status: **NOT IMPLEMENTED — REQUIRES DESIGN**

| Capability | Current State | Needed for Hybrid |
|------------|---------------|-------------------|
| **Pending task discovery** | ❌ No queue polling | Worker must query `messages WHERE status='pending'` |
| **Atomic claim** | ❌ No | `UPDATE messages SET status='processing', worker_id=$1 WHERE id=$2 AND status='pending' RETURNING *` |
| **Stale job detection** | ❌ No | `worker_status.last_heartbeat` + TTL; re-claim stuck jobs |
| **Lease expiration** | ❌ No | Processing timeout (e.g., 5 min) → reset to pending |
| **Dead letter** | ❌ No | `status='failed'` with `error_message`; max retries |
| **Idempotency** | ✅ Backend has `IdempotencyKey` table | Worker must pass idempotency key to backend |
| **Ordering** | ❌ No | FIFO by `created_at` for same conversation |
| **Multiple workers** | ❌ No | Each worker unique `worker_id`; atomic claim prevents double-processing |

### Existing Foundation
- `ai/worker/queue.py` has Celery with Redis, retries, timeouts — **but Celery requires Redis server**
- `VerificationService` has `processing_time_ms` tracking
- `IdempotencyKey` model exists in backend

### Recommended: Supabase Polling (No Redis)
Since the requirement is "user's PC may be OFF", a **Redis-dependent Celery worker cannot run locally without Redis**. Direct Supabase polling is simpler:
- Worker polls `messages` table every N seconds
- Atomic claim via `SELECT ... FOR UPDATE SKIP LOCKED` or `UPDATE ... RETURNING`
- No external Redis needed — Supabase IS the queue

---

## 7. LOCAL FILE PATHS / STORAGE

### Status: **INCOMPATIBLE — LOCAL STORAGE USED**

| Component | Local Path | Evidence | Migration |
|-----------|------------|----------|-----------|
| **Receipt uploads** | `UPLOAD_DIR=./storage/uploads` | `config.py:12`, `uploads.py:42-44` | Supabase Storage bucket `receipts/` |
| **AI file hash** | Computed from local file | `uploads.py:28` `sha256(data).hexdigest()` | Compute from Supabase Storage download |
| **Perceptual hash** | Column exists but unused in AI path | `models.py:108` `perceptual_hash` | Store in Supabase; load for duplicate check |
| **OCR image loading** | `cv2.imdecode` from bytes | `ocr/service.py:222-227` | Works with bytes from Supabase Storage |

### Supabase Storage Integration
- Frontend uploads receipt → Supabase Storage → returns public/signed URL
- Worker downloads from Storage URL → runs AI → result
- No local filesystem dependency in worker

---

## 8. FUNCTIONALITY REQUIRING PC ONLINE

### Status: **CRITICAL GAPS**

| Functionality | Requires PC Online? | Evidence | Hybrid Solution |
|---------------|---------------------|----------|-----------------|
| **Receipt AI processing** | ✅ Yes | No cloud AI; only local Ollama/Tesseract | Worker must be online to process |
| **Financial ledger posting** | ✅ Yes | Backend `verify_and_post_from_ai()` runs locally | Worker posts to Supabase DB |
| **Chat message processing** | ✅ Yes | Frontend simulates; no real processing | Worker processes AI intents from messages |
| **Message acceptance** | ❌ No | Frontend → Supabase direct | ✅ Works offline |
| **Public fund view** | ❌ No | Frontend reads from Supabase | ✅ Works offline |
| **Campaign/roster view** | ❌ No | Frontend reads from Supabase | ✅ Works offline |
| **Admin review** | ❌ No | Frontend reads from Supabase | ✅ Works offline |

### Conclusion
**Cloud layer (Vercel + Supabase) remains fully functional for read operations when PC is OFF.**
Only **write operations requiring AI/ledger** (receipt upload → verification → ledger post) are delayed until worker comes online.

---

## 9. CLASSIFICATION SUMMARY

| Area | Classification | Confidence |
|------|----------------|------------|
| Frontend → Vercel | COMPATIBLE_WITH_REMEDIATION | High |
| Frontend assumes local backend | INCOMPATIBLE | High |
| Backend as worker | PARTIALLY_COMPATIBLE | High |
| Database → Supabase | COMPATIBLE_WITH_ADAPTERS | High |
| AI modules as library | COMPATIBLE | High |
| Worker recovery | NOT_IMPLEMENTED | High |
| Local storage | INCOMPATIBLE | High |
| PC-online requirements | PARTIALLY_COMPATIBLE | High |

---

## 10. CRITICAL BLOCKERS FOR HYBRID DEPLOYMENT

1. **No API client in frontend** — Must build from scratch
2. **No Supabase Auth integration** — Must replace mock auth
3. **No Realtime subscriptions** — Must add for live updates
4. **Worker doesn't exist** — Must implement Supabase polling worker
5. **Duplicate detector not persistent** — Must integrate with Supabase
6. **Local file storage** — Must migrate to Supabase Storage
7. **RLS policies missing** — Must define for all tables
8. **Supabase Realtime publications** — Must configure

---

## 11. REUSABLE COMPONENTS (UNCHANGED)

- **Backend**: `ledger.py`, `models.py`, `schemas.py`, `audit.py`, `activity.py`, `verify_and_post_from_ai()`
- **AI**: `ocr/`, `extraction/`, `verification/`, `matching/`, `duplicate/` (with persistence adapter)
- **Frontend**: All UI components, views, design system, TypeScript types, mock data structure
- **Database**: Schema, migrations, constraints, indexes

---

## 12. CONFIDENCE ASSESSMENT

- **Verified**: All findings based on direct code inspection
- **Partially Verified**: Supabase-specific behaviors (RLS, Realtime) inferred from documentation, not tested
- **Assumed**: Worker polling performance, Supabase connection limits
- **Not Verified**: Actual deployment to Vercel/Supabase, end-to-end integration
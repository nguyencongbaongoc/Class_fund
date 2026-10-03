# 00_PHASE1_PREFLIGHT.md

## Phase 1 Preflight — Completed

### Evidence Read (Phase 0)
- 09_RECOMMENDED_INTEGRATION_PLAN.md — Integration strategy (reuse existing backend/AI/frontend; build adapters)
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md — Frontend → Vercel compatible; backend as worker; Supabase polling needed; AI modules pure Python
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md — Schema aligned; UUID/numeric/date/JSON compatible; RLS missing
- 13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md — Celery/Redis incompatible with PC-off; Supabase polling worker required
- 14_ADMIN_AUTH_AND_RBAC_AUDIT.md — 4 existing roles (OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC); need Supabase Auth + user_roles
- 15_CHAT_REALTIME_COMPATIBILITY.md — Existing ChatView complete; needs realtime adapter
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md — Service role only in worker; RLS on all tables; Ollama localhost only
- 18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md — PARTIALLY_COMPATIBLE; no destructive rewrites
- 19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md — Guest flow missing: UUID message ID, public code, recall token, photo persistence, status tracking

### Git Safety
- `git init` executed; initial commit `dc7768e` with all 282 files preserved.
- No existing source files deleted or overwritten.

### Verified Installed Models
- `ollama list`: `qwen2.5vl:3b` (vision), `qwen3.5:4b` (text) confirmed installed.
- Default worker target: `qwen2.5vl:3b`.

### Existing Components Reused (per Phase 0 evidence)
- `app/services/ledger.py` (verify_and_post_from_ai, post_revert) — 100% reusable
- `ai/ocr/service.py`, `ai/extraction/service.py`, `ai/verification/service.py`, `ai/matching/service.py` — pure Python, zero HTTP
- `ai/contracts.py` — structured contracts preserved
- Frontend: ChatView, UploadReceiptView, LedgerView, DashboardView — UI preserved; adapter layer added
- Database schema (`models.py`, `schemas.py`) — preserved; new tables added for messages, worker_status, user_roles

### Phase 1 Scope (this phase only)
- Configuration contract (env vars, no secrets in frontend)
- Supabase database foundation (new tables, indexes, foreign keys, UUID PKs, numeric money, UTC timestamps)
- Guest message contract (message UUID, sender_name, sender_photo reference, status, created_at)
- Admin auth/RBAC foundation (user_roles mapping existing 4 roles)
- RLS policies documented (not fully deployed; SQL contracts defined)
- Frontend adapter skeleton (`src/lib/supabase/` structure)
- Realtime adapter skeleton
- Photo upload path definition (Supabase Storage contract)
- Local worker skeleton (polling design, atomic claim, heartbeat, lease recovery)
- Ollama adapter (`ai/ollama_client.py` concept)
- AI output contract (structured JSON schema)
- Financial gatekeeper contract (existing verify_and_post_from_ai preserved)
- Recall safety contract (message state checks, no delete, compensating reversal)
- Integration tests (new test definitions; existing tests preserved)

### Safety Confirmations
- `SUPABASE_SERVICE_ROLE_KEY` will NOT be placed in frontend code.
- `OLLAMA_BASE_URL` remains `http://127.0.0.1:11434` (localhost only).
- No production financial transactions performed.
- Existing ledger/reversal semantics unchanged.
- No rewrite of `ledger.py`, `ai/services/`, or all frontend views.

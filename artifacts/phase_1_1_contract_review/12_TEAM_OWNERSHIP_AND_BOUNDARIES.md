# 12_TEAM_OWNERSHIP_AND_BOUNDARIES.md

## Responsibility Boundaries (Phase 0 + Phase 1 Evidence)
Evidence: `09_RECOMMENDED_INTEGRATION_PLAN.md` (responsibility split: Minh/Ngọc/Hải); `11_HYBRID_ARCHITECTURE_COMPATIBILITY.md` (Minh: DB/auth/ledger; Ngọc: AI/worker; Hải: UI/realtime); `14_ADMIN_AUTH_AND_RBAC_AUDIT.md` (responsibility mapping); `18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md` (responsibility boundaries confirmed); `14_PHASE1_FINAL_REPORT.md` (reuses same split).

## Minh (Backend / DB / Auth / Ledger / Security)
- Source evidence verified: `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py` (actual inspection).
- Owns: `verify_and_post_from_ai()`, `post_revert()`, `post_transaction()`, `calculate_balance()` (preserved; no rewrites allowed without coordination).
- Owns: `user_roles` table design (`02`); `messages` schema extension; `worker_status` schema; `audit_logs` policies; `IdempotencyKey` contract (`ledger.py` lines 39–57).
- Owns: `RLS` SQL contracts (`05`); `Supabase` connection config (`01`); `DATABASE_URL` / `pool_pre_ping` settings.
- Owns: `service_role` isolation; `SERVICE_ROLE_KEY` environment management.
- Shared contracts requiring Minh freeze before parallel work:
  - `user_roles.role` enum values (`OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`) — must not change without updating `14` RBAC mapping.
  - `messages` schema (`02`) — any column rename or FK change breaks adapter design (`03`, `06`, `07`).
  - `IdempotencyKey` key/fingerprint format (`ledger.py`) — changes to `_make_request_fingerprint()` break retry/idempotency stability (`08` audit).
  - `post_transaction()` parameters and behavior (`ledger.py` lines 59–118) — changes affect `verify_and_post_from_ai()` (`11`) and adapter (`10`).
- Must coordinate with Ngọc: worker claim SQL (`08`) uses `messages.status` and `lease_expires_at`; `verify_and_post_from_ai()` parameter `message_id` (new contract in `11` — requires `post_transaction()` to handle or adapter to provide `message.id` linkage; currently `post_transaction()` does not accept `message.id` — contract proposes it; source unimplemented).
- Must coordinate with Hải: `messages` schema defines `public_code`, `status`, `ai_result` — these fields appear in `ChatView` (`03`, `07`); adapter contracts (`06`) must align; no conflicts identified at design level.

## Ngọc (AI / OCR / Vision / Worker / Extraction / Verification)
- Source evidence verified by reference (not fully reopened): `ai/ocr/service.py`, `ai/extraction/service.py`, `ai/verification/service.py`, `ai/matching/service.py` (Phase 0 `11` audit confirms 100% reusable).
- Owns: `ollama_client.py` adapter design (`09`); `VerificationService.verify()` integration (`21` reference); `DuplicateDetector` persistence adapter (design only; `11` references); structured AI output schema (`10`).
- Owns: `local worker` skeleton (`08`): claim/recovery/heartbeat/retry logic; `Supabase` polling design; `Ollama` vision call.
- Owns: `qwen2.5vl:3b` model verification (`01` + `ollama list` runtime); vision output contract (`10`).
- Shared contracts requiring Ngọc freeze:
  - `messages.status` transition rules (`03`): worker updates `pending` → `processing` → `posted`/`awaiting_admin`/`failed`; adapter (`06`) reads these; frontend (`07`) displays these. Any status value rename breaks all components.
  - `messages.transaction_id` linkage (`02` / `11`): worker sets this after `verify_and_post_from_ai()`; adapter (`03`) and frontend (`07`) rely on it for receipt preview.
  - `VerificationResult` contract (`ai/contracts.py`): adapter (`09`) produces this; `verify_and_post_from_ai()` consumes it; any schema change requires adapter + gatekeeper update.
  - Idempotency format stability (`08` / `11`): worker passes `idempotency_key` to `verify_and_post_from_ai()`; any format change must align with `_make_request_fingerprint()` and `IdempotencyKey` DB design (`ledger.py`).
- Must coordinate with Minh: `messages.transaction_id` requires `Transaction.id` returned by `post_transaction()`; `message.id` linkage requires adapter or `post_transaction()` to handle it (contract proposes it; source unimplemented).
- Must coordinate with Hải: AI output (`ai_result`) appears in `messages` (`07`); `status` badges (`07`) depend on AI processing result (`10`); adapter contracts (`06`) define how `ChatView` consumes `message` data including `ai_result`.

## Hải (Frontend / Chat / Upload / Admin Dashboard / Real-Time / UX)
- Source evidence verified by reference (not fully reopened): `ChatView.tsx`, `UploadReceiptView.tsx`, `AppContext.tsx`, `mockDatabase.ts` (`19` Phase 0 audit; `02` Phase 0 inventory; `06` adapter references existing views).
- Owns: `src/lib/supabase/` adapter design (`06`); `useRealtimeMessages()` design (`07`); `ChatView` reuse (`03`); `UploadReceiptView` photo/full name input (`19` confirms input exists; adapter design adds persistence); `public_code` display; status badge display (`processing`, `awaiting_admin`, `recalled`, `failed`); `realtime` subscription/reconnect (`07`).
- Owns: `vercel.json` design (`11` Phase 0 reference); `VITE_SUPABASE_URL` / `ANON_KEY` environment design (`01`); `.env.template` contracts.
- Owns: `guest identity` flow (`03`): photo selection, full name input, message creation; no login required.
- Shared contracts requiring Hải freeze:
  - `ChatMessage` type (`03` / `src/types/index.ts`): adapter (`06`) produces this from DB (`snake_case` to `camelCase` mapping concept); `ChatView` consumes it.
  - `public_code` display: `CF-...` format (`03`); must not be passed to recall authorization endpoint (security contract `05` / `12`).
  - `message.status` badges (`07`): design defines `processing` spinner, `awaiting_admin` warning, `recalled` disabled button, `failed` retry option; any status rename breaks `ChatView` logic.
  - `realtime` event payload (`07`): `payload.new` mapped to `ChatMessage`; event `INSERT`/`UPDATE` contracts; adapter hook must handle duplicate events (`eventId` tracking).
- Must coordinate with Minh: adapter uses `VITE_SUPABASE_URL` / `ANON_KEY` (`01` / `06`); no `SERVICE_ROLE_KEY` in any `src/` file; RLS policies (`05`) enforce authorization; adapter must use RLS-compliant queries (no direct table access bypass).
- Must coordinate with Ngọc: adapter (`06`) passes `message.id` (for linkages) but adapter source does not yet exist; adapter must receive `ai_result` from `messages` (not directly from AI adapter); `status` updates come from realtime events (not direct AI adapter call).

## Cross-Component Contracts That Must Be Frozen Before Phase 2
- `messages` schema (`02`): any column/constraint change requires adapter (`06`), realtime (`07`), worker (`08`), AI (`10`), financial (`11`), recall (`12`) updates.
- `user_roles.role` enum (`02` / `14`): any role change requires RLS (`05`), adapter auth (`04` / `06`), admin dashboard updates (`15` Phase 0 reference).
- `VerificationResult` / structured output schema (`10`): adapter (`09`) produces this; `verify_and_post_from_ai()` (`11`) consumes this; `messages.ai_result` (`02` / `07`) stores this.
- `IdempotencyKey` format (`ledger.py` + `08` + `11`): must be resolved (see `08_FINANCIAL_IDEMPOTENCY_AUDIT.md`) before worker retry logic is finalized.
- `OLLAMA_MODEL` default (`09` / `01`): `qwen2.5vl:3b`; must not change without adapter (`09`) and vision contract (`10`) updates.
- `public_code` authorization exclusion (`03` / `12`): `public_code` never authorizes any action; authorization mechanism (token) must be implemented (Phase 2) without using `public_code`.

## Module Modification Restrictions (Phase 1.1 — Confirmed)
- No changes to `app/services/ledger.py` (verified: `git diff` shows no tracked source modifications; only artifacts added).
- No changes to `ai/` services (`ai/ocr/service.py`, `ai/verification/service.py`, etc. — preserved by design; no modifications made).
- No changes to `classfund/src/views/ChatView.tsx` or other frontend views (preserved; adapter design added; source unchanged).
- No changes to `.env` production variables (only `01` contract defines variables; no `.env` file modified).
- No changes to `vite.config.ts` (unverified by direct inspection, but `git diff` confirms no tracked source modifications beyond artifacts).
- Adapter files (`src/lib/supabase/*`) not yet created; creation reserved for Phase 2.

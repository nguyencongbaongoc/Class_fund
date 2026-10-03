# 05_AUTH_RLS_SECURITY_REVIEW.md

## Auth / RBAC Evidence (Actual)
Source inspected: `14_ADMIN_AUTH_AND_RBAC_AUDIT.md` (read fully); `04_AUTH_RBAC.md` (Phase 1 contract); `04_DATABASE_AND_FINANCIAL_INTEGRITY.md` (Phase 0 reference).
`app/models/models.py` (line 20–24): `Role` enum preserved (`OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`). Confirmed by `ledger.py` imports (line 10: `Role` not directly used but `users` reference preserved).
`user_roles` table SQL (`02`): `user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE`. Agreement: maps `auth.uid()` → `user_roles.role`.

## RLS Evidence (Actual)
`05_RLS_SECURITY.md` (all policies defined by SQL contract; no execution):
- `messages`: member read own; admin all; insert with `auth.uid()` or `NULL` (guest).
- `transactions`: public verified read; treasurer write.
- `user_roles`: member own; admin manage.
- `audit_logs`: admin only; no `INSERT` for non-service roles.
- `uploads`: public verified; auth own; auth upload.
- `worker_status`: admin read; service bypass.
Agreement: covers all target entities; default deny; service role isolated.

## Secret Boundary Evidence
- `01` contract: `SUPABASE_SERVICE_ROLE_KEY` listed only under private environment variables.
- `05`: `SERVICE_ROLE_KEY` never referenced in any SQL policy as a user-facing mechanism (policies use `authenticated`, `anon`, `current_user_role()`); service role relies on key-based bypass, not policy.
- `06`: Adapter `client.ts` uses `ANON_KEY` only (design only; file not created; no source leaks key).
- Actual source inspection: `class-fund-backend-v0.1/class-fund-backend/app/core/config.py` (not fully read in this session) referenced by `ledger.py`; no secret leakage verified in adapter files (none exist yet).
Evidence: `git ls-files` confirms no new `src/lib/supabase/client.ts` source file; adapter remains design-only.

## Security Conflicts (Critical Gaps — BLOCKED)
1. **Recall authorization missing** (`12` design; `19` Phase 0 audit: zero authorization). Token generation source not implemented; authorization endpoint not implemented. `public_code` explicitly excluded as authorization (design correct), but no replacement mechanism exists in source.
2. **RLS policies not executed** (`05` contracts only). No `ALTER TABLE ENABLE ROW LEVEL SECURITY` executed; no `CREATE POLICY` executed; no Supabase dashboard interaction; no executed policy test evidence.
3. **Service-role isolation contract but no adapter deployment** (`01` + `06`). Worker skeleton (`08`) not implemented as running process; service role key isolation relies on worker process design, not runtime verification.
4. **Guest user direct DB mutation** (`05` member policy allows `auth.uid()` insert; guest `sender_id = NULL` allowed by `auth_insert_own_message`). Design allows unauthenticated insert. This aligns with `03` guest contract but requires frontend `ANON_KEY` to enforce; no executed frontend insert verified.

## Resolution (Documentation Only — No Source Change)
- Confirm `public_code` must not be used as authorization (design already confirms; add explicit note in `03` / `12` contract that authorization depends solely on private token).
- Document that `service_role` bypass is only valid when worker process uses the key; adapter files must exclude it.
- Confirm `auth.uid()` for members; `NULL` for guests with `sender_name` required (`03` already defines this).

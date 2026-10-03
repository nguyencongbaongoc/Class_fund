# 04_AUTH_RBAC.md

## Phase 1 Admin Authentication / RBAC Foundation

### Source Evidence (Phase 0)
- 14_ADMIN_AUTH_AND_RBAC_AUDIT.md: Existing 4 roles (`OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`) mapped from backend RBAC. Frontend `switchRole()` is UI-only, insecure. Supabase Auth + custom `user_roles` table required.
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: Frontend needs login/logout; backend `get_current_user` requires replacement with service-role identity for worker.
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: `user_roles` table design; `current_user_role()` SQL function.
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md: Service role only for worker; RLS enforces authorization; frontend only UI behavior.

### Existing Role Model (Preserved)
```
OWNER_TREASURER → Admin (full fund control, treasurer actions, revert, audit access)
MODERATOR        → Admin (moderate scope; campaign/student management; review messages)
MEMBER           → Member (send messages, view own conversation, public fund view)
PUBLIC           → Anonymous / public read (public fund, verified ledger entries, campaigns)
```
- Evidence: `app/models/models.py:20-24` (Role enum verified).

### Migration Path (Phase 1 Foundation — Not Full Migration)
- Option C (Hybrid) selected: Supabase Auth handles authentication; custom `user_roles` table handles authorization (per 14 recommendation).
- `users` table from backend mapped to `auth.users` via `user_id` reference in `user_roles`.
- Admin user seeding concept documented (Supabase Auth Admin API) but not executed in Phase 1.

### Frontend Auth Contract (Skeleton)
```typescript
// Frontend uses ANON_KEY + Supabase Auth session
// Role fetched from user_roles table via RLS-enforced query
const { data: roleData } = await supabase
  .from('user_roles')
  .select('role')
  .eq('user_id', session?.user?.id)
  .single()
```
- Evidence: 14 (frontend auth flow example).

### Security Rules
- Authorization enforced server-side / database-side (RLS). Frontend role checks are UI behavior only.
- `SERVICE_ROLE_KEY` never reaches frontend; worker identity isolated.
- `current_user_role()` SQL function referenced in RLS policy definitions.

### RBAC Enforcement (Concept — Policies Documented in 05_RLS_SECURITY.md)
- Members: read own conversation; insert own messages.
- Admin (`OWNER_TREASURER` / `MODERATOR`): read all messages; manage roles; review `awaiting_admin`; write audit logs.
- Service role (worker): bypasses RLS for message claiming and ledger posting.
- Evidence: 14 (policy examples), 16 (dual enforcement architecture).

# PHASE 0 ADDENDUM — ADMIN AUTH AND RBAC AUDIT

## Executive Summary
**Status: PARTIALLY_COMPATIBLE** — The existing RBAC model (4 roles) maps to Admin/Member requirements but requires Supabase Auth integration and RLS policies for secure enforcement. Current frontend-only role checks are insufficient.

---

## 1. EXISTING RBAC MODEL

### Backend Roles (`app/models/models.py:20-24`)
```python
class Role(str, enum.Enum):
    OWNER_TREASURER = "OWNER_TREASURER"  # Full financial control
    MODERATOR = "MODERATOR"              # Campaign/student management
    MEMBER = "MEMBER"                    # Regular user
    PUBLIC = "PUBLIC"                    # Read-only public access
```

### Role Permissions (Backend Enforcement)

| Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|----------|-----------------|-----------|--------|--------|
| `/fund/balance` | ✅ | ✅ | ✅ | ❌ |
| `/fund/transactions` | ✅ | ✅ | ✅ | ❌ |
| `/fund/accounts/{id}/opening-balance` | ✅ | ❌ | ❌ | ❌ |
| `/fund/bank-accounts` (POST) | ✅ | ❌ | ❌ | ❌ |
| `/fund/credit` | ✅ | ❌ | ❌ | ❌ |
| `/fund/debit` | ✅ | ❌ | ❌ | ❌ |
| `/fund/transactions/{id}/revert` | ✅ | ❌ | ❌ | ❌ |
| `/campaigns/students` (POST) | ✅ | ✅ | ❌ | ❌ |
| `/campaigns` (POST/PATCH) | ✅ | ✅ | ❌ | ❌ |
| `/campaigns/{id}/students` | ✅ | ✅ | ❌ | ❌ |
| `/uploads` (POST) | ✅ | ✅ | ✅ | ✅ (no auth) |
| `/chat/messages` | ✅ | ✅ | ✅ | ❌ |
| `/public/*` | ✅ | ✅ | ✅ | ✅ |

### Frontend Role Checks (`AppContext.tsx:200-211`)
```typescript
switchRole(role: UserRole) {
  if (role === 'TREASURER') setCurrentUser(MOCK_USERS.treasurer);
  else if (role === 'MODERATOR') setCurrentUser(MOCK_USERS.moderator);
  else if (role === 'MEMBER') setCurrentUser(MOCK_USERS.member);
  else setCurrentUser(MOCK_USERS.public);
}
```
**Critical Finding**: Frontend role switching is **purely UI simulation** — no backend validation.

---

## 2. TARGET ROLES: ADMIN & MEMBER

### Required Mapping

| Target Role | Maps To | Capabilities |
|-------------|---------|--------------|
| **Admin** | `OWNER_TREASURER` + `MODERATOR` combined | All backend permissions + worker status view + admin review queue |
| **Member** | `MEMBER` | Send messages, view own receipts, view public fund, view campaign status |

### Gap Analysis

| Admin Capability | Current Support | Gap |
|------------------|-----------------|-----|
| Login/logout | ✅ Backend has `/auth/login`, `/auth/logout` | Frontend has no login UI |
| View all messages | ✅ `/chat/messages` returns all | Frontend shows all mock messages |
| View pending jobs | ❌ No job queue | Need `messages` table with `status='pending'` |
| Review AI extraction | ⚠️ `UploadStatus.NEEDS_REVIEW` exists | No admin review UI; need message status `awaiting_admin` |
| Approve/reject financial ops | ✅ Backend `verify_and_post_from_ai` posts if VERIFIED | Need admin action to override `NEEDS_REVIEW` |
| View ledger and balance | ✅ `/fund/balance`, `/fund/transactions` | Frontend reads mock data |
| Reverse transactions | ✅ `/fund/transactions/{id}/revert` | Frontend has `revertTransaction` mock |
| View audit logs | ❌ No endpoint | Need `/admin/audit-logs` |
| Manage members | ✅ `/campaigns/students` CRUD | Frontend has `markStudentPaid` mock |
| View worker status | ❌ No worker | Need `worker_status` table |

| Member Capability | Current Support | Gap |
|-------------------|-----------------|-----|
| Login/logout | ✅ Backend | Frontend no login UI |
| Send messages | ✅ `/chat/messages` POST | Frontend mock only |
| View permitted chat | ✅ Backend returns all (no filtering) | Need conversation-based filtering |
| View public fund | ✅ `/public/fund` | Frontend mock |
| View own transaction status | ⚠️ `/uploads/{id}` returns status | Need member-specific filtering |

---

## 3. SUPABASE AUTH COMPATIBILITY

### Current Auth Flow
```
POST /api/v1/auth/login (email, password)
  → Verify argon2 hash in users table
  → Create JWT (HS256) with sub=user_id, role=user.role
  → Return access_token
  → Client sends Authorization: Bearer <token>
  → Backend validates JWT, checks revoked_tokens
```

### Supabase Auth Flow
```
supabase.auth.signInWithPassword({ email, password })
  → Returns session { access_token, refresh_token, user }
  → access_token is JWT (RS256) with standard claims + custom claims
  → Client uses supabase-js client (auto-attaches token)
  → RLS policies use auth.uid() and auth.jwt()
```

### Migration Options

| Option | Description | Effort | Risk |
|--------|-------------|--------|------|
| **A: Full Migration** | Move users to `auth.users`, use Supabase Auth entirely | High | Password migration required |
| **B: Custom JWT + Supabase** | Keep backend auth, issue Supabase-compatible JWTs | Medium | Dual auth complexity |
| **C: Hybrid** | Supabase Auth for login, custom `user_roles` table for RBAC | Medium | Sync required |

### Recommended: Option C (Hybrid)

```sql
-- Custom roles table (Supabase Auth doesn't have native RBAC)
CREATE TABLE user_roles (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role varchar(30) NOT NULL CHECK (role IN ('OWNER_TREASURER', 'MODERATOR', 'MEMBER', 'PUBLIC')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- RLS policy helper function
CREATE OR REPLACE FUNCTION current_user_role()
RETURNS varchar AS $$
  SELECT role FROM user_roles WHERE user_id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- Example RLS policy
CREATE POLICY "treasurer_fund_write" ON transactions
FOR INSERT TO authenticated
WITH CHECK (current_user_role() = 'OWNER_TREASURER');
```

### Frontend Integration
```typescript
// src/lib/auth/supabase.ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)

// Login
const { data, error } = await supabase.auth.signInWithPassword({ email, password })

// Get current user role
const { data: roleData } = await supabase
  .from('user_roles')
  .select('role')
  .eq('user_id', supabase.auth.getUser().data.user?.id)
  .single()
```

---

## 4. RBAC ENFORCEMENT ARCHITECTURE

### Current: Backend-Only Enforcement
- FastAPI `require_roles()` dependency checks `user.role`
- All mutating endpoints protected
- **But**: Frontend has no token, no real enforcement

### Hybrid: Dual Enforcement

| Layer | Mechanism |
|-------|-----------|
| **Frontend (UI)** | Hide/disable buttons based on `user.role` from Supabase |
| **Supabase RLS** | Database-level policies using `current_user_role()` |
| **Backend API** | Service-role key bypasses RLS; validates worker identity |
| **Worker** | Service-role key; no user context needed |

### Critical: Never Trust Frontend-Only Checks
```typescript
// BAD - Frontend only
{currentUser.role === 'TREASURER' && <button>Delete</button>}

// GOOD - RLS enforces at database
// Even if frontend shows button, INSERT will fail if not treasurer
```

---

## 5. ADMIN PRIVILEGE ESCALATION

### Current: No Escalation Path
- Roles assigned at user creation
- No admin UI to promote users

### Required: Admin Promotion Flow
```sql
-- Only existing admin can promote
CREATE POLICY "admin_manage_roles" ON user_roles
FOR ALL TO authenticated
USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'))
WITH CHECK (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
```

### Frontend Admin Panel
- Only visible to `OWNER_TREASURER`/`MODERATOR`
- List users with role dropdown
- Call `supabase.from('user_roles').upsert({ user_id, role })`

---

## 6. SESSION VALIDATION

### Current Backend
```python
# deps.py:16-28
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)  # Validates JWT signature + expiry
    revoked = db.get(RevokedToken, payload["jti"])
    if revoked: raise HTTPException(401, "Token revoked")
    return db.get(User, payload["sub"])
```

### Supabase Session
- Access token: 1 hour (configurable)
- Refresh token: Never expires (rotation enabled)
- `supabase.auth.getSession()` auto-refreshes
- **No revocation table needed** — Supabase handles invalidation

### Worker Session
- Uses **service_role key** (bypasses RLS entirely)
- Not tied to user session
- Long-lived; rotate periodically

---

## 7. FRONTEND-ONLY ROLE CHECKS (CURRENT)

### Current Pattern (Insecure for Production)
```typescript
// AppContext.tsx:82-84
const [currentUser, setCurrentUser] = useState<User>(MOCK_USERS.treasurer);

// CampaignView.tsx:171-173
{(currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && (
  <button onClick={() => markStudentPaid(student.id, !isPaid)}>
```

### Required: Backend-Validated Role
```typescript
// New: Fetch role from Supabase on auth state change
supabase.auth.onAuthStateChange(async (event, session) => {
  if (session?.user) {
    const { data } = await supabase
      .from('user_roles')
      .select('role')
      .eq('user_id', session.user.id)
      .single()
    setUserRole(data?.role || 'MEMBER')
  }
})

// UI still uses role for UX, but mutations go through Supabase client
// RLS enforces at database level
```

---

## 8. RLS POLICIES FOR TARGET ENTITIES

### messages Table
```sql
-- Members: read own conversation, insert own messages
CREATE POLICY "member_read_own_conversation" ON messages
FOR SELECT TO authenticated
USING (
  conversation_id IN (
    SELECT conversation_id FROM conversation_participants WHERE user_id = auth.uid()
  )
);

CREATE POLICY "member_insert_own" ON messages
FOR INSERT TO authenticated
WITH CHECK (sender_id = auth.uid());

-- Admin: read all, update status
CREATE POLICY "admin_all_messages" ON messages
FOR ALL TO authenticated
USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'))
WITH CHECK (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));

-- Worker (service role): bypasses RLS entirely
```

### financial_ledger (transactions/ledger_entries)
```sql
-- Public: read verified entries
CREATE POLICY "public_read_verified" ON ledger_entries
FOR SELECT TO anon, authenticated
USING (status = 'VERIFIED');

-- Admin: write all
CREATE POLICY "admin_write_ledger" ON transactions
FOR INSERT TO authenticated
WITH CHECK (current_user_role() = 'OWNER_TREASURER');
```

### worker_status
```sql
-- Worker (service role): upsert own status
-- Admin: read all
CREATE POLICY "admin_read_workers" ON worker_status
FOR SELECT TO authenticated
USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
```

---

## 9. SERVICE-ROLE KEY EXPOSURE RISKS

### Current: No Service Role
- Backend runs with full DB access
- No separation of concerns

### Hybrid: Service Role for Worker Only
```python
# Worker uses service_role key
supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)  # Bypasses ALL RLS

# Frontend uses anon key
supabase = create_client(SUPABASE_URL, ANON_KEY)  # Subject to RLS
```

### Security Rules
| Key | Who Has It | Permissions |
|-----|------------|-------------|
| `ANON_KEY` | Public (frontend bundle) | Read public tables; RLS enforced |
| `SERVICE_ROLE_KEY` | Worker process ONLY (env var) | Full DB access; **NEVER in frontend** |
| `JWT_SECRET` | Backend only (if kept) | Token signing |

### Mitigation
- Store `SERVICE_ROLE_KEY` in Windows Credential Manager or `.env` (gitignored)
- Rotate periodically via Supabase dashboard
- Monitor usage in Supabase logs

---

## 10. ADMIN ACCOUNT CREATION

### Current: No Provisioning
- Users created via `POST /auth/register` (not implemented) or direct DB insert

### Hybrid: Supabase Auth Admin API
```python
# Backend/admin script (run once)
from supabase import create_client, Client

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# Create admin user
response = supabase.auth.admin.create_user({
    "email": "admin@classfund.edu.vn",
    "password": "secure_password",  # User changes on first login
    "email_confirm": True,
    "user_metadata": {"full_name": "Nguyễn Thu Trang", "role": "OWNER_TREASURER"}
})

user_id = response.user.id

# Assign role
supabase.table('user_roles').insert({
    'user_id': user_id,
    'role': 'OWNER_TREASURER'
}).execute()
```

---

## 11. COMPATIBILITY MATRIX

| Requirement | Current Backend | Current Frontend | Hybrid Needed | Status |
|-------------|-----------------|------------------|---------------|--------|
| Login/logout | ✅ JWT | ❌ Mock only | Supabase Auth + UI | **REMEDIATION** |
| Role storage | `users.role` column | Mock state | `user_roles` table + Supabase Auth | **ADAPTER** |
| Admin permissions | `require_roles()` | UI hide/show | RLS + service role | **ADAPTER** |
| Member permissions | Implicit (all auth) | UI hide/show | RLS policies | **ADAPTER** |
| Session management | JWT + revocation | None | Supabase auto-refresh | **MIGRATION** |
| Admin promotion | None | None | Admin UI + RLS policy | **NEW** |
| Worker auth | N/A | N/A | Service role key | **NEW** |
| Audit log access | None | None | Admin-only RLS | **NEW** |

---

## 12. RECOMMENDATION

1. **Migrate to Supabase Auth** (Option C) — preserves custom roles via `user_roles` table
2. **Implement RLS policies** for all tables — database-level enforcement
3. **Build login/logout UI** in frontend using `supabase-js`
4. **Remove mock `switchRole()`** — replace with real auth state
5. **Worker uses service_role key** — stored securely on Windows PC
6. **Add admin review UI** for `awaiting_admin` messages

---

## 13. CONFIDENCE ASSESSMENT

- **Verified**: Backend RBAC code, Supabase Auth capabilities, RLS syntax
- **Partially Verified**: Migration path for existing users (requires Supabase admin API)
- **Assumed**: Frontend can integrate `supabase-js` without major refactor
- **Not Verified**: Actual RLS policy performance, Supabase Auth rate limits
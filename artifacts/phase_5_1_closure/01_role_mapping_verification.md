# Phase 5.1 — Role Mapping Verification

## Findings Summary

**Verdict: `ROLE_MAPPING_MISMATCH`** — The frontend uses `TREASURER` as a display label that maps to the backend's canonical `OWNER_TREASURER` role, but this mapping is implicit and not formally defined in code.

## Backend Role Definition (Canonical)

**File:** `class-fund-backend-v0.1/class-fund-backend/app/models/models.py:20-24`

```python
class Role(str, enum.Enum):
    OWNER_TREASURER = "OWNER_TREASURER"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"
    PUBLIC = "PUBLIC"
```

**Authorization Dependencies:**
- `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)` — Used on `/admin/*` routes (`admin.py:20`)
- `require_roles(Role.OWNER_TREASURER)` — Used on `/fund/credit`, `/fund/debit`, `/fund/transactions/{id}/revert`, `/fund/accounts/{id}/opening-balance`, `/fund/bank-accounts` POST (`fund.py`)
- `require_role(Role.OWNER_TREASURER, Role.MODERATOR)` — Used on `/internal/review/*` routes (`review.py:19`)

The backend **only recognizes** `OWNER_TREASURER` — there is no `TREASURER` role in the database or authorization logic.

## Frontend Role Definition

**File:** `classfund/classfund/src/types/index.ts:1`

```typescript
export type UserRole = 'TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC';
```

The frontend defines `TREASURER` as a distinct `UserRole` value — **different** from the backend's `OWNER_TREASURER`.

## Frontend Role Mapping (Implicit)

### 1. AppContext Role Switching
**File:** `classfund/classfund/src/context/AppContext.tsx:216-227`

```typescript
const switchRole = (role: UserRole) => {
    if (role === 'TREASURER') setCurrentUser(MOCK_USERS.treasurer);
    else if (role === 'MODERATOR') setCurrentUser(MOCK_USERS.moderator);
    // ...
};
```

### 2. Mock Users
**File:** `classfund/classfund/src/data/mockDatabase.ts` (not fully read, but referenced)

The mock data uses `MOCK_USERS.treasurer` which has `role: 'TREASURER'` in the frontend type system.

### 3. Navbar Admin Check
**File:** `classfund/classfund/src/components/common/Navbar.tsx:27`

```typescript
const isAdmin = currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR';
```

### 4. Admin Dashboard View Check
**File:** `classfund/classfund/src/views/AdminDashboardView.tsx:187-195`

```typescript
{(currentUser.role === 'TREASURER' || currentUser.role === 'MODERATOR') && (
    <button onClick={() => setIsExpenseModalOpen(true)}>...</button>
)}
```

### 5. Admin Ledger View Check
**File:** `classfund/classfund/src/views/AdminLedgerView.tsx:93-100`

```typescript
{(currentUser.role === 'TREASURER') && (
    <button>Nạp thủ công</button>
)}
```

### 6. API Authorization Header
**File:** `classfund/classfund/src/lib/adminApi.ts:49-53`

```typescript
function getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
}
```

The frontend sends the JWT token. The **backend validates the token and extracts the user's actual role from the database** (which is `OWNER_TREASURER`).

## The Mismatch

| Aspect | Backend | Frontend |
|--------|---------|----------|
| Canonical Role | `OWNER_TREASURER` | `TREASURER` (in `UserRole` type) |
| Authorization Check | `require_roles(Role.OWNER_TREASURER, ...)` | `currentUser.role === 'TREASURER'` |
| Mock Data | N/A (uses DB) | `MOCK_USERS.treasurer` has `role: 'TREASURER'` |
| Role Switching | N/A | `switchRole('TREASURER')` → sets mock user |

## Impact Analysis

### Current Behavior (Working Because)
1. **Mock mode**: Frontend uses local mock data with `TREASURER` role — no real backend auth
2. **Real auth flow**: When JWT is used, backend validates token → extracts `OWNER_TREASURER` from DB → authorization passes because backend checks `Role.OWNER_TREASURER`
3. **Frontend checks are UX only**: Hiding/showing buttons based on `TREASURER` — backend is the actual gatekeeper

### Risk Areas
1. **No explicit mapping**: No code converts `TREASURER` ↔ `OWNER_TREASURER`
2. **Real auth integration**: When Supabase Auth is connected, the JWT payload will contain the backend role (`OWNER_TREASURER`). The frontend `currentUser.role` will be populated from JWT `role` claim.
3. **Potential breakage**: If JWT `role` = `"OWNER_TREASURER"` but frontend checks `=== 'TREASURER'`, admin features will be hidden for legitimate treasurers.

## Source Evidence

### Backend Auth Flow
**File:** `class-fund-backend-v0.1/class-fund-backend/app/api/deps.py:16-28`

```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    user = db.get(User, user_id)
    return user  # User.role is Role.OWNER_TREASURER
```

**File:** `class-fund-backend-v0.1/class-fund-backend/app/models/models.py:73-81`

```python
class User(Base):
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.MEMBER)
    # Role values: OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC
```

### Frontend Auth Context (Missing Real Implementation)
The frontend `AppContext` uses mock data. No real JWT parsing or role mapping from token to `UserRole` type exists yet.

## Required Remediation (For Live Integration)

1. **Add role mapping in frontend auth:**
   ```typescript
   // When parsing JWT or fetching /auth/me
   const roleMap: Record<string, UserRole> = {
       'OWNER_TREASURER': 'TREASURER',
       'MODERATOR': 'MODERATOR',
       'MEMBER': 'MEMBER',
       'PUBLIC': 'PUBLIC',
   };
   currentUser.role = roleMap[backendRole] || 'PUBLIC';
   ```

2. **Or align frontend type to backend:**
   Change `UserRole` to use `OWNER_TREASURER` (breaking change for mock data)

3. **Document the mapping** in architecture docs

## Conclusion

The role mapping works **accidentally** in mock mode but is **not formally implemented** for real authentication. This is a `ROLE_MAPPING_MISMATCH` that will surface when live Supabase Auth is integrated.

**Impact:** Non-critical for source-level closure (backend authorization is authoritative), but must be fixed before live demo.
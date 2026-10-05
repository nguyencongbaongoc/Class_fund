# Phase 5.2 — Role Mapping Remediation

## Problem Statement (from Phase 5.1)
- Backend canonical role: `OWNER_TREASURER`
- Frontend role type: `TREASURER` (in `UserRole` type)
- No explicit mapping in authentication flow
- Works in mock mode; may fail with live Supabase Auth

## Solution Implemented

### 1. Backend Role Definitions (Authoritative — Unchanged)
**File:** `class-fund-backend-v0.1/class-fund-backend/app/models/models.py:20-24`

```python
class Role(str, enum.Enum):
    OWNER_TREASURER = "OWNER_TREASURER"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"
    PUBLIC = "PUBLIC"
```

The backend role model remains the single source of truth for authorization.

### 2. Frontend Role Type System (Updated)
**File:** `classfund/classfund/src/types/index.ts:1-37`

```typescript
// Backend canonical roles (authoritative - matches database enum)
export type BackendRole = 'OWNER_TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC';

// Frontend display roles (UI compatible - for display only)
export type FrontendRole = 'TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC';

// Legacy alias for backward compatibility
export type UserRole = FrontendRole;

/**
 * Normalizes backend canonical role to frontend display role.
 * Backend is authoritative; this is a one-way mapping for UI display only.
 */
export function normalizeRole(backendRole: BackendRole): FrontendRole {
  switch (backendRole) {
    case 'OWNER_TREASURER':
      return 'TREASURER';
    case 'MODERATOR':
      return 'MODERATOR';
    case 'MEMBER':
      return 'MEMBER';
    case 'PUBLIC':
      return 'PUBLIC';
    default:
      // Fail closed - unknown roles get minimal access
      return 'PUBLIC';
  }
}

/**
 * Validates that a role string is a known backend role.
 * Returns the canonical backend role or null if invalid.
 */
export function validateBackendRole(role: string): BackendRole | null {
  const validRoles: BackendRole[] = ['OWNER_TREASURER', 'MODERATOR', 'MEMBER', 'PUBLIC'];
  return validRoles.includes(role as BackendRole) ? role as BackendRole : null;
}
```

Key design decisions:
- **Explicit mapping**: `normalizeRole()` is the single source of truth for backend→frontend role conversion
- **Fail closed**: Unknown backend roles map to `PUBLIC` (minimal access)
- **Validation**: `validateBackendRole()` rejects unknown role strings
- **No reverse mapping**: Frontend→backend is not provided (backend authorization is authoritative)

### 3. AppContext Role State Management (Updated)
**File:** `classfund/classfund/src/context/AppContext.tsx:32-65, 264-309`

Added dual role state:
- `currentBackendRole` — canonical role from backend (authoritative)
- `currentUserFrontendRole` — normalized role for UI display

```typescript
const [currentBackendRole, setCurrentBackendRoleState] = useState<BackendRole>('OWNER_TREASURER');
const [currentUserFrontendRole, setCurrentUserFrontendRoleState] = useState<FrontendRole>('TREASURER');

// ...
const setCurrentBackendRole = (role: BackendRole) => {
  const validRole = validateBackendRole(role);
  if (!validRole) {
    addToast({ type: 'error', title: 'Invalid role', description: `Unknown backend role: ${role}` });
    return;
  }
  setCurrentBackendRoleState(validRole);
  const frontendRole = normalizeRole(validRole);
  setCurrentUserFrontendRoleState(frontendRole);
  
  // Update mock user for demo purposes
  switch (validRole) {
    case 'OWNER_TREASURER': setCurrentUser(MOCK_USERS.treasurer); break;
    case 'MODERATOR': setCurrentUser(MOCK_USERS.moderator); break;
    case 'MEMBER': setCurrentUser(MOCK_USERS.member); break;
    case 'PUBLIC': setCurrentUser(MOCK_USERS.public); break;
  }
};

const switchRole = (frontendRole: FrontendRole) => {
  const backendRoleMap: Record<FrontendRole, BackendRole> = {
    'TREASURER': 'OWNER_TREASURER',
    'MODERATOR': 'MODERATOR',
    'MEMBER': 'MEMBER',
    'PUBLIC': 'PUBLIC',
  };
  const backendRole = backendRoleMap[frontendRole];
  setCurrentBackendRole(backendRole);
};
```

### 4. Admin Navigation Guards (Updated)
**File:** `classfund/classfund/src/components/common/Navbar.tsx:29`

```typescript
// Uses backend role for authorization decisions
const isAdmin = currentBackendRole === 'OWNER_TREASURER' || currentBackendRole === 'MODERATOR';
```

### 5. Admin View Role Checks (Updated)
**Files:**
- `classfund/classfund/src/views/AdminDashboardView.tsx:187` — Uses `currentUser.role` (frontend role for UI)
- `classfund/classfund/src/views/AdminLedgerView.tsx:150` — Uses `currentUserFrontendRole`

## Verification Tests Required

| Test Case | Expected Result |
|-----------|-----------------|
| `OWNER_TREASURER` → `normalizeRole()` | Returns `'TREASURER'` |
| `MODERATOR` → `normalizeRole()` | Returns `'MODERATOR'` |
| `MEMBER` → `normalizeRole()` | Returns `'MEMBER'` |
| `PUBLIC` → `normalizeRole()` | Returns `'PUBLIC'` |
| Unknown role → `normalizeRole()` | Returns `'PUBLIC'` (fail closed) |
| Valid backend role → `validateBackendRole()` | Returns canonical role |
| Invalid role string → `validateBackendRole()` | Returns `null` |
| `setCurrentBackendRole('OWNER_TREASURER')` | Sets both backend and frontend roles |
| `switchRole('TREASURER')` | Maps to `OWNER_TREASURER` backend |
| Navbar admin tabs visible for `OWNER_TREASURER` | ✅ Shows |
| Navbar admin tabs visible for `MODERATOR` | ✅ Shows |
| Navbar admin tabs hidden for `MEMBER` | ✅ Hidden |
| Navbar admin tabs hidden for `PUBLIC` | ✅ Hidden |

## Test Evidence
- TypeScript strict check: ✅ PASS
- Production build: ✅ PASS
- No runtime errors in role switching

## Conclusion
Role mapping is now **explicit, centralized, and fail-closed**. The backend remains authoritative; the frontend normalization layer is purely for UI display. This will work correctly when live Supabase Auth provides `OWNER_TREASURER` in JWT claims.
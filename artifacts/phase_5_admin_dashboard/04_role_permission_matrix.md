# Phase 5 — Role Permission Matrix

## Role Definitions (from `app/models/models.py`)

```python
class Role(str, enum.Enum):
    OWNER_TREASURER = "OWNER_TREASURER"  # Full financial + admin access
    MODERATOR = "MODERATOR"              # Review + monitoring, no financial mutations
    MEMBER = "MEMBER"                    # Standard user (chat, upload, view public)
    PUBLIC = "PUBLIC"                    # Unauthenticated (public fund view only)
```

## Permission Matrix by Feature Area

### 1. Fund & Ledger Management

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| View balance | GET `/fund/balance` | ✅ | ✅ | ✅ | ❌ |
| View transactions | GET `/fund/transactions` | ✅ | ✅ | ✅ | ❌ |
| View bank accounts | GET `/fund/bank-accounts` | ✅ | ✅ | ✅ | ❌ |
| Create bank account | POST `/fund/bank-accounts` | ✅ | ❌ | ❌ | ❌ |
| Set opening balance | PUT `/fund/accounts/{id}/opening-balance` | ✅ | ❌ | ❌ | ❌ |
| Manual credit (income) | POST `/fund/credit` | ✅ | ❌ | ❌ | ❌ |
| Manual debit (expense) | POST `/fund/debit` | ✅ | ❌ | ❌ | ❌ |
| Revert transaction | POST `/fund/transactions/{id}/revert` | ✅ | ❌ | ❌ | ❌ |

**Frontend Enforcement:**
- Admin Ledger View: Show manual entry/revert buttons only for OWNER_TREASURER
- MODERATOR sees read-only ledger with admin filters
- MEMBER/PUBLIC redirected to public views

### 2. AI Review Queue

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| List pending reviews | GET `/internal/review` | ✅ | ✅ | ❌ | ❌ |
| View review detail | GET `/internal/review/{id}` | ✅ | ✅ | ❌ | ❌ |
| Approve extraction | POST `/internal/review/{id}/approve` | ✅ | ✅ | ❌ | ❌ |
| Reject extraction | POST `/internal/review/{id}/reject` | ✅ | ✅ | ❌ | ❌ |
| View original image | GET `/internal/ai/uploads/{id}/file` | ✅ | ✅ | ❌ | ❌ |

**Notes:**
- Both OWNER_TREASURER and MODERATOR can approve/reject
- Approval goes through financial gatekeeper (ledger posting)
- MODERATOR approval has same financial effect as OWNER_TREASURER

**Frontend Enforcement:**
- AI Review Queue tab visible only to OWNER_TREASURER/MODERATOR
- Approve/Reject buttons enabled for both roles
- Image viewer accessible to both roles

### 3. Audit Log

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| View audit logs | GET `/admin/audit-logs` | ✅ | ✅ | ❌ | ❌ |
| Filter by action/entity | Query params | ✅ | ✅ | ❌ | ❌ |
| View audit detail | Click row in table | ✅ | ✅ | ❌ | ❌ |

**Frontend Enforcement:**
- Audit Log tab visible to OWNER_TREASURER/MODERATOR
- Read-only for both roles (immutable history)

### 4. System Monitoring

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| View worker status | GET `/admin/workers` | ✅ | ✅ | ❌ | ❌ |
| View system health | GET `/admin/health` | ✅ | ✅ | ❌ | ❌ |
| View queue status | GET `/admin/queue-status` | ✅ | ✅ | ❌ | ❌ |
| View admin stats | GET `/admin/stats` | ✅ | ✅ | ❌ | ❌ |

**Frontend Enforcement:**
- System Monitoring tab visible to OWNER_TREASURER/MODERATOR
- Read-only for both roles

### 5. User Management (Conditional - Requires Backend Support)

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| List users | GET `/admin/users` | ✅ | ❌ | ❌ | ❌ |
| Update user role | PUT `/admin/users/{id}/role` | ✅ | ❌ | ❌ | ❌ |
| View own profile | GET `/auth/me` | ✅ | ✅ | ✅ | ❌ |

**Notes:**
- User management endpoints DO NOT EXIST yet
- Only OWNER_TREASURER should manage roles
- MODERATOR cannot promote/demote users
- Implementation depends on backend decision

### 6. Public/Shared Features

| Action | Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|--------|----------|-----------------|-----------|--------|--------|
| Public fund view | GET `/public/fund` | ✅ | ✅ | ✅ | ✅ |
| Public bank accounts | GET `/public/bank-accounts` | ✅ | ✅ | ✅ | ✅ |
| Upload receipt | POST `/uploads` | ✅ | ✅ | ✅ | ✅* |
| Chat (guest) | WebSocket/REST | ✅ | ✅ | ✅ | ✅ |
| Login | POST `/auth/login` | ✅ | ✅ | ✅ | ✅ |

*PUBLIC can upload but requires uploader_name (no auth)

---

## Frontend Navigation by Role

### OWNER_TREASURER (Full Admin Access)
```
Tabs: [Dashboard] [Ledger] [Upload] [Campaign] [Chat] [Bank] [Donate] [Public]
      [Admin: Overview] [Admin: Review] [Admin: Ledger] [Admin: Audit] [Admin: System] [Admin: Users]
```

### MODERATOR (Review + Monitoring)
```
Tabs: [Dashboard] [Ledger] [Upload] [Campaign] [Chat] [Bank] [Donate] [Public]
      [Admin: Overview] [Admin: Review] [Admin: Ledger] [Admin: Audit] [Admin: System]
```
- No "Users" tab
- Ledger: read-only (no manual entry/revert)
- Admin Ledger: read-only with filters

### MEMBER (Standard User)
```
Tabs: [Dashboard] [Ledger] [Upload] [Campaign] [Chat] [Bank] [Donate] [Public]
```
- No admin tabs
- Can upload receipts, chat, view ledger
- Cannot access admin features

### PUBLIC (Unauthenticated)
```
Tabs: [Public Fund] [Bank QR] [Donate] [Guest Chat]
```
- Only public-facing views
- No authentication required
- Cannot upload (needs name), cannot chat (needs name)

---

## Backend Authorization Implementation

### Existing Dependencies (`app/api/deps.py`)

```python
def require_roles(*roles: Role) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency
```

### Current Route Protections

**`fund.py`:**
- `/credit` - `require_roles(Role.OWNER_TREASURER)`
- `/debit` - `require_roles(Role.OWNER_TREASURER)`
- `/transactions/{id}/revert` - `require_roles(Role.OWNER_TREASURER)`
- `/accounts/{id}/opening-balance` - `require_roles(Role.OWNER_TREASURER)`
- `/bank-accounts` POST - `require_roles(Role.OWNER_TREASURER)`
- Others - `get_current_user` (any authenticated)

**`review.py`:**
- All routes - `dependencies=[Depends(require_role(Role.OWNER_TREASURER, Role.MODERATOR))]`

**`ai_internal.py`:**
- All routes - `dependencies=[Depends(require_ai_service)]` (service-to-service)

---

## New Admin Endpoints - Required Authorization

### `/admin/stats` - GET
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))]
```

### `/admin/audit-logs` - GET
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))]
```

### `/admin/workers` - GET
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))]
```

### `/admin/health` - GET
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))]
```

### `/admin/queue-status` - GET
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))]
```

### `/admin/users` - GET (if implemented)
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER))]
```

### `/admin/users/{id}/role` - PUT (if implemented)
```python
dependencies=[Depends(require_roles(Role.OWNER_TREASURER))]
```

---

## Frontend Authorization Implementation

### Role Check Hook (`src/hooks/useRole.ts`)
```typescript
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';

export function useRole() {
  const { currentUser } = useApp();
  
  const hasRole = (...roles: UserRole[]) => roles.includes(currentUser.role);
  const isAdmin = () => hasRole('OWNER_TREASURER', 'MODERATOR');
  const isOwner = () => hasRole('OWNER_TREASURER');
  const isModerator = () => hasRole('MODERATOR');
  const isMember = () => hasRole('MEMBER');
  const isPublic = () => hasRole('PUBLIC');
  
  return { currentUser, hasRole, isAdmin, isOwner, isModerator, isMember, isPublic };
}
```

### Admin Route Guard Component
```typescript
import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useRole } from '../hooks/useRole';

interface AdminRouteProps {
  children: ReactNode;
  allowedRoles?: UserRole[];
}

export const AdminRoute: React.FC<AdminRouteProps> = ({ 
  children, 
  allowedRoles = ['OWNER_TREASURER', 'MODERATOR'] 
}) => {
  const { hasRole } = useRole();
  const location = useLocation();
  
  if (!hasRole(...allowedRoles)) {
    return <Navigate to="/dashboard" replace state={{ from: location }} />;
  }
  
  return <>{children}</>;
};
```

### Conditional Rendering in Navbar
```typescript
const { isAdmin, isOwner } = useRole();

// Admin tabs only for admin roles
{isAdmin() && (
  <>
    <AdminTab name="Overview" tab="admin-dashboard" />
    <AdminTab name="AI Review" tab="admin-review" />
    <AdminTab name="Ledger" tab="admin-ledger" />
    <AdminTab name="Audit" tab="admin-audit" />
    <AdminTab name="System" tab="admin-system" />
    {isOwner() && <AdminTab name="Users" tab="admin-users" />}
  </>
)}
```

### Action Button Permissions
```typescript
// Manual entry button - only OWNER_TREASURER
{isOwner() && (
  <Button onClick={openManualEntryModal}>Manual Entry</Button>
)}

// Revert button - only OWNER_TREASURER
{isOwner() && tx.status === 'VERIFIED' && (
  <Button onClick={() => openRevertModal(tx)}>Revert</Button>
)}

// Approve/Reject - both OWNER_TREASURER and MODERATOR
{isAdmin() && (
  <>
    <Button onClick={() => approve(extraction.id)}>Approve</Button>
    <Button onClick={() => reject(extraction.id)}>Reject</Button>
  </>
)}
```

---

## Security Notes

### Backend Authorization is Authoritative
- Frontend hiding/disabling is UX only
- All mutating endpoints enforce roles server-side
- JWT token validated on every request
- Revoked token check on every request

### No Privilege Escalation
- MODERATOR cannot access OWNER_TREASURER-only endpoints
- MEMBER cannot access admin endpoints
- PUBLIC cannot access authenticated endpoints

### Audit Trail
- All admin actions logged via `write_audit()`
- Actor ID, action, entity, before/after data captured
- Immutable - no delete/update of audit logs

### Token Management
- Access tokens short-lived (configurable)
- Refresh token rotation (if implemented)
- Logout revokes token (stored in `RevokedToken` table)
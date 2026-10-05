# Phase 6 Authentication Replacement Design

## Overview
This document designs the self-hosted authentication system to replace Supabase Auth, preserving all current security properties and role mappings.

---

## 1. Current Authentication Architecture

### 1.1 Supabase Auth Usage
| Component | Usage | Replacement |
|-----------|-------|-------------|
| JWT Verification | `supabase_client.py:verify_jwt()` | Local JWT verification |
| User Lookup | `supabase_client.py:get_user_by_id()` | Local DB query |
| Password Hashing | `app/core/security.py` (bcrypt) | **Already local** - keep |
| Token Creation | `app/core/security.py:create_access_token()` | **Already local** - keep |
| Role Claims | JWT `role` claim | **Already local** - keep |

### 1.2 Local Auth Already Implemented
```python
# app/core/security.py - EXISTING, WORKING
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, role: str, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

### 1.3 FastAPI Dependencies (EXISTING)
```python
# app/api/deps.py - EXISTING
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User, Role

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.get(User, user_id)
    if not user or user.role.value != role:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*allowed_roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
```

---

## 2. Supabase Auth Code to Remove

### 2.1 Dead Code in supabase_client.py
```python
# REMOVE these methods:
def verify_jwt(self, token: str) -> dict:  # Lines 117-124
    # Supabase JWT verification - UNUSED
    # Local JWT verification already in app.core.security

def get_user_by_id(self, user_id: str) -> dict:  # Lines 126-132
    # Supabase admin user lookup - UNUSED
    # Local DB query via get_current_user

def enable_rls(self, table: str):  # Lines 135-137
    # Supabase RLS - UNUSED

def create_policy(self, table: str, policy_name: str, definition: str, roles: list = None):  # Lines 139-146
    # Supabase RLS policies - UNUSED
```

### 2.2 Unused Config Variables
```python
# app/core/config.py - REMOVE
supabase_url: Optional[str] = None
supabase_service_key: Optional[str] = None
supabase_anon_key: Optional[str] = None
supabase_jwt_secret: Optional[str] = None  # Different from jwt_secret
```

---

## 3. Enhanced Local Auth Features

### 3.1 Refresh Token Implementation

**Current:** Only access tokens (60 min expiry)
**Required:** Refresh tokens for better UX

```python
# app/core/security.py - ADD
from uuid import uuid4

def create_refresh_token(subject: str, expires_delta: timedelta = None) -> str:
    """Create long-lived refresh token (stored in DB)."""
    token = uuid4().hex
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=30))
    
    # Store in revoked_tokens table (reuse with type='refresh')
    # Or create new refresh_tokens table
    return token

def verify_refresh_token(token: str, db: Session) -> str | None:
    """Verify refresh token and return user_id."""
    # Check revoked_tokens table for valid refresh token
    # Return user_id if valid
    pass
```

### 3.2 Token Refresh Endpoint

```python
# app/api/routes/auth.py - ADD
@router.post("/refresh")
def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = verify_refresh_token(refresh_token, db)
    if not user_id:
        raise HTTPException(401, "Invalid refresh token")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    
    access_token = create_access_token(subject=user.id, role=user.role.value)
    new_refresh = create_refresh_token(user_id)
    
    # Rotate refresh token (invalidate old, store new)
    rotate_refresh_token(db, refresh_token, new_refresh, user_id)
    
    return {"access_token": access_token, "refresh_token": new_refresh, "token_type": "bearer"}
```

### 3.3 Session Revocation (Already Exists)

```python
# revoked_tokens table - ALREADY EXISTS
class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

# Usage in logout:
@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = decode_access_token(credentials.credentials)
    jti = payload.get("jti")  # Add jti to token payload
    exp = payload.get("exp")
    
    revoked = RevokedToken(
        jti=jti,
        user_id=payload["sub"],
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)
    )
    db.add(revoked)
    db.commit()
    return {"message": "Logged out"}
```

### 3.4 Password Reset Flow

```python
# app/api/routes/auth.py - ADD
@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        # Generate reset token, store with expiry
        # Send email (via notification service)
        pass
    # Always return success (don't reveal if email exists)
    return {"message": "If email exists, reset link sent"}

@router.post("/reset-password")
def reset_password(token: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db)):
    # Verify token, update password_hash
    pass
```

---

## 4. Role Mapping Preservation

### 4.1 Role Hierarchy (Unchanged)

| Role | Permissions | JWT Claim |
|------|-------------|-----------|
| `OWNER_TREASURER` | Full access: financial, admin, users, campaigns | `role: "OWNER_TREASURER"` |
| `MODERATOR` | Review AI extractions, manage campaigns, view audit | `role: "MODERATOR"` |
| `MEMBER` | Upload receipts, view own transactions, chat | `role: "MEMBER"` |
| `PUBLIC` | View public fund info, create guest messages | `role: "PUBLIC"` |

### 4.2 Permission Matrix

| Endpoint | OWNER_TREASURER | MODERATOR | MEMBER | PUBLIC |
|----------|-----------------|-----------|--------|--------|
| `/admin/*` | ✅ | ❌ | ❌ | ❌ |
| `/internal/review/*` | ✅ | ✅ | ❌ | ❌ |
| `/fund/*` | ✅ | ✅ | ✅ | ❌ |
| `/campaigns/*` | ✅ | ✅ | ✅ | ❌ |
| `/uploads` | ✅ | ✅ | ✅ | ❌ |
| `/messages` | ✅ | ✅ | ✅ | ✅ (guest) |
| `/public/*` | ✅ | ✅ | ✅ | ✅ |

---

## 5. Frontend Authentication Updates

### 5.1 Remove Supabase Auth Config

```typescript
// classfund/classfund/src/hooks/useChat.ts - REMOVE
supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,

// classfund/classfund/src/lib/realtime.ts - REMOVE
supabaseUrl?: string;
supabaseAnonKey?: string;
// ... all Supabase client creation
```

### 5.2 Local Auth Service

```typescript
// classfund/classfund/src/lib/auth.ts - CREATE NEW
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export const authService = {
  async login(email: string, password: string): Promise<TokenPair> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  async register(data: { email: string; password: string; name: string }): Promise<TokenPair> {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Registration failed');
    return response.json();
  },

  async refresh(refreshToken: string): Promise<TokenPair> {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ refresh_token: refreshToken }),
    });
    if (!response.ok) throw new Error('Refresh failed');
    return response.json();
  },

  async logout(accessToken: string): Promise<void> {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  },

  getStoredTokens(): TokenPair | null {
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');
    return access && refresh ? { access_token: access, refresh_token: refresh } : null;
  },

  setTokens(tokens: TokenPair): void {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  },

  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};
```

### 5.3 Auto-Refresh Interceptor

```typescript
// classfund/classfund/src/lib/api.ts - ENHANCE
let isRefreshing = false;
let refreshPromise: Promise<TokenPair> | null = null;

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const tokens = authService.getStoredTokens();
  const headers = new Headers(options.headers);
  if (tokens?.access_token) {
    headers.set('Authorization', `Bearer ${tokens.access_token}`);
  }

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && tokens?.refresh_token && !url.includes('/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = authService.refresh(tokens.refresh_token).finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }
    
    const newTokens = await refreshPromise;
    if (newTokens) {
      authService.setTokens(newTokens);
      headers.set('Authorization', `Bearer ${newTokens.access_token}`);
      response = await fetch(url, { ...options, headers });
    }
  }

  return response;
}
```

---

## 6. Security Hardening

### 6.1 Token Security
- Access token: 60 minutes (configurable)
- Refresh token: 30 days, rotated on use
- JWT algorithm: HS256 (symmetric, secret in env)
- Token storage: HttpOnly cookies (preferred) or localStorage with XSS protection

### 6.2 Password Policy
```python
# app/core/security.py - ADD validation
def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain number"
    if not re.search(r'[!@#$%^&*]', password):
        return False, "Password must contain special character"
    return True, "OK"
```

### 6.3 Rate Limiting
```python
# app/api/routes/auth.py - ADD rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("5/minute")
def login(...):
    ...

@router.post("/register")
@limiter.limit("3/minute")
def register(...):
    ...
```

---

## 7. Migration Plan

### 7.1 Phase 1: Remove Supabase Auth Code
1. Delete `verify_jwt`, `get_user_by_id`, `enable_rls`, `create_policy` from `supabase_client.py`
2. Remove Supabase auth config from `config.py`
3. Remove Supabase auth env vars from `.env.example`

### 7.2 Phase 2: Enhance Local Auth
1. Add refresh token support
2. Add token refresh endpoint
3. Add logout with revocation
4. Add password reset flow

### 7.3 Phase 3: Frontend Migration
1. Create `auth.ts` service
2. Update `api.ts` with auto-refresh
3. Remove Supabase config from frontend
4. Remove `@supabase/supabase-js` from `package.json`

### 7.4 Phase 4: Testing
1. Test login/register/refresh/logout
2. Test token expiry and refresh
3. Test role-based access
4. Test concurrent sessions

---

## 8. Verification Checklist

- [ ] `supabase_client.py` has no auth methods
- [ ] `config.py` has no Supabase auth vars
- [ ] Local JWT verification works for all endpoints
- [ ] Refresh token flow works
- [ ] Session revocation works
- [ ] Password reset works
- [ ] Frontend uses local auth only
- [ ] `@supabase/supabase-js` removed from package.json
- [ ] All role permissions preserved
- [ ] Rate limiting on auth endpoints

---

**Status: AUTH REPLACEMENT DESIGN COMPLETE - Ready for Storage Replacement Design**
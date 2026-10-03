# 05_SUPABASE_BACKEND_INTEGRATION.md

## Phase 2 Supabase Backend Integration

**Status**: ✅ CODE COMPLETE — ⏳ LIVE INTEGRATION BLOCKED_EXTERNAL_DEPENDENCY
**Location**: `app/services/supabase_client.py`, `app/api/deps.py`

### 1. Integration Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SUPABASE INTEGRATION LAYER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │  Backend App     │    │  Supabase Client │    │  Supabase Platform  │   │
│  │  (FastAPI)       │◄───│  (Python SDK)    │◄───│                     │   │
│  │                  │    │                  │    │  ┌──────────────┐  │   │
│  │  • Routes        │    │  • Admin Client  │    │  │ PostgreSQL   │  │   │
│  │  • Services      │    │  • Anon Client   │    │  │ (Database)   │  │   │
│  │  • Worker        │    │  • User Client   │    │  ├──────────────┤  │   │
│  │                  │    │                  │    │  │ Storage      │  │   │
│  │  Uses:           │    │  Operations:     │    │  │ (Receipts)   │  │   │
│  │  • get_db()      │    │  • upload_       │    │  ├──────────────┤  │   │
│  │  • verify_jwt()  │    │    receipt()     │    │  │ Realtime     │  │   │
│  │  • upload_       │    │  • download_     │    │  │ (Messages,   │  │   │
│  │    receipt()     │    │    receipt()     │    │  │  Workers)    │  │   │
│  │  • subscribe_*() │    │  • verify_jwt()  │    │  ├──────────────┤  │   │
│  │                  │    │  • RLS helpers   │    │  │ Auth         │  │   │
│  └──────────────────┘    └──────────────────┘    │  │ (JWT, Users) │  │   │
│                                                   └──────────────────┘  │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Client Architecture

#### 2.1 Three Client Pattern

```python
class SupabaseClient:
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or SupabaseConfig()
        self._admin_client: Optional[Client] = None
        self._anon_client: Optional[Client] = None
    
    @property
    def admin(self) -> Client:
        """Service role - server-side ONLY. Full bypass of RLS."""
        if self._admin_client is None:
            if not self.config.service_key:
                raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
            self._admin_client = create_client(self.config.url, self.config.service_key)
        return self._admin_client
    
    @property
    def anon(self) -> Client:
        """Anonymous - public operations. Subject to RLS."""
        if self._anon_client is None:
            if not self.config.anon_key:
                raise RuntimeError("SUPABASE_ANON_KEY not configured")
            self._anon_client = create_client(self.config.url, self.config.anon_key)
        return self._anon_client
    
    def get_user_client(self, access_token: str) -> Client:
        """Per-request authenticated client. Subject to RLS."""
        client = create_client(self.config.url, self.config.anon_key)
        client.auth.set_session(access_token, "")
        return client
```

**Security Boundary**:
| Client | Credential | Use Case | RLS |
|--------|------------|----------|-----|
| `admin` | `SERVICE_ROLE_KEY` | Worker, internal APIs, storage, RLS mgmt | **Bypassed** |
| `anon` | `ANON_KEY` | Public reads, unauthenticated writes | **Enforced** |
| `user` | User JWT | Authenticated user operations | **Enforced** |

#### 2.2 Configuration

```python
class SupabaseConfig:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    def validate(self) -> bool:
        return all([self.url, self.service_key, self.anon_key])
```

**Required Environment Variables** (BLOCKED - not provided):
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ... (server only, never in frontend)
SUPABASE_ANON_KEY=eyJ... (public, safe for frontend)
SUPABASE_JWT_SECRET=... (for JWT verification)
```

### 3. Storage Operations

**Bucket**: `receipts` (public access enabled)

```python
def upload_receipt(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
    """Upload receipt to Supabase Storage. Returns public URL."""
    bucket = "receipts"
    path = f"uploads/{file_name}"
    try:
        self.admin.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type}
        )
        return self.admin.storage.from_(bucket).get_public_url(path)
    except APIError as e:
        if "already exists" in str(e):
            return self.admin.storage.from_(bucket).get_public_url(path)
        raise

def download_receipt(self, path: str) -> bytes:
    bucket = "receipts"
    return self.admin.storage.from_(bucket).download(path)

def delete_receipt(self, path: str) -> bool:
    bucket = "receipts"
    try:
        self.admin.storage.from_(bucket).remove([path])
        return True
    except APIError:
        return False
```

**Integration with Upload API** (`uploads.py`):
```python
@router.post("", response_model=UploadOut, status_code=201)
async def create_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate file (MIME, size) - TODO Phase 2
    file_bytes = await file.read()
    file_hash = sha256(file_bytes).hexdigest()
    
    # Check duplicate
    existing = db.execute(select(Upload).where(Upload.file_hash == file_hash)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Duplicate file")
    
    # Upload to Supabase Storage
    supabase = get_supabase_client()
    storage_path = supabase.upload_receipt(file_bytes, file.filename, file.content_type)
    
    # Create upload record
    upload = Upload(
        file_hash=file_hash,
        original_filename=file.filename,
        storage_path=storage_path,  # Public URL
        uploader_name="Guest",
        status=UploadStatus.PENDING,
    )
    db.add(upload)
    db.commit()
    return upload
```

### 4. Realtime Subscriptions

```python
def subscribe_to_messages(self, conversation_id: str, callback):
    """Subscribe to message changes in a conversation."""
    channel = self.admin.channel(f"messages:{conversation_id}")
    channel.on(
        "postgres_changes",
        {
            "event": "*",
            "schema": "public",
            "table": "messages",
            "filter": f"conversation_id=eq.{conversation_id}"
        },
        callback
    )
    channel.subscribe()
    return channel

def subscribe_to_worker_status(self, callback):
    """Subscribe to worker status changes."""
    channel = self.admin.channel("worker_status")
    channel.on(
        "postgres_changes",
        {
            "event": "*",
            "schema": "public",
            "table": "worker_status"
        },
        callback
    )
    channel.subscribe()
    return channel
```

**Frontend Integration** (Phase 3):
```javascript
// Subscribe to message updates
const channel = supabase.channel('messages:conv-123')
channel.on('postgres_changes', {
  event: '*', schema: 'public', table: 'messages',
  filter: 'conversation_id=eq.conv-123'
}, (payload) => {
  // Update UI with new message status
})
channel.subscribe()
```

### 5. Auth Integration

#### 5.1 JWT Verification

```python
def verify_jwt(self, token: str) -> dict:
    """Verify JWT and return claims."""
    try:
        response = self.admin.auth.get_user(token)
        return response.user.model_dump() if response.user else {}
    except Exception:
        return {}
```

#### 5.2 FastAPI Dependency (`app/api/deps.py`)

```python
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    supabase: SupabaseClient = Depends(get_supabase_client),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    claims = supabase.verify_jwt(token)
    if not claims:
        raise HTTPException(401, "Invalid or expired token")
    
    user_id = claims.get("id") or claims.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_roles(*allowed_roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker

def require_ai_service(
    authorization: str = Header(None),
    supabase: SupabaseClient = Depends(get_supabase_client),
):
    """Verify service-to-service auth for AI adapter."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing service token")
    token = authorization.split(" ")[1]
    # Verify against AI_SERVICE_TOKEN env or Supabase service role
    expected = os.getenv("AI_SERVICE_TOKEN")
    if not expected or token != expected:
        raise HTTPException(403, "Invalid service token")
    return True
```

### 6. RLS Policy Helpers

```python
def enable_rls(self, table: str):
    """Enable RLS on a table (admin only)."""
    self.admin.rpc("enable_rls", {"table_name": table}).execute()

def create_policy(self, table: str, policy_name: str, definition: str, roles: list = None):
    """Create RLS policy (admin only)."""
    self.admin.rpc("create_policy", {
        "table_name": table,
        "policy_name": policy_name,
        "definition": definition,
        "roles": roles or ["anon", "authenticated"]
    }).execute()
```

**Policies Defined** (from `12_SECURITY_AND_RLS_AUDIT.md`):

```sql
-- Messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "messages_guest_create" ON messages FOR INSERT TO anon WITH CHECK (sender_role = 'PUBLIC');
CREATE POLICY "messages_guest_read" ON messages FOR SELECT TO anon USING (sender_id IS NULL AND sender_role = 'PUBLIC');
CREATE POLICY "messages_admin_all" ON messages FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Transactions
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "transactions_admin" ON transactions FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Worker Status
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "worker_admin" ON worker_status FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Recall Tokens
ALTER TABLE recall_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "recall_token_owner" ON recall_tokens FOR SELECT TO anon USING (
    EXISTS (SELECT 1 FROM messages m WHERE m.id = recall_tokens.message_id AND m.sender_id IS NULL)
);
CREATE POLICY "recall_token_admin" ON recall_tokens FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Uploads
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "uploads_guest_create" ON uploads FOR INSERT TO anon WITH CHECK (uploaded_by IS NULL);
CREATE POLICY "uploads_guest_read" ON uploads FOR SELECT TO anon USING (uploaded_by IS NULL);
CREATE POLICY "uploads_admin_all" ON uploads FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));
```

### 7. Health Check

```python
def check_supabase_connection() -> bool:
    """Check if Supabase is reachable."""
    try:
        client = get_supabase_client()
        client.admin.table("messages").select("id").limit(1).execute()
        return True
    except Exception:
        return False
```

**Health Endpoint** (`health.py`):
```python
@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Database
    db.execute(text("SELECT 1"))
    
    # Supabase
    supabase_ok = check_supabase_connection()
    
    return {
        "status": "healthy" if supabase_ok else "degraded",
        "database": "ok",
        "supabase": "ok" if supabase_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

### 8. Database Connection (SQLAlchemy + Supabase)

**Configuration** (`app/core/config.py`):
```python
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./test.db")
    # For Supabase: postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
```

**Session Management** (`app/db/session.py`):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine(settings.database_url, future=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Worker Database** (`worker/main.py`):
```python
self.engine = create_engine(database_url, future=True, pool_size=5, max_overflow=10)
self.Session = sessionmaker(bind=self.engine)
```

### 9. Migration Compatibility

All migrations (0001-0004) are PostgreSQL-compatible:
- UUID as `String(36)` (not native UUID for portability)
- `TIMESTAMP WITH TIME ZONE` for all datetime
- `JSONB` for metadata columns
- Partial indexes with `postgresql_where`
- `ON CONFLICT` for upserts

**Apply to Supabase**:
```bash
# In Supabase SQL Editor or via CLI
alembic upgrade head
```

### 10. Testing Strategy

| Test Type | Status | Notes |
|-----------|--------|-------|
| Unit tests (mocked client) | ⏳ PENDING | Need to add |
| Storage upload/download | BLOCKED | Requires credentials |
| Realtime subscription | BLOCKED | Requires credentials |
| JWT verification | BLOCKED | Requires credentials |
| RLS policy enforcement | BLOCKED | Requires Supabase project |
| Multi-user isolation | BLOCKED | Requires Supabase project |

**Mock Testing Pattern**:
```python
# tests/test_supabase_mock.py
from unittest.mock import AsyncMock, MagicMock, patch

def test_upload_receipt_mock():
    with patch("app.services.supabase_client.create_client") as mock_create:
        mock_admin = MagicMock()
        mock_admin.storage.from_.return_value.upload.return_value = None
        mock_admin.storage.from_.return_value.get_public_url.return_value = "https://xxx.supabase.co/storage/v1/object/public/receipts/uploads/test.png"
        mock_create.return_value = mock_admin
        
        client = SupabaseClient()
        url = client.upload_receipt(b"test", "test.png", "image/png")
        assert "supabase.co" in url
```

### 11. Current Status

| Component | Code | Unit Tests | Live Test | Status |
|-----------|------|------------|-----------|--------|
| Client wrapper | ✅ | ⏳ | BLOCKED | READY |
| Storage ops | ✅ | ⏳ | BLOCKED | READY |
| Realtime | ✅ | ⏳ | BLOCKED | READY |
| Auth/JWT | ✅ | ⏳ | BLOCKED | READY |
| RLS helpers | ✅ | ⏳ | BLOCKED | READY |
| Health check | ✅ | ⏳ | BLOCKED | READY |
| SQLAlchemy + Supabase | ✅ | ✅ (SQLite) | BLOCKED | READY |

### 12. Blockers

| Blocker | Impact | Resolution |
|---------|--------|------------|
| No Supabase credentials | Cannot verify live integration | Marked BLOCKED_EXTERNAL_DEPENDENCY |
| No Supabase project | Cannot test RLS, Realtime, Storage | Need project setup |
| No JWT secret | Cannot verify auth flow | Need Supabase project |

### 13. Phase 2 Deliverables

- ✅ `SupabaseClient` class with three-client pattern
- ✅ Storage operations (upload/download/delete)
- ✅ Realtime subscription helpers
- ✅ JWT verification for auth
- ✅ RLS policy management helpers
- ✅ Health check endpoint
- ✅ SQLAlchemy compatible with Supabase PostgreSQL
- ⏳ Unit tests with mocks (TODO)
- ⏳ Integration test documentation (TODO)

---

**Status**: ✅ CODE COMPLETE — All Supabase integration code implemented and ready. Live verification **BLOCKED_EXTERNAL_DEPENDENCY** (no credentials provided). Mock-based unit tests should be added in Phase 2.
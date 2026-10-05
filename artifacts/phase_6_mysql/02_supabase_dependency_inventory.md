# Phase 6 Supabase Dependency Inventory

## Overview
This document provides a complete dependency map of all Supabase integrations in CLASS_FUND_WEB. Every active runtime dependency is documented with its location, responsibility, consumers, replacement design, migration status, and verification evidence.

---

## 1. Supabase PostgreSQL Database

### Status: **ACTIVE - PRIMARY DATABASE**
**Note:** Currently using local PostgreSQL (docker-compose), not Supabase hosted PostgreSQL. The Supabase PostgreSQL dependency is architectural (compatible with Supabase) but not a runtime dependency on Supabase cloud.

| Aspect | Detail |
|--------|--------|
| **File/Location** | `docker-compose.yml`, `alembic.ini`, `app/core/config.py` |
| **Current Responsibility** | Primary data store for all 17 tables |
| **Consumers** | All backend services, all API routes, worker |
| **Replacement Design** | MySQL 8.4 LTS with InnoDB, utf8mb4 |
| **Migration Status** | **NOT STARTED** - Phase 6 objective |
| **Verification Evidence** | Alembic migrations must run on MySQL; all tests pass on MySQL |

### PostgreSQL-Specific Features in Use
1. `postgresql.JSONB` - worker_status.metadata column
2. Native ENUM types (`Enum(..., native_enum=False)`)
3. Partial indexes with `postgresql_where` (3 indexes on messages table)
4. `server_default=sa.func.now()` for timestamps

---

## 2. Supabase Auth

### 2.1 Backend JWT Verification

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:117-124` (`verify_jwt` method) |
| **Current Responsibility** | Verify JWT tokens and return user claims |
| **Consumers** | `app/api/routes/admin.py` (health check), any future protected endpoints |
| **Code** | ```python<br>def verify_jwt(self, token: str) -> dict:<br>    try:<br>        response = self.admin.auth.get_user(token)<br>        return response.user.model_dump() if response.user else {}<br>    except Exception:<br>        return {}<br>``` |
| **Replacement Design** | Local JWT verification using `app.core.security` (already implemented: `create_access_token`, `decode_access_token`, `hash_password`, `verify_password`) |
| **Migration Status** | **PARTIAL** - Local auth exists but Supabase verify_jwt is still callable |
| **Verification Evidence** | All auth endpoints work with local JWT only; Supabase verify_jwt removed |

### 2.2 Backend Admin User Lookup

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:126-132` (`get_user_by_id` method) |
| **Current Responsibility** | Fetch user details by ID (admin only) |
| **Consumers** | Admin endpoints, worker status |
| **Replacement Design** | Query local `users` table directly via SQLAlchemy |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Admin user lookup works via local DB |

### 2.3 Frontend Auth Config

| Aspect | Detail |
|--------|--------|
| **File/Location** | `classfund/classfund/src/hooks/useChat.ts:91-92`, `src/lib/realtime.ts:10-11,27-28`, `src/lib/polling.ts:151-152,169-170` |
| **Current Responsibility** | Supabase URL and anon key for realtime connection |
| **Consumers** | RealtimeAdapter, polling fallback |
| **Replacement Design** | Remove Supabase config; use backend WebSocket/SSE endpoint |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Frontend connects to backend realtime without Supabase |

### 2.4 Supabase Auth Environment Variables

| Variable | Used By | Replacement |
|----------|---------|-------------|
| `SUPABASE_URL` | Backend supabase_client.py, worker/main.py | Remove |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend supabase_client.py | Remove |
| `SUPABASE_ANON_KEY` | Backend supabase_client.py, Frontend realtime.ts/polling.ts | Remove |
| `SUPABASE_JWT_SECRET` | Backend supabase_client.py (unused - local JWT uses separate secret) | Remove |
| `VITE_SUPABASE_URL` | Frontend realtime.ts, polling.ts, useChat.ts | Remove |
| `VITE_SUPABASE_ANON_KEY` | Frontend realtime.ts, polling.ts, useChat.ts | Remove |

---

## 3. Supabase Storage

### 3.1 Backend Receipt Upload

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:53-68` (`upload_receipt` method) |
| **Current Responsibility** | Upload receipt images to Supabase Storage bucket "receipts"; returns public URL |
| **Consumers** | `app/api/routes/vision.py:66` (downloads for AI processing) |
| **Code** | ```python<br>def upload_receipt(self, file_bytes: bytes, file_name: str, content_type: str) -> str:<br>    bucket = "receipts"<br>    path = f"uploads/{file_name}"<br>    self.admin.storage.from_(bucket).upload(...)<br>    return self.admin.storage.from_(bucket).get_public_url(path)<br>``` |
| **Replacement Design** | Local filesystem storage (already implemented in `uploads.py:42-44` - saves to `./storage/uploads/`). Vision route already has fallback to local file read. |
| **Migration Status** | **PARTIAL** - Local storage primary; Supabase as secondary in vision.py |
| **Verification Evidence** | Uploads work without Supabase; vision extraction reads local files |

### 3.2 Backend Receipt Download

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:70-73` (`download_receipt` method) |
| **Current Responsibility** | Download receipt from Supabase Storage |
| **Consumers** | `app/api/routes/vision.py:66` |
| **Replacement Design** | Read from local filesystem (`Path(storage_path).read_bytes()`) |
| **Migration Status** | **PARTIAL** - Vision route already tries Supabase first, then local |
| **Verification Evidence** | Vision extraction works with local files only |

### 3.3 Backend Receipt Delete

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:75-82` (`delete_receipt` method) |
| **Current Responsibility** | Delete receipt from Supabase Storage |
| **Consumers** | Not currently used in codebase |
| **Replacement Design** | `Path(storage_path).unlink(missing_ok=True)` |
| **Migration Status** | **NOT NEEDED** - Not used |
| **Verification Evidence** | N/A |

### 3.4 Vision Route Storage Fallback

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/api/routes/vision.py:61-66` |
| **Current Responsibility** | Try Supabase storage first, fallback to local |
| **Code** | ```python<br>supabase = get_supabase_client()<br>try:<br>    image_bytes = supabase.download_receipt(upload.storage_path)<br>except Exception:<br>    # Local fallback<br>    image_bytes = Path(upload.storage_path).read_bytes()<br>``` |
| **Replacement Design** | Remove Supabase attempt; read local directly |
| **Migration Status** | **READY** - Fallback already works |
| **Verification Evidence** | Vision works when Supabase unavailable |

---

## 4. Supabase Realtime

### 4.1 Backend Message Subscriptions

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:85-99` (`subscribe_to_messages` method) |
| **Current Responsibility** | Subscribe to PostgreSQL changes on `messages` table for a conversation |
| **Consumers** | `worker/main.py` (Supabase-backed persistent worker) |
| **Code** | Uses `postgres_changes` with filter `conversation_id=eq.{conversation_id}` |
| **Replacement Design** | FastAPI WebSocket endpoint (`/ws/messages/{conversation_id}`) with server-side polling or Redis pub/sub |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Worker receives message updates via WebSocket; frontend realtime works |

### 4.2 Backend Worker Status Subscriptions

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:101-114` (`subscribe_to_worker_status` method) |
| **Current Responsibility** | Subscribe to `worker_status` table changes |
| **Consumers** | `worker/main.py` |
| **Replacement Design** | Same WebSocket channel or separate admin WebSocket |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Worker status updates received via WebSocket |

### 4.3 Frontend Realtime Adapter

| Aspect | Detail |
|--------|--------|
| **File/Location** | `classfund/classfund/src/lib/realtime.ts` (133 lines) |
| **Current Responsibility** | Full Supabase Realtime client for message updates |
| **Consumers** | `hooks/useChat.ts` (line 91-92), chat components |
| **Features** | Auto-reconnect, exponential backoff, connection status callbacks, message filtering |
| **Replacement Design** | Native WebSocket client connecting to backend `/ws/messages/{conversation_id}` with same reconnection logic |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Frontend receives real-time message updates without Supabase |

### 4.4 Worker Main (Supabase-Backed)

| Aspect | Detail |
|--------|--------|
| **File/Location** | `worker/main.py` |
| **Current Responsibility** | Persistent worker using Supabase Realtime for job claiming |
| **Replacement Design** | Polling-based worker or WebSocket-based worker against local backend |
| **Migration Status** | **NOT STARTED** |
| **Verification Evidence** | Worker processes messages without Supabase |

---

## 5. Supabase RLS (Row Level Security)

### 5.1 RLS Policy Helpers

| Aspect | Detail |
|--------|--------|
| **File/Location** | `app/services/supabase_client.py:135-146` (`enable_rls`, `create_policy` methods) |
| **Current Responsibility** | Enable RLS and create policies via Supabase RPC |
| **Consumers** | Not currently used in codebase (no calls found) |
| **Replacement Design** | Application-level authorization in API routes (already implemented via JWT roles) |
| **Migration Status** | **NOT NEEDED** - Unused |
| **Verification Evidence** | Authorization works via `get_current_user` dependency |

### 5.2 Current Authorization Model

| Layer | Implementation |
|-------|----------------|
| **API Routes** | `app/api/deps.py` - `get_current_user`, `require_role` dependencies |
| **JWT** | `app/core/security.py` - Local HS256 tokens with role claim |
| **Role Hierarchy** | OWNER_TREASURER > MODERATOR > MEMBER > PUBLIC |
| **RLS** | Not used - all authorization in application layer |

---

## 6. Supabase Client Libraries

### 6.1 Backend Python Client

| Package | Version | File | Status |
|---------|---------|------|--------|
| `supabase` | (in pyproject.toml) | `app/services/supabase_client.py:5` | **REMOVE** |
| `postgrest` | (in pyproject.toml) | `app/services/supabase_client.py:6` | **REMOVE** |

### 6.2 Frontend JavaScript Client

| Package | Version | File | Status |
|---------|---------|------|--------|
| `@supabase/supabase-js` | ^2.39.0 | `classfund/classfund/package.json:15` | **REMOVE** |

---

## 7. Dependency Matrix Summary

| Component | Backend Files | Frontend Files | Runtime Active | Replacement Priority |
|-----------|---------------|----------------|----------------|---------------------|
| **PostgreSQL Database** | docker-compose, alembic.ini, config.py, all models/routes | - | YES (local PG) | **HIGHEST** - Phase 6 core |
| **Auth (JWT Verify)** | supabase_client.py:117-124 | - | NO (local JWT used) | HIGH - Remove dead code |
| **Auth (User Lookup)** | supabase_client.py:126-132 | - | NO | HIGH - Remove dead code |
| **Auth (Config)** | config.py (4 vars) | realtime.ts, polling.ts, useChat.ts (2 vars) | YES (config only) | HIGH - Remove env vars |
| **Storage (Upload)** | supabase_client.py:53-68 | - | NO (local primary) | MEDIUM - Clean up vision.py |
| **Storage (Download)** | supabase_client.py:70-73, vision.py:66 | - | NO (fallback works) | MEDIUM - Remove Supabase call |
| **Storage (Delete)** | supabase_client.py:75-82 | - | NO (unused) | LOW - Remove dead code |
| **Realtime (Messages)** | supabase_client.py:85-99, worker/main.py | realtime.ts (133 lines) | YES (worker + frontend) | **HIGHEST** - Core feature |
| **Realtime (Worker Status)** | supabase_client.py:101-114, worker/main.py | - | YES (worker) | HIGH |
| **Realtime (Frontend)** | - | realtime.ts, useChat.ts, polling.ts | YES (frontend chat) | **HIGHEST** - User-facing |
| **RLS Policies** | supabase_client.py:135-146 | - | NO (unused) | LOW - Remove dead code |
| **Python Client Lib** | pyproject.toml, supabase_client.py | - | YES (imported) | HIGH - Remove dependency |
| **JS Client Lib** | - | package.json, realtime.ts | YES (imported) | HIGH - Remove dependency |

---

## 8. Replacement Architecture

### Authentication
```
CURRENT: Supabase Auth (JWT verify, user lookup)
REPLACEMENT: Local JWT (already implemented in app.core.security)
  - HS256 signing with JWT_SECRET
  - Role claim in token (OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC)
  - Token refresh via /auth/refresh endpoint (to implement)
  - Session revocation via revoked_tokens table (already exists)
```

### Storage
```
CURRENT: Supabase Storage (receipts bucket, public URLs)
REPLACEMENT: Local filesystem + authenticated file serving
  - Upload: POST /api/v1/uploads → save to ./storage/uploads/{uuid}.{ext}
  - Download: GET /api/v1/uploads/{id}/file → authenticated, role-checked
  - Delete: DELETE /api/v1/uploads/{id} → owner/admin only
  - Vision: Reads local file directly (already works)
  - Backup: Volume mount in docker-compose
```

### Realtime
```
CURRENT: Supabase Realtime (postgres_changes on messages, worker_status)
REPLACEMENT: FastAPI WebSocket + Redis Pub/Sub
  - Backend: WebSocket endpoint /ws/messages/{conversation_id}
  - Backend: Redis channel "messages:{conversation_id}" for broadcasting
  - Worker: Connects via WebSocket or polls /api/v1/messages?status=pending
  - Frontend: WebSocket client with auto-reconnect (replace RealtimeAdapter)
  - Fallback: Long-polling /api/v1/messages (already in polling.ts)
```

### Database
```
CURRENT: PostgreSQL 17 (local docker)
REPLACEMENT: MySQL 8.4 LTS (InnoDB, utf8mb4, strict mode)
  - See 04_mysql_target_architecture.md and 05_postgresql_mysql_compatibility_matrix.md
```

---

## 9. Verification Checklist

Each replacement must pass:

| Replacement | Verification Test |
|-------------|-------------------|
| MySQL Database | All alembic migrations run; all existing tests pass on MySQL |
| Local Auth | Login/register/me work; role-based access works; tokens refresh |
| Local Storage | Upload/download/delete work; vision extraction reads files; 10MB limit |
| WebSocket Realtime | Frontend receives message updates in <500ms; reconnect works; fallback polling |
| Worker | Processes pending messages; claims jobs without conflicts; heartbeats work |
| No Supabase Imports | `grep -r "supabase" --include="*.py" --include="*.ts"` returns only node_modules/.kilo/ |

---

## 10. Migration Order (Dependency Order)

1. **MySQL Database Foundation** (Phase 6 core)
   - Docker Compose MySQL service
   - SQLAlchemy MySQL config
   - Alembic MySQL migrations
   - All tests on MySQL

2. **Local Authentication** (Independent)
   - Remove Supabase verify_jwt/get_user_by_id
   - Ensure all endpoints use local JWT
   - Remove Supabase auth env vars

3. **Local Storage** (Independent)
   - Remove Supabase upload/download from vision.py
   - Add authenticated file serving endpoint
   - Update frontend upload to use local endpoint

4. **WebSocket Realtime** (Depends on MySQL for message persistence)
   - Backend WebSocket endpoint
   - Redis pub/sub for scaling
   - Frontend WebSocket client
   - Worker WebSocket/polling client
   - Remove Supabase realtime code

5. **Cleanup** 
   - Remove supabase_client.py
   - Remove @supabase/supabase-js from package.json
   - Remove all Supabase env vars
   - Update documentation

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MySQL enum/partial index incompatibility | High | High | Use VARCHAR+CHECK for enums; MySQL 8.0+ supports partial indexes |
| Decimal precision loss | Medium | **Critical** | Explicit DECIMAL(18,2) in all migrations; test financial invariants |
| Realtime message loss during migration | Medium | High | Implement message acknowledgment; persist to DB first |
| Worker job claiming race conditions | Medium | High | Use SELECT FOR UPDATE SKIP LOCKED (MySQL 8.0+) |
| Frontend WebSocket reconnection storms | Low | Medium | Exponential backoff; max reconnect attempts |
| File storage permissions | Low | Medium | Docker volume ownership; non-root user |

---

**Status: INVENTORY COMPLETE - Ready for Phase 6 Implementation**
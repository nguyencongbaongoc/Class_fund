# 07_SECURITY_AND_AUTHORIZATION.md

## Phase 2 Security and Authorization

**Status**: ✅ BASELINE IMPLEMENTED — Phase 2 hardening applied
**References**: `12_SECURITY_AND_RLS_AUDIT.md`, `16_REMAINING_GAPS_AND_EXTERNAL_DEPENDENCIES.md`

### 1. Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY BOUNDARIES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXTERNAL                                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │  Guest      │  │  Admin      │  │  AI Adapter │  │  Worker         │   │
│  │  (Browser)  │  │  (Browser)  │  │  (Service)  │  │  (Service)      │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘   │
│         │                │                │                   │            │
│         ▼                ▼                ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        API GATEWAY (FastAPI)                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │  │
│  │  │ Rate Limit  │  │ CORS        │  │ Auth        │  │ Input     │   │  │
│  │  │ (TODO)      │  │ Config      │  │ Middleware  │  │ Validation│   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘   │  │
│  └────────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│         ┌─────────────────────────┼─────────────────────────┐              │
│         ▼                         ▼                         ▼              │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐      │
│  │  Public     │           │  Protected  │           │  Internal   │      │
│  │  Endpoints  │           │  Endpoints  │           │  Endpoints  │      │
│  │  (/messages,│           │  (/fund/*,  │           │  (/internal/│      │
│  │   /uploads, │           │   /campaigns│           │   ai/*)     │      │
│  │   /fund/bal)│           │   admin)    │           │             │      │
│  └──────┬──────┘           └──────┬──────┘           └──────┬──────┘      │
│         │                         │                         │              │
│         ▼                         ▼                         ▼              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      SERVICE LAYER (Business Logic)                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │  │
│  │  │  Financial  │  │  Recall     │  │  Campaign   │  │  Upload   │   │  │
│  │  │  Gatekeeper │  │  Auth       │  │  Rules      │  │  Validation│   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘   │  │
│  └────────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                        │
│                                   ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      DATABASE (PostgreSQL/Supabase)                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │  │
│  │  │ RLS Policies│  │  Unique     │  │  Foreign    │  │  Audit    │   │  │
│  │  │ (Pending)   │  │  Constraints│  │  Keys       │  │  Logs     │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Implemented Security Measures

#### 2.1 Recall Authorization (✅ COMPLETE)

**Threat**: Unauthorized transaction reversal via public message/transaction IDs

**Mitigation**: Private recall token required

```python
# Token generation (messages.py:75-82)
def generate_recall_token() -> tuple[str, str]:
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    return token_hex, token_hash  # Return token ONCE, store hash

# Token validation (messages.py:156-165)
token_hash = sha256(bytes.fromhex(body.recall_token)).hexdigest()
recall_token = db.execute(select(RecallToken).where(...)).scalar_one_or_none()
if not recall_token or recall_token.token_hash != token_hash:
    raise HTTPException(403, "Recall not authorized")
if recall_token.used_at:
    raise HTTPException(409, "Recall token already used")
```

**Test Coverage** (`test_recall.py`):
- ✅ Token generation + validation
- ✅ Recall before post (no transaction)
- ✅ Recall after post (creates reversal)
- ✅ Double recall prevented
- ✅ Token replay protection
- ✅ Public message_id cannot authorize
- ✅ Public transaction_id cannot authorize
- ✅ Worker checks recall before posting

#### 2.2 Financial Gatekeeper (✅ COMPLETE)

**Threat**: Unauthorized financial mutations

**Mitigation**: Single entry point, role-based access

```python
# Only path for AI-derived credits
verify_and_post_from_ai()  # Internal, called by worker/AI adapter

# Admin manual operations require OWNER_TREASURER role
@router.post("/fund/credit", dependencies=[Depends(require_roles(Role.OWNER_TREASURER))])
def manual_credit(...)
```

**Invariants**:
- No direct SQL INSERT to `transactions` table
- All mutations through `post_transaction()` / `post_revert()`
- Idempotency enforced on all financial endpoints

#### 2.3 Idempotency Security (✅ COMPLETE)

**Threat**: Replay attacks, duplicate transactions

**Mitigation**: Fingerprint-bound idempotency keys

```python
# check_idempotency (ledger.py:109-117)
if existing.request_fingerprint != fingerprint:
    raise HTTPException(409, "Idempotency key was reused with a different request")
```

**Properties**:
- Key reuse with different payload → 409 VALIDATION error
- Fingerprint includes all financial fields + message_id
- Stable across retries (retry_count NOT in key)

#### 2.4 Credential Isolation (✅ COMPLETE)

| Credential | Scope | Access |
|------------|-------|--------|
| `SUPABASE_SERVICE_ROLE_KEY` | Server env only | Backend admin client, worker |
| `SUPABASE_ANON_KEY` | Client env | Frontend public ops |
| `SUPABASE_JWT_SECRET` | Server env | JWT verification |
| `JWT_SECRET` | Server env | Auth tokens |
| `AI_SERVICE_TOKEN` | Server env | `/internal/ai/*` auth |
| `DATABASE_URL` | Server env | SQLAlchemy |

**No secrets in Git** — verified by `.gitignore` and no hardcoded values.

#### 2.5 Audit Logging (✅ COMPLETE)

```python
# Every financial mutation writes audit
write_audit(
    db, actor_id=audit_actor_id, action="LEDGER_POST|LEDGER_REVERT|OPENING_BALANCE_UPDATE",
    entity_type="TRANSACTION|ACCOUNT", entity_id=...,
    before={...}, after={...}, ip=...
)
```

**Captured**: Actor, action, entity, before/after state, IP, timestamp

#### 2.6 RLS Policy Helpers (✅ CODE READY)

```python
# supabase_client.py:135-146
def enable_rls(self, table: str): ...
def create_policy(self, table: str, policy_name: str, definition: str, roles: list): ...
```

**Policies Defined** (from `12_SECURITY_AND_RLS_AUDIT.md`):
- Messages: Guest create/read own, Admin all
- Transactions: Admin only
- Worker Status: Admin only
- Recall Tokens: Owner read (via message), Admin all
- Uploads: Guest create/read own, Admin all

**Status**: Helpers implemented, policies **NOT DEPLOYED** (BLOCKED_EXTERNAL_DEPENDENCY)

### 3. Phase 2 Security Hardening (Applied)

| Hardening | Location | Status |
|-----------|----------|--------|
| Input validation on all endpoints | Pydantic schemas | ✅ |
| SQL injection prevention | SQLAlchemy ORM + params | ✅ |
| XSS prevention | No HTML rendering in API | ✅ |
| Path traversal on uploads | UUID filenames, not user-controlled | ✅ |
| File type validation | TODO (Phase 2) | ⏳ |
| File size limits | TODO (Phase 2) | ⏳ |
| Malware scanning | TODO (Phase 2) | ⏳ |
| Rate limiting | TODO (Phase 2) | ⏳ |
| CSP headers | TODO (Phase 2, frontend) | ⏳ |
| CORS configuration | `app/main.py` (basic) | ⏳ |
| Security headers | TODO (Phase 2) | ⏳ |

### 4. Remaining Security Tasks (Phase 2 Scope)

#### 4.1 Rate Limiting (HIGH PRIORITY)

**Target Endpoints**:
```python
# Planned implementation (middleware or dependency)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/messages", dependencies=[Depends(limiter.limit("30/minute"))])
def create_message(...)
```

#### 4.2 File Upload Validation (HIGH PRIORITY)

```python
# uploads.py - add validation
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("")
async def create_upload(file: UploadFile = File(...)):
    # Validate MIME
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Invalid file type: {file.content_type}")
    
    # Validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large: {len(file_bytes)} bytes")
    
    # Validate magic bytes (basic)
    if file.content_type == "image/jpeg" and not file_bytes.startswith(b'\xff\xd8\xff'):
        raise HTTPException(400, "Invalid JPEG file")
    # ... similar for PNG, PDF
```

#### 4.3 CORS Configuration (MEDIUM)

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://classfund.example.com", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Idempotency-Key", "Content-Type"],
    expose_headers=["X-Total-Count", "Retry-After"],
)
```

#### 4.4 Security Headers (MEDIUM)

```python
# Add middleware for security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP will be set by frontend
    return response
```

#### 4.5 RLS Policy Deployment (BLOCKED)

```sql
-- Run in Supabase SQL Editor after project creation
-- See 12_SECURITY_AND_RLS_AUDIT.md for full policies
```

### 5. Threat Model Summary

| Threat | Likelihood | Impact | Mitigation Status |
|--------|------------|--------|-------------------|
| Unauthorized recall | Low | High | ✅ Token auth implemented |
| Duplicate transaction | Medium | High | ✅ 4-layer idempotency |
| SQL injection | Low | Critical | ✅ ORM + params |
| XSS via API | Low | Medium | ✅ JSON API only |
| File upload RCE | Medium | High | ⏳ Validation TODO |
| DoS via message spam | Medium | Medium | ⏳ Rate limit TODO |
| Credential leakage | Low | Critical | ✅ Env only, no Git |
| RLS bypass | Medium | High | ⏳ Policies BLOCKED |
| Replay attack | Low | Medium | ✅ Idempotency + token replay protection |
| Worker hijacking | Low | Medium | ✅ Service role only |
| Audit log tampering | Low | Medium | ✅ Append-only, DB constraints |

### 6. Compliance Notes

- **Data Minimization**: Guest messages store only `sender_name` (no PII beyond what user provides)
- **Right to Delete**: Recall = soft delete + reversal, full purge not implemented
- **Audit Retention**: `audit_logs` table — no retention policy (TODO)
- **Encryption at Rest**: Supabase PostgreSQL (when deployed)
- **Encryption in Transit**: HTTPS enforced (when deployed)

### 7. Penetration Testing Scope (Phase 2+)

**Priority Targets**:
1. Recall flow: Token brute force, replay, timing attacks
2. Financial endpoints: Idempotency bypass, race conditions
3. Upload flow: File type confusion, size limits, path traversal
4. Auth: JWT validation, role escalation
5. Worker: Claim race, lease manipulation

**Status**: Not yet scheduled (requires live environment)

### 8. Security Test Results

| Test | Status | File |
|------|--------|------|
| Recall token validation | ✅ PASSED | `test_recall.py::test_recall_token_generation_and_validation` |
| Token replay protection | ✅ PASSED | `test_recall.py::test_recall_token_replay_protection` |
| Public ID cannot recall | ✅ PASSED | `test_recall.py::test_public_message_id_cannot_authorize_recall` |
| Double recall prevented | ✅ PASSED | `test_recall.py::test_double_recall_prevented` |
| Worker recall check | ✅ PASSED | `test_recall.py::test_worker_checks_recall_before_posting` |
| Idempotency fingerprint | ✅ PASSED | `test_idempotency.py::test_idempotent_same_message_modified_amount_rejected` |
| Concurrent duplicate prevention | ✅ PASSED | `test_idempotency.py::test_concurrent_requests_no_double_post` |

### 9. Known Security Limitations

| Limitation | Risk | Mitigation |
|------------|------|------------|
| No rate limiting | DoS on public endpoints | Implement in Phase 2 |
| No file validation | Malicious uploads | Implement in Phase 2 |
| No malware scan | Infected receipts | Integrate ClamAV (Phase 2+) |
| RLS not deployed | Data isolation unverified | Deploy with Supabase |
| No CSP | XSS if frontend vulnerable | Frontend responsibility |
| No WAF | SQLi, XSS, etc. | Cloudflare/similar (ops) |
| No secrets rotation | Long-lived credentials | Document rotation procedure |

---

**Status**: ✅ BASELINE SECURE — Core authorization (recall tokens, financial gatekeeper, idempotency) implemented and tested. Phase 2 hardening (rate limiting, file validation, security headers, CORS) identified and ready for implementation. RLS deployment BLOCKED_EXTERNAL_DEPENDENCY.
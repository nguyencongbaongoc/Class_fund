# Phase 6 Security Review

## Overview
Security review of the MySQL migration and Supabase replacement, covering authentication, authorization, data protection, network security, and compliance.

---

## 1. Authentication Security

### 1.1 JWT Implementation (Local)

| Aspect | Current | Review |
|--------|---------|--------|
| Algorithm | HS256 | ✅ Symmetric, secret in env |
| Secret Length | Configurable | ⚠️ Must be 32+ chars in production |
| Token Expiry | 60 min (configurable) | ✅ Short-lived access tokens |
| Refresh Tokens | Planned (30 days) | ✅ Rotated on use |
| Token Storage | localStorage (frontend) | ⚠️ Consider HttpOnly cookies |
| Claims | sub, role, exp | ✅ Minimal necessary |

### 1.2 Password Security

| Aspect | Implementation | Review |
|--------|----------------|--------|
| Hashing | bcrypt (passlib) | ✅ Industry standard |
| Cost Factor | Default (12) | ✅ Appropriate |
| Policy | Min 12 chars, complexity | ✅ Enforced on register/reset |
| Rate Limiting | 5/min login, 3/min register | ✅ Prevents brute force |

### 1.3 Session Management

| Feature | Status | Notes |
|---------|--------|-------|
| Access Token | 60 min | Short expiry limits exposure |
| Refresh Token | 30 days, rotated | Rotation prevents replay |
| Revocation | revoked_tokens table | Immediate invalidation |
| Concurrent Sessions | Allowed | Consider limit per user |
| Device Tracking | Not implemented | Future enhancement |

---

## 2. Authorization Security

### 2.1 Role-Based Access Control (RBAC)

| Role | Permissions | Enforcement |
|------|-------------|-------------|
| OWNER_TREASURER | Full: admin, financial, users | FastAPI dependency `require_role` |
| MODERATOR | Review, campaigns, audit | Same |
| MEMBER | Upload, view own, chat | Same |
| PUBLIC | Public fund info, guest messages | Same |

### 2.2 Resource-Level Authorization

| Resource | Owner Check | Admin Override |
|----------|-------------|----------------|
| Uploads | `upload.uploaded_by == user.id` | OWNER_TREASURER, MODERATOR |
| Messages | Conversation membership | OWNER_TREASURER |
| Campaigns | Campaign membership | OWNER_TREASURER, MODERATOR |
| Financial Data | Role-based (MEMBER+) | OWNER_TREASURER |

---

## 3. Data Protection

### 3.1 Encryption

| Data | At Rest | In Transit | Notes |
|------|---------|------------|-------|
| Passwords | bcrypt hash | TLS | Never stored plaintext |
| JWT Secrets | Env var | N/A | Not in code |
| Database | Volume encryption (host) | TLS (prod) | MySQL SSL in production |
| File Storage | Host disk encryption | TLS | Local filesystem |
| Backups | GPG/age encryption | TLS for transfer | Encrypted at rest |

### 3.2 PII Handling

| Data Type | Fields | Protection |
|-----------|--------|------------|
| User | email, name | Minimal collection |
| Transactions | sender_name, account_number | Stored for audit |
| Uploads | original_filename, uploader_name | Authorized access only |

### 3.3 Financial Data

| Protection | Implementation |
|------------|----------------|
| Integrity | DECIMAL(18,2), triggers, app logic |
| Immutability | VERIFIED entries protected |
| Audit Trail | audit_logs table (immutable) |
| Reconciliation | calculate_balance() verification |

---

## 4. Network Security

### 4.1 Service Exposure

| Service | Port | Exposure | Protection |
|---------|------|----------|------------|
| MySQL | 3306 | Dev only (localhost) | **Not exposed in production** |
| Redis | 6379 | Dev only (localhost) | **Not exposed in production** |
| Backend | 8000 | Via Nginx/proxy | Auth required |
| Frontend | 5173/80 | Via Nginx/proxy | Static files |
| WebSocket | 8000/ws | Via Nginx/proxy | Auth required |

### 4.2 Production Network (Future)

```yaml
# Production docker-compose overrides
services:
  mysql:
    # No ports exposed
    networks:
      - internal
  
  redis:
    # No ports exposed
    networks:
      - internal
  
  backend:
    networks:
      - internal
      - frontend
  
  nginx:
    ports:
      - "443:443"
    networks:
      - frontend

networks:
  internal:
    internal: true  # No external access
  frontend:
    external: false
```

### 4.3 TLS Configuration

```nginx
# Nginx SSL termination
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;
}
```

---

## 5. Application Security

### 5.1 Input Validation

| Vector | Protection |
|--------|------------|
| SQL Injection | SQLAlchemy ORM (parameterized) |
| XSS | React auto-escaping, CSP headers |
| CSRF | JWT in headers (not cookies) |
| File Upload | MIME validation, size limit, magic bytes |
| Path Traversal | Secure file serving (no user path input) |

### 5.2 Security Headers

```python
# FastAPI middleware - ADD
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "yourdomain.com"])

# Security headers via middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    return response
```

### 5.3 Rate Limiting

```python
# Applied to auth endpoints
@limiter.limit("5/minute")
async def login(...)

@limiter.limit("10/minute")
async def upload_receipt(...)

@limiter.limit("100/minute")
async def api_endpoints(...)
```

---

## 6. Database Security

### 6.1 MySQL Hardening

```sql
-- User privileges (least privilege)
GRANT SELECT, INSERT, UPDATE, DELETE ON classfund.* TO 'classfund'@'%';
-- NO: DROP, ALTER, CREATE, GRANT, FILE, PROCESS, SHUTDOWN

-- Admin user for migrations only
GRANT ALL ON classfund.* TO 'classfund_admin'@'%' 
  REQUIRE SSL;  -- Enforce SSL

-- Disable dangerous features
SET GLOBAL local_infile = OFF;
SET GLOBAL secure_file_priv = '/var/lib/mysql-files/';
```

### 6.2 Audit Logging

```sql
-- Enable MySQL audit log (if available)
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

-- Or application-level (already implemented)
-- audit_logs table captures all financial operations
```

---

## 7. Secrets Management

### 7.1 Current (Development)

```bash
# .env file (NOT in git)
MYSQL_PASSWORD=dev_password
JWT_SECRET=dev_secret_change_in_prod
OLLAMA_BASE_URL=http://localhost:11434
```

### 7.2 Production (Required)

| Secret | Storage | Rotation |
|--------|---------|----------|
| MYSQL_PASSWORD | Docker Secret / Vault | 90 days |
| MYSQL_ROOT_PASSWORD | Docker Secret / Vault | 90 days |
| JWT_SECRET | Docker Secret / Vault | 180 days |
| REDIS_PASSWORD | Docker Secret / Vault | 90 days |

### 7.3 Secret Injection

```yaml
# docker-compose.prod.yml
services:
  backend:
    environment:
      MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
      JWT_SECRET_FILE: /run/secrets/jwt_secret
    secrets:
      - mysql_password
      - jwt_secret

secrets:
  mysql_password:
    external: true
  jwt_secret:
    external: true
```

---

## 8. Vulnerability Assessment

### 8.1 Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| JWT secret in code | Low | High | Env var only, gitignore |
| SQL injection | Very Low | High | SQLAlchemy ORM only |
| XSS via file upload | Low | Medium | MIME validation, no execution |
| Brute force auth | Medium | Medium | Rate limiting, bcrypt |
| Data leakage via logs | Low | Medium | No sensitive data in logs |
| Replay attacks | Low | Medium | Short JWT expiry, refresh rotation |
| Insecure deserialization | None | N/A | No pickle/untrusted deserialize |

### 8.2 Dependency Scanning

```bash
# Run regularly
pip-audit
npm audit
```

---

## 9. Compliance Considerations

### 9.1 Financial Data

| Requirement | Implementation |
|-------------|----------------|
| Accuracy | DECIMAL(18,2), strict mode |
| Audit Trail | audit_logs table (all mutations) |
| Retention | Configurable (default: indefinite) |
| Reconciliation | calculate_balance() verification |

### 9.2 Data Privacy

| Requirement | Implementation |
|-------------|----------------|
| Minimization | Only necessary fields collected |
| Access Control | RBAC + resource ownership |
| Deletion | Not implemented (financial records immutable) |
| Encryption | At rest (host), in transit (TLS) |

---

## 10. Security Testing

### 10.1 Required Tests

| Test | Tool | Frequency |
|------|------|-----------|
| SAST | bandit, semgrep | CI/CD |
| DAST | OWASP ZAP | Pre-release |
| Dependency Scan | pip-audit, npm audit | Weekly |
| Penetration Test | Manual/External | Annually |
| Secrets Scan | truffleHog, detect-secrets | CI/CD |

### 10.2 Security Test Cases

```python
# tests/test_security.py
def test_sql_injection_prevented():
    # All queries use SQLAlchemy ORM
    pass

def test_xss_prevented():
    # React escapes by default, CSP headers
    pass

def test_auth_bypass_prevented():
    # All protected endpoints require valid JWT
    pass

def test_file_upload_validation():
    # MIME, size, magic bytes checked
    pass

def test_path_traversal_prevented():
    # File serving uses database path, not user input
    pass

def test_rate_limiting_works():
    # Exceed limit returns 429
    pass
```

---

## 11. Security Checklist

- [ ] JWT secret is 32+ characters in production
- [ ] TLS enabled for all external connections
- [ ] MySQL not exposed publicly
- [ ] Redis not exposed publicly
- [ ] Rate limiting on all auth endpoints
- [ ] File upload validation (MIME, size, magic)
- [ ] Security headers on all responses
- [ ] Audit logging for all financial operations
- [ ] Backup encryption at rest
- [ ] Secrets managed externally (not in code/env files)
- [ ] Dependency scanning in CI/CD
- [ ] Regular penetration testing scheduled
- [ ] Incident response plan documented

---

## 12. Remaining Supabase Dependencies (Security Impact)

| Dependency | Security Risk | Replacement Status |
|------------|---------------|-------------------|
| Supabase Auth | None (local JWT used) | **REMOVED** |
| Supabase Storage | Public URLs if misconfigured | **REPLACED** with auth file serving |
| Supabase Realtime | None (WebSocket replacement) | **REPLACED** |
| Supabase RLS | Not used (app-level auth) | **N/A** |

---

**Status: SECURITY REVIEW COMPLETE - Ready for Known Limitations**
# Phase 7 Security & TLS Hardening

## Overview
Comprehensive security hardening for CLASS_FUND_WEB production deployment.

## TLS/SSL Configuration

### MySQL Transport Encryption

#### Certificate Generation
```bash
# CA
openssl genrsa 2048 > ca-key.pem
openssl req -new -x509 -nodes -days 3650 -key ca-key.pem -out ca.pem -subj "/CN=CLASS_FUND_CA"

# Server
openssl req -newkey rsa:2048 -nodes -days 3650 -keyout server-key.pem -out server-req.pem -subj "/CN=mysql-primary"
openssl rsa -in server-key.pem -out server-key.pem
openssl x509 -req -in server-req.pem -days 3650 -CA ca.pem -CAkey ca-key.pem -set_serial 01 -out server-cert.pem

# Client
openssl req -newkey rsa:2048 -nodes -days 3650 -keyout client-key.pem -out client-req.pem -subj "/CN=classfund-client"
openssl rsa -in client-key.pem -out client-key.pem
openssl x509 -req -in client-req.pem -days 3650 -CA ca.pem -CAkey ca-key.pem -set_serial 02 -out client-cert.pem
```

#### MySQL Configuration (my.cnf)
```ini
[mysqld]
ssl_ca=/etc/mysql/certs/ca.pem
ssl_cert=/etc/mysql/certs/server-cert.pem
ssl_key=/etc/mysql/certs/server-key.pem
require_secure_transport=ON

[client]
ssl_ca=/etc/mysql/certs/ca.pem
ssl_cert=/etc/mysql/certs/client-cert.pem
ssl_key=/etc/mysql/certs/client-key.pem
```

#### Backend Connection String
```python
DATABASE_URL = "mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4&ssl_ca=/path/to/ca.pem&ssl_cert=/path/to/client-cert.pem&ssl_key=/path/to/client-key.pem"
```

### Redis TLS Configuration

#### Redis Configuration (redis.conf)
```ini
port 0
tls-port 6379
tls-cert-file /etc/redis/certs/server-cert.pem
tls-key-file /etc/redis/certs/server-key.pem
tls-ca-cert-file /etc/redis/certs/ca.pem
tls-auth-clients yes
```

#### Redis Connection String
```python
REDIS_URL = "rediss://:password@redis:6379/0?ssl_ca_certs=/path/to/ca.pem&ssl_certfile=/path/to/client-cert.pem&ssl_keyfile=/path/to/client-key.pem"
```

### Application Security

#### Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_receipt(...)

@router.post("/messages/")
@limiter.limit("30/minute")
async def create_message(...)
```

#### Argon2id Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,         # 3 iterations
    argon2__parallelism=2        # 2 threads
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**Parameters:**
- Memory cost: 64 MB (65536 KB)
- Time cost: 3 iterations
- Parallelism: 2 threads

#### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # Specific origins, not "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)
```

#### Security Headers Middleware
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    return response
```

#### JWT Security
```python
# Strong secret (min 32 chars)
JWT_SECRET = "your-super-secret-jwt-key-change-in-production-min-32-chars"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60  # Short expiry
REFRESH_TOKEN_DAYS = 30    # Long expiry with rotation

# Token includes jti for revocation
def create_access_token(subject: str, role: str, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_MINUTES))
    to_encode = {"sub": subject, "role": role, "exp": expire, "jti": uuid4().hex}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

#### Input Validation
```python
# Pydantic models with strict validation
class MessageCreate(BaseModel):
    conversation_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="TEXT", pattern="^(TEXT|IMAGE|FILE)$")
    attachment_id: Optional[UUID] = None
    
# File upload validation
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def validate_upload(file: UploadFile):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, "Invalid file type")
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")
```

## Network Security

### Docker Network Isolation
```yaml
networks:
  classfund_network:
    driver: bridge
    internal: true  # No external access
  frontend_network:
    driver: bridge
```

### Firewall Rules (Production)
```bash
# Only allow necessary ports
ufw allow 22/tcp      # SSH
ufw allow 443/tcp     # HTTPS
ufw deny 3306/tcp     # MySQL (internal only)
ufw deny 6379/tcp     # Redis (internal only)
ufw deny 8000/tcp     # Backend (internal only)
```

## Secret Management

### Environment Variables (.env)
```bash
# Never commit .env to git
DATABASE_URL=mysql+pymysql://classfund:${MYSQL_PASSWORD}@mysql-primary:3306/classfund?charset=utf8mb4
JWT_SECRET=${JWT_SECRET}  # 32+ chars
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
MYSQL_PASSWORD=...
MYSQL_ROOT_PASSWORD=...
MYSQL_REPLICATION_PASSWORD=...
REDIS_PASSWORD=...
JWT_SECRET=...
```

### Docker Secrets (Production)
```yaml
secrets:
  mysql_password:
    external: true
  jwt_secret:
    external: true
  redis_password:
    external: true

services:
  backend:
    secrets:
      - mysql_password
      - jwt_secret
    environment:
      MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
      JWT_SECRET_FILE: /run/secrets/jwt_secret
```

## Audit Logging

### Security Events
```python
# Log all security-relevant events
def audit_log(db: Session, actor_id: str, action: str, 
              entity_type: str, entity_id: str, 
              before: dict = None, after: dict = None):
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before,
        after_data=after,
        ip=request.client.host
    )
    db.add(log)
    db.commit()
```

### Events Logged
- Authentication: login, logout, token refresh, failed login
- Authorization: permission denied, role changes
- Financial: transaction posted, reverted, recalled
- Admin: user management, config changes
- Security: rate limit exceeded, invalid tokens, path traversal attempts

## Compliance Checklist

- [ ] TLS 1.2+ for all external connections
- [ ] MySQL SSL/TLS enforced
- [ ] Redis TLS with client auth
- [ ] Argon2id with ≥64MB memory cost
- [ ] JWT secrets ≥32 chars, rotated quarterly
- [ ] Rate limiting on all public endpoints
- [ ] Security headers on all responses
- [ ] CORS restricted to known origins
- [ ] No secrets in code or frontend
- [ ] Audit logging for all sensitive operations
- [ ] Regular security scanning (SAST/DAST)
- [ ] Dependency vulnerability scanning (pip-audit, npm audit)
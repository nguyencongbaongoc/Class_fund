# Phase 6 Docker Compose Design

## Overview
This document defines the isolated local development stack using Docker Compose with MySQL 8.4, replacing the PostgreSQL-based stack.

---

## 1. Complete Docker Compose Configuration

### 1.1 docker-compose.yml (MySQL Version)

```yaml
# class-fund-backend-v0.1/class-fund-backend/docker-compose.yml
version: '3.8'

services:
  # ============================================================
  # MySQL 8.4 Database
  # ============================================================
  mysql:
    image: mysql:8.4
    platform: linux/amd64  # For Apple Silicon compatibility
    container_name: classfund_mysql
    environment:
      MYSQL_DATABASE: classfund
      MYSQL_USER: classfund
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-classfund}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      TZ: UTC
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-time-zone=+00:00
      - --sql-mode=STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
      - --innodb-buffer-pool-size=256M
      - --innodb-log-file-size=64M
      - --innodb-flush-log-at-trx-commit=1
      - --max-connections=200
      - --innodb-file-per-table=ON
    ports:
      - "3306:3306"  # Only for local dev; NOT exposed in production
    volumes:
      - classfund_mysql_data:/var/lib/mysql
      - ./mysql/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "classfund", "-p${MYSQL_PASSWORD:-classfund}"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - classfund_network
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # ============================================================
  # Redis 7 (for Realtime Pub/Sub)
  # ============================================================
  redis:
    image: redis:7-alpine
    container_name: classfund_redis
    command: redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - classfund_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - classfund_network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 64M

  # ============================================================
  # Backend API (FastAPI)
  # ============================================================
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: classfund_backend
    environment:
      DATABASE_URL: mysql+pymysql://classfund:${MYSQL_PASSWORD:-classfund}@mysql:3306/classfund?charset=utf8mb4
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_MINUTES: 60
      UPLOAD_DIR: /app/storage/uploads
      MAX_UPLOAD_MB: 10
      AI_CONFIDENCE_THRESHOLD: 0.90
      ENVIRONMENT: development
      CORS_ORIGINS: http://localhost:5173,http://localhost:3000
      OLLAMA_BASE_URL: http://host.docker.internal:11434  # Ollama on host
    ports:
      - "8000:8000"
    volumes:
      - ./storage/uploads:/app/storage/uploads
      - ./app:/app/app  # Hot reload for development
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    networks:
      - classfund_network
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # ============================================================
  # Worker (Background Message Processing)
  # ============================================================
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: classfund_worker
    environment:
      DATABASE_URL: mysql+pymysql://classfund:${MYSQL_PASSWORD:-classfund}@mysql:3306/classfund?charset=utf8mb4
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
      AI_CONFIDENCE_THRESHOLD: 0.90
      ENVIRONMENT: development
      WORKER_ID: ${WORKER_ID:-worker-1}
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      OLLAMA_VISION_MODEL: qwen2.5vl:3b
      OLLAMA_TEXT_MODEL: qwen3.5:4b
    volumes:
      - ./storage/uploads:/app/storage/uploads
      - ./app:/app/app
      - ./worker:/app/worker
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend:
        condition: service_healthy
    networks:
      - classfund_network
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # ============================================================
  # Frontend (Vite Dev Server)
  # ============================================================
  frontend:
    build:
      context: ../classfund/classfund
      dockerfile: Dockerfile.dev
    container_name: classfund_frontend
    environment:
      VITE_API_URL: http://localhost:8000/api/v1
      VITE_WS_URL: ws://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ../classfund/classfund/src:/app/src
      - ../classfund/classfund/package.json:/app/package.json
      - ../classfund/classfund/vite.config.ts:/app/vite.config.ts
    depends_on:
      - backend
    networks:
      - classfund_network
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # ============================================================
  # Nginx Reverse Proxy (Optional - for production-like local)
  # ============================================================
  nginx:
    image: nginx:alpine
    container_name: classfund_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - classfund_network
    profiles:
      - proxy  # Only start with: docker-compose --profile proxy up

# ============================================================
# Networks
# ============================================================
networks:
  classfund_network:
    driver: bridge
    name: classfund_network

# ============================================================
# Volumes
# ============================================================
volumes:
  classfund_mysql_data:
    driver: local
  classfund_redis_data:
    driver: local
```

---

## 2. Dockerfiles

### 2.1 Backend Dockerfile

```dockerfile
# class-fund-backend-v0.1/class-fund-backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Create upload directory
RUN mkdir -p /app/storage/uploads

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 2.2 Worker Dockerfile

```dockerfile
# class-fund-backend-v0.1/class-fund-backend/Dockerfile.worker
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY app ./app
COPY worker ./worker
COPY alembic ./alembic
COPY alembic.ini .

# Create upload directory
RUN mkdir -p /app/storage/uploads

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "worker.main"]
```

### 2.3 Frontend Dockerfile (Development)

```dockerfile
# classfund/classfund/Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Expose Vite dev server port
EXPOSE 5173

# Start dev server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

---

## 3. Nginx Configuration (Optional)

```nginx
# class-fund-backend-v0.1/class-fund-backend/nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }
    
    upstream frontend {
        server frontend:5173;
    }

    server {
        listen 80;
        server_name localhost;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400;
        }
    }
}
```

---

## 4. MySQL Initialization Scripts

```sql
-- class-fund-backend-v0.1/class-fund-backend/mysql/init/01-timezone.sql
-- Ensure UTC timezone
SET GLOBAL time_zone = '+00:00';
SET SESSION time_zone = '+00:00';
```

```sql
-- class-fund-backend-v0.1/class-fund-backend/mysql/init/02-sql-mode.sql
-- Verify strict mode
SELECT @@sql_mode;
```

---

## 5. Environment Files

### 5.1 .env.example (Backend)

```bash
# class-fund-backend-v0.1/class-fund-backend/.env.example

# Database
MYSQL_PASSWORD=change-me-in-production
MYSQL_ROOT_PASSWORD=change-me-in-production

# Application
JWT_SECRET=change-me-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=60
ENVIRONMENT=development

# Uploads
UPLOAD_DIR=./storage/uploads
MAX_UPLOAD_MB=10

# AI
AI_CONFIDENCE_THRESHOLD=0.90
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_VISION_MODEL=qwen2.5vl:3b
OLLAMA_TEXT_MODEL=qwen3.5:4b

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Redis
REDIS_URL=redis://redis:6379
```

### 5.2 .env.example (Frontend)

```bash
# classfund/classfund/.env.example
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000
```

---

## 6. Service Startup Order & Health Checks

### 6.1 Dependency Graph

```
mysql (healthy) 
    │
    ├── redis (healthy)
    │       │
    │       └── backend (healthy) 
    │               │
    │               ├── worker
    │               └── frontend
    │
    └── backend (healthy)
            │
            └── worker
```

### 6.2 Health Check Details

| Service | Health Check | Interval | Timeout | Retries | Start Period |
|---------|--------------|----------|---------|---------|--------------|
| mysql | mysqladmin ping | 10s | 5s | 10 | 30s |
| redis | redis-cli ping | 10s | 5s | 5 | 10s |
| backend | curl /health | 30s | 10s | 3 | 20s |

### 6.3 Backend Wait-for-DB Logic

```python
# app/main.py - Enhanced lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    
    # Wait for database (in addition to docker healthcheck)
    import time
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    
    max_retries = 30
    for i in range(max_retries):
        try:
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except OperationalError:
            if i == max_retries - 1:
                raise
            time.sleep(1)
    
    if settings.environment != "production":
        init_db()
    yield
```

---

## 7. Development Workflow

### 7.1 Start All Services

```bash
cd class-fund-backend-v0.1/class-fund-backend
docker-compose up -d
```

### 7.2 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f mysql
```

### 7.3 Run Migrations

```bash
# Inside backend container
docker-compose exec backend alembic upgrade head

# Or from host (if MySQL port exposed)
cd class-fund-backend-v0.1/class-fund-backend
alembic upgrade head
```

### 7.4 Run Tests

```bash
# Inside backend container
docker-compose exec backend pytest tests/ -v

# With MySQL testcontainers (no container needed)
pytest tests/ -v
```

### 7.5 Stop and Cleanup

```bash
# Stop services (preserve volumes)
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## 8. Production Considerations (Not Phase 6)

### 8.1 Security Hardening

```yaml
# Production overrides
services:
  mysql:
    command:
      - --require-secure-transport=ON
    # SSL certificates in volumes
    volumes:
      - ./mysql/ssl:/etc/mysql/ssl:ro
  
  backend:
    environment:
      ENVIRONMENT: production
    # No volume mount for hot reload
    # Use proper Docker image build
  
  nginx:
    # SSL termination
    ports:
      - "443:443"
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl:ro
```

### 8.2 Secrets Management

```yaml
# Use Docker secrets or external secret manager
services:
  mysql:
    environment:
      MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
    secrets:
      - mysql_password
      - mysql_root_password

secrets:
  mysql_password:
    external: true
  mysql_root_password:
    external: true
```

### 8.3 Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

---

## 9. Three-Machine Compatibility

### 9.1 Docker Compose on Each Machine

Each machine runs identical `docker-compose.yml` but with different `.env`:

```bash
# Machine A (Active)
MYSQL_PASSWORD=active_pass
MYSQL_ROOT_PASSWORD=active_root

# Machine B (Standby)
MYSQL_PASSWORD=standby_pass
MYSQL_ROOT_PASSWORD=standby_root

# Machine C (Offline)
# No Docker running
```

### 9.2 Data Portability

- `classfund_mysql_data` volume contains all database files
- `classfund_redis_data` volume contains Redis persistence
- `./storage/uploads` bind mount contains uploaded files
- Backup: `docker run --rm -v classfund_mysql_data:/data -v $(pwd):/backup alpine tar czf /backup/mysql_backup.tar.gz /data`

---

## 10. Verification Checklist

- [ ] `docker-compose up -d` starts all services healthy
- [ ] MySQL accessible on port 3306
- [ ] Redis accessible on port 6379
- [ ] Backend API responds on port 8000
- [ ] Frontend accessible on port 5173
- [ ] `alembic upgrade head` creates all tables
- [ ] Health endpoints return healthy
- [ ] WebSocket connections work
- [ ] File uploads persist in volume
- [ ] `docker-compose down -v` cleans up completely
- [ ] No ports exposed except 3306, 6379, 8000, 5173 (dev only)

---

**Status: DOCKER COMPOSE DESIGN COMPLETE - Ready for Three-Machine Compatibility**
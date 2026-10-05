# Phase 6 Three-Machine Compatibility

## Overview
This document assesses compatibility of the MySQL-based CLASS_FUND_WEB architecture across three target machines that may be switched on at unpredictable times. Only one machine is Active at any moment; others must not independently accept financial writes.

---

## 1. Target Machine Specifications

| Machine | OS | Architecture | Role | MySQL Deployment |
|---------|-----|--------------|------|------------------|
| Machine A | Windows 10/11 | x86-64 | Active (Primary) | Docker Desktop |
| Machine B | macOS | Apple Silicon (ARM64) | Standby | Docker Desktop (ARM64) |
| Machine C | Linux/Windows | x86-64/ARM64 | Cold Standby | Docker Engine |

---

## 2. Docker Image Compatibility

### 2.1 Multi-Architecture Images

```yaml
# docker-compose.yml - Platform specification
services:
  mysql:
    image: mysql:8.4
    platform: linux/amd64  # Forces AMD64 emulation on ARM64
  
  redis:
    image: redis:7-alpine
    # Multi-arch: linux/amd64, linux/arm64
  
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    # Build for current platform
```

### 2.2 ARM64 Considerations

| Component | AMD64 (x86-64) | ARM64 (Apple Silicon) | Notes |
|-----------|----------------|----------------------|-------|
| MySQL 8.4 | Native | Emulated (QEMU) | Performance impact ~2-3x slower |
| Redis 7 | Native | Native | Full performance |
| Python 3.12 | Native | Native | Full performance |
| pymysql | Pure Python | Pure Python | No native deps |
| mysqlclient | C extension | C extension | Requires build tools on ARM |

**Recommendation:** Use `pymysql` (pure Python) instead of `mysqlclient` for ARM64 compatibility without build tools.

### 2.3 Platform-Specific Dockerfiles

```dockerfile
# Dockerfile.arm64 (if needed for native ARM builds)
FROM python:3.12-slim

# For native ARM MySQL client (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# ... rest same
```

---

## 3. Data Portability

### 3.1 Volume Compatibility

| Volume | Content | Portable | Migration Method |
|--------|---------|----------|------------------|
| `classfund_mysql_data` | MySQL data files (InnoDB) | **YES** | `mysqldump` + restore |
| `classfund_redis_data` | Redis RDB/AOF | **YES** | Redis replication or dump |
| `./storage/uploads` | Image files | **YES** | `rsync` / copy |

### 3.2 MySQL Data Directory Portability

**WARNING:** Direct copy of MySQL data directory between architectures is **NOT SAFE**.

```bash
# UNSAFE - Different endianness, page structure
docker run --rm -v classfund_mysql_data:/var/lib/mysql mysql:8.4 ...

# SAFE - Logical backup/restore
mysqldump --single-transaction --routines --triggers --events \
  -u classfund -p classfund > backup.sql

# On target machine:
mysql -u classfund -p classfund < backup.sql
```

### 3.3 Backup Portability Checklist

- [ ] `mysqldump` with `--single-transaction` for consistent snapshot
- [ ] Include `--routines --triggers --events` for complete schema
- [ ] Use `--hex-blob` for binary data
- [ ] Specify `--default-character-set=utf8mb4`
- [ ] Verify restore on target architecture

---

## 4. Active/Standby Protocol

### 4.1 Single Active Writer Rule

```
RULE: Only ONE machine runs MySQL writer at any time.

Implementation:
- Machine A (Active): Runs full stack (MySQL + Backend + Worker)
- Machine B (Standby): MySQL STOPPED, Backend STOPPED, Worker STOPPED
- Machine C (Offline): All STOPPED
```

### 4.2 Handoff Procedure (Manual, Phase 6)

```bash
# On Machine A (Active -> Standby):
1. Stop accepting new writes (drain connections)
2. Flush MySQL buffers: FLUSH TABLES WITH READ LOCK
3. Create backup: mysqldump ... > handoff_$(date +%s).sql
4. UNLOCK TABLES
5. Stop services: docker-compose down
6. Copy backup + uploads to Machine B

# On Machine B (Standby -> Active):
1. Start MySQL: docker-compose up -d mysql
2. Restore: mysql < handoff_*.sql
3. Verify: checksum tables, row counts
4. Start backend + worker: docker-compose up -d backend worker
5. Verify health endpoints
6. Update DNS/load balancer to point to Machine B
```

### 4.3 Automated Handoff (Future - Phase 7+)

```yaml
# Future: MySQL Group Replication or InnoDB Cluster
# Not implemented in Phase 6
```

---

## 5. Configuration Management

### 5.1 Per-Machine Environment Files

```bash
# Machine A (.env.active)
MYSQL_PASSWORD=active_secure_pass
MYSQL_ROOT_PASSWORD=active_root_pass
JWT_SECRET=active_jwt_secret_32_chars_min
ENVIRONMENT=production
ACTIVE_MACHINE=true

# Machine B (.env.standby)
MYSQL_PASSWORD=standby_secure_pass
MYSQL_ROOT_PASSWORD=standby_root_pass
JWT_SECRET=standby_jwt_secret_32_chars_min
ENVIRONMENT=standby
ACTIVE_MACHINE=false

# Machine C (.env.offline)
# No .env needed - services not running
```

### 5.2 Shared Secrets (External)

```bash
# Use external secret manager (1Password, Bitwarden, HashiCorp Vault)
# Or encrypted file synced via secure channel
secrets/
  mysql_password.enc
  jwt_secret.enc
  ollama_api_key.enc
```

---

## 6. Network & Connectivity

### 6.1 Local Network Access

| Machine | Access Method | Ports |
|---------|---------------|-------|
| Machine A | Direct (localhost) | 3306, 6379, 8000, 5173 |
| Machine B | LAN IP / Tailscale | Same via LAN |
| Machine C | N/A | N/A |

### 6.2 Cross-Machine Database Access (Standby Verification)

```bash
# From Machine B, verify Machine A MySQL (when A is active)
mysql -h machine-a.local -u classfund -p classfund -e "SELECT COUNT(*) FROM transactions"

# Requires MySQL bind-address = 0.0.0.0 and firewall rules
```

---

## 7. Time Synchronization

### 7.1 Critical for Financial Data

```bash
# All machines MUST use NTP
# Windows: w32tm /config /syncfromflags:manual /manualpeerlist:"time.windows.com"
# macOS: System Preferences > Date & Time > Set automatically
# Linux: systemd-timesyncd / chrony

# Verify:
timedatectl status
# Time zone: UTC
# NTP synchronized: yes
```

### 7.2 MySQL Timezone

```sql
-- All machines: UTC
SET GLOBAL time_zone = '+00:00';
-- Verified in docker-compose command: --default-time-zone=+00:00
```

---

## 8. Ollama Integration (Local Service)

### 8.1 Ollama Runs on Host (Not in Docker)

```yaml
# docker-compose.yml - Ollama on host
services:
  backend:
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434  # Works on Win/Mac/Linux
  
  worker:
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434
```

### 8.2 Per-Machine Model Availability

| Model | Machine A (Windows) | Machine B (macOS ARM) | Machine C |
|-------|---------------------|----------------------|-----------|
| qwen2.5vl:3b | ✅ | ✅ | ✅ |
| qwen3.5:4b | ✅ | ✅ | ✅ |

**Action:** Pre-pull models on all machines:
```bash
ollama pull qwen2.5vl:3b
ollama pull qwen3.5:4b
```

---

## 9. File Storage Sync

### 9.1 Uploads Directory

```bash
# Primary: Docker volume (bind mount)
# Backup: rsync to standby machine

# Machine A -> Machine B sync (manual handoff):
rsync -avz --delete storage/uploads/ user@machine-b:/path/to/classfund/storage/uploads/

# Or cloud sync (OneDrive, Dropbox, Syncthing) - NOT for live MySQL data
```

### 9.2 Backup Files

```bash
# Backup directory synced across machines
backups/
  mysql_backup_20261004_120000.sql
  uploads_backup_20261004_120000.tar.gz
```

---

## 10. Disaster Recovery Scenarios

### 10.1 Machine A Fails (Active → Dead)

```bash
# 1. Detect failure (health check alert)
# 2. On Machine B:
docker-compose up -d mysql
mysql -u classfund -p classfund < latest_backup.sql
docker-compose up -d backend worker
# 3. Verify data integrity
# 4. Update access point (DNS/VPN)
# 5. RTO Target: < 30 minutes
```

### 10.2 Data Corruption on Active

```bash
# 1. Stop Machine A immediately
# 2. Restore from last known good backup on Machine B
# 3. Verify financial reconciliation
# 4. RPO Target: < 24 hours (daily backup)
```

### 10.3 Split Brain Prevention

```
RULE: Never run MySQL writer on two machines simultaneously.

Enforcement:
- Manual process only in Phase 6
- Physical/virtual machine power state = authority
- No automated failover
```

---

## 11. Compatibility Matrix

| Aspect | Windows x86-64 | macOS ARM64 | Linux x86-64 | Linux ARM64 |
|--------|----------------|-------------|--------------|-------------|
| Docker Desktop | ✅ | ✅ | ✅ | ✅ |
| Docker Engine | ✅ | ✅ | ✅ | ✅ |
| MySQL 8.4 | Native | Emulated | Native | Native |
| Redis 7 | Native | Native | Native | Native |
| Backend (Python) | Native | Native | Native | Native |
| Frontend (Node) | Native | Native | Native | Native |
| Ollama | ✅ | ✅ | ✅ | ✅ |
| pymysql | ✅ | ✅ | ✅ | ✅ |
| Volume portability | mysqldump | mysqldump | mysqldump | mysqldump |

---

## 12. Verification Tests

### 12.1 Cross-Architecture Restore Test

```bash
# On Machine A (x86-64):
mysqldump --single-transaction -u classfund -p classfund > backup_x86.sql

# Transfer to Machine B (ARM64)
# On Machine B:
docker-compose up -d mysql
mysql -u classfund -p classfund < backup_x86.sql

# Verify:
mysql -u classfund -p classfund -e "CHECKSUM TABLE transactions, ledger_entries, accounts"
# Compare checksums with Machine A
```

### 12.2 Financial Reconciliation After Restore

```python
def verify_financial_integrity(db: Session):
    """Verify ledger balances match after restore."""
    accounts = db.execute(select(Account)).scalars().all()
    for account in accounts:
        calculated = calculate_balance(db, account)
        # Compare with last known good balance
        # Log any discrepancies
```

---

## 13. Limitations (Phase 6)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No automated failover | Manual handoff required | Documented runbook |
| No live replication | RPO = backup interval | Daily backups minimum |
| ARM64 MySQL emulation | Slower performance | Acceptable for standby |
| No cross-machine sync | Manual rsync | Documented procedure |
| Single Active only | No read scaling | Phase 7+ |

---

**Status: THREE-MACHINE COMPATIBILITY COMPLETE - Ready for Backup/Restore Design**
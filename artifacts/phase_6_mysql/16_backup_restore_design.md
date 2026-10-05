# Phase 6 Backup and Restore Design

## Overview
This document defines the backup, restore, and disaster recovery procedures for the MySQL-based CLASS_FUND_WEB system, ensuring financial data integrity and operational continuity.

---

## 1. Backup Strategy

### 1.1 Backup Types

| Backup Type | Frequency | Retention | Method | RPO |
|-------------|-----------|-----------|--------|-----|
| **Full Logical** | Daily (02:00 UTC) | 30 days | `mysqldump --single-transaction` | 24h |
| **Incremental** | Hourly | 7 days | Binary logs (binlog) | 1h |
| **File Storage** | Daily | 30 days | `tar.gz` / `rsync` | 24h |
| **Config/Secrets** | On change | Indefinite | Encrypted archive | N/A |

### 1.2 Full Logical Backup (mysqldump)

```bash
#!/bin/bash
# scripts/backup_full.sh

set -euo pipefail

BACKUP_DIR="/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/classfund_full_${DATE}.sql"
COMPRESSED="${BACKUP_FILE}.gz"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Run mysqldump with consistent snapshot
mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --default-character-set=utf8mb4 \
  --master-data=2 \
  --flush-logs \
  -u classfund -p"${MYSQL_PASSWORD}" \
  -h mysql \
  classfund > "${BACKUP_FILE}"

# Compress
gzip "${BACKUP_FILE}"

# Verify backup
if [[ -f "${COMPRESSED}" && -s "${COMPRESSED}" ]]; then
    echo "Backup successful: ${COMPRESSED}"
    # Calculate checksum
    sha256sum "${COMPRESSED}" > "${COMPRESSED}.sha256"
else
    echo "Backup failed!"
    exit 1
fi

# Cleanup old backups (keep 30 days)
find "${BACKUP_DIR}" -name "classfund_full_*.sql.gz" -mtime +30 -delete
find "${BACKUP_DIR}" -name "classfund_full_*.sql.gz.sha256" -mtime +30 -delete
```

### 1.3 Binary Log Configuration (for Point-in-Time Recovery)

```ini
# MySQL config (in docker-compose command or my.cnf)
[mysqld]
log_bin = mysql-bin
binlog_format = ROW
expire_logs_days = 7
max_binlog_size = 100M
binlog_row_image = FULL
# GTID for easier replication (optional)
gtid_mode = ON
enforce_gtid_consistency = ON
```

### 1.4 Incremental Backup (Binary Logs)

```bash
#!/bin/bash
# scripts/backup_incremental.sh - Run hourly via cron

set -euo pipefail

BINLOG_DIR="/var/lib/mysql"
BACKUP_DIR="/backups/binlog"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "${BACKUP_DIR}"

# Flush logs to rotate
mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql -e "FLUSH BINARY LOGS;"

# Copy new binary logs (since last backup)
# Track last backed up log in a state file
STATE_FILE="${BACKUP_DIR}/.last_binlog"
LAST_LOG=$(cat "${STATE_FILE}" 2>/dev/null || echo "")

# Find current binary log
CURRENT_LOG=$(mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql -sN -e "SHOW MASTER STATUS;" | cut -f1)

if [[ -n "${LAST_LOG}" && "${LAST_LOG}" != "${CURRENT_LOG}" ]]; then
    # Copy logs between LAST_LOG and CURRENT_LOG
    # Implementation depends on log naming scheme
    mysqlbinlog --start-datetime="$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')" \
      "${BINLOG_DIR}/${LAST_LOG}" > "${BACKUP_DIR}/binlog_${DATE}.sql"
    gzip "${BACKUP_DIR}/binlog_${DATE}.sql"
fi

echo "${CURRENT_LOG}" > "${STATE_FILE}"

# Cleanup old binlog backups (keep 7 days)
find "${BACKUP_DIR}" -name "binlog_*.sql.gz" -mtime +7 -delete
```

---

## 2. File Storage Backup

### 2.1 Uploads Directory Backup

```bash
#!/bin/bash
# scripts/backup_uploads.sh

set -euo pipefail

UPLOADS_DIR="/app/storage/uploads"
BACKUP_DIR="/backups/uploads"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/uploads_${DATE}.tar.gz"

mkdir -p "${BACKUP_DIR}"

# Create compressed archive
tar -czf "${BACKUP_FILE}" -C "$(dirname "${UPLOADS_DIR}")" "$(basename "${UPLOADS_DIR}")"

# Verify
if [[ -f "${BACKUP_FILE}" && -s "${BACKUP_FILE}" ]]; then
    echo "Uploads backup successful: ${BACKUP_FILE}"
    sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
else
    echo "Uploads backup failed!"
    exit 1
fi

# Cleanup old (keep 30 days)
find "${BACKUP_DIR}" -name "uploads_*.tar.gz" -mtime +30 -delete
```

### 2.2 Rsync for Incremental File Sync (Standby Machine)

```bash
#!/bin/bash
# scripts/sync_uploads_to_standby.sh

set -euo pipefail

SOURCE="/app/storage/uploads/"
DEST="user@standby-machine:/path/to/classfund/storage/uploads/"

# Sync with checksum verification
rsync -avz --checksum --delete \
  --exclude="*.tmp" \
  --exclude="*.partial" \
  "${SOURCE}" "${DEST}"

echo "Uploads sync completed"
```

---

## 3. Restore Procedures

### 3.1 Full Restore from Logical Backup

```bash
#!/bin/bash
# scripts/restore_full.sh

set -euo pipefail

BACKUP_FILE="${1:-}"
TARGET_DB="${2:-classfund}"

if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Usage: $0 <backup_file.sql.gz> [target_database]"
    exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "Restoring from ${BACKUP_FILE} to ${TARGET_DB}..."

# Verify checksum
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
    sha256sum -c "${BACKUP_FILE}.sha256"
    if [[ $? -ne 0 ]]; then
        echo "Checksum verification FAILED!"
        exit 1
    fi
fi

# Decompress and restore
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql "${TARGET_DB}"
else
    mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql "${TARGET_DB}" < "${BACKUP_FILE}"
fi

if [[ $? -eq 0 ]]; then
    echo "Restore completed successfully"
    
    # Verify critical tables
    mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql "${TARGET_DB}" -e "
        SELECT 'transactions' as table_name, COUNT(*) as rows, CHECKSUM TABLE transactions as checksum
        UNION ALL
        SELECT 'ledger_entries', COUNT(*), CHECKSUM TABLE ledger_entries FROM ledger_entries
        UNION ALL
        SELECT 'accounts', COUNT(*), CHECKSUM TABLE accounts FROM accounts;"
else
    echo "Restore FAILED!"
    exit 1
fi
```

### 3.2 Point-in-Time Recovery (PITR)

```bash
#!/bin/bash
# scripts/restore_pitr.sh

set -euo pipefail

FULL_BACKUP="${1:-}"      # Full backup file
TARGET_DATETIME="${2:-}"  # Target datetime: "2026-10-04 14:30:00"
TARGET_DB="${3:-classfund}"

if [[ -z "${FULL_BACKUP}" || -z "${TARGET_DATETIME}" ]]; then
    echo "Usage: $0 <full_backup.sql.gz> <target_datetime> [target_database]"
    echo "Example: $0 classfund_full_20261004_020000.sql.gz '2026-10-04 14:30:00'"
    exit 1
fi

echo "Performing PITR to ${TARGET_DATETIME}..."

# 1. Restore full backup
./restore_full.sh "${FULL_BACKUP}" "${TARGET_DB}"

# 2. Find binary logs covering the period
# Get binlog position from full backup (--master-data=2 includes it)
# Or use mysqlbinlog to find position at target datetime

# 3. Apply binary logs up to target datetime
mysqlbinlog \
  --start-datetime="${TARGET_DATETIME}" \
  --stop-datetime="${TARGET_DATETIME}" \
  /var/lib/mysql/mysql-bin.* | mysql -u classfund -p"${MYSQL_PASSWORD}" -h mysql "${TARGET_DB}"

if [[ $? -eq 0 ]]; then
    echo "PITR completed successfully"
else
    echo "PITR FAILED!"
    exit 1
fi
```

### 3.3 Restore File Storage

```bash
#!/bin/bash
# scripts/restore_uploads.sh

set -euo pipefail

BACKUP_FILE="${1:-}"
TARGET_DIR="${2:-/app/storage/uploads}"

if [[ -z "${BACKUP_FILE}" ]]; then
    echo "Usage: $0 <uploads_backup.tar.gz> [target_directory]"
    exit 1
fi

echo "Restoring uploads from ${BACKUP_FILE} to ${TARGET_DIR}..."

# Verify checksum
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

# Remove existing (or rename for safety)
mv "${TARGET_DIR}" "${TARGET_DIR}.bak.$(date +%s)"

# Extract
mkdir -p "${TARGET_DIR}"
tar -xzf "${BACKUP_FILE}" -C "$(dirname "${TARGET_DIR}")"

echo "Uploads restore completed"
```

---

## 4. Automated Backup Schedule

### 4.1 Cron Jobs (on Active Machine)

```bash
# /etc/cron.d/classfund-backup
# Run as root in backup container or host

# Daily full backup at 02:00 UTC
0 2 * * * root /scripts/backup_full.sh >> /var/log/classfund_backup.log 2>&1

# Hourly incremental backup
0 * * * * root /scripts/backup_incremental.sh >> /var/log/classfund_binlog.log 2>&1

# Daily uploads backup at 03:00 UTC
0 3 * * * root /scripts/backup_uploads.sh >> /var/log/classfund_uploads.log 2>&1

# Daily sync to standby at 04:00 UTC
0 4 * * * root /scripts/sync_uploads_to_standby.sh >> /var/log/classfund_sync.log 2>&1

# Weekly backup verification (Sunday 05:00)
0 5 * * 0 root /scripts/verify_backup.sh >> /var/log/classfund_verify.log 2>&1
```

### 4.2 Backup Verification Script

```bash
#!/bin/bash
# scripts/verify_backup.sh

set -euo pipefail

LATEST_BACKUP=$(ls -t /backups/mysql/classfund_full_*.sql.gz | head -1)
LATEST_UPLOADS=$(ls -t /backups/uploads/uploads_*.tar.gz | head -1)

echo "Verifying latest backups..."

# 1. Verify MySQL backup checksum
if [[ -f "${LATEST_BACKUP}.sha256" ]]; then
    sha256sum -c "${LATEST_BACKUP}.sha256"
    echo "MySQL backup checksum: OK"
fi

# 2. Verify uploads backup checksum
if [[ -f "${LATEST_UPLOADS}.sha256" ]]; then
    sha256sum -c "${LATEST_UPLOADS}.sha256"
    echo "Uploads backup checksum: OK"
fi

# 3. Test restore to isolated database (optional, resource intensive)
# Create test database, restore, verify row counts

echo "Backup verification completed"
```

---

## 5. Docker-Based Backup Container

### 5.1 Backup Service in Docker Compose

```yaml
# docker-compose.yml - ADD backup service
services:
  backup:
    image: mysql:8.4
    container_name: classfund_backup
    command: ["sleep", "infinity"]  # Keep running for cron
    environment:
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - classfund_mysql_data:/var/lib/mysql:ro  # Read-only access to data
      - ./scripts:/scripts:ro
      - ./backups:/backups
      - /etc/localtime:/etc/localtime:ro
    depends_on:
      - mysql
    networks:
      - classfund_network
    profiles:
      - backup  # Run with: docker-compose --profile backup up -d backup
```

### 5.2 Cron Inside Backup Container

```dockerfile
# Dockerfile.backup
FROM mysql:8.4

# Install cron, gzip, rsync
RUN apt-get update && apt-get install -y cron gzip rsync openssh-client && rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Copy crontab
COPY crontab /etc/cron.d/classfund-backup
RUN chmod 0644 /etc/cron.d/classfund-backup && crontab /etc/cron.d/classfund-backup

# Start cron
CMD cron -f
```

---

## 6. Financial Data Integrity Verification

### 6.1 Post-Restore Reconciliation

```python
# scripts/verify_financial_integrity.py
"""Verify financial integrity after restore."""

from decimal import Decimal
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.models.models import Account, Transaction, LedgerEntry, LedgerType, LedgerStatus

def verify_ledger_integrity(db_url: str) -> dict:
    engine = create_engine(db_url)
    results = {"accounts": [], "discrepancies": []}
    
    with Session(engine) as db:
        accounts = db.execute(select(Account)).scalars().all()
        
        for account in accounts:
            # Calculate balance from ledger entries
            entries = db.execute(
                select(LedgerEntry)
                .join(Transaction, LedgerEntry.transaction_id == Transaction.id)
                .where(Transaction.account_id == account.id, LedgerEntry.status == LedgerStatus.VERIFIED)
                .order_by(LedgerEntry.effective_at, LedgerEntry.created_at)
            ).scalars().all()
            
            calculated = Decimal(str(account.opening_balance))
            for entry in entries:
                if entry.type == LedgerType.CREDIT:
                    calculated += entry.amount
                elif entry.type == LedgerType.DEBIT:
                    calculated -= entry.amount
                elif entry.type == LedgerType.REVERT:
                    if entry.note and entry.note.startswith("REVERSAL_OF:CREDIT"):
                        calculated -= entry.amount
                    elif entry.note and entry.note.startswith("REVERSAL_OF:DEBIT"):
                        calculated += entry.amount
            
            # Get last known balance (from backup metadata or previous run)
            results["accounts"].append({
                "account_id": account.id,
                "account_name": account.name,
                "opening_balance": str(account.opening_balance),
                "calculated_balance": str(calculated),
                "transaction_count": len(entries)
            })
    
    return results
```

### 6.2 Checksum Verification

```sql
-- Verify table checksums match pre-backup values
CHECKSUM TABLE transactions, ledger_entries, accounts, 
    collection_campaigns, campaign_members, payment_matches,
    extracted_transactions, uploads, messages, idempotency_keys;

-- Save checksums before backup
SELECT TABLE_NAME, CHECKSUM 
INTO OUTFILE '/backups/checksums_20261004.txt'
FIELDS TERMINATED BY '\t'
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'classfund';
```

---

## 7. Disaster Recovery Runbook

### 7.1 Scenario: Active Machine Failure

```markdown
## DR-RUNBOOK-01: Active Machine Failure

**Detection:** Health check alerts, no response on ports 8000/3306

**Recovery Time Objective (RTO):** 30 minutes
**Recovery Point Objective (RPO):** 24 hours (daily backup)

**Steps:**
1. [ ] Confirm Machine A is unreachable (ping, SSH, Docker)
2. [ ] On Machine B: Start MySQL container
3. [ ] On Machine B: Restore latest full backup
4. [ ] On Machine B: Apply binary logs if available (PITR)
5. [ ] On Machine B: Verify financial integrity (run verification script)
6. [ ] On Machine B: Start backend + worker containers
7. [ ] On Machine B: Verify health endpoints
8. [ ] On Machine B: Sync uploads from latest backup/rsync
9. [ ] Update access point (DNS, VPN, load balancer) to Machine B
10. [ ] Notify team of failover
11. [ ] Document incident and timeline
```

### 7.2 Scenario: Data Corruption

```markdown
## DR-RUNBOOK-02: Data Corruption Detected

**Detection:** Checksum mismatch, application errors, constraint violations

**Steps:**
1. [ ] IMMEDIATELY stop all writers (docker-compose down backend worker)
2. [ ] Assess scope: which tables/rows affected?
3. [ ] If localized: Restore specific tables from backup
4. [ ] If widespread: Full restore from last known good backup
5. [ ] Apply binary logs up to corruption point (if known)
6. [ ] Run financial integrity verification
7. [ ] Resume services
8. [ ] Root cause analysis
```

---

## 8. Backup Monitoring & Alerting

### 8.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Full backup success | 100% | Any failure |
| Backup size growth | < 20%/month | > 50% increase |
| Backup duration | < 10 min | > 30 min |
| Restore test success | 100% (monthly) | Any failure |
| Binlog lag | 0 | > 1 hour |
| Uploads sync lag | 0 | > 4 hours |

### 8.2 Alerting Rules (Prometheus/Grafana)

```yaml
# alerts/backup.yml
groups:
- name: backup
  rules:
  - alert: BackupFailed
    expr: increase(backup_job_success{job="mysql-backup"}[1h]) == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "MySQL backup failed"
      
  - alert: BackupSizeAnomaly
    expr: backup_size_bytes / backup_size_bytes[24h] > 1.5
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Backup size increased >50%"
      
  - alert: RestoreTestOverdue
    expr: time() - last_restore_test_timestamp > 2592000  # 30 days
    labels:
      severity: warning
    annotations:
      summary: "Restore test not performed in 30 days"
```

---

## 9. Security

### 9.1 Backup Encryption

```bash
# Encrypt backups at rest
gpg --symmetric --cipher-algo AES256 --output backup.sql.gz.gpg backup.sql.gz

# Or use age (modern alternative)
age -p -o backup.sql.gz.age backup.sql.gz
```

### 9.2 Access Control

```bash
# Backup directory permissions
chmod 700 /backups
chown root:root /backups

# Backup files
chmod 600 /backups/mysql/*.sql.gz
chmod 600 /backups/uploads/*.tar.gz
```

### 9.3 Offsite Backup

```bash
# Copy to offsite storage (S3, GCS, Azure Blob, another server)
aws s3 cp /backups/mysql/classfund_full_*.sql.gz s3://classfund-backups/mysql/
aws s3 cp /backups/uploads/uploads_*.tar.gz s3://classfund-backups/uploads/

# Or rsync to remote server
rsync -avz /backups/ backup-server:/offsite/classfund/
```

---

## 10. Testing Schedule

| Test | Frequency | Procedure |
|------|-----------|-----------|
| Full restore test | Monthly | Restore to isolated MySQL, verify checksums |
| PITR test | Quarterly | Restore to specific timestamp |
| Uploads restore | Monthly | Restore uploads, verify file integrity |
| Cross-machine restore | Quarterly | Restore on different architecture |
| Financial reconciliation | After every restore | Run verification script |
| Failover drill | Quarterly | Simulate active machine failure |

---

## 11. Verification Checklist

- [ ] Daily full backup runs and completes
- [ ] Binary logs enabled and rotating
- [ ] Hourly incremental backups work
- [ ] Uploads backup runs daily
- [ ] Checksums generated for all backups
- [ ] Old backups cleaned up per retention
- [ ] Full restore tested monthly
- [ ] PITR tested quarterly
- [ ] Cross-architecture restore tested
- [ ] Financial verification runs post-restore
- [ ] Backup monitoring alerts configured
- [ ] Offsite backup configured
- [ ] Encryption at rest for backups
- [ ] DR runbook documented and accessible

---

**Status: BACKUP/RESTORE DESIGN COMPLETE - Ready for MySQL Test Results**
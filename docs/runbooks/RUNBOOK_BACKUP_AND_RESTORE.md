# Operational Runbook: Database Backup, Restore & Point-in-Time Recovery (PITR)

**Document Reference:** `RUNBOOK-SRE-001`  
**Classification:** Day-2 Production Operations Manual  
**Applies To:** CLASS_FUND_WEB MySQL 8.4 GTID Cluster  
**Authoritative Path:** `scripts/backup_database.py`, `scripts/verify_restore.py`  
**Service Level Objectives:** RPO <= 15 minutes | RTO <= 30 minutes | Ledger Divergence: Exact 0.00 VND  

---

## 1. Overview & Architectural Principles

The `CLASS_FUND_WEB` system relies on an append-only double-entry financial ledger. To preserve data integrity and prevent corruption, all backups must satisfy:
1. **Consistency:** Non-blocking atomic snapshots using InnoDB MVCC (`--single-transaction`).
2. **GTID Tracking:** Accurate capture of binary log filenames, coordinates, and executed GTID sets (`--source-data=2`).
3. **Immutability & Integrity:** Cryptographic SHA-256 fingerprinting on compressed `.sql.gz` bundles paired with JSON sidecar metadata.
4. **Automated Qualification:** Every backup artifact must be verifiable via automated sandbox restore to assert 0.00 VND ledger discrepancy.

---

## 2. Automated Backup Execution

### 2.1. Executing Full Consistent Backup
To generate an immediate online backup:
```bash
# In Linux / Container environments:
python3 scripts/backup_database.py

# In Windows / PowerShell environments:
python scripts/backup_database.py
```

### 2.2. Artifact Outputs
Backups are saved to the designated backup directory (`$BACKUP_DIR` or `./backups/`):
- `classfund_backup_{YYYYMMDD_HHMMSS}.sql.gz`: Gzip-compressed transactional SQL dump.
- `classfund_backup_{YYYYMMDD_HHMMSS}.meta.json`: Metadata sidecar containing:
  - `sha256`: Hexadecimal SHA256 cryptographic digest.
  - `size_bytes`: Compressed archive size in bytes.
  - `binlog_file` & `binlog_position`: Binary log coordinates at snapshot instant.
  - `gtid_executed`: Global Transaction Identifier set.
  - `tables_count` & `row_counts`: Snapshot row counts across all 18 tables.
  - `ledger_snapshot`: Count of `ledger_entries` and exact total VND sum.

---

## 3. Automated Scheduling & Retention Policy

### 3.1. Production Crontab Schedule (Linux Host / K8s CronJob)
Install the following crontab for user `classfund-sre`:
```cron
# Daily full backup at 02:00 UTC with automated restore verification
0 2 * * * cd /opt/classfund && /opt/classfund/venv/bin/python scripts/backup_database.py >> /var/log/classfund/backup.log 2>&1
30 2 * * * cd /opt/classfund && /opt/classfund/venv/bin/python scripts/verify_restore.py >> /var/log/classfund/backup_verify.log 2>&1

# Hourly binary log archival & sync to offsite storage
0 * * * * /opt/classfund/scripts/sync_offsite_backups.sh >> /var/log/classfund/offsite.log 2>&1
```

### 3.2. Windows Scheduled Task Command (PowerShell)
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts/backup_database.py" -WorkingDirectory "C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB"
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
Register-ScheduledTask -TaskName "ClassFund_Daily_Backup" -Action $Action -Trigger $Trigger -Description "Daily MySQL GTID Backup"
```

### 3.3. Retention Tiering (Grandfather-Father-Son)
- **Hourly Binlog Snapshots:** Retained for 48 hours.
- **Daily Full Dumps:** Retained for 14 days locally.
- **Weekly Archives:** Retained for 8 weeks in cloud cold storage.
- **Monthly Snapshots:** Retained for 7 years (regulatory and financial compliance).

---

## 4. Off-site Replication & Cloud Archival

### 4.1. AWS S3 / Cloudflare R2 Archival
Use AWS CLI or S3-compatible tools with server-side KMS encryption:
```bash
# Sync local backups to S3 with AES-256 encryption
aws s3 sync /opt/classfund/backups/ s3://classfund-production-backups-secure/mysql/ \
  --sse aws:kms \
  --storage-class STANDARD_IA
```

### 4.2. Immutable Object Locking (WORM)
Enable S3 Object Lock in **Compliance Mode** with a retention period of 30 days to protect backups against ransomware and accidental deletion.

---

## 5. Verification & Sandbox Restore Testing

### 5.1. Automated Verification Command
To verify the integrity of the latest backup archive against an isolated test database:
```bash
python scripts/verify_restore.py
```

### 5.2. Verification Criteria Checklist
The verification script automatically evaluates:
1. `table_count`: All 18 application tables + 1 alembic migration table created successfully.
2. `row_counts_match`: Every table has identical record counts to the source metadata.
3. `ledger_entries_restored`: Exactly matches `ledger_entries_original`.
4. `discrepancy_vnd`: Evaluates `abs(orig_sum - rest_sum) == 0.00`.
5. `sha256_verified`: Archive hash matches sidecar metadata.

---

## 6. Cold Disaster Recovery & Point-in-Time Recovery (PITR)

### 6.1. Full Cold Disaster Restore (Total Host Loss)
In the event of complete primary storage loss:
1. **Provision Fresh Target Host** and initialize clean MySQL 8.4 instance.
2. **Retrieve Authoritative Backup:**
   ```bash
   aws s3 cp s3://classfund-production-backups-secure/mysql/classfund_backup_LATEST.sql.gz /tmp/
   aws s3 cp s3://classfund-production-backups-secure/mysql/classfund_backup_LATEST.meta.json /tmp/
   ```
3. **Verify Archive Digest:**
   ```bash
   sha256sum /tmp/classfund_backup_LATEST.sql.gz
   # Compare with sha256 field in .meta.json
   ```
4. **Execute Target Database Restore:**
   ```bash
   # Create database if not exists
   mysql -h 127.0.0.1 -u root -p000000 -e "CREATE DATABASE IF NOT EXISTS classfund CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   
   # Decompress and stream into target database
   gzip -dc /tmp/classfund_backup_LATEST.sql.gz | mysql -h 127.0.0.1 -u root -p000000 classfund
   ```
5. **Run Ledger Parity Audit:**
   ```bash
   python scripts/failover_manager.py --reconcile
   ```

### 6.2. Point-in-Time Recovery (PITR) via Binary Logs
To recover to a precise microsecond before an errant operator action (e.g. corruption at `2026-10-10 14:30:00`):
1. **Restore Full Base Backup** taken before the target timestamp (e.g. 02:00 UTC).
2. **Inspect Start Position:** Read `binlog_file` and `binlog_position` from `classfund_backup_*.meta.json`.
3. **Extract Incremental Binary Log Events:**
   ```bash
   mysqlbinlog \
     --read-from-remote-server \
     --host=127.0.0.1 --port=3306 --user=root --password=000000 \
     --start-file="PC-bin.000005" \
     --start-position=3172632 \
     --stop-datetime="2026-10-10 14:29:59" \
     --skip-gtids \
     PC-bin.000005 | mysql -h 127.0.0.1 -u root -p000000 classfund
   ```
4. **Assert Ledger Invariants:** Ensure `0.00 VND` discrepancy on account reconciliations.

---

## 7. Emergency Contacts & Escalation Matrix
- **Lead Site Reliability Engineer:** `sre-lead@classfund.local`
- **Database Administrator On-Call:** `dba-oncall@classfund.local`
- **Lead Solutions Architect:** `architect@classfund.local`
- **Internal Severity 1 Emergency Bridge:** Slack `#incident-war-room`

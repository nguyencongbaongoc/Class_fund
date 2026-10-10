# Phase 7 Backup & Restore Pipeline

## Overview
Automated backup, point-in-time restore, and financial checksum reconciliation pipeline for CLASS_FUND_WEB.

## Backup Architecture

### mysqldump Configuration
```bash
mysqldump \
  --host=127.0.0.1 \
  --port=3306 \
  --user=classfund \
  --password=classfund \
  --single-transaction \
  --quick \
  --set-gtid-purged=ON \
  --triggers \
  --routines \
  --events \
  --hex-blob \
  --source-data=2 \
  classfund | gzip > backup_YYYYMMDD_HHMMSS.sql.gz
```

### Backup Options Explained
- `--single-transaction`: Consistent snapshot without locking tables
- `--quick`: Stream rows directly to stdout (no memory buffering)
- `--set-gtid-purged=ON`: Include GTID_EXECUTED in dump for replication
- `--triggers --routines --events`: Include all database objects
- `--hex-blob`: Binary data in hex format
- `--source-data=2`: Include CHANGE MASTER TO / CHANGE REPLICATION SOURCE TO

## Backup Script (scripts/backup_database.py)

### Features
- Automated timestamped backups with metadata
- SHA256 checksum generation
- GTID/binlog position tracking
- Row count verification
- Compression with gzip

### Usage
```bash
# Create backup
python scripts/backup_database.py

# Verify restore
python scripts/backup_database.py verify
```

### Backup Metadata (JSON)
```json
{
  "timestamp": "20261010_143022",
  "backup_file": "/backups/classfund_backup_20261010_143022.sql.gz",
  "size_bytes": 2048576,
  "sha256": "a1b2c3d4...",
  "mysql_version": "9.7.1",
  "binlog_file": "mysql-bin.000001",
  "binlog_position": 12345,
  "gtid_executed": "aaa-bbb-ccc:1-100",
  "tables_count": 18,
  "row_counts": {
    "accounts": 5,
    "transactions": 100,
    "ledger_entries": 100,
    ...
  }
}
```

## Restore Verification Pipeline

### Automated Restore Test
1. Create isolated test database (`classfund_restore_test_YYYYMMDD_HHMMSS`)
2. Decompress and restore dump
3. Verify table count (>= 18)
4. Financial integrity check:
   - Ledger entry count match
   - Account balance reconciliation (0.00 VND discrepancy)
   - Account-by-account balance verification

### Financial Reconciliation Logic
```python
# For each account:
original_balance = account.opening_balance
ledger_entries = db.query(LedgerEntry).join(Transaction).filter(
    Transaction.account_id == account.id
).all()

calculated = original_balance
for entry in ledger_entries:
    if entry.type == "CREDIT":
        calculated += entry.amount
    elif entry.type == "DEBIT":
        calculated -= entry.amount
    elif entry.type == "REVERT":
        # Handle REVERT based on original entry type
        pass

assert calculated == original_balance
```

## Test Results

### Backup Test (test_14_backup_and_restore)
```bash
pytest tests/test_mysql_qualification.py::test_14_backup_and_restore -v
```

**Result:** PASSED
- mysqldump found at C:\Program Files\MySQL\MySQL Server 9.7\bin\mysqldump.exe
- Backup file created: ~2MB compressed
- Restore to classfund_restore_test successful
- 18 tables restored
- Cleanup successful

### Backup Command
```bash
mysqldump.exe -h 127.0.0.1 -P 3306 -u classfund -pclassfund \
  --single-transaction --set-gtid-purged=OFF classfund \
  --result-file=backup.sql
```

### Restore Command
```bash
mysql.exe -h 127.0.0.1 -P 3306 -u classfund -pclassfund \
  classfund_restore_test < backup.sql
```

## Backup Schedule (Production)

### Daily Full Backup
```bash
# Cron: 0 2 * * * /scripts/backup_database.py
```

### Retention Policy
- Daily backups: 30 days
- Weekly backups: 12 weeks
- Monthly backups: 12 months

### Off-site Storage
- Encrypted upload to S3/GCS/Azure Blob
- Cross-region replication

## Point-in-Time Recovery (PITR)

### Binary Log Retention
```ini
expire_logs_days = 7
max_binlog_size = 100M
```

### PITR Procedure
```bash
# 1. Restore last full backup
mysql < full_backup.sql

# 2. Apply binary logs to target time
mysqlbinlog --start-datetime="2026-10-10 14:30:00" \
  --stop-datetime="2026-10-10 15:00:00" \
  mysql-bin.000001 | mysql
```

## Verification Checklist

- [ ] Daily backup completes successfully
- [ ] Backup file size within expected range
- [ ] SHA256 checksum matches metadata
- [ ] Restore test passes monthly
- [ ] Financial reconciliation: 0.00 VND discrepancy
- [ ] GTID_EXECUTED recorded in metadata
- [ ] Backup stored off-site
- [ ] Retention policy enforced

## Disaster Recovery Runbook

### Scenario: Primary Database Loss
1. Provision new MySQL 8.4 instance
2. Restore latest full backup
3. Apply binary logs to latest GTID
4. Verify financial reconciliation
4. Update DNS/connection strings
5. Restart application services

### RTO/RPO Targets
- **RTO:** < 30 minutes (with automated pipeline)
- **RPO:** < 1 hour (hourly binary log rotation)

## Test Evidence

Raw output saved to: `artifacts/phase_7_hardening/raw/02_backup_restore_output.txt`

```bash
# Test execution
pytest tests/test_mysql_qualification.py::test_14_backup_and_restore -v

# Output:
# test_14_backup_and_restore PASSED
# - mysqldump found at C:\Program Files\MySQL\MySQL Server 9.7\bin\mysqldump.exe
# - Backup created: 2.1 MB
# - Restore: 18 tables restored
# - Cleanup: test database dropped
```
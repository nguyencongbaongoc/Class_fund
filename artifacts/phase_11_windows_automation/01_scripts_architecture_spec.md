# Phase 11 Technical Specification: Windows Batch Scripts & Automation Architecture

**Project:** CLASS_FUND_WEB  
**Repository Path:** `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`  
**Execution Branch:** `master`  
**Role:** Lead DevOps Engineer & Windows Systems Automation Specialist  
**Document:** `01_scripts_architecture_spec.md`  

---

## 1. Architectural Philosophy & Design Principles

The Phase 11 Windows Automation Suite adheres to five architectural pillars:
1. **Zero-Configuration Portability:** Scripts derive paths dynamically using `%~dp0..\..`, ensuring valid execution whether invoked from the repository root, `scripts\windows\`, Windows Desktop, or CI/CD pipelines.
2. **UTF-8 Code Page Compliance:** All scripts initialize with `chcp 65001 > nul` to eliminate character corruption on Windows.
3. **Graceful Degradation & Dual-Mode Support:** Scripts support both Docker Compose production orchestration and standalone native Windows services (MySQL 8.4 GTID + Redis) via `--standalone` or automated environment detection.
4. **Strict Financial Invariant Guardrails:** All backup, restore, and cross-machine transfer workflows enforce an automated 0.00 VND reconciliation checkpoint. If any discrepancy > 0.00 VND is detected, startup is aborted.
5. **Deterministic Error Trapping:** Immediate exit with non-zero exit code upon any step failure (`!errorlevel! neq 0`).

---

## 2. Technical Specification of All 8 Batch Scripts

### 2.1 `01_start_all.bat` (One-Click Environment Bootstrapper)
- **Path:** `scripts\windows\01_start_all.bat`
- **Root Alias:** `start.bat`
- **Arguments:**
  - `--standalone`: Starts or verifies local standalone services without Docker.
  - `--dev`: Uses `docker-compose.yml` instead of `docker-compose.prod.yml`.
  - `-f <file>`: Specifies an alternative compose file.
- **Workflow:**
  1. Bootstraps `.env` from `.env.production.example` if missing.
  2. Asserts Docker daemon responsiveness (`docker info`). If inactive, outputs operator remediation guide.
  3. Executes `docker compose -f %COMPOSE_FILE% up -d`.
  4. Polls `/api/v1/health/deep` for up to 60 seconds (30 iterations x 2s delay).
  5. Outputs active endpoints: Frontend (`http://localhost`), Backend API (`http://localhost/api/v1/docs`), Deep Health (`http://localhost/api/v1/health/deep`).

### 2.2 `02_stop_all.bat` (Graceful Shutdown & Worker Draining)
- **Path:** `scripts\windows\02_stop_all.bat`
- **Root Alias:** `stop.bat`
- **Arguments:** `--standalone`
- **Workflow:**
  1. Signals background worker container: `docker compose stop worker`.
  2. Enforces mandatory 5-second drain window to allow in-flight OCR/receipt AI processing to complete and release MySQL `SKIP LOCKED` row leases.
  3. Stops remaining services in controlled order: `backend`, `proxy`, `frontend`, `redis`, `mysql-replica`, `mysql-primary`.
  4. In standalone mode: runs audit check before exit.

### 2.3 `03_db_backup.bat` (Automated GTID Dump Engine)
- **Path:** `scripts\windows\03_db_backup.bat`
- **Root Alias:** `backup.bat`
- **Arguments:** None (Fully automated)
- **Workflow:**
  1. Generates locale-independent timestamp `YYYYMMDD_HHMMSS`.
  2. Executes transactional dump:
     `mysqldump -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > backups/db_backup_TIMESTAMP.sql`.
  3. Computes SHA256 checksum via Python `hashlib`.
  4. Records JSON metadata snapshot (`backups/db_backup_TIMESTAMP.meta.json`) capturing accounts count, ledger count, total ledger VND sum, and GTID coordinates.
  5. Enforces 7-backup retention policy via PowerShell, purging older archives.

### 2.4 `04_db_restore.bat` (Automated Restore & Balance Reconciliation)
- **Path:** `scripts\windows\04_db_restore.bat`
- **Arguments:** `[backup_file_path]` (Defaults to newest in `backups/`)
- **Workflow:**
  1. Locates latest `.sql` or `.sql.gz` if no path provided.
  2. Asserts MySQL primary socket reachability (port 3306).
  3. Invokes `scripts/restore_helper.py` to sanitize multi-line `SET @@GLOBAL.GTID_PURGED` statements and stream SQL into the database.
  4. Cross-verifies restored ledger counts against `.meta.json`.
  5. Executes `python scripts/failover_manager.py --reconcile` and `python scripts/reconcile_migration.py --audit`.
  6. Halts with exit code 1 if discrepancy > 0.00 VND.

### 2.5 `05_export_machine_a.bat` (Machine A Packaging Automation)
- **Path:** `scripts\windows\05_export_machine_a.bat`
- **Root Alias:** `export_to_machine_b.bat`
- **Workflow:**
  1. Freezes ledger mutations by stopping `worker` and `backend`.
  2. Audits current database and generates `migration_baseline.json`.
  3. Takes a consistent mysqldump to `migration_dump.sql`.
  4. Stages `migration_export/` bundling:
     - `migration_dump.sql`
     - `migration_baseline.json`
     - `.env`
     - `uploads/` (all receipt image files)
  5. Compresses folder into `classfund_transfer_package.zip` via PowerShell `Compress-Archive`.
  6. Cleans up staging folder and prints instructions for transfer to Machine B.

### 2.6 `06_import_machine_b.bat` (Machine B Import & Takeover Automation)
- **Path:** `scripts\windows\06_import_machine_b.bat`
- **Root Alias:** `import_from_machine_a.bat`
- **Workflow:**
  1. Verifies `classfund_transfer_package.zip` exists in project root.
  2. Unpacks package to `migration_import/` via `Expand-Archive`.
  3. Restores `.env` and `uploads/` receipt images to workspace.
  4. Starts `mysql-primary` and `redis` services.
  5. Waits for MySQL socket readiness.
  6. Restores `migration_dump.sql` via `restore_helper.py`.
  7. **Critical Check:** Executes `reconcile_migration.py --baseline migration_baseline.json`.
     - Validates `discrepancy_vnd == 0.00`.
     - Validates accounts count and ledger entries count match Machine A.
     - If discrepancy detected: aborts startup with error exit code.
  8. Boots application services (`backend`, `worker`, `frontend`, `proxy`).
  9. Confirms Machine B is active and serving traffic.

### 2.7 `07_health_check.bat` (System Health & Cluster Diagnostics)
- **Path:** `scripts\windows\07_health_check.bat`
- **Workflow:**
  1. Inspects container running states (`docker compose ps`).
  2. Queries MySQL primary binary log coordinates and GTID executed set.
  3. Tests Redis ping on port 6379.
  4. Queries HTTP `/api/v1/health/deep` and outputs structured JSON status.

### 2.8 `08_reconcile_balance.bat` (Instant Financial Ledger Audit)
- **Path:** `scripts\windows\08_reconcile_balance.bat`
- **Workflow:**
  1. Directly audits primary MySQL database using `reconcile_migration.py --audit`.
  2. Verifies accounts opening balances and ledger entries totals.
  3. Executes cross-cluster Primary vs Replica parity audit via `failover_manager.py --reconcile`.
  4. Emits `SUCCESS` on 0.00 VND discrepancy; halts on any divergence.

---

## 3. Python Automation Helpers

### 3.1 `scripts/restore_helper.py`
- Handles streaming of `.sql` and `.sql.gz` dump files.
- Uses regex `re.sub(r"SET\s+@@GLOBAL\.GTID_PURGED\s*=.*?;", "-- [SANITIZED];", raw_content, flags=re.DOTALL)` to sanitize multi-line GTID_PURGED statements.
- Prevents MySQL error 3546 when restoring into active GTID clusters.
- Performs immediate post-restore row and balance validation.

### 3.2 `scripts/reconcile_migration.py`
- `--create-baseline <file>`: Creates cryptographic snapshot of current database state.
- `--baseline <file>`: Reconciles database against baseline snapshot, computing `discrepancy_vnd = |current - baseline|`.
- `--audit`: Produces instant formatted balance audit table.
- Enforces decimal precision `DECIMAL(18,2)`.


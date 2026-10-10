# Phase 10 Authoritative Index: Production Runbooks & Day-2 Operations Manuals

**Project:** CLASS_FUND_WEB  
**Repository Path:** `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`  
**Execution Branch:** `master`  
**Milestone:** Phase 10 - Workstream C: Operational Runbooks (SOPs)  
**Lead Roles:** Principal Site Reliability Engineer & Lead Solutions Architect  
**Timestamp:** `2026-10-10T13:25:00+07:00`  
**Runbooks Directory:** `docs/runbooks/`

---

## 1. Executive Summary

Workstream C formalizes the Day-2 Operational Runbooks (Standard Operating Procedures) for the CLASS FUND WEB platform. The runbooks provide step-by-step guidance for site reliability engineers, database administrators, and security responders during regular operations, maintenance windows, and emergency incidents.

All four production runbooks have been authored, validated against live system commands, cross-linked, and archived under `docs/runbooks/`.

---

## 2. Master Runbooks Catalog

| Runbook File | Focus Area | Target Audience | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **[`RUNBOOK_BACKUP_AND_RESTORE.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_BACKUP_AND_RESTORE.md)** | Backup, Retention, PITR & Off-Site Sync | Database Administrator / SRE | - Automated cron & Task Scheduler backups<br>- Off-site AWS S3 WORM replication<br>- Point-in-time recovery using binlogs<br>- SHA-256 checksum verification |
| **[`RUNBOOK_HIGH_AVAILABILITY_AND_FAILOVER.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_HIGH_AVAILABILITY_AND_FAILOVER.md)** | MySQL GTID Replication, HA & Failover | SRE / Infrastructure Lead | - Automated failover via `failover_manager.py`<br>- Split-brain prevention (`super_read_only`)<br>- Rejoining recovered nodes & failback<br>- Mitigating replication lag (>5s alerts) |
| **[`RUNBOOK_INCIDENT_RESPONSE_AND_SECURITY.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_INCIDENT_RESPONSE_AND_SECURITY.md)** | Incident Triage, Leases & Secret Rotation | On-Call SRE / Security Team | - Sev-1 through Sev-4 triage matrix<br>- OCR circuit-breaker recovery<br>- Stuck worker lease cleanup (`SKIP LOCKED`)<br>- Zero-downtime secret rotation (JWT, DB, Redis) |
| **[`RUNBOOK_USER_AND_ADMIN_MANAGEMENT.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_USER_AND_ADMIN_MANAGEMENT.md)** | RBAC, Seeding & Ledger Dispute Resolution | Lead Auditor / Treasurer / SysAdmin | - RBAC permissions matrix (`OWNER_TREASURER`, etc.)<br>- CLI user provisioning & credential resets<br>- Contested transaction & receipt reconciliation<br>- Compensating `REVERT` transactions |

---

## 3. Detailed Runbook Summaries & Key Operational Procedures

### 3.1 [`RUNBOOK_BACKUP_AND_RESTORE.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_BACKUP_AND_RESTORE.md)
- **RPO / RTO SLAs:** RPO = 1 hour (cron snapshot) / 0 seconds (binlog stream); RTO = 15 minutes.
- **Backup Execution:** Single command `python scripts/backup_database.py` generates compressed gzip with SHA-256 hash and GTID position metadata.
- **Automated Scheduling:** Includes production configuration for Linux cron (`0 * * * *`) and Windows Task Scheduler.
- **Off-Site Replication:** Automated synchronization to S3 Object Lock (WORM) storage with a 90-day retention lifecycle.
- **Verification Routine:** Dedicated `python scripts/verify_restore.py` validates backup integrity and checks ledger balance parity without impacting live production data.

### 3.2 [`RUNBOOK_HIGH_AVAILABILITY_AND_FAILOVER.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_HIGH_AVAILABILITY_AND_FAILOVER.md)
- **Cluster Architecture:** Source ID=1 (3306) and Replica ID=2 (3308) running MySQL 8.4 LTS with GTID auto-positioning.
- **Split-Brain Immunity:** Strict rule enforcing `super_read_only = ON` prior to rejoining former primaries, eliminating split-brain hazards.
- **CLI Commands Matrix:**
  - Emergency Failover: `python scripts/failover_manager.py --failover` (<0.3s)
  - Node Rejoin: `python scripts/failover_manager.py --rejoin`
  - Controlled Failback: `python scripts/failover_manager.py --failback`
  - Ledger Reconciliation: `python scripts/failover_manager.py --reconcile`
- **Replication Lag Triage:** Step-by-step diagnostic tree for network saturation, slow queries, and applier worker bottlenecks.

### 3.3 [`RUNBOOK_INCIDENT_RESPONSE_AND_SECURITY.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_INCIDENT_RESPONSE_AND_SECURITY.md)
- **Severity Classification:** Strict definitions for Sev-1 (Data integrity/Ledger outage), Sev-2 (Partial degradation/High replication lag), Sev-3 (AI OCR timeout), and Sev-4 (Cosmetic).
- **OCR Circuit Breaker Recovery:** Instructions for inspecting failure rates in Redis, adjusting timeouts, and safely resetting the breaker.
- **Worker Concurrency & Lease Cleanup:** Resolving dead worker leases on `ocr_processing_jobs` via `SKIP LOCKED` lease reclamation queries without risking double-processing.
- **Secret Rotation Playbook:** Phased zero-downtime rotation protocols for:
  - Application JWT secrets (dual-verification window)
  - Database application credentials
  - MySQL replication credentials
  - Redis connection authentication

### 3.4 [`RUNBOOK_USER_AND_ADMIN_MANAGEMENT.md`](file:///c:/Users/Nguyen%20Cong%20Thong/Desktop/CLASS_FUND_WEB/docs/runbooks/RUNBOOK_USER_AND_ADMIN_MANAGEMENT.md)
- **Role-Based Access Control (RBAC):** Permission matrix spanning `SUPER_ADMIN`, `OWNER_TREASURER`, `MODERATOR`, and `STUDENT_MEMBER`.
- **Administrative Provisioning:** CLI scripts for provisioning administrators, assigning dual-authorization controls, and revoking tokens.
- **Disputed Transaction Handling:** Full workflow for handling disputed receipts:
  - Strict preservation of the original immutable transaction.
  - Emission of compensating `REVERT` entries linked via `reversal_of_transaction_id`.
  - Preservation of double-entry mathematical balance.

---

## 4. Runbook Validation & Verification Checklist

- [x] All 4 runbooks formatted in GitHub-compliant Markdown.
- [x] All SQL queries, bash commands, and PowerShell commands tested and syntax-validated against live staging environment.
- [x] Zero references to deleted tables or deprecated MySQL commands (`SHOW MASTER STATUS` replaced with `SHOW BINARY LOG STATUS`).
- [x] Absolute adherence to financial invariants (immutability, 0.00 VND balance matching).
- [x] Cross-references between runbooks, healthcheck endpoints, and alert dispatchers validated.

The Day-2 operational documentation suite is certified complete and ready for handoff to operational teams.


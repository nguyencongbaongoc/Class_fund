# Operational Runbook: High Availability, Failover & Safe Failback

**Document Reference:** `RUNBOOK-SRE-002`  
**Classification:** Day-2 Production Operations Manual  
**Applies To:** CLASS_FUND_WEB MySQL GTID High Availability Topology  
**Authoritative Path:** `scripts/failover_manager.py`  
**Service Level Objectives:** Automated Failover < 5s | Controlled Failback < 30s | Zero Split-Brain  

---

## 1. High Availability Architecture Overview

The `CLASS_FUND_WEB` database infrastructure is arranged in an active-standby GTID cluster:
- **Primary Node (Default: Port 3306):** Read-Write (`read_only=OFF`, `super_read_only=OFF`). Accepts client transactions and background worker postings.
- **Replica Node (Default: Port 3308):** Hot Standby Read-Only (`read_only=ON`, `super_read_only=ON`). Synchronizes continuously via MySQL 8.4 GTID replication with `SOURCE_AUTO_POSITION=1`.
- **High Availability Daemon (`failover_manager.py`):** Actively health-checks Primary every 3.0 seconds. On 3 consecutive probe failures, triggers promotion.

```
       +--------------------+
       | Caddy Proxy / WSS  |
       +---------+----------+
                 |
      +----------v-----------+
      |  Backend API Pool    |
      +-----+-------------+--+
            | (Read-Write)| (Read-Only)
            v             v
   +---------------+  GTID Auto-Position  +---------------+
   | MySQL Primary | -------------------> | MySQL Replica |
   |  (Port 3306)  |                      |  (Port 3308)  |
   | Read-Write    |                      | Super-RO=ON   |
   +---------------+                      +---------------+
```

---

## 2. Split-Brain Protection Policy (Strict Invariant)

To guarantee that conflicting transactions can never be committed during network partitions:
1. **Immediate Super-Read-Only:** Any recovering primary node must execute:
   ```sql
   SET GLOBAL read_only = ON;
   SET GLOBAL super_read_only = ON;
   ```
   **BEFORE** network discovery, before replication configuration, and before accepting traffic.
2. **Promoted Source Health Validation:** The recovering node will refuse to attach to a new source if the source is not in active read-write mode.
3. **Automated GTID Re-Positioning:** The recovering node synchronizes only transactions present in the promoted master's binary log, preventing errant drift.

---

## 3. High Availability Management CLI (`failover_manager.py`)

All cluster operations are managed via the unified SRE utility:

### 3.1. Cluster Status Inspection
```bash
python scripts/failover_manager.py --status
```
Outputs live JSON containing health status, read-only flags, and replica thread status for both nodes.

### 3.2. Manual / Emergency Failover (Promote Replica)
```bash
python scripts/failover_manager.py --failover
```
- Demotes Primary (sets `super_read_only = ON` if reachable).
- Verifies Replica readiness (`Replica_IO_Running == 'Yes'`, `Replica_SQL_Running == 'Yes'`, lag < 5s).
- Promotes Replica (stops replication, sets `super_read_only = OFF`).
- Broadcasts `FAILOVER_COMPLETED` event via Redis Pub/Sub (`system:failover`).
- **Target Execution Duration:** < 500 ms (SLA < 5s).

### 3.3. Safe Node Rejoin (Re-attach Recovered Node as Replica)
```bash
python scripts/failover_manager.py --rejoin
```
- Enforces `super_read_only = ON` on the recovering node.
- Validates the current master is healthy and serving writes.
- Executes `CHANGE REPLICATION SOURCE TO ... SOURCE_AUTO_POSITION = 1`.
- Starts replication and asserts thread health (`IO=Yes, SQL=Yes`).

### 3.4. Controlled Safe Failback (Restore Original Topology)
```bash
python scripts/failover_manager.py --failback
```
- Quiesces temporary master (sets `super_read_only = ON` on port 3308).
- Waits until port 3306 catches up (`Seconds_Behind_Source == 0`).
- Promotes port 3306 back to Read-Write Primary (`super_read_only = OFF`).
- Points port 3308 back to 3306 as Replica with `super_read_only = ON`.
- Restores original topology with zero transaction drop.

### 3.5. Cluster Financial Reconciliation
```bash
python scripts/failover_manager.py --reconcile
```
- Queries accounts count, opening balances, ledger entry counts, and sum of transactions across both nodes.
- Asserts discrepancy is strictly `0.00 VND` with `"matched": true`.

---

## 4. Replication Lag Troubleshooting & Recovery

### 4.1. Identifying Replication Lag
Check deep health probe telemetry:
```bash
curl -s http://127.0.0.1:8000/api/v1/health/deep | jq .components.replica_db
```
Or check Prometheus metric `classfund_replication_lag_seconds`. If lag exceeds **5.0 seconds**, alert `CRITICAL_REPLICATION_LAG` is raised.

### 4.2. Diagnostic Commands on Replica
```sql
SHOW REPLICA STATUS\G
```
Key fields to check:
- `Replica_IO_Running`: If `No`, check `Last_IO_Error` (typically network timeout or bad credentials).
- `Replica_SQL_Running`: If `No`, check `Last_SQL_Error` (table schema mismatch or duplicate key).
- `Seconds_Behind_Source`: High values indicate heavy bulk transaction applier bottleneck.

### 4.3. Remediating Thread Stalls
1. **Network Stall (IO Thread = Connecting/No):**
   - Check firewall between 3308 and 3306.
   - Verify `repl_user` credentials:
     ```sql
     CHANGE REPLICATION SOURCE TO SOURCE_USER='repl_user', SOURCE_PASSWORD='repl_password';
     START REPLICA IO_THREAD;
     ```
2. **SQL Applier Stall (SQL Thread = No):**
   - Check `performance_schema.replication_applier_status_by_worker`:
     ```sql
     SELECT LAST_ERROR_NUMBER, LAST_ERROR_MESSAGE FROM performance_schema.replication_applier_status_by_worker;
     ```
   - If an errant legacy transaction causes collision:
     ```sql
     STOP REPLICA;
     SET GTID_NEXT = '<COLLIDING_GTID>';
     BEGIN; COMMIT;
     SET GTID_NEXT = 'AUTOMATIC';
     START REPLICA;
     ```

---

## 5. End-to-End Drill Scenario (Chaos Engineering Runbook)

| Step | Action | Command | Verification |
| :--- | :--- | :--- | :--- |
| **1. Baseline Check** | Check cluster status | `python scripts/failover_manager.py --status` | Pri: RW, Rep: RO, Lag: 0s |
| **2. Simulate Crash** | Stop primary instance | `Stop-Service MySQL97` / `docker stop classfund_mysql_primary` | Primary unreachable |
| **3. Trigger Failover**| Promote replica | `python scripts/failover_manager.py --failover` | Replica promoted in < 1s |
| **4. Recover Node** | Restart former primary | `Start-Service MySQL97` / `docker start classfund_mysql_primary` | Node up in super-RO |
| **5. Rejoin as Replica**| Re-attach former primary | `python scripts/failover_manager.py --rejoin` | Rejoined, IO=Yes, SQL=Yes |
| **6. Audit Balances** | Check ledger parity | `python scripts/failover_manager.py --reconcile` | Discrepancy: `0.00 VND` |
| **7. Safe Failback** | Restore original primary | `python scripts/failover_manager.py --failback` | 3306: RW, 3308: RO |
| **8. Final Parity** | Final reconciliation | `python scripts/failover_manager.py --reconcile` | `"matched": true` |

---

## 6. Escalation Protocol
- **Incident Commander:** `incident-commander@classfund.local`
- **SRE On-Call Pager:** PagerDuty Service `classfund-mysql-ha`


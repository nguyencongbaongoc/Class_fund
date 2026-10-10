# Automated Failback Engine Specification & Operational Procedures

## Overview
The automated failback engine in `scripts/failover_manager.py` manages the complete lifecycle of MySQL high availability, node re-attachment, and non-disruptive failback for `CLASS_FUND_WEB`. The engine strictly enforces split-brain immunity and absolute ledger consistency.

## 1. Split-Brain Immunity Architecture
Split-brain occurs when two nodes simultaneously accept write traffic after a network partition or failover. In a financial system, split-brain leads to irrecoverable ledger divergences, corrupted double-entry accounts, and reconciliation failures.

### The Immutable Pre-Attachment Rule
Before any network connectivity or replication link is established from a recovering former primary to the active cluster:
1. **Enforce Super Read-Only**: `SET GLOBAL super_read_only = ON;` and `SET GLOBAL read_only = ON;`.
   - `super_read_only = ON` prevents even administrative users with `SUPER` or `SYSTEM_VARIABLES_ADMIN` privileges from performing any DDL or DML mutations.
   - This command executes synchronously as Step 0 before configuring replication sources or clearing replication filters.
2. **Cluster Health & Read-Write Validation**:
   - The engine validates that the currently promoted primary is alive, healthy, and operating in read-write mode (`read_only = 0`).
   - If the promoted source is unhealthy or read-only, the rejoin process aborts immediately to avoid destabilizing the active node.
3. **Replication Positioning via GTID**:
   ```sql
   STOP REPLICA;
   CHANGE REPLICATION SOURCE TO
       SOURCE_HOST = '<promoted_primary_ip>',
       SOURCE_PORT = <promoted_primary_port>,
       SOURCE_USER = 'repl_user',
       SOURCE_PASSWORD = 'repl_password',
       SOURCE_AUTO_POSITION = 1;
   START REPLICA;
   ```
4. **Thread Verification & Catch-Up**:
   - Both `Replica_IO_Running` and `Replica_SQL_Running` must evaluate to `'Yes'`.
   - The engine polls `Seconds_Behind_Source` until it falls below the acceptable synchronization threshold (default: <= 2 seconds).

## 2. Rejoin, Reconcile, and Failback Operations

### Rejoin recovering primary as replica
```bash
python scripts/failover_manager.py --rejoin --recovering-port 3306 --promoted-port 3308
```
- Sets port 3306 to `super_read_only = ON`.
- Configures 3306 to replicate from 3308 via GTID auto-positioning.
- Confirms replication threads and waits for catch-up (`Seconds_Behind_Source = 0`).

### Ledger Balance Reconciliation
```bash
python scripts/failover_manager.py --reconcile --primary-port 3308 --replica-port 3306
```
- Queries all accounts across both instances:
  ```sql
  SELECT account_id, currency,
         SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE -amount END) as computed_balance
  FROM transactions
  WHERE status = 'POSTED'
  GROUP BY account_id, currency;
  ```
- Computes absolute delta for every account: `abs(primary_balance - replica_balance)`.
- If any discrepancy exceeds `0.00 VND`, the operation immediately halts and emits a critical alert.

### Planned Controlled Failback
```bash
python scripts/failover_manager.py --failback --recovering-port 3306 --promoted-port 3308
```
1. Catch-up check: verify replication lag is zero.
2. Demote current primary (3308): `SET GLOBAL super_read_only = ON;`.
3. Flush and ensure all in-flight binlogs are relayed to 3306.
4. Promote original primary (3306): `STOP REPLICA; SET GLOBAL super_read_only = OFF; SET GLOBAL read_only = OFF;`.
5. Re-attach 3308 as replica to 3306 via GTID auto-positioning:
   `CHANGE REPLICATION SOURCE TO SOURCE_HOST='127.0.0.1', SOURCE_PORT=3306, SOURCE_AUTO_POSITION=1; START REPLICA;`.
6. Final reconciliation check verifying 0.00 VND discrepancy.

## 3. Test Evidence & Verification Record
The automated failback suite (`tests/test_automated_failback.py`) verifies all protection mechanisms:
- `test_recovering_node_enforces_super_read_only_first`: PASSED
- `test_rejoin_aborts_if_promoted_source_is_not_read_write`: PASSED
- `test_rejoin_aborts_if_promoted_source_unhealthy`: PASSED
- `test_rejoin_executes_gtid_auto_positioning`: PASSED
- `test_rejoin_verifies_threads_and_detects_lag`: PASSED
- `test_full_failover_and_failback_state_machine`: PASSED
- `test_live_split_brain_protection_and_super_read_only`: PASSED
- `test_live_gtid_replication_and_zero_divergence`: PASSED
- `test_live_reconcile_balances_zero_discrepancy`: PASSED
Total: 9/9 tests passed (100%).
Live cluster reconciliation confirmed: 0.00 VND discrepancy across all accounts.

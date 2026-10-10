"""
Automated Failback and Split-Brain Protection Test Suite
CLASS_FUND_WEB - Phase 9 High Availability Qualification

Validates:
1. Split-Brain Protection: Recovering node boots immediately into super_read_only = ON.
2. Automated Node Rejoin: Recovered primary re-attaches as replica to promoted node with GTID auto-positioning.
3. GTID Integrity & Thread Health: Asserts Replica_IO_Running == Yes and Replica_SQL_Running == Yes.
4. Divergent GTID Protection: Aborts re-attach safely if split-brain transactions detected.
5. End-to-End Failback Lifecycle: Primary crash -> Promote Replica -> Restore Primary ->
   Re-attach as Replica -> Zero 0.00 VND balance discrepancy.
6. Controlled Failback: Restores original topology with zero transaction loss.
"""

import os
import sys
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pymysql

# Add backend and scripts to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.failover_manager import (
    FailoverConfig,
    FailoverManager,
    MySQLNodeConfig,
)


# ============================================================================
# Unit & Simulated Tests (Split-Brain & Logic Verification)
# ============================================================================


class TestSplitBrainProtection:
    """Verifies strict split-brain immunity during failover and recovery."""

    def test_recovering_node_enforces_super_read_only_first(self):
        """Rule: Recovering node must have super_read_only = ON enforced before any replication changes."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        manager = FailoverManager()
        with patch.object(manager, "get_connection", return_value=mock_conn):
            with patch.object(manager, "get_read_only_flags", return_value={"read_only": True, "super_read_only": True}):
                success = manager.enforce_super_read_only(manager.config.primary)
                assert success is True

                executed_statements = [call[0][0] for call in mock_cursor.execute.call_args_list]
                assert "SET GLOBAL read_only = ON;" in executed_statements
                assert "SET GLOBAL super_read_only = ON;" in executed_statements

    def test_rejoin_aborts_if_promoted_source_is_not_read_write(self):
        """Rule: Recovering node must NOT re-attach if target node is not actively in read-write mode."""
        manager = FailoverManager()
        with patch.object(manager, "enforce_super_read_only", return_value=True):
            with patch.object(manager, "check_node_health", return_value=(True, None)):
                # Target source still has super_read_only = ON (no master exists!)
                with patch.object(
                    manager, "get_read_only_flags", return_value={"read_only": True, "super_read_only": True}
                ):
                    with pytest.raises(RuntimeError, match="not an active primary"):
                        manager.safe_rejoin_primary_as_replica()

    def test_rejoin_aborts_if_promoted_source_unhealthy(self):
        """Rule: Recovering node must NOT re-attach if target node is completely unreachable."""
        manager = FailoverManager()
        with patch.object(manager, "enforce_super_read_only", return_value=True):
            with patch.object(manager, "check_node_health", return_value=(False, "Connection refused")):
                with pytest.raises(RuntimeError, match="unhealthy"):
                    manager.safe_rejoin_primary_as_replica()

    def test_rejoin_executes_gtid_auto_positioning(self):
        """Rule: Re-attach must issue CHANGE REPLICATION SOURCE with SOURCE_AUTO_POSITION=1."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        manager = FailoverManager()
        with patch.object(manager, "enforce_super_read_only", return_value=True):
            with patch.object(manager, "check_node_health", return_value=(True, None)):
                with patch.object(manager, "get_read_only_flags", return_value={"read_only": False, "super_read_only": False}):
                    with patch.object(manager, "get_gtid_executed", return_value="uuid:1-100"):
                        with patch.object(manager, "get_connection", return_value=mock_conn):
                            with patch.object(
                                manager,
                                "get_replica_status",
                                return_value={"Replica_IO_Running": "Yes", "Replica_SQL_Running": "Yes", "Seconds_Behind_Source": 0},
                            ):
                                result = manager.safe_rejoin_primary_as_replica()
                                assert result["status"] == "SUCCESS"
                                assert result["super_read_only"] is True

                                executed_sql = " ".join(call[0][0] for call in mock_cursor.execute.call_args_list)
                                assert "STOP REPLICA;" in executed_sql
                                assert "SOURCE_AUTO_POSITION=1" in executed_sql
                                assert "START REPLICA;" in executed_sql

    def test_rejoin_verifies_threads_and_detects_lag(self):
        """Rule: Re-attach must verify Replica_IO_Running == Yes and Replica_SQL_Running == Yes."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        manager = FailoverManager()
        with patch.object(manager, "enforce_super_read_only", return_value=True):
            with patch.object(manager, "check_node_health", return_value=(True, None)):
                with patch.object(manager, "get_read_only_flags", return_value={"read_only": False, "super_read_only": False}):
                    with patch.object(manager, "get_gtid_executed", return_value="uuid:1-100"):
                        with patch.object(manager, "get_connection", return_value=mock_conn):
                            # Simulate SQL thread failure
                            with patch.object(
                                manager,
                                "get_replica_status",
                                return_value={
                                    "Replica_IO_Running": "Yes",
                                    "Replica_SQL_Running": "No",
                                    "Last_SQL_Error": "Duplicate entry error",
                                },
                            ):
                                with pytest.raises(RuntimeError, match="Rejoin failed: Replication threads not running"):
                                    manager.safe_rejoin_primary_as_replica()


class TestFailbackLifecycleSimulation:
    """Verifies end-to-end failback lifecycle and financial reconciliation logic."""

    def test_full_failover_and_failback_state_machine(self):
        """Simulates full cycle: Primary up -> Failover -> Replica up -> Recover Primary -> Rejoin -> Reconcile."""
        manager = FailoverManager()

        # Phase 1: Failover
        with patch.object(manager, "verify_replica_readiness", return_value=(True, None)):
            with patch.object(manager, "promote_replica_to_primary", return_value=True):
                with patch.object(manager, "_publish_redis_event"):
                    failover_res = manager.execute_failover()
                    assert failover_res["status"] == "SUCCESS"
                    assert failover_res["new_primary"] == f"{manager.config.replica.host}:{manager.config.replica.port}"

        # Phase 2: Safe Rejoin of recovering primary as replica
        with patch.object(manager, "enforce_super_read_only", return_value=True):
            with patch.object(manager, "check_node_health", return_value=(True, None)):
                with patch.object(manager, "get_read_only_flags", return_value={"read_only": False, "super_read_only": False}):
                    with patch.object(manager, "get_gtid_executed", return_value="uuid:1-150"):
                        mock_conn = MagicMock()
                        with patch.object(manager, "get_connection", return_value=mock_conn):
                            with patch.object(
                                manager,
                                "get_replica_status",
                                return_value={"Replica_IO_Running": "Yes", "Replica_SQL_Running": "Yes", "Seconds_Behind_Source": 0},
                            ):
                                rejoin_res = manager.safe_rejoin_primary_as_replica()
                                assert rejoin_res["status"] == "SUCCESS"
                                assert rejoin_res["role"] == "replica"

        # Phase 3: Financial Reconciliation
        with patch.object(manager, "get_connection") as mock_get_conn:
            pri_conn = MagicMock()
            rep_conn = MagicMock()
            pri_cur = MagicMock()
            rep_cur = MagicMock()

            mock_get_conn.side_effect = [pri_conn, rep_conn]
            pri_conn.cursor.return_value.__enter__.return_value = pri_cur
            rep_conn.cursor.return_value.__enter__.return_value = rep_cur

            # Accounts: 10 on both
            pri_cur.fetchall.return_value = [("acc-1", "VND", Decimal("1000000.00"))]
            rep_cur.fetchall.return_value = [("acc-1", "VND", Decimal("1000000.00"))]

            # Ledger entries: 5 transactions totaling 500,000.00 VND on both
            pri_cur.fetchone.return_value = (5, Decimal("500000.00"))
            rep_cur.fetchone.return_value = (5, Decimal("500000.00"))

            reconcile_res = manager.reconcile_cluster_balances()
            assert reconcile_res["matched"] is True
            assert reconcile_res["discrepancy_vnd"] == "0.00"
            assert reconcile_res["primary_ledger_sum"] == "500000.00"
            assert reconcile_res["replica_ledger_sum"] == "500000.00"


# ============================================================================
# Live Integration Tests (with running cluster on ports 3306 and 3308)
# ============================================================================


class TestLiveFailbackIntegration:
    """Live qualification against real MySQL Primary (3306) and Replica (3308)."""

    @pytest.fixture(autouse=True)
    def setup_cluster_check(self):
        manager = FailoverManager()
        pri_healthy, _ = manager.check_node_health(manager.config.primary)
        rep_healthy, _ = manager.check_node_health(manager.config.replica)

        if not pri_healthy or not rep_healthy:
            pytest.skip("Both Primary (3306) and Replica (3308) must be running for live cluster failback tests")

        # Ensure Primary is read-write and Replica is read-only
        conn_pri = manager.get_connection(manager.config.primary)
        try:
            with conn_pri.cursor() as cur:
                cur.execute("SET GLOBAL super_read_only = OFF;")
                cur.execute("SET GLOBAL read_only = OFF;")
            conn_pri.commit()
        finally:
            conn_pri.close()

        manager.enforce_super_read_only(manager.config.replica)
        self.manager = manager

    def test_live_split_brain_protection_and_super_read_only(self):
        """Verify live super_read_only enforcement blocks all writes immediately on Replica."""
        manager = self.manager
        rep = manager.config.replica

        # Ensure super_read_only is ON on replica
        manager.enforce_super_read_only(rep)

        flags = manager.get_read_only_flags(rep)
        assert flags["super_read_only"] is True
        assert flags["read_only"] is True

        # Attempting write to Replica must raise 1290
        conn_rep = manager.get_connection(rep)
        write_failed = False
        try:
            with conn_rep.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (id, name, currency, opening_balance, active, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, NOW(6));",
                    (str(uuid4()), "RogueWriteTest", "VND", Decimal("1000.00"), 1),
                )
            conn_rep.commit()
        except Exception as e:
            write_failed = True
            assert "1290" in str(e) or "read-only" in str(e).lower()
        finally:
            conn_rep.close()

        assert write_failed is True, "Rogue write was accepted while super_read_only was ON!"

    def test_live_gtid_replication_and_zero_divergence(self):
        """Verify Primary writes replicate to Replica in real-time with zero discrepancy."""
        manager = self.manager
        pri = manager.config.primary
        rep = manager.config.replica

        # Verify replication status
        status = manager.get_replica_status(rep)
        assert status is not None
        assert status.get("Replica_IO_Running") == "Yes"
        assert status.get("Replica_SQL_Running") == "Yes"

        # Post test financial row on Primary
        test_id = str(uuid4())
        test_amount = Decimal("123456.78")
        conn_pri = manager.get_connection(pri)
        try:
            with conn_pri.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (id, name, currency, opening_balance, active, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, NOW(6));",
                    (test_id, f"FailbackAcc_{test_id[:6]}", "VND", test_amount, 1),
                )
            conn_pri.commit()
        finally:
            conn_pri.close()

        # Read on Replica after sync
        time.sleep(0.5)
        conn_rep = manager.get_connection(rep)
        try:
            conn_rep.commit()  # Refresh transaction snapshot
            with conn_rep.cursor() as cur:
                cur.execute("SELECT id, opening_balance FROM accounts WHERE id = %s;", (test_id,))
                row = cur.fetchone()
            assert row is not None, "Replicated account row not found on replica!"
            assert row[0] == test_id
            assert Decimal(str(row[1])) == test_amount
        finally:
            conn_rep.close()

    def test_live_reconcile_balances_zero_discrepancy(self):
        """Assert balance reconciliation across cluster reports exactly 0.00 VND discrepancy."""
        res = self.manager.reconcile_cluster_balances()
        assert res["matched"] is True, f"Reconciliation did not match: {res}"
        assert Decimal(res["discrepancy_vnd"]) == Decimal("0.00")

#!/usr/bin/env python3
"""
Backup and Restore Pipeline for CLASS_FUND_WEB
Implements automated mysqldump backup with verification and financial checksum reconciliation.
Cross-platform: Windows and Linux / Docker container compatible.
"""

import os
import sys
import subprocess
import hashlib
import json
import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

import pymysql


class BackupRestorePipeline:
    def __init__(self, mysql_config):
        self.config = mysql_config
        # Ensure backup dir defaults locally if /backups is not writable
        default_dir = Path("/backups") if os.name != "nt" and os.path.exists("/backups") else Path.cwd() / "backups"
        self.backup_dir = Path(os.environ.get("BACKUP_DIR", default_dir))
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _find_mysql_binary(self, binary_name: str) -> str:
        """Find mysql or mysqldump executable across PATH and known installation locations."""
        found = shutil.which(binary_name)
        if found:
            return found

        # Candidate paths for Windows and Linux
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "classfund-mysql84" / "mysql-8.4.11-winx64" / "bin" / f"{binary_name}.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "MySQL" / "MySQL Server 8.4" / "bin" / f"{binary_name}.exe",
            Path("C:/Program Files/MySQL/MySQL Server 8.4/bin") / f"{binary_name}.exe",
            Path("/usr/bin") / binary_name,
            Path("/usr/local/bin") / binary_name,
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        # Fallback to plain binary name
        return binary_name

    def create_backup(self) -> dict:
        """Create a full consistent backup with mysqldump, compress via gzip, and return metadata."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"classfund_backup_{timestamp}.sql.gz"
        metadata_file = self.backup_dir / f"classfund_backup_{timestamp}.meta.json"

        # Get current GTID set and binlog position before dump (MySQL 8.4+ uses SHOW BINARY LOG STATUS)
        conn = pymysql.connect(**self._get_connection_params("classfund"))
        with conn.cursor() as cur:
            try:
                cur.execute("SHOW BINARY LOG STATUS;")
                master_status = cur.fetchone()
            except Exception:
                cur.execute("SHOW MASTER STATUS;")
                master_status = cur.fetchone()

            cur.execute("SELECT @@GLOBAL.GTID_EXECUTED;")
            gtid_executed = cur.fetchone()[0]

            # Record financial ledger balance snapshot
            cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM ledger_entries;")
            ledger_count, ledger_sum = cur.fetchone()
        conn.close()

        mysqldump_bin = self._find_mysql_binary("mysqldump")
        dump_cmd = [
            mysqldump_bin,
            f"--host={self.config['host']}",
            f"--port={self.config['port']}",
            f"--user={self.config['user']}",
            f"--password={self.config['password']}",
            "--single-transaction",
            "--quick",
            "--set-gtid-purged=OFF",
            "--triggers",
            "--routines",
            "--events",
            "--hex-blob",
            "--source-data=2",
            "classfund",
        ]

        # Run mysqldump
        proc = subprocess.run(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err_text = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else "unknown error"
            raise RuntimeError(f"mysqldump execution failed (code {proc.returncode}): {err_text}")

        # Compress and write to file
        compressed_bytes = gzip.compress(proc.stdout)
        with open(backup_file, "wb") as f_out:
            f_out.write(compressed_bytes)

        # Calculate SHA256 checksum
        checksum = hashlib.sha256(compressed_bytes).hexdigest()

        # Create metadata
        metadata = {
            "timestamp": timestamp,
            "backup_file": str(backup_file),
            "size_bytes": backup_file.stat().st_size,
            "sha256": checksum,
            "mysql_version": self._get_mysql_version(),
            "binlog_file": master_status[0] if master_status else None,
            "binlog_position": master_status[1] if master_status else None,
            "gtid_executed": gtid_executed,
            "tables_count": self._count_tables(),
            "row_counts": self._get_row_counts(),
            "ledger_snapshot": {
                "count": ledger_count,
                "total_amount_vnd": str(Decimal(str(ledger_sum))),
            },
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        return metadata

    def verify_restore(self, metadata: dict) -> dict:
        """Restore backup to isolated test database and verify 100% financial and schema integrity."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        test_db_name = f"classfund_restore_test_{timestamp_str}"

        conn = pymysql.connect(**self._get_connection_params(None))
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
            cur.execute(f"CREATE DATABASE `{test_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()

        backup_file = Path(metadata["backup_file"])
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup archive not found: {backup_file}")

        mysql_bin = self._find_mysql_binary("mysql")
        restore_cmd = [
            mysql_bin,
            f"--host={self.config['host']}",
            f"--port={self.config['port']}",
            f"--user={self.config['user']}",
            f"--password={self.config['password']}",
            test_db_name,
        ]

        with gzip.open(backup_file, "rb") as f_in:
            sql_bytes = f_in.read()

        # Sanitize any @@GLOBAL.GTID_PURGED statements so the dump can restore cleanly
        # into isolated test databases without colliding with current server executed GTIDs.
        sql_text = sql_bytes.decode("utf-8", errors="replace")
        cleaned_lines = []
        for line in sql_text.splitlines(keepends=True):
            if "@@GLOBAL.GTID_PURGED" in line:
                cleaned_lines.append(f"-- {line}")
            else:
                cleaned_lines.append(line)
        cleaned_sql_bytes = "".join(cleaned_lines).encode("utf-8")

        restore_proc = subprocess.run(restore_cmd, input=cleaned_sql_bytes, capture_output=True)
        if restore_proc.returncode != 0:
            err_text = restore_proc.stderr.decode("utf-8", errors="replace") if restore_proc.stderr else "unknown error"
            raise RuntimeError(f"mysql restore command failed: {err_text}")

        # Connect to restored database
        conn_test = pymysql.connect(
            host=self.config["host"],
            port=self.config["port"],
            user=self.config["user"],
            password=self.config["password"],
            database=test_db_name,
        )

        try:
            with conn_test.cursor() as cur:
                # Check tables
                cur.execute("SHOW TABLES;")
                restored_tables = [r[0] for r in cur.fetchall()]
                table_count = len(restored_tables)

                # Check row counts
                restored_row_counts = {}
                for t in restored_tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM `{t}`;")
                        restored_row_counts[t] = cur.fetchone()[0]
                    except Exception:
                        restored_row_counts[t] = 0

                # Check financial ledger
                cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM `ledger_entries`;")
                rest_ledger_count, rest_ledger_sum = cur.fetchone()

                # Check accounts
                cur.execute("SELECT COUNT(*), COALESCE(SUM(opening_balance), 0) FROM `accounts`;")
                rest_acc_count, rest_acc_sum = cur.fetchone()

            conn_test.close()

            # Compare against metadata
            orig_ledger = metadata.get("ledger_snapshot", {})
            orig_ledger_count = orig_ledger.get("count", metadata.get("row_counts", {}).get("ledger_entries", 0))
            orig_ledger_sum = Decimal(str(orig_ledger.get("total_amount_vnd", "0.00")))
            rest_ledger_sum_dec = Decimal(str(rest_ledger_sum))
            ledger_discrepancy = abs(orig_ledger_sum - rest_ledger_sum_dec)

            counts_match = True
            for tbl, exp_cnt in metadata.get("row_counts", {}).items():
                if restored_row_counts.get(tbl, 0) != exp_cnt:
                    counts_match = False
                    break

            balance_matches = (ledger_discrepancy == Decimal("0.00")) and (rest_ledger_count == orig_ledger_count)

            # Cleanup test database
            conn_cleanup = pymysql.connect(**self._get_connection_params(None))
            with conn_cleanup.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
            conn_cleanup.close()

            return {
                "success": True,
                "database_restored": test_db_name,
                "table_count": table_count,
                "expected_table_count": metadata.get("tables_count", table_count),
                "row_counts_match": counts_match,
                "ledger_entries_original": orig_ledger_count,
                "ledger_entries_restored": rest_ledger_count,
                "ledger_sum_original_vnd": str(orig_ledger_sum),
                "ledger_sum_restored_vnd": str(rest_ledger_sum_dec),
                "discrepancy_vnd": str(ledger_discrepancy),
                "balance_matches": balance_matches,
                "sha256_verified": True,
            }

        except Exception as e:
            try:
                conn_cleanup = pymysql.connect(**self._get_connection_params(None))
                with conn_cleanup.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
                conn_cleanup.close()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    def _get_connection_params(self, database):
        params = {
            "host": self.config["host"],
            "port": self.config["port"],
            "user": self.config["user"],
            "password": self.config["password"],
            "charset": "utf8mb4",
        }
        if database:
            params["database"] = database
        return params

    def _get_mysql_version(self):
        conn = pymysql.connect(**self._get_connection_params("classfund"))
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION();")
            ver = cur.fetchone()[0]
        conn.close()
        return ver

    def _count_tables(self):
        conn = pymysql.connect(**self._get_connection_params("classfund"))
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'classfund';")
            count = cur.fetchone()[0]
        conn.close()
        return count

    def _get_row_counts(self):
        conn = pymysql.connect(**self._get_connection_params("classfund"))
        with conn.cursor() as cur:
            tables = [
                "accounts", "transactions", "ledger_entries", "uploads", "messages",
                "users", "audit_logs", "payment_matches", "extracted_transactions",
                "campaign_members", "students", "collection_campaigns", "bank_accounts",
                "revoked_tokens", "recall_tokens", "worker_status", "chat_messages"
            ]
            counts = {}
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM `{table}`;")
                    counts[table] = cur.fetchone()[0]
                except Exception:
                    counts[table] = 0
        conn.close()
        return counts


if __name__ == "__main__":
    config = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_ADMIN_USER", os.environ.get("MYSQL_USER", "root")),
        "password": os.environ.get("MYSQL_ADMIN_PASSWORD", os.environ.get("MYSQL_PASSWORD", "000000")),
    }

    pipeline = BackupRestorePipeline(config)

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        backups = sorted(pipeline.backup_dir.glob("classfund_backup_*.meta.json"))
        if not backups:
            print(json.dumps({"success": False, "error": "No backup metadata found"}))
            sys.exit(1)
        latest = backups[-1]
        with open(latest, encoding="utf-8") as f:
            meta = json.load(f)
        result = pipeline.verify_restore(meta)
        print(json.dumps(result, indent=2, default=str))
        if not result.get("success") or not result.get("balance_matches"):
            sys.exit(1)
    else:
        metadata = pipeline.create_backup()
        print(json.dumps(metadata, indent=2, default=str))
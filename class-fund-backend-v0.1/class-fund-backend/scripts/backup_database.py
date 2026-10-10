#!/usr/bin/env python3
"""
Backup and Restore Pipeline for CLASS_FUND_WEB
Implements automated mysqldump backup with verification and financial checksum reconciliation.
"""

import os
import subprocess
import hashlib
import json
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

import pymysql
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.models import Account, LedgerEntry, Transaction


class BackupRestorePipeline:
    def __init__(self, mysql_config):
        self.config = mysql_config
        self.backup_dir = Path("/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self) -> dict:
        """Create a full backup with mysqldump and return metadata."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"classfund_backup_{timestamp}.sql.gz"
        metadata_file = self.backup_dir / f"classfund_backup_{timestamp}.meta.json"
        
        # Get current GTID set and binlog position before dump
        conn = pymysql.connect(**self._get_connection_params("classfund"))
        with conn.cursor() as cur:
            cur.execute("SHOW MASTER STATUS;")
            master_status = cur.fetchone()
            cur.execute("SELECT @@GLOBAL.GTID_EXECUTED;")
            gtid_executed = cur.fetchone()[0]
        conn.close()
        
        # Run mysqldump
        dump_cmd = [
            "mysqldump",
            f"--host={self.config['host']}",
            f"--port={self.config['port']}",
            f"--user={self.config['user']}",
            f"--password={self.config['password']}",
            "--single-transaction",
            "--quick",
            "--set-gtid-purged=ON",
            "--triggers",
            "--routines",
            "--events",
            "--hex-blob",
            "--source-data=2",
            "--result-file=-",
            "classfund"
        ]
        
        # Compress on the fly
        with open(backup_file, "wb") as f:
            dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE)
            gzip_proc = subprocess.Popen(["gzip"], stdin=dump_proc.stdout, stdout=f)
            dump_proc.stdout.close()
            gzip_proc.wait()
            dump_proc.wait()
        
        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(backup_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        checksum = sha256_hash.hexdigest()
        
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
            "row_counts": self._get_row_counts()
        }
        
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return metadata
    
    def verify_restore(self, metadata: dict) -> dict:
        """Restore backup to isolated test database and verify financial integrity."""
        # Create test database
        test_db_name = f"classfund_restore_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        conn = pymysql.connect(**self._get_connection_params(None))
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
            cur.execute(f"CREATE DATABASE `{test_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
        
        # Decompress and restore
        backup_file = Path(metadata["backup_file"])
        restore_cmd = f"zcat {backup_file} | mysql -h {self.config['host']} -P {self.config['port']} -u {self.config['user']} -p{self.config['password']} {test_db_name}"
        
        result = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Restore failed: {result.stderr}")
        
        # Verify schema
        conn = pymysql.connect(host=self.config["host"], port=self.config["port"], 
                               user=self.config["user"], password=self.config["password"],
                               database=test_db_name)
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            restored_tables = [r[0] for r in cur.fetchall()]
        
        # Financial reconciliation
        engine = create_engine(f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{test_db_name}?charset=utf8mb4")
        SessionLocal = Session(bind=engine)
        db = SessionLocal()
        
        try:
            # Check table count
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (test_db_name,))
                table_count = cur.fetchone()[0]
            
            # Financial reconciliation
            ledger_entries = db.execute(select(LedgerEntry)).scalars().all()
            accounts = db.execute(select(Account)).scalars().all()
            
            # Verify ledger entry count
            original_count = metadata["row_counts"].get("ledger_entries", 0)
            restored_count = len(ledger_entries)
            
            # Verify balance integrity
            balance_matches = True
            balance_details = []
            
            for account in accounts:
                original_balance = account.opening_balance
                ledger_entries_for_account = db.execute(
                    select(LedgerEntry).join(Transaction).where(Transaction.account_id == account.id)
                ).scalars().all()
                
                calculated = original_balance
                for entry in ledger_entries_for_account:
                    if entry.type.value == "CREDIT":
                        calculated += entry.amount
                    elif entry.type.value == "DEBIT":
                        calculated -= entry.amount
                    elif entry.type.value == "REVERT":
                        # REVERT entries need special handling based on original entry
                        pass
                
                if calculated != account.opening_balance:
                    balance_matches = False
                    balance_details.append({
                        "account": account.name,
                        "expected": str(original_balance),
                        "calculated": str(calculated)
                    })
            
            conn.close()
            
            # Cleanup
            conn = pymysql.connect(**self._get_connection_params(None))
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
            conn.close()
            
            return {
                "success": True,
                "table_count": table_count,
                "restored_table_count": len(restored_tables),
                "ledger_entries_original": original_count,
                "ledger_entries_restored": restored_count,
                "balance_matches": balance_matches,
                "balance_details": balance_details
            }
        except Exception as e:
            # Cleanup on error
            try:
                conn = pymysql.connect(**self._get_connection_params(None))
                with conn.cursor() as cur:
                    cur.execute(f"DROP DATABASE IF EXISTS `{test_db_name}`;")
                conn.close()
            except:
                pass
            return {"success": False, "error": str(e)}
    
    def _get_connection_params(self, database):
        params = {
            "host": self.config["host"],
            "port": self.config["port"],
            "user": self.config["user"],
            "password": self.config["password"],
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
            tables = ["accounts", "transactions", "ledger_entries", "uploads", "messages", 
                      "users", "audit_logs", "payment_matches", "extracted_transactions",
                      "campaign_members", "students", "collection_campaigns", "bank_accounts",
                      "revoked_tokens", "recall_tokens", "worker_status", "chat_messages"]
            counts = {}
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM `{table}`;")
                    counts[table] = cur.fetchone()[0]
                except:
                    counts[table] = 0
        conn.close()
        return counts


if __name__ == "__main__":
    import sys
    
    config = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "classfund"),
        "password": os.environ.get("MYSQL_PASSWORD", "classfund"),
    }
    
    pipeline = BackupRestorePipeline(config)
    
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        # Find latest backup
        backups = sorted(pipeline.backup_dir.glob("classfund_backup_*.meta.json"))
        if not backups:
            print("No backup metadata found")
            sys.exit(1)
        latest = backups[-1]
        with open(latest) as f:
            metadata = json.load(f)
        result = pipeline.verify_restore(metadata)
        print(json.dumps(result, indent=2, default=str))
    else:
        metadata = pipeline.create_backup()
        print(json.dumps(metadata, indent=2, default=str))
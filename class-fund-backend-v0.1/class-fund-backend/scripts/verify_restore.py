#!/usr/bin/env python3
"""
Disaster Recovery Verification Script for CLASS_FUND_WEB
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup_database import BackupRestorePipeline

if __name__ == "__main__":
    import os, json, argparse

    parser = argparse.ArgumentParser(description="Verify MySQL disaster recovery restore and ledger parity.")
    parser.add_argument("--backup-meta", type=str, default=None, help="Path to backup metadata .meta.json file")
    parser.add_argument("--host", type=str, default=os.environ.get("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "3306")))
    parser.add_argument("--user", type=str, default=os.environ.get("MYSQL_ADMIN_USER", os.environ.get("MYSQL_USER", "root")))
    parser.add_argument("--password", type=str, default=os.environ.get("MYSQL_ADMIN_PASSWORD", os.environ.get("MYSQL_PASSWORD", "000000")))
    args = parser.parse_args()

    config = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "password": args.password,
    }

    pipeline = BackupRestorePipeline(config)

    meta_file = None
    if args.backup_meta:
        meta_file = Path(args.backup_meta)
    else:
        meta_files = sorted(pipeline.backup_dir.glob("classfund_backup_*.meta.json"))
        if meta_files:
            meta_file = meta_files[-1]

    if not meta_file or not meta_file.exists():
        print(f"No existing backup metadata found. Creating fresh backup for verification...")
        metadata = pipeline.create_backup()
        meta_file = Path(metadata["backup_file"]).with_suffix("").with_suffix(".meta.json")

    with open(meta_file, encoding="utf-8") as f:
        metadata = json.load(f)

    result = pipeline.verify_restore(metadata)
    print(json.dumps(result, indent=2, default=str))

    if not result.get("success") or not result.get("balance_matches"):
        sys.exit(1)

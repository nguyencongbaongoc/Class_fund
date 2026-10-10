#!/usr/bin/env python3
"""
Wrapper for backup_database.py in root scripts directory.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "class-fund-backend-v0.1" / "class-fund-backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup_database import BackupRestorePipeline

if __name__ == "__main__":
    import os, json
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

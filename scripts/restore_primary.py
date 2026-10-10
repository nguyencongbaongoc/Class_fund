import gzip
import subprocess
import pymysql
from pathlib import Path

# Unset read_only temporarily on 3306 to restore data
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000')
with conn.cursor() as cur:
    cur.execute("STOP REPLICA;")
    cur.execute("RESET REPLICA;")
    cur.execute("SET GLOBAL super_read_only = OFF;")
    cur.execute("SET GLOBAL read_only = OFF;")
    cur.execute("DROP DATABASE IF EXISTS classfund_restore_test_20261010_060751;")
    cur.execute("CREATE DATABASE IF NOT EXISTS classfund CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
conn.close()

# Drop database and tables on 3308 too if test database remains
conn = pymysql.connect(host='127.0.0.1', port=3308, user='root', password='000000')
with conn.cursor() as cur:
    cur.execute("DROP DATABASE IF EXISTS classfund_restore_test_20261010_060751;")
conn.close()

# Find latest backup
backups = sorted(Path("backups").glob("classfund_backup_*.sql.gz"))
latest_backup = backups[-1]
print(f"Restoring {latest_backup} to 3306 classfund...")

mysql_bin = r"C:\Users\Nguyen Cong Thong\AppData\Local\classfund-mysql84\mysql-8.4.11-winx64\bin\mysql.exe"
restore_cmd = [
    mysql_bin,
    "--host=127.0.0.1",
    "--port=3306",
    "--user=root",
    "--password=000000",
    "classfund"
]

with gzip.open(latest_backup, "rb") as f_in:
    sql_text = f_in.read().decode("utf-8", errors="replace")

cleaned_lines = []
for line in sql_text.splitlines(keepends=True):
    if "@@GLOBAL.GTID_PURGED" in line:
        cleaned_lines.append(f"-- {line}")
    else:
        cleaned_lines.append(line)
cleaned_sql_bytes = "".join(cleaned_lines).encode("utf-8")

proc = subprocess.run(restore_cmd, input=cleaned_sql_bytes, capture_output=True)
if proc.returncode != 0:
    print("Restore error:", proc.stderr.decode("utf-8", errors="replace"))
else:
    print("Restore to 3306 successful!")

# Verify tables on 3306
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000', database='classfund')
with conn.cursor() as cur:
    cur.execute("SHOW TABLES;")
    tables = [r[0] for r in cur.fetchall()]
    print(f"3306 tables count: {len(tables)}")
conn.close()


import os
import subprocess
import pymysql
import time

MYSQL_BIN = r"C:\Users\Nguyen Cong Thong\AppData\Local\classfund-mysql84\mysql-8.4.11-winx64\bin\mysql.exe"
MYSQLDUMP = r"C:\Users\Nguyen Cong Thong\AppData\Local\classfund-mysql84\mysql-8.4.11-winx64\bin\mysqldump.exe"

print("Step 1: Setting up replication user on Primary (port 3307)...")
conn_pri = pymysql.connect(host="127.0.0.1", port=3307, user="root")
cur_pri = conn_pri.cursor()
cur_pri.execute("CREATE USER IF NOT EXISTS 'repl'@'127.0.0.1' IDENTIFIED BY 'replpassword';")
cur_pri.execute("ALTER USER 'repl'@'127.0.0.1' IDENTIFIED BY 'replpassword';")
cur_pri.execute("GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD ON *.* TO 'repl'@'127.0.0.1';")
cur_pri.execute("FLUSH PRIVILEGES;")
cur_pri.execute("SHOW BINARY LOG STATUS;")
row_master = cur_pri.fetchone()
print(f"Primary Binary Log Status: {row_master}")
conn_pri.commit()
conn_pri.close()

print("Step 2: Exporting Primary database with GTID coordinates...")
dump_path = r"C:\Users\Nguyen Cong Thong\AppData\Local\classfund-mysql84\repl_init.sql"
dump_cmd = [
    MYSQLDUMP,
    "-h", "127.0.0.1", "-P", "3307", "-u", "root",
    "--single-transaction",
    "--set-gtid-purged=ON",
    "--databases", "classfund",
    f"--result-file={dump_path}"
]
subprocess.run(dump_cmd, check=True)
print(f"Exported {os.path.getsize(dump_path)} bytes.")

print("Step 3: Loading database into Replica (port 3308)...")
# Disable super_read_only temporarily on replica to import initial dump
conn_rep = pymysql.connect(host="127.0.0.1", port=3308, user="root")
cur_rep = conn_rep.cursor()
cur_rep.execute("SET GLOBAL read_only = OFF;")
cur_rep.execute("SET GLOBAL super_read_only = OFF;")
conn_rep.commit()

# Import dump
restore_cmd = f'"{MYSQL_BIN}" -h 127.0.0.1 -P 3308 -u root < "{dump_path}"'
subprocess.run(restore_cmd, shell=True, check=True)

# Re-enable read_only and super_read_only on replica
cur_rep.execute("SET GLOBAL read_only = ON;")
cur_rep.execute("SET GLOBAL super_read_only = ON;")

# Reset replica if needed and configure source
cur_rep.execute("STOP REPLICA;")
cur_rep.execute("RESET REPLICA ALL;")
cur_rep.execute("""
    CHANGE REPLICATION SOURCE TO
        SOURCE_HOST='127.0.0.1',
        SOURCE_PORT=3307,
        SOURCE_USER='repl',
        SOURCE_PASSWORD='replpassword',
        SOURCE_AUTO_POSITION=1,
        GET_SOURCE_PUBLIC_KEY=1;
""")
cur_rep.execute("START REPLICA;")
conn_rep.commit()
time.sleep(2)

print("Step 4: Checking Replica status...")
cur_rep.execute("SHOW REPLICA STATUS;")
cols = [desc[0] for desc in cur_rep.description]
status_row = cur_rep.fetchone()
rep_dict = dict(zip(cols, status_row)) if status_row else {}

io_running = rep_dict.get("Replica_IO_Running")
sql_running = rep_dict.get("Replica_SQL_Running")
last_io_err = rep_dict.get("Last_IO_Error")
last_sql_err = rep_dict.get("Last_SQL_Error")
retrieved_gtid = rep_dict.get("Retrieved_Gtid_Set")
executed_gtid = rep_dict.get("Executed_Gtid_Set")

print(f"Replica_IO_Running: {io_running}")
print(f"Replica_SQL_Running: {sql_running}")
print(f"Last_IO_Error: {last_io_err}")
print(f"Last_SQL_Error: {last_sql_err}")
print(f"Retrieved_Gtid_Set: {retrieved_gtid}")
print(f"Executed_Gtid_Set: {executed_gtid}")

conn_rep.close()

if io_running == "Yes" and sql_running == "Yes":
    print("SUCCESS: GTID Replication is fully active and synchronized!")
else:
    print("WARNING: Replication did not start cleanly.")

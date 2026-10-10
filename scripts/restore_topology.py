import time
import pymysql

# 1. Ensure 3306 is primary (super_read_only = OFF)
conn_pri = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000')
with conn_pri.cursor() as cur:
    cur.execute("STOP REPLICA;")
    cur.execute("SET GLOBAL super_read_only = OFF;")
    cur.execute("SET GLOBAL read_only = OFF;")
conn_pri.commit()
conn_pri.close()
print("3306 set to read-write Primary.")

# 2. Point 3308 back to 3306 as replica
conn_rep = pymysql.connect(host='127.0.0.1', port=3308, user='root', password='000000')
with conn_rep.cursor() as cur:
    cur.execute("STOP REPLICA;")
    cur.execute("RESET REPLICA;")
    change_sql = """
        CHANGE REPLICATION SOURCE TO
            SOURCE_HOST='127.0.0.1',
            SOURCE_PORT=3306,
            SOURCE_USER='repl_user',
            SOURCE_PASSWORD='repl_password',
            SOURCE_AUTO_POSITION=1,
            GET_SOURCE_PUBLIC_KEY=1;
    """
    cur.execute(change_sql)
    cur.execute("START REPLICA;")
    cur.execute("SET GLOBAL read_only = ON;")
    cur.execute("SET GLOBAL super_read_only = ON;")
conn_rep.commit()

time.sleep(1)
with conn_rep.cursor() as cur:
    cur.execute("SHOW REPLICA STATUS;")
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    st = dict(zip(cols, row))
    print("3308 Replica_IO_Running:", st.get("Replica_IO_Running"))
    print("3308 Replica_SQL_Running:", st.get("Replica_SQL_Running"))
    print("3308 Seconds_Behind_Source:", st.get("Seconds_Behind_Source"))
conn_rep.close()


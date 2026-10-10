import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000')
with conn.cursor() as cur:
    cur.execute("STOP REPLICA;")
    cur.execute("RESET REPLICA;")
    for i in range(1, 21):
        gtid = f"f6f61fd0-c06e-11f1-ab28-d8bbc13b2fc2:{i}"
        try:
            cur.execute(f"SET GTID_NEXT = '{gtid}';")
            cur.execute("BEGIN;")
            cur.execute("COMMIT;")
        except Exception as e:
            print(f"Skipping {gtid}: {e}")
    cur.execute("SET GTID_NEXT = 'AUTOMATIC';")
conn.close()
print("GTID sync completed on 3306.")


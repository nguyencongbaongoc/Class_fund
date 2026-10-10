import pymysql

for port in [3306, 3308]:
    try:
        conn = pymysql.connect(host='127.0.0.1', port=port, user='root', password='000000')
        with conn.cursor() as cur:
            cur.execute("CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_password';")
            cur.execute("GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD ON *.* TO 'repl_user'@'%';")
            cur.execute("FLUSH PRIVILEGES;")
        conn.close()
        print(f"Configured repl_user on port {port}")
    except Exception as e:
        print(f"Error on {port}: {e}")


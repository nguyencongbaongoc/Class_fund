import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3307,
    user='classfund',
    password='classfundpassword',
    database='classfund'
)
cur = conn.cursor()

# 1. Total tables
cur.execute("SHOW TABLES;")
tables = [r[0] for r in cur.fetchall()]
print(f"Total tables: {len(tables)}")
print(f"Tables list: {sorted(tables)}\n")

expected_18 = [
    'accounts', 'audit_logs', 'bank_accounts', 'campaign_members',
    'chat_messages', 'collection_campaigns', 'extracted_transactions',
    'idempotency_keys', 'ledger_entries', 'messages', 'payment_matches',
    'recall_tokens', 'revoked_tokens', 'students', 'transactions',
    'uploads', 'users', 'worker_status'
]
app_tables = [t for t in tables if t != 'alembic_version']
missing = set(expected_18) - set(app_tables)
extra = set(app_tables) - set(expected_18)
print(f"All 18 expected tables present: {len(missing) == 0 and len(extra) == 0}")
if missing:
    print(f"Missing: {missing}")
if extra:
    print(f"Extra: {extra}")

# 2. Engines & Collation
cur.execute("""
    SELECT TABLE_NAME, ENGINE, TABLE_COLLATION 
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = 'classfund'
    ORDER BY TABLE_NAME
""")
non_innodb = []
non_utf8mb4 = []
for row in cur.fetchall():
    t_name, engine, collation = row
    if engine != 'InnoDB':
        non_innodb.append((t_name, engine))
    if not collation.startswith('utf8mb4'):
        non_utf8mb4.append((t_name, collation))
print(f"All tables InnoDB: {len(non_innodb) == 0}")
print(f"All tables utf8mb4: {len(non_utf8mb4) == 0}")

# 3. Foreign Keys count
cur.execute("""
    SELECT COUNT(*) 
    FROM information_schema.TABLE_CONSTRAINTS 
    WHERE CONSTRAINT_SCHEMA = 'classfund' AND CONSTRAINT_TYPE = 'FOREIGN KEY'
""")
fk_count = cur.fetchone()[0]
print(f"Total foreign key constraints: {fk_count}")

# 4. Check decimal column types
cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'classfund' AND DATA_TYPE = 'decimal'
    ORDER BY TABLE_NAME, COLUMN_NAME
""")
print("\nDECIMAL columns:")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}: {row[2]}")

# 5. Check datetime column types
cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'classfund' AND DATA_TYPE = 'datetime'
    ORDER BY TABLE_NAME, COLUMN_NAME
""")
print("\nDATETIME columns:")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}: {row[2]}")

# 6. Check unique constraints
cur.execute("""
    SELECT TABLE_NAME, CONSTRAINT_NAME
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = 'classfund' AND CONSTRAINT_TYPE = 'UNIQUE'
    ORDER BY TABLE_NAME, CONSTRAINT_NAME
""")
print("\nUNIQUE constraints:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Phase 8 Replica Deployment Report

## Overview
Deployment and configuration of MySQL 8.4 GTID Source-Replica cluster for CLASS_FUND_WEB.

## Cluster Topology

| Component | Host | Port | Server ID | Role |
|-----------|------|------|-----------|------|
| Primary (Source) | 127.0.0.1 | 3306 | 1 | Primary (Read-Write) |
| Replica | 127.0.0.1 | 3308 | 2 | Replica (Read-Only) |

## Primary Configuration (mysql-primary)

### my.ini (Primary)
```ini
[mysqld]
server-id=1
port=3306
bind-address=0.0.0.0
named-pipe=ON
socket=MYSQL
gtid-mode=ON
enforce-gtid-consistency=ON
log-bin=mysql-bin
binlog-format=ROW
binlog-row-image=FULL
sync-binlog=1
log-replica-updates=ON
log-bin=mysql-bin
sync-binlog=1
binlog-row-image=FULL
log-replica-updates=ON
```

### GTID Status
```sql
SHOW MASTER STATUS;
+------------------+----------+--------------+------------------+-------------------------------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB | Executed_Gtid_Set                         |
+------------------+----------+--------------+------------------+-------------------------------------------+
| PC-bin.000005    | 384503   |              |                  | 5e10d807-bfeb-11f1-9cc2-d8bbc13b2fc2:1-520 |
+------------------+----------+--------------+------------------+-------------------------------------------+

SHOW VARIABLES LIKE 'gtid_mode';
+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| gtid_mode     | ON    |
+---------------+-------+

SHOW VARIABLES LIKE 'enforce_gtid_consistency';
+--------------------------+-------+
| Variable_name            | Value |
+--------------------------+-------+
| enforce_gtid_consistency | ON    |
+--------------------------+-------+
```

### Replication User
```sql
CREATE USER 'repl_user'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;
```

## Replica Configuration (mysql-replica)

### my.ini (Replica)
```ini
[mysqld]
server-id=2
port=3308
bind-address=0.0.0.0
named-pipe=ON
socket=MYSQL2
gtid-mode=ON
enforce-gtid-consistency=ON
log-bin=mysql-bin
binlog-format=ROW
binlog-row-image=FULL
sync-binlog=1
log-replica-updates=ON
read-only=ON
super-read-only=ON
relay-log=mysql-relay-bin
relay-log-index=mysql-relay-bin.index
relay-log-recovery=ON
relay-log-purge=ON
```

### Replication Configuration
```sql
STOP REPLICA;
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='127.0.0.1',
    SOURCE_PORT=3306,
    SOURCE_USER='repl_user',
    SOURCE_PASSWORD='repl_password',
    SOURCE_AUTO_POSITION=1,
    GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
```

## Replication Status

### Replica Error Log Evidence
```
2026-10-10T03:58:07.234585Z 14 [System] [MY-010597] [Repl] 'CHANGE REPLICATION SOURCE FOR CHANNEL '' executed'.
Previous state source_host='', source_port= 3306, source_log_file='', source_log_pos= 4, source_bind=''.
New state source_host='127.0.0.1', source_port= 3306, source_log_file='', source_log_pos= 4, source_bind=''.

2026-10-10T03:58:07.302840Z 15 [System] [MY-014002] [Repl] Replica receiver thread for channel '': connected to source 'repl_user@127.0.0.1:3306' with server_uuid=5e10d807-bfeb-11f1-9cc2-d8bbc13b2fc2, server_id=1. Starting GTID-based replication.
```

## Replication Verification Commands

```sql
-- On Replica
SHOW REPLICA STATUS\G
-- Expected:
-- Replica_IO_Running: Yes
-- Replica_SQL_Running: Yes
-- Seconds_Behind_Source: 0
-- Retrieved_Gtid_Set: 5e10d807-bfeb-11f1-9cc2-d8bbc13b2fc2:1-520
-- Executed_Gtid_Set: 5e10d807-bfeb-11f1-9cc2-d8bbc13b2fc2:1-520
```

## GTID Verification

### Primary Variables
```sql
SHOW VARIABLES LIKE 'gtid_mode';           -- ON
SHOW VARIABLES LIKE 'enforce_gtid_consistency'; -- ON
SHOW VARIABLES LIKE 'log_bin';             -- ON
SHOW VARIABLES LIKE 'server_id';           -- 1
```

### Replica Variables
```sql
SHOW VARIABLES LIKE 'gtid_mode';           -- ON
SHOW VARIABLES LIKE 'enforce_gtid_consistency'; -- ON
SHOW VARIABLES LIKE 'log_bin';             -- ON
SHOW VARIABLES LIKE 'server_id';           -- 2
SHOW VARIABLES LIKE 'read_only';           -- ON
SHOW VARIABLES LIKE 'super_read_only';     -- ON
```

## Replication Bootstrap Script

### init_replication.sh
```bash
#!/bin/bash
# MySQL GTID Replication Bootstrap Script

# 1. Create replication user on Primary
mysql -h mysql-primary -u root -p${MYSQL_ROOT_PASSWORD} <<EOF
CREATE USER IF NOT EXISTS '${MYSQL_REPLICATION_USER}'@'%' IDENTIFIED BY '${MYSQL_REPLICATION_PASSWORD}';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO '${MYSQL_REPLICATION_USER}'@'%';
FLUSH PRIVILEGES;
EOF

# 2. Configure Replica
mysql -u root -p${MYSQL_ROOT_PASSWORD} <<EOF
STOP REPLICA;
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='mysql-primary',
    SOURCE_USER='${MYSQL_REPLICATION_USER}',
    SOURCE_PASSWORD='${MYSQL_REPLICATION_PASSWORD}',
    SOURCE_AUTO_POSITION=1,
    GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
EOF
```

## Docker Compose Integration

```yaml
services:
  mysql-primary:
    image: mysql:8.4
    platform: linux/amd64
    environment:
      MYSQL_DATABASE: classfund
      MYSQL_USER: classfund
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_REPLICATION_USER: ${MYSQL_REPLICATION_USER}
      MYSQL_REPLICATION_PASSWORD: ${MYSQL_REPLICATION_PASSWORD}
    command:
      - --server-id=1
      - --gtid-mode=ON
      - --enforce-gtid-consistency=ON
      - --log-bin=mysql-bin
      - --binlog-format=ROW
      - --sync-binlog=1
      - --log-replica-updates=ON
    volumes:
      - classfund_mysql_primary_data:/var/lib/mysql
      - ./mysql/scripts:/docker-entrypoint-initdb.d/scripts:ro

  mysql-replica:
    image: mysql:8.4
    platform: linux/amd64
    environment:
      MYSQL_DATABASE: classfund
      MYSQL_USER: classfund
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_REPLICATION_USER: ${MYSQL_REPLICATION_USER}
      MYSQL_REPLICATION_PASSWORD: ${MYSQL_REPLICATION_PASSWORD}
    command:
      - --server-id=2
      - --gtid-mode=ON
      - --enforce-gtid-consistency=ON
      - --log-bin=mysql-bin
      - --binlog-format=ROW
      - --sync-binlog=1
      - --log-replica-updates=ON
      - --read-only=ON
      - --super-read-only=ON
      - --relay-log=mysql-relay-bin
    volumes:
      - classfund_mysql_replica_data:/var/lib/mysql
    depends_on:
      mysql-primary:
        condition: service_healthy
```

## Verification Checklist

- [ ] Primary server_id = 1, gtid_mode = ON
- [ ] Replica server_id = 2, gtid_mode = ON
- [ ] Replication user created on Primary
- [ ] CHANGE REPLICATION SOURCE executed on Replica
- [ ] Replica_IO_Running = Yes
- [ ] Replica_SQL_Running = Yes
- [ ] Seconds_Behind_Source = 0
- [ ] GTID sets match between Primary and Replica
- [ ] Direct writes to Replica rejected (Error 1290)
- [ ] Primary accepts writes, Replica rejects writes
- [ ] Test data inserted on Primary appears on Replica within < 1s
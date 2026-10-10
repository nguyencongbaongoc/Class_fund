# Phase 7 MySQL Cluster & GTID Configuration

## Overview
Documentation of the MySQL 8.4+ GTID Source-Replica cluster configuration for CLASS_FUND_WEB.

## Cluster Topology

### Primary (Source) - mysql-primary
- **Host:** 127.0.0.1:3306
- **Server ID:** 1
- **GTID Mode:** ON
- **Binary Logging:** ROW format, sync_binlog=1
- **User:** classfund/classfund
- **Root:** root/000000

### Replica - mysql-replica
- **Host:** 127.0.0.1:3308
- **Server ID:** 2
- **GTID Mode:** ON
- **Read Only:** super_read_only=ON
- **User:** classfund/classfund
- **Root:** root/000000

## GTID Configuration

### Primary Configuration (mysql-primary)
```ini
[mysqld]
server-id=1
gtid_mode=ON
enforce_gtid_consistency=ON
binlog_format=ROW
log_bin=mysql-bin
sync_binlog=1
binlog_row_image=FULL
log_replica_updates=ON
```

### Replica Configuration (mysql-replica)
```ini
[mysqld]
server-id=2
gtid_mode=ON
enforce_gtid_consistency=ON
binlog_format=ROW
log_bin=mysql-bin
sync_binlog=1
log_replica_updates=ON
read_only=ON
super_read_only=ON
relay_log=mysql-relay-bin
```

## Replication Bootstrap Process

### 1. Primary Initialization
```sql
-- Run on primary
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;
```

### 2. Replica Configuration
```sql
-- Run on replica
STOP REPLICA;
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='mysql-primary',
    SOURCE_USER='repl_user',
    SOURCE_PASSWORD='repl_password',
    SOURCE_AUTO_POSITION=1,
    GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
```

## Verification Commands

### Check Primary Status
```sql
SHOW MASTER STATUS;
SHOW VARIABLES LIKE 'gtid_mode';
SHOW VARIABLES LIKE 'enforce_gtid_consistency';
SHOW VARIABLES LIKE 'log_bin';
```

### Check Replica Status
```sql
SHOW REPLICA STATUS\G
```

**Expected Output:**
```
Replica_IO_Running: Yes
Replica_SQL_Running: Yes
Seconds_Behind_Source: 0
```

## Docker Compose Integration

The `docker-compose.yml` defines both services with:
- Shared `mysql/scripts` volume for bootstrap scripts
- Proper environment variables for replication credentials
- Health checks for both instances
- Depends_on with service_healthy conditions

## GTID Readiness Verification

Run test:
```bash
pytest tests/test_mysql_qualification.py::test_13_three_machine_gtid_readiness -v
```

**Verification Criteria:**
- gtid_mode = ON
- enforce_gtid_consistency = ON
- log_bin = ON
- server_id >= 1

## Replication Lag Monitoring

```sql
-- On replica
SHOW REPLICA STATUS;
-- Check: Seconds_Behind_Source = 0

-- On primary
SHOW MASTER STATUS;
```

## Failover Procedure

### Promote Replica to Primary
```sql
-- On replica
STOP REPLICA;
SET GLOBAL super_read_only = OFF;
SET GLOBAL read_only = OFF;
```

### Demote Primary to Replica
```sql
-- On old primary
SET GLOBAL read_only = ON;
SET GLOBAL super_read_only = ON;

-- On new primary (old replica)
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='old-primary-host',
    SOURCE_USER='repl_user',
    SOURCE_PASSWORD='repl_password',
    SOURCE_AUTO_POSITION=1;
START REPLICA;
```

## Network Configuration

- **Network:** `classfund_network` (bridge)
- **Internal DNS:** mysql-primary, mysql-replica
- **External Ports:** 3306 (primary), 3307 (replica external)

## Health Checks

Both instances have healthcheck:
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "classfund", "-p${MYSQL_PASSWORD}"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 30s
```
# Phase 8 Automated Failover Specification

## Overview
Automated failover mechanism for MySQL GTID Source-Replica cluster to ensure high availability without financial data loss.

## Architecture

```
┌─────────────────┐     Health Check (2-3s)      ┌─────────────────┐
│  Failover       │ ◀──────────────────────────▶ │   mysql-primary │
│  Manager        │                              │   (Port 3306)   │
│  (Daemon)       │                              │  server_id=1    │
└────────┬────────┘                              └────────┬────────┘
         │                                              │
         │ Failover Trigger (3 consecutive failures)    │
         ▼                                              ▼
┌─────────────────┐     Promote Replica                ┌─────────────────┐
│  Application    │ ◀────────────────────────────────── │  mysql-replica  │
│  (Backend)      │     Update Connection Target       │   (Port 3308)   │
│  Connection     │                                    │  server_id=2    │
└─────────────────┘                                    └─────────────────┘
```

## Failover Manager Design

### `scripts/failover_manager.py`

```python
#!/usr/bin/env python3
"""
Automated MySQL Failover Manager
Monitors Primary health and orchestrates failover to Replica.
"""

import asyncio
import logging
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pymysql
import redis

logger = logging.getLogger(__name__)


@dataclass
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str = "classfund"


@dataclass
class FailoverConfig:
    primary: MySQLConfig
    replica: MySQLConfig
    check_interval: int = 3  # seconds
    failure_threshold: int = 3  # consecutive failures
    check_timeout: int = 5  # seconds
    promotion_timeout: int = 30  # seconds
    replication_lag_threshold: int = 5  # seconds


class FailoverManager:
    def __init__(self, config: FailoverConfig):
        self.config = config
        self.running = False
        self.consecutive_failures = 0
        self.failover_in_progress = False
        self._primary_conn: Optional[pymysql.Connection] = None
        self._replica_conn: Optional[pymysql.Connection] = None
        
    async def start(self):
        """Start the failover manager."""
        self.running = True
        logger.info("Failover Manager started")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        while self.running:
            await self._health_check_cycle()
            await asyncio.sleep(self.config.check_interval)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _health_check_cycle(self):
        """Perform one health check cycle."""
        if self.failover_in_progress:
            return
            
        primary_healthy = await self._check_primary_health()
        
        if not primary_healthy:
            self.consecutive_failures += 1
            logger.warning(f"Primary health check failed ({self.consecutive_failures}/{self.config.failure_threshold})")
            
            if self.consecutive_failures >= self.config.failure_threshold:
                await self._trigger_failover()
        else:
            self.consecutive_failures = 0
    
    async def _check_primary_health(self) -> bool:
        """Check if Primary is healthy."""
        try:
            conn = pymysql.connect(
                host=self.config.primary.host,
                port=self.config.primary.port,
                user=self.config.primary.user,
                password=self.config.primary.password,
                database=self.config.primary.database,
                connect_timeout=self.config.check_timeout
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()
            conn.close()
            return result is not None and result[0] == 1
        except Exception as e:
            logger.debug(f"Primary health check failed: {e}")
            return False
    
    async def _trigger_failover(self):
        """Execute failover to Replica."""
        logger.critical("FAILOVER TRIGGERED: Primary unreachable, promoting Replica")
        self.failover_in_progress = True
        
        try:
            # 1. Verify Replica has caught up
            if not await self._verify_replica_ready():
                logger.error("Replica not ready for promotion, aborting failover")
                return
            
            # 2. Promote Replica
            await self._promote_replica()
            
            # 3. Update application connection (notify backend)
            await self._notify_backend_failover()
            
            # 4. Log failover event
            self._log_failover_event()
            
            logger.info("FAILOVER COMPLETED SUCCESSFULLY")
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
        finally:
            self.failover_in_progress = False
            self.consecutive_failures = 0
    
    async def _verify_replica_ready(self) -> bool:
        """Verify Replica is caught up and ready for promotion."""
        try:
            conn = pymysql.connect(
                host=self.config.replica.host,
                port=self.config.replica.port,
                user=self.config.replica.user,
                password=self.config.replica.password,
                database=self.config.replica.database,
                connect_timeout=self.config.check_timeout
            )
            with conn.cursor() as cur:
                # Check replication status
                cur.execute("SHOW REPLICA STATUS;")
                cols = [desc[0] for desc in cur.description]
                status = dict(zip(cols, cur.fetchone()))
                
                if status.get("Replica_IO_Running") != "Yes":
                    logger.error(f"Replica_IO_Running: {status.get('Replica_IO_Running')}")
                    return False
                
                if status.get("Replica_SQL_Running") != "Yes":
                    logger.error(f"Replica_SQL_Running: {status.get('Replica_SQL_Running')}")
                    return False
                
                seconds_behind = status.get("Seconds_Behind_Source")
                if seconds_behind is not None and seconds_behind > self.config.replication_lag_threshold:
                    logger.error(f"Replication lag too high: {seconds_behind}s")
                    return False
                
                # Check GTID synchronization
                cur.execute("SELECT @@GLOBAL.GTID_EXECUTED;")
                replica_gtid = cur.fetchone()[0]
                logger.info(f"Replica GTID Executed: {replica_gtid}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Replica readiness check failed: {e}")
            return False
    
    async def _promote_replica(self):
        """Promote Replica to Primary."""
        logger.info("Promoting Replica to Primary...")
        
        conn = pymysql.connect(
            host=self.config.replica.host,
            port=self.config.replica.port,
            user=self.config.replica.user,
            password=self.config.replica.password,
            database=self.config.replica.database,
            connect_timeout=self.config.promotion_timeout
        )
        
        try:
            with conn.cursor() as cur:
                # Stop replication
                cur.execute("STOP REPLICA;")
                logger.info("Replica stopped")
                
                # Promote to read-write
                cur.execute("SET GLOBAL super_read_only = OFF;")
                cur.execute("SET GLOBAL read_only = OFF;")
                logger.info("Replica promoted to read-write")
                
                conn.commit()
        finally:
            conn.close()
    
    async def _notify_backend_failover(self):
        """Notify backend of failover via Redis or HTTP."""
        # Option 1: Redis Pub/Sub
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            await r.publish("system:failover", json.dumps({
                "event": "FAILOVER_COMPLETED",
                "new_primary": "127.0.0.1:3308",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
            logger.info("Failover notification published to Redis")
        except Exception as e:
            logger.warning(f"Failed to publish failover event to Redis: {e}")
    
    def _log_failover_event(self):
        """Log failover event to audit trail."""
        logger.critical(f"FAILOVER EVENT: {datetime.now(timezone.utc).isoformat()} - "
                       f"Primary demoted, Replica promoted. "
                       f"New Primary: {self.config.replica.host}:{self.config.replica.port}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = FailoverConfig(
        primary=MySQLConfig(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="000000",
            database="classfund"
        ),
        replica=MySQLConfig(
            host="127.0.0.1",
            port=3308,
            user="root",
            password="000000",
            database="classfund"
        )
    )
    
    manager = FailoverManager(config)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
```

## Integration with Backend

### Backend Connection Management

```python
# app/core/database.py
import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    def __init__(self):
        self.primary_url = os.getenv("DATABASE_URL_PRIMARY", "mysql+pymysql://...")
        self.replica_url = os.getenv("DATABASE_URL_REPLICA", "mysql+pymysql://...")
        self.current_url = self.primary_url
        self._engine = None
    
    async def get_engine(self):
        if self._engine is None:
            self._engine = create_async_engine(
                self.current_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        return self._engine
    
    async def failover_to_replica(self):
        """Switch to replica for read operations."""
        if self.current_url != self.replica_url:
            self.current_url = self.replica_url
            await self._engine.dispose()
            self._engine = None
            logger.info("Switched database connection to Replica")
    
    async def failback_to_primary(self):
        """Switch back to primary after recovery."""
        if self.current_url != self.primary_url:
            self.current_url = self.primary_url
            await self._engine.dispose()
            self._engine = None
            logger.info("Switched database connection back to Primary")
```

### Redis Pub/Sub Failover Notification

```python
# In failover_manager.py
async def _notify_backend_failover(self):
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        await r.publish("system:failover", json.dumps({
            "event": "FAILOVER_COMPLETED",
            "new_primary": f"{self.config.replica.host}:{self.config.replica.port}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "old_primary": f"{self.config.primary.host}:{self.config.primary.port}"
        }))
    except Exception as e:
        logger.warning(f"Failed to publish failover event: {e}")
```

## Automated Failover Test

```python
# tests/test_automated_failover.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.failover_manager import FailoverManager, MySQLConfig, FailoverConfig

@pytest.mark.asyncio
async def test_failover_promotes_replica():
    """Test that failover correctly promotes replica."""
    config = FailoverConfig(
        primary=MySQLConfig(host="127.0.0.1", port=3306, user="root", password="test"),
        replica=MySQLConfig(host="127.0.0.1", port=3308, user="root", password="test"),
    )
    
    manager = FailoverManager(config)
    
    # Mock health checks
    with patch.object(manager, '_check_primary_health', new_callable=AsyncMock) as mock_check:
        mock_check.side_effect = [False, False, False]  # 3 failures
        
        with patch.object(manager, '_verify_replica_ready', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True
            
            with patch.object(manager, '_promote_replica', new_callable=AsyncMock) as mock_promote:
                mock_promote.return_value = None
                
                with patch.object(manager, '_notify_backend_failover', new_callable=AsyncMock):
                    # Trigger failover
                    manager.consecutive_failures = 2
                    await manager._health_check_cycle()
                    
                    assert manager.failover_in_progress == True
                    mock_promote.assert_called_once()


@pytest.mark.asyncio
async def test_failover_aborts_if_replica_not_ready():
    """Failover should abort if replica is not caught up."""
    config = FailoverConfig(
        primary=MySQLConfig(host="127.0.0.1", port=3306, user="root", password="test"),
        replica=MySQLConfig(host="127.0.0.1", port=3308, user="root", password="test"),
    )
    
    manager = FailoverManager(config)
    
    with patch.object(manager, '_check_primary_health', return_value=False):
        with patch.object(manager, '_verify_replica_ready', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = False  # Replica not ready
            
            manager.consecutive_failures = 2
            await manager._health_check_cycle()
            
            # Failover should not proceed
            assert manager.failover_in_progress == False


# Integration test with real MySQL
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_failover_integration():
    """Integration test with real MySQL instances."""
    pytest.skip("Requires running MySQL Primary/Replica cluster")
    
    config = FailoverConfig(
        primary=MySQLConfig(
            host="127.0.0.1", port=3306,
            user="root", password="000000", database="classfund"
        ),
        replica=MySQLConfig(
            host="127.0.0.1", port=3308,
            user="root", password="000000", database="classfund"
        ),
    )
    
    manager = FailoverManager(config)
    
    # 1. Verify Primary is healthy
    assert await manager._check_primary_health() == True
    
    # 2. Verify Replica is ready
    assert await manager._verify_replica_ready() == True
    
    # 3. Simulate primary failure (stop primary)
    # ... stop primary container ...
    
    # 4. Trigger failover
    manager.consecutive_failures = 3
    await manager._trigger_failover()
    
    # 5. Verify failover completed
    # ... check that Replica is now read-write ...
```

## Failover Telemetry

### Audit Log Entry
```sql
INSERT INTO audit_logs (actor_id, action, entity_type, entity_id, after_data, created_at)
VALUES ('system', 'FAILOVER', 'mysql_cluster', 'primary_to_replica', 
        '{"old_primary": "127.0.0.1:3306", "new_primary": "127.0.0.1:3308", "trigger": "health_check_failure"}',
        NOW());
```

### Prometheus Metrics
```python
from prometheus_client import Counter, Gauge, Histogram

failover_total = Counter('mysql_failover_total', 'Total number of failovers', ['result'])
failover_duration = Histogram('mysql_failover_duration_seconds', 'Failover duration')
replication_lag = Gauge('mysql_replication_lag_seconds', 'Replication lag in seconds')
primary_healthy = Gauge('mysql_primary_healthy', 'Primary health status (1=healthy, 0=unhealthy)')
```

## Deployment

### Systemd Service (Linux)
```ini
# /etc/systemd/system/mysql-failover-manager.service
[Unit]
Description=MySQL Failover Manager
After=network.target mysql.service redis.service
Requires=mysql.service redis.service

[Service]
Type=simple
User=mysql
ExecStart=/usr/bin/python3 /opt/classfund/scripts/failover_manager.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Windows Service (NSSM)
```cmd
nssm install ClassFundFailoverManager "C:\Python312\python.exe" "C:\classfund\scripts\failover_manager.py"
nssm set ClassFundFailoverManager AppDirectory C:\classfund\scripts
nssm set ClassFundFailoverManager AppStdout C:\classfund\logs\failover.log
nssm set ClassFundFailoverManager AppStderr C:\classfund\logs\failover_error.log
nssm start ClassFundFailoverManager
```

## Verification Checklist

- [ ] Failover Manager starts and connects to both Primary and Replica
- [ ] Health check runs every 3 seconds
- [ ] 3 consecutive failures trigger failover
- [ ] Replica promoted to read-write (super_read_only=OFF)
- [ ] Replication stopped on promoted Replica
- [ ] Backend notified of new Primary endpoint
- [ ] Audit log entry created
- [ ] Prometheus metrics updated
- [ ] Original Primary demoted (read_only=ON) after recovery
- [ ] Replication re-established in reverse direction
#!/bin/bash
# MySQL GTID Replication Bootstrap Script
# This script runs on the replica to configure and start replication from the primary

set -e

# Wait for primary to be ready
echo "Waiting for primary MySQL to be ready..."
until mysqladmin ping -h mysql-primary -u root -p"${MYSQL_ROOT_PASSWORD}" --silent; do
    echo "Waiting for primary..."
    sleep 5
done

echo "Primary is ready. Configuring replication..."

# Create replication user on primary
mysql -h mysql-primary -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
CREATE USER IF NOT EXISTS '${MYSQL_REPLICATION_USER}'@'%' IDENTIFIED BY '${MYSQL_REPLICATION_PASSWORD}';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO '${MYSQL_REPLICATION_USER}'@'%';
FLUSH PRIVILEGES;
EOF

echo "Replication user created on primary."

# Wait a moment for privileges to propagate
sleep 2

# Configure replica to connect to primary
# Note: We use GTID auto-positioning
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
STOP REPLICA;
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='mysql-primary',
    SOURCE_USER='${MYSQL_REPLICATION_USER}',
    SOURCE_PASSWORD='${MYSQL_REPLICATION_PASSWORD}',
    SOURCE_AUTO_POSITION=1,
    GET_SOURCE_PUBLIC_KEY=1;
START REPLICA;
EOF

echo "Replication configured and started."

# Wait for replication to catch up
sleep 5

# Verify replication status
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW REPLICA STATUS\G"

# Check if replication is running
REPLICA_IO=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -sN -e "SHOW REPLICA STATUS" | awk -F'\t' '{print $11}')
REPLICA_SQL=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -sN -e "SHOW REPLICA STATUS" | awk -F'\t' '{print $12}')

if [ "$REPLICA_IO" = "Yes" ] && [ "$REPLICA_SQL" = "Yes" ]; then
    echo "SUCCESS: Replication is running (IO: $REPLICA_IO, SQL: $REPLICA_SQL)"
    exit 0
else
    echo "WARNING: Replication may not be fully running yet (IO: $REPLICA_IO, SQL: $REPLICA_SQL)"
    exit 1
fi
#!/bin/bash
set -e

# Create multiple databases for different microservices
databases=("userdb" "productdb" "orderdb" "paymentdb" "notificationdb")

for db in "${databases[@]}"; do
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE $db;
    GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
done

echo "All databases created successfully"

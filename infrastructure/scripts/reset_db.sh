#!/usr/bin/env bash
# reset_db.sh — Drop and recreate the stockagent database.
# WARNING: Destroys all data. Development use only.
# Usage:  bash infrastructure/scripts/reset_db.sh

set -euo pipefail

echo "[!] This will DELETE all data in the stockagent database."
read -r -p "    Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS stockagent;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE stockagent;"
docker compose exec postgres psql -U postgres -d stockagent \
    -f /docker-entrypoint-initdb.d/01_init.sql

echo "[+] Database reset complete."

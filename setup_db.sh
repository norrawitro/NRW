#!/bin/bash
# NRW Setup Script — รันครั้งเดียวหลังติดตั้ง PostgreSQL
# Usage: bash setup_db.sh

set -e

echo "=== NRW Database Setup ==="

# Load environment variables
if [ -f .env ]; then
  source .env
fi

# ใช้ค่าจาก environment หรือ prompt
DB_USER="${NRW_DB_USER:-nrw_user}"
DB_NAME="${NRW_DB_NAME:-nrw_db}"

if [ -z "$NRW_DB_PASSWORD" ]; then
  echo "⚠️  NRW_DB_PASSWORD not set"
  read -sp "Enter database password: " DB_PASSWORD
  echo
else
  DB_PASSWORD="$NRW_DB_PASSWORD"
fi

# 1. สร้าง PostgreSQL user และ database
sudo -u postgres psql <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  ELSE
    ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "✅ Database ready: $DB_NAME"

# 2. สร้าง .env จาก example ถ้ายังไม่มี
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env created from .env.example"
  echo "⚠️  กรุณาแก้ไขค่าใน .env ก่อนรัน server"
else
  echo "⚠️  .env already exists, skipping"
fi

echo "=== Setup complete! ==="
echo "1. แก้ไข .env ให้ถูกต้อง"
echo "2. รัน server ด้วย: bash start.sh"

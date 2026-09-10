#!/bin/bash
# NRW Setup Script — รันครั้งเดียวหลังติดตั้ง PostgreSQL
# Usage: bash setup_db.sh

set -e

echo "=== NRW Database Setup ==="

# 1. สร้าง PostgreSQL user และ database
sudo -u postgres psql <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nrw_user') THEN
    CREATE USER nrw_user WITH PASSWORD 'nrw_password_2024';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE nrw_db OWNER nrw_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nrw_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE nrw_db TO nrw_user;
EOF

echo "✅ Database ready: nrw_db"

# 2. สร้าง .env จาก example
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i 's/nrw_user:password/nrw_user:nrw_password_2024/' .env
  echo "✅ .env created"
else
  echo "⚠️  .env already exists, skipping"
fi

echo "=== Setup complete! ==="
echo "รัน server ด้วย: bash start.sh"

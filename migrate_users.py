"""Migrate users table: add missing columns"""
from app.database import engine
from sqlalchemy import text

migrations = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100) NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS note TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE",
]

with engine.connect() as conn:
    for sql in migrations:
        conn.execute(text(sql))
        print(f"OK: {sql[:60]}...")
    conn.commit()

print("\nMigration complete!")

# Verify
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
    ))
    print("Columns now:", [r[0] for r in result])

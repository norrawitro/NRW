"""ลบ test rows ที่สร้างตอนทดสอบ POST /iot/data (device_id='test-dev2')"""
import os
from dotenv import load_dotenv

load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("DELETE FROM sensor_data WHERE device_id='test-dev2'")
print("deleted:", cur.rowcount)
conn.commit()
cur.execute("SELECT count(*) FROM sensor_data")
print("rows left:", cur.fetchone()[0])
conn.close()

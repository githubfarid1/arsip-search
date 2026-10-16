#!/bin/bash
set -e

echo "=== Arsip Search API Entry Point ==="

# Wait for MySQL to be ready
echo "⏳ Waiting for MySQL at ${DB_HOST:-host.docker.internal}:${DB_PORT:-3307}..."
python3 -c "
import time, os, sys
import pymysql

host = os.getenv('DB_HOST', 'host.docker.internal')
port = int(os.getenv('DB_PORT', '3307'))
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', 'password')
database = os.getenv('DB_NAME', 'arsip_bws')

max_retries = 30
for i in range(max_retries):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset='utf8mb4')
        conn.close()
        print('✅ MySQL is ready!')
        sys.exit(0)
    except Exception as e:
        print(f'  Attempt {i+1}/{max_retries}: MySQL not ready yet ({e})')
        time.sleep(2)

print('❌ MySQL did not become ready in time')
sys.exit(1)
"

echo "🚀 Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8888 "$@"
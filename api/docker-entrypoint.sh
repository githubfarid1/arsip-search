#!/bin/bash
set -e

echo "=== Arsip Search API Entry Point ==="

# Wait for PDF mount to be ready (NAS from another PC may mount late).
# Exit on timeout so Docker restarts and re-resolves the bind mount.
echo "⏳ Waiting for PDF path at ${PDF_BASE_PATH:-/pdfs/arsip_tata}..."
python3 -c "
import os, sys, time

path = os.getenv('PDF_BASE_PATH', '/pdfs/arsip_tata')
timeout = int(os.getenv('PDF_WAIT_TIMEOUT', '30'))
interval = 2
deadline = time.time() + timeout

while time.time() < deadline:
    try:
        if os.path.isdir(path) and os.listdir(path):
            print(f'✅ PDF path ready: {path}')
            sys.exit(0)
    except Exception as e:
        print(f'  PDF path not ready: {e}')
    time.sleep(interval)

print(f'❌ PDF path not ready in {timeout}s: {path}')
print('   Exiting so Docker can restart once the NAS mount is available.')
sys.exit(1)
"

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
#!/bin/bash
# NRW Start Script
# Usage: bash start.sh

set -e

cd /home/uusirw/projects/myserver

# Activate venv
source venv/bin/activate

echo "=== Starting NRW Server ==="
echo "Local:    http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

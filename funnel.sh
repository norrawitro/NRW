#!/bin/bash
# WKW Tailscale Funnel Setup
# เปิด public access ผ่าน Tailscale Funnel
# Domain: https://wkw.tail85b885.ts.net  (มาจากชื่อเครื่องใน Tailscale — ตั้งด้วย: sudo tailscale set --hostname=wkw)

set -e

echo "=== WKW Tailscale Funnel ==="

# 1. Reset old config first (IMPORTANT!)
echo "Resetting old config..."
tailscale serve reset 2>/dev/null || true
tailscale funnel reset 2>/dev/null || true

sleep 1

# 2. Setup serve (internal access)
echo "Setting up serve..."
tailscale serve --bg 8000

sleep 1

# 3. Enable funnel (public access)
echo "Enabling funnel..."
tailscale funnel --bg 8000

echo ""
echo "✅ Funnel active!"
URL=$(tailscale status --json 2>/dev/null | python3 -c "import json,sys; print('https://'+json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))" 2>/dev/null || echo "https://wkw.tail85b885.ts.net")
echo "🌐 Public URL: $URL"
echo ""
echo "ปิด funnel ด้วย: tailscale funnel off && tailscale serve off"

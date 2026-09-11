#!/bin/bash
# NRW Tailscale Funnel Setup
# เปิด public access ผ่าน Tailscale Funnel
# Domain: https://nora-web.tail85b885.ts.net

set -e

echo "=== NRW Tailscale Funnel ==="

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
echo "🌐 Public URL: https://nora-web.tail85b885.ts.net"
echo ""
echo "ปิด funnel ด้วย: tailscale funnel off && tailscale serve off"

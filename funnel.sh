#!/bin/bash
# NRW Tailscale Funnel Setup
# เปิด public access ผ่าน Tailscale Funnel
# Domain: https://nora-web.tail85b885.ts.net

set -e

echo "=== NRW Tailscale Funnel ==="

# เปิด funnel port 8000 → HTTPS public
sudo tailscale funnel --bg 8000

echo ""
echo "✅ Funnel active!"
echo "🌐 Public URL: https://nora-web.tail85b885.ts.net"
echo ""
echo "ปิด funnel ด้วย: sudo tailscale funnel --bg off"

#!/bin/bash
# NRW Tailscale Funnel Setup
# เปิด public access ผ่าน Tailscale Funnel
# Domain: https://laptop-s6iicvgh.tail85b885.ts.net

set -e

echo "=== NRW Tailscale Funnel ==="

# เปิด funnel port 8000 → HTTPS public
sudo tailscale funnel --bg 8000

echo ""
echo "✅ Funnel active!"
echo "🌐 Public URL: https://laptop-s6iicvgh.tail85b885.ts.net"
echo ""
echo "ปิด funnel ด้วย: sudo tailscale funnel --bg off"

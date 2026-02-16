@echo off
title Nana AI Tunnel
color 0A

echo ==================================================
echo      Nana AI - Cloudflare Quick Tunnel
echo ==================================================
echo.
echo Starting secure tunnel to http://localhost:3001...
echo.
echo [INSTRUCTIONS]
echo 1. Look for a URL ending in .trycloudflare.com below
echo 2. Copy that URL (e.g., https://heavy-zebra-42.trycloudflare.com)
echo 3. Use this URL for your Frontend deployment
echo.
echo NOTE: If you close this window, the tunnel will stop!
echo.

cloudflared tunnel --url http://localhost:3001

pause

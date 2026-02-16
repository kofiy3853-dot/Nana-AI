# Cloudflare Tunnel Quick Start Script
# Run this script as Administrator

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Nana AI - Cloudflare Tunnel Quick Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  This script requires Administrator privileges!" -ForegroundColor Yellow
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

# Step 1: Install cloudflared
Write-Host "Step 1: Installing cloudflared..." -ForegroundColor Green
try {
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    Write-Host "✅ cloudflared installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install cloudflared. Please install manually." -ForegroundColor Red
    Write-Host "Download from: https://github.com/cloudflare/cloudflared/releases/latest" -ForegroundColor Yellow
    pause
    exit
}

Write-Host ""
Write-Host "Step 2: Authenticate with Cloudflare..." -ForegroundColor Green
Write-Host "A browser window will open. Please authorize cloudflared." -ForegroundColor Yellow
Write-Host ""
pause

cloudflared tunnel login

Write-Host ""
Write-Host "Step 3: Create tunnel..." -ForegroundColor Green
$tunnelName = "nana-ai"
cloudflared tunnel create $tunnelName

Write-Host ""
Write-Host "Step 4: Get tunnel information..." -ForegroundColor Green
$tunnelInfo = cloudflared tunnel list | Select-String $tunnelName
Write-Host $tunnelInfo -ForegroundColor Cyan

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Next Steps (Manual):" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Create config file at: $env:USERPROFILE\.cloudflared\config.yml" -ForegroundColor Yellow
Write-Host "2. Add your tunnel configuration (see phase3_cloudflare_tunnel.md)" -ForegroundColor Yellow
Write-Host "3. Run: cloudflared tunnel run nana-ai" -ForegroundColor Yellow
Write-Host "4. Test your tunnel URL" -ForegroundColor Yellow
Write-Host "5. Install as service: cloudflared service install" -ForegroundColor Yellow
Write-Host ""
Write-Host "For detailed instructions, see: phase3_cloudflare_tunnel.md" -ForegroundColor Cyan
Write-Host ""
pause

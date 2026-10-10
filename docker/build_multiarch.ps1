# CLASS_FUND_WEB - Multi-Architecture Container Build Pipeline (PowerShell)
param (
    [string]$Registry = "classfund",
    [string]$Version = "0.1.0-prod",
    [string]$Platforms = "linux/amd64,linux/arm64"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "CLASS_FUND_WEB Multi-Architecture Build Pipeline (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "Registry:  $Registry"
Write-Host "Version:   $Version"
Write-Host "Platforms: $Platforms"
Write-Host "==============================================================================" -ForegroundColor Cyan

# Check buildx
$builderExists = docker buildx ls | Select-String "classfund-builder"
if (-not $builderExists) {
    Write-Host "Creating docker buildx builder: classfund-builder..." -ForegroundColor Yellow
    docker buildx create --name classfund-builder --driver docker-container --bootstrap --use
} else {
    docker buildx use classfund-builder
}

Write-Host "`n>>> [1/4] Building Backend Image ($Platforms)..." -ForegroundColor Green
docker buildx build `
    --platform $Platforms `
    --file "$RootDir/docker/Dockerfile.backend" `
    --tag "$Registry/backend:$Version" `
    --tag "$Registry/backend:latest" `
    "$RootDir/class-fund-backend-v0.1/class-fund-backend"

Write-Host "`n>>> [2/4] Building Worker Image ($Platforms)..." -ForegroundColor Green
docker buildx build `
    --platform $Platforms `
    --file "$RootDir/docker/Dockerfile.worker" `
    --tag "$Registry/worker:$Version" `
    --tag "$Registry/worker:latest" `
    "$RootDir/class-fund-backend-v0.1/class-fund-backend"

Write-Host "`n>>> [3/4] Building Frontend Image ($Platforms)..." -ForegroundColor Green
docker buildx build `
    --platform $Platforms `
    --file "$RootDir/docker/Dockerfile.frontend" `
    --tag "$Registry/frontend:$Version" `
    --tag "$Registry/frontend:latest" `
    "$RootDir/classfund/classfund"

Write-Host "`n>>> [4/4] Building Edge Proxy Image ($Platforms)..." -ForegroundColor Green
docker buildx build `
    --platform $Platforms `
    --file "$RootDir/docker/Dockerfile.proxy" `
    --tag "$Registry/proxy:$Version" `
    --tag "$Registry/proxy:latest" `
    "$RootDir"

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host "MULTI-ARCHITECTURE BUILD COMPLETE FOR ALL SERVICES: linux/amd64 & linux/arm64" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

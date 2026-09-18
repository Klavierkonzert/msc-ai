<#
.SYNOPSIS
    Automated environment setup script for Evolutionary Design (PowerShell).
#>
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "=== [1/5] Checking Python Dependencies ===" -ForegroundColor Cyan
if (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip install -r requirements.txt
} else {
    Write-Error "Neither pip nor python was found on PATH. Please ensure Python is installed and active."
}

Write-Host "`n=== [2/5] Locating Framsticks Simulator ===" -ForegroundColor Cyan
$framsCandidates = Get-ChildItem -Directory -Path $ScriptDir -Filter "Framsticks*" | 
    Where-Object { $_.Name -match "^Framsticks\d+$" } | 
    Sort-Object { [int]($_.Name -replace "\D") } -Descending

if (-not $framsCandidates -or $framsCandidates.Count -eq 0) {
    Write-Error "Framsticks directory (e.g. Framsticks55) not found in '$ScriptDir'.`nPlease download the latest Framsticks build from http://www.framsticks.com/apps-devel and extract it here."
}

$framsDir = $framsCandidates[0].FullName
Write-Host "Found Framsticks distribution at: $framsDir"

Write-Host "`n=== [3/5] Verifying framspy Directory ===" -ForegroundColor Cyan
$framspyDir = Join-Path $ScriptDir "framspy-download"
if (-not (Test-Path $framspyDir)) {
    Write-Error "'framspy-download' directory not found in '$ScriptDir'.`nDownload it using SVN:`n  svn checkout https://www.framsticks.com/svn/framsticks/framspy/ framspy-download"
}
Write-Host "Found framspy-download directory."

Write-Host "`n=== [4/5] Copying Simulation Files (*.sim) ===" -ForegroundColor Cyan
$dataDir = Join-Path $framsDir "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

Get-ChildItem -Path $framspyDir -Filter "*.sim" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dataDir -Force
    Write-Host "Copied $($_.Name) -> $dataDir"
}

$unevenGroundPath = Join-Path $dataDir "uneven-ground.sim"
if (-not (Test-Path $unevenGroundPath)) {
    Write-Host "Downloading uneven-ground.sim to $dataDir..."
    Invoke-WebRequest -Uri "https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim" -OutFile $unevenGroundPath
    Write-Host "Downloaded uneven-ground.sim successfully."
} else {
    Write-Host "uneven-ground.sim is already present in $dataDir."
}

Write-Host "`n=== [5/5] Testing Simulator Interoperation ===" -ForegroundColor Cyan
$libPath = Join-Path $framsDir "frams-objects.dll"
if (-not (Test-Path $libPath)) {
    Write-Error "Could not find 'frams-objects.dll' in $framsDir."
}

Write-Host "Found Framsticks library at: $libPath"
python (Join-Path $framspyDir "frams-test.py") $framsDir


Write-Host "`n==============================================================================" -ForegroundColor Green
Write-Host " Setup complete! Evolutionary Design environment is configured and ready." -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green

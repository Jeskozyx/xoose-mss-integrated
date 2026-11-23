param(
    [string]$DistRoot = ""
)

$ErrorActionPreference = "Stop"

$ExtRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($DistRoot)) {
    $DistRoot = Join-Path $ExtRoot "dist"
}

& (Join-Path $PSScriptRoot "build-chromium.ps1") -OutDir (Join-Path $DistRoot "chromium") -CreateZip
& (Join-Path $PSScriptRoot "build-firefox.ps1") -OutDir (Join-Path $DistRoot "firefox") -CreateZip

Write-Output "PACKAGE_ALL_OK: $DistRoot"

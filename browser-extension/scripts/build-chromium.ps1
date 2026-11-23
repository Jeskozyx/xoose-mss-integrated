param(
    [string]$OutDir = "",
    [switch]$CreateZip
)

$ErrorActionPreference = "Stop"

$ExtRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $ExtRoot "dist\chromium"
}

if (Test-Path $OutDir) {
    Remove-Item -Path $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# Salin aset Chromium (Chrome & Edge MV3)
Copy-Item -Path (Join-Path $ExtRoot "chromium\*") -Destination $OutDir -Recurse -Force

# Salin modul shared
$SharedDst = Join-Path $OutDir "shared"
New-Item -ItemType Directory -Path $SharedDst -Force | Out-Null
Copy-Item -Path (Join-Path $ExtRoot "shared\*.js") -Destination $SharedDst -Force

if ($CreateZip) {
    $ZipPath = Join-Path (Split-Path -Parent $OutDir) "xoose-capture-chromium.zip"
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $ZipPath -Force
    Write-Output "ZIP_CREATED: $ZipPath"
}

Write-Output "BUILD_CHROMIUM_OK: $OutDir"

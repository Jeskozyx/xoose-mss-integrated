param(
    [string]$OutDir = "",
    [switch]$CreateZip
)

$ErrorActionPreference = "Stop"

$ExtRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $ExtRoot "dist\firefox"
}

if (Test-Path $OutDir) {
    Remove-Item -Path $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# Salin aset Firefox (MV3 Gecko variant)
Copy-Item -Path (Join-Path $ExtRoot "firefox\*") -Destination $OutDir -Recurse -Force

# Salin modul shared
$SharedDst = Join-Path $OutDir "shared"
New-Item -ItemType Directory -Path $SharedDst -Force | Out-Null
Copy-Item -Path (Join-Path $ExtRoot "shared\*.js") -Destination $SharedDst -Force

if ($CreateZip) {
    $ZipPath = Join-Path (Split-Path -Parent $OutDir) "xoose-capture-firefox.zip"
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $ZipPath -Force
    Write-Output "ZIP_CREATED: $ZipPath"
}

Write-Output "BUILD_FIREFOX_OK: $OutDir"

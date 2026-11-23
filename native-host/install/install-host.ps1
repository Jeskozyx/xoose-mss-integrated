param(
    [string]$ChromeExtensionId = "",
    [string]$EdgeExtensionId = "",
    [string]$FirefoxAddonId = "loveyou-capture@xoose.local",
    [string]$HostExecutable = "",
    [string]$PythonPath = "",
    [string]$InstallDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$HostName = "com.xoose.loveyou.host"
$NativeHostRoot = Split-Path -Parent $PSScriptRoot
$TemplateDir = Join-Path $NativeHostRoot "host_manifest"

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "XooseLoveYouAgent\native-host"
}

if (-not (Test-Path $InstallDir)) {
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
}

# Tentukan binary executable host (PyInstaller .exe jika diberikan, atau wrapper .bat ke python host.py)
if ([string]::IsNullOrWhiteSpace($HostExecutable)) {
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $pyCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pyCmd) {
            throw "Python tidak ditemukan di PATH. Berikan parameter -PythonPath atau -HostExecutable."
        }
        $PythonPath = $pyCmd.Source
    }
    $HostScript = Join-Path $NativeHostRoot "host.py"
    if (-not (Test-Path $HostScript)) {
        throw "host.py tidak ditemukan di $HostScript"
    }
    $WrapperBat = Join-Path $InstallDir "xoose-native-host.bat"
    $BatContent = "@echo off`r`n`"$PythonPath`" -u `"$HostScript`" %*`r`n"
    if (-not $DryRun) {
        Set-Content -Path $WrapperBat -Value $BatContent -Encoding Ascii -NoNewline
    }
    $ResolvedHostPath = $WrapperBat
} else {
    $ResolvedHostPath = (Resolve-Path $HostExecutable).Path
}

$EscapedHostPath = $ResolvedHostPath.Replace("\", "\\")

function Register-BrowserHost {
    param(
        [string]$BrowserLabel,
        [string]$TemplateFile,
        [string]$OutFileName,
        [string]$RegistryPath,
        [hashtable]$Replacements
    )

    $TemplatePath = Join-Path $TemplateDir $TemplateFile
    if (-not (Test-Path $TemplatePath)) {
        throw "Template manifest tidak ditemukan: $TemplatePath"
    }

    $Content = Get-Content -Path $TemplatePath -Raw -Encoding UTF8
    $Content = $Content.Replace("{{HOST_EXECUTABLE_PATH}}", $EscapedHostPath)
    foreach ($k in $Replacements.Keys) {
        $Content = $Content.Replace($k, $Replacements[$k])
    }

    # Validasi hasil JSON sebelum registrasi
    $null = $Content | ConvertFrom-Json

    $ManifestOut = Join-Path $InstallDir $OutFileName
    if ($DryRun) {
        Write-Output "[DRY-RUN] $BrowserLabel -> Manifest: $ManifestOut | Registry: $RegistryPath"
        return
    }

    Set-Content -Path $ManifestOut -Value $Content -Encoding UTF8
    if (-not (Test-Path $RegistryPath)) {
        New-Item -Path $RegistryPath -Force | Out-Null
    }
    Set-ItemProperty -Path $RegistryPath -Name "(default)" -Value $ManifestOut
    Write-Output "[OK] $BrowserLabel terdaftar -> $RegistryPath = $ManifestOut"
}

$RegisteredCount = 0

if (-not [string]::IsNullOrWhiteSpace($ChromeExtensionId)) {
    if ($ChromeExtensionId -notmatch "^[a-p]{32}$") {
        throw "ChromeExtensionId tidak valid (wajib 32 karakter a-p dari chrome://extensions): '$ChromeExtensionId'"
    }
    Register-BrowserHost `
        -BrowserLabel "Google Chrome" `
        -TemplateFile "chrome.template.json" `
        -OutFileName "com.xoose.loveyou.host.chrome.json" `
        -RegistryPath "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName" `
        -Replacements @{ "{{CHROME_EXTENSION_ID}}" = $ChromeExtensionId }
    $RegisteredCount++
} else {
    Write-Output "[SKIP] Google Chrome: -ChromeExtensionId belum diberikan."
}

if (-not [string]::IsNullOrWhiteSpace($EdgeExtensionId)) {
    if ($EdgeExtensionId -notmatch "^[a-p]{32}$") {
        throw "EdgeExtensionId tidak valid (wajib 32 karakter a-p dari edge://extensions): '$EdgeExtensionId'"
    }
    Register-BrowserHost `
        -BrowserLabel "Microsoft Edge" `
        -TemplateFile "edge.template.json" `
        -OutFileName "com.xoose.loveyou.host.edge.json" `
        -RegistryPath "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName" `
        -Replacements @{ "{{EDGE_EXTENSION_ID}}" = $EdgeExtensionId }
    $RegisteredCount++
} else {
    Write-Output "[SKIP] Microsoft Edge: -EdgeExtensionId belum diberikan."
}

if (-not [string]::IsNullOrWhiteSpace($FirefoxAddonId)) {
    Register-BrowserHost `
        -BrowserLabel "Mozilla Firefox" `
        -TemplateFile "firefox.template.json" `
        -OutFileName "com.xoose.loveyou.host.firefox.json" `
        -RegistryPath "HKCU:\Software\Mozilla\NativeMessagingHosts\$HostName" `
        -Replacements @{ "{{FIREFOX_ADDON_GECKO_ID}}" = $FirefoxAddonId }
    $RegisteredCount++
}

Write-Output "INSTALL_HOST_COMPLETE: $RegisteredCount browser target diproses (Host: $ResolvedHostPath)."

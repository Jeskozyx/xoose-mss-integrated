param(
    [string]$InstallDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$HostName = "com.xoose.loveyou.host"
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "XooseLoveYouAgent\native-host"
}

$RegistryKeys = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName",
    "HKCU:\Software\Mozilla\NativeMessagingHosts\$HostName"
)

foreach ($rk in $RegistryKeys) {
    if (Test-Path $rk) {
        if ($DryRun) {
            Write-Output "[DRY-RUN] Akan menghapus registry key: $rk"
        } else {
            Remove-Item -Path $rk -Recurse -Force
            Write-Output "[REMOVED] Registry key: $rk"
        }
    } else {
        Write-Output "[SKIP] Tidak ditemukan: $rk"
    }
}

$FilesToRemove = @(
    "com.xoose.loveyou.host.chrome.json",
    "com.xoose.loveyou.host.edge.json",
    "com.xoose.loveyou.host.firefox.json",
    "xoose-native-host.bat"
)

foreach ($f in $FilesToRemove) {
    $p = Join-Path $InstallDir $f
    if (Test-Path $p) {
        if ($DryRun) {
            Write-Output "[DRY-RUN] Akan menghapus file: $p"
        } else {
            Remove-Item -Path $p -Force
            Write-Output "[REMOVED] File: $p"
        }
    }
}

Write-Output "UNINSTALL_HOST_COMPLETE: Registry & manifest Native Messaging dibersihkan."

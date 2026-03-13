# INSTALL.ps1 — Right-click > Run with PowerShell (as Administrator)
$dir = "C:\FunFunPod"
Write-Host "Installing FunFunPod..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $dir | Out-Null

$src = Join-Path $PSScriptRoot "FunFunConnect.ps1"
if (-not (Test-Path $src)) {
    Write-Host "ERROR: FunFunConnect.ps1 must be in the same folder as INSTALL.ps1" -ForegroundColor Red
    Read-Host; exit 1
}
Copy-Item $src "$dir\FunFunConnect.ps1" -Force

# Create shortcut
$wsh = New-Object -ComObject WScript.Shell
$lnkPath = "$dir\FunFunPod.lnk"
$lnk = $wsh.CreateShortcut($lnkPath)
$lnk.TargetPath       = "powershell.exe"
$lnk.Arguments        = "-ExecutionPolicy Bypass -NoProfile -File `"$dir\FunFunConnect.ps1`""
$lnk.IconLocation     = "C:\Program Files\Parsec\parsecd.exe,0"
$lnk.Description      = "FunFunPod"
$lnk.WorkingDirectory = $dir
$lnk.Save()

# Desktop copy
Copy-Item $lnkPath "$env:USERPROFILE\Desktop\FunFunPod.lnk" -Force
Write-Host "Shortcut on Desktop." -ForegroundColor Green

# Pin to taskbar
$shell  = New-Object -ComObject Shell.Application
$folder = $shell.Namespace($dir)
$item   = $folder.ParseName("FunFunPod.lnk")
$pin    = $item.Verbs() | Where-Object { ($_.Name -replace '&','') -match "Pin to taskbar" }
if ($pin) {
    $pin.DoIt()
    Write-Host "Pinned to taskbar." -ForegroundColor Green
} else {
    Write-Host "Auto-pin failed. Right-click FunFunPod on Desktop > 'Pin to taskbar'." -ForegroundColor Yellow
}

Write-Host "`nDone. Click FunFunPod to connect." -ForegroundColor Green
Read-Host

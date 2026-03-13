# INSTALL.ps1 — Right-click > Run as Administrator
$dir = "C:\FunFunPod"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "Downloading FunFunConnect.ps1..." -ForegroundColor Cyan
$url = "https://raw.githubusercontent.com/Eru-Iluvatar-the-One/Runpod-Gaming/main/FunFunConnect.ps1"
Invoke-WebRequest $url -OutFile "$dir\FunFunConnect.ps1" -UseBasicParsing

# Shortcut
$wsh = New-Object -ComObject WScript.Shell
$lnkPath = "$dir\FunFunPod.lnk"
$lnk = $wsh.CreateShortcut($lnkPath)
$lnk.TargetPath       = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$lnk.Arguments        = "-ExecutionPolicy Bypass -NoProfile -File `"$dir\FunFunConnect.ps1`""
$lnk.IconLocation     = "C:\Program Files\Parsec\parsecd.exe,0"
$lnk.Description      = "FunFunPod"
$lnk.WorkingDirectory = $dir
$lnk.Save()

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
    Write-Host "Right-click FunFunPod on Desktop > Pin to taskbar" -ForegroundColor Yellow
}

Write-Host "`nDone. Click FunFunPod on taskbar to play." -ForegroundColor Green
Read-Host

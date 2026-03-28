$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
Write-Host "[1/3] Running vite build..."
$env:NODE_ENV = "production"
& "C:\Program Files\nodejs\node.exe" "node_modules\.bin\vite" build 2>&1 | Tee-Object -FilePath "$PSScriptRoot\build.log"
Write-Host "[2/3] Vite done. Running electron-builder..."
& "C:\Program Files\nodejs\node.exe" "node_modules\.bin\electron-builder" build --config electron-builder.yml --publish never 2>&1 | Tee-Object -Append -FilePath "$PSScriptRoot\build.log"
Write-Host "[3/3] Build complete."
$exe = Get-ChildItem "$PSScriptRoot\release\*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($exe) {
    Write-Host "EXE: $($exe.FullName)" -ForegroundColor Green
} else {
    Write-Host "NO EXE FOUND in release/" -ForegroundColor Red
    Get-ChildItem "$PSScriptRoot\release\" -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_.FullName }
}

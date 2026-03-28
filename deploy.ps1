# deploy.ps1 — Fix creds, build, push, deploy, open. One paste.
$ErrorActionPreference = 'Stop'
$DOCKER = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$GIT    = "C:\Program Files\Git\bin\git.exe"
$REPO   = "D:\GitHub\FunPod-RunpodGaming"
$IMAGE  = "eruilu/funfunpod:latest"

# ── Secrets from registry ────────────────────────────────────
$RUNPOD_KEY = Get-ItemPropertyValue "HKCU:\Environment" -Name "Funpod-RunpodGaming"
$DOCKER_PAT = Get-ItemPropertyValue "HKCU:\Environment" -Name "Docker-Funpod-Runpod-Gaming"

# ── Fix docker-credential-desktop PATH error ─────────────────
$cfgPath = "$env:USERPROFILE\.docker\config.json"
if (Test-Path $cfgPath) {
    $raw = Get-Content $cfgPath -Raw
    $patched = $raw -replace '"credsStore"\s*:\s*"[^"]*"', '"credsStore": ""'
    [IO.File]::WriteAllText($cfgPath, $patched)
} else {
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.docker" -Force | Out-Null
    [IO.File]::WriteAllText($cfgPath, '{"auths":{},"credsStore":""}')
}
Write-Host "[1/7] Docker config patched" -ForegroundColor Green

# ── Docker login (cmd /c avoids PS pipe+spaces-in-path bug) ──
$loginResult = cmd /c "echo $DOCKER_PAT | `"$DOCKER`" login --username eruilu --password-stdin 2>&1"
$loginResult | Write-Host
if ($LASTEXITCODE -ne 0) { throw "Docker login failed" }
Write-Host "[2/7] Docker login OK" -ForegroundColor Green

# ── Git pull latest ──────────────────────────────────────────
& $GIT -C $REPO fetch origin main 2>&1 | Out-Null
& $GIT -C $REPO reset --hard origin/main 2>&1 | Out-Null
Write-Host "[3/7] Repo synced" -ForegroundColor Green

# ── Build ────────────────────────────────────────────────────
Write-Host "[4/7] Building $IMAGE (this takes a few minutes)..." -ForegroundColor Cyan
& $DOCKER build --platform linux/amd64 -t $IMAGE $REPO 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
Write-Host "[4/7] Build OK" -ForegroundColor Green

# ── Push ─────────────────────────────────────────────────────
Write-Host "[5/7] Pushing $IMAGE ..." -ForegroundColor Cyan
& $DOCKER push $IMAGE 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "Docker push failed" }
Write-Host "[5/7] Push OK" -ForegroundColor Green

# ── Stop old pod ─────────────────────────────────────────────
try {
    $oldPod = Get-ItemPropertyValue "HKCU:\Environment" -Name "FunFunPodID" -ErrorAction SilentlyContinue
    if ($oldPod) {
        $stopBody = '{"query":"mutation{podStop(input:{podId:\"' + $oldPod + '\"}){id}}"}' 
        Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$RUNPOD_KEY" -Method POST -ContentType "application/json" -Body $stopBody | Out-Null
        Write-Host "[5.5] Stopped old pod $oldPod" -ForegroundColor Yellow
    }
} catch {}

# ── Deploy new pod ───────────────────────────────────────────
Write-Host "[6/7] Deploying new A40 pod..." -ForegroundColor Cyan
$deployBody = '{"query":"mutation { podFindAndDeployOnDemand(input: { name: \"FunFunPod\", imageName: \"eruilu/funfunpod:latest\", gpuTypeId: \"NVIDIA A40\", cloudType: SECURE, gpuCount: 1, volumeInGb: 175, containerDiskInGb: 75, volumeMountPath: \"/workspace\", ports: \"8080/http,8081/tcp,22/tcp\", startSsh: true, env: [] }) { id desiredStatus } }"}' 
$result = Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$RUNPOD_KEY" -Method POST -ContentType "application/json" -Body $deployBody
if ($result.errors) {
    $result.errors | ForEach-Object { Write-Host "  ERROR: $($_.message)" -ForegroundColor Red }
    throw "Pod deploy failed"
}
$POD_ID = $result.data.podFindAndDeployOnDemand.id
if (-not $POD_ID) { throw "No pod ID returned: $($result | ConvertTo-Json -Depth 5)" }
Set-ItemProperty "HKCU:\Environment" -Name "FunFunPodID" -Value $POD_ID
$env:FunFunPodID = $POD_ID
Write-Host "[6/7] Pod $POD_ID deployed" -ForegroundColor Green

# ── Poll until Neko lives ────────────────────────────────────
Write-Host "[7/7] Waiting for Neko..." -ForegroundColor Cyan
$url = "https://$POD_ID-8080.proxy.runpod.net"
$ready = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
        if ($r.StatusCode -lt 500) { $ready = $true; break }
    } catch {
        $msg = $_.Exception.Message
        if ($msg -match "(\d{3})") { $code = $Matches[1] } else { $code = "..." }
        Write-Host "  wait $i ($code)"
    }
    Start-Sleep 10
}

if ($ready) {
    Write-Host "`n[DONE] Neko LIVE: $url" -ForegroundColor Green
    Start-Process $url
} else {
    Write-Host "`n[TIMEOUT] Pod deployed but Neko not responding yet." -ForegroundColor Yellow
    Write-Host "  Try manually: $url" -ForegroundColor Yellow
    Write-Host "  Check logs: RunPod dashboard -> pod $POD_ID -> Logs" -ForegroundColor Yellow
}

Write-Host "`n  Pod: $POD_ID | URL: $url | Pass: admin" -ForegroundColor Magenta

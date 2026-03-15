# FunFunConnect.ps1 — Neko browser streaming edition
# Double-click shortcut -> pod starts -> browser opens -> play
# Requires env vars: FunFunPod (RunPod API key), FunFunPodID (pod ID)

param(
    [string]$PodID    = $env:FunFunPodID,
    [string]$ApiKey   = $env:FunFunPod,
    [string]$NekoPass = "neko"
)

$ErrorActionPreference = "Stop"
$LogFile = "$env:USERPROFILE\funfunconnect.log"
Start-Transcript -Path $LogFile -Append -Force

if (-not $PodID)  { Write-Error "Set env var FunFunPodID to your RunPod pod ID."; exit 1 }
if (-not $ApiKey) { Write-Error "Set env var FunFunPod to your RunPod API key.";  exit 1 }

$headers = @{ "Authorization" = "Bearer $ApiKey"; "Content-Type" = "application/json" }

# --- Resume pod if not running ---
function Get-PodStatus {
    $q = '{"query":"{ pod(input:{podId:\"' + $PodID + '\"}) { desiredStatus runtime { uptimeInSeconds } } }"}'
    $r = Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$ApiKey" `
         -Method POST -Headers $headers -Body $q
    return $r.data.pod
}

Write-Host ">> Checking pod status..."
$pod = Get-PodStatus

if ($pod.desiredStatus -ne "RUNNING") {
    Write-Host ">> Starting pod $PodID..."
    $mutation = '{"query":"mutation { podResume(input:{podId:\"' + $PodID + '\", gpuCount:1}) { id desiredStatus } }"}'
    Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$ApiKey" `
        -Method POST -Headers $headers -Body $mutation | Out-Null
}

# --- Wait for running + neko port ready ---
Write-Host ">> Waiting for pod to be ready (this takes ~60s on cold start)..."
$NekoUrl = "https://$PodID-8080.proxy.runpod.net"
$ready   = $false
$timeout = (Get-Date).AddMinutes(5)

while ((Get-Date) -lt $timeout) {
    try {
        $resp = Invoke-WebRequest -Uri $NekoUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($resp.StatusCode -lt 500) { $ready = $true; break }
    } catch { }
    Write-Host "  ...not ready yet, retrying in 10s"
    Start-Sleep 10
}

if (-not $ready) {
    Write-Error "Pod did not become ready within 5 minutes. Check RunPod dashboard."
    Stop-Transcript; exit 1
}

# --- Open browser ---
Write-Host ">> Pod ready. Opening browser..."
Start-Process "$NekoUrl"

Write-Host ">> Done. Password for neko: $NekoPass"
Stop-Transcript

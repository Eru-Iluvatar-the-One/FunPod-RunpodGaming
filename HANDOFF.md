# HANDOFF — FunFunPod: Total War Three Kingdoms at 4K/144Hz

**Trigger:** `BARAHIR HANDOFF runpod-gaming`
**BEACON ID:** BRH-4D-0323-0400Z
**Mission:** Eru plays Total War: Three Kingdoms at 4K 144Hz via RunPod GPU streaming. Do not stop until the game is clickable.

---

## §PAST — What Happened

- **Week of failure:** Blind deploy-pray-crash loops. V-007, V-008, V-009. Orc waves.
- **Root causes identified this session:**
  1. No `[program:app]` in supervisord — nvidia-base is a BASE, needs window manager + app configured
  2. Xvfb replacing Xorg kills GPU encoding — nvh264enc needs real X server or EGL
  3. Zero WebRTC config — no TCPMUX, no ICELITE, no SCREEN env vars
  4. `set -e` in neko-init.sh — silent exit on any failure
  5. pulseaudio conflict with supervisord's own pulse management
- **Arena.AI prompt delivered** — full diagnostic request covering all 5 root causes
- **Gemini Deep Research RUNNING** — Eru will bring the report
- **Eru's Order deployed** — ERUS-ORDER.md in all 11 repos. WHAT/HOW/WHY gate is now law.
- **Tengwar Voice fixed** — vad_filter → false. Build launched.
- **Image `eruilu/funfunpod:latest` is STALE** — DO NOT DEPLOY until rebuilt with fixes

## §PRESENT — What Eru Brings to Next Session

Eru arrives with **Gemini Deep Research report** containing corrected:
- Dockerfile
- neko-init.sh
- Required env vars for TCP-only WebRTC on RunPod
- Proper supervisord app config (openbox + Steam)
- Display server strategy (Xorg EGL vs Xvfb)

## §FUTURE — The Execution Sequence (Eru's Order)

**Station IV will execute these steps IN ORDER. No skipping. No improvising.**

### Step 0: WHAT/HOW/WHY Gate
Read Gemini report. State WHAT we're building, HOW, and WHY. Get Eru's approval.

### Step 1: Implement Fixes
- Write corrected `Dockerfile` to `D:\GitHub\FunPod-RunpodGaming\Dockerfile`
- Write corrected `neko-init.sh` to same repo
- Commit both via `github:create_or_update_file` (get SHA first)

### Step 2: Build & Push
```powershell
Set-Location 'D:\GitHub\FunPod-RunpodGaming'
& .\build-and-push.ps1
```
Wait for completion. Verify push succeeded on Docker Hub.

### Step 3: Deploy Fresh Pod
Use GraphQL deploy template (below). NEVER reuse old pods.
```powershell
$apiKey = Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'Funpod-RunpodGaming'
$query = '{"query":"mutation { podFindAndDeployOnDemand(input: { name: \"FunFunPod\", imageName: \"eruilu/funfunpod:latest\", gpuTypeId: \"NVIDIA RTX A4000\", cloudType: ALL, gpuCount: 1, volumeInGb: 50, containerDiskInGb: 30, minVcpuCount: 4, minMemoryInGb: 16, ports: \"8080/http,8081/tcp\", dockerArgs: \"\", env: [] }) { id desiredStatus imageName machine { gpuDisplayName } } }"}'
$resp = Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$apiKey" -Method Post -ContentType 'application/json' -Body $query
$resp | ConvertTo-Json -Depth 10
```
Save pod ID to `HKCU:\Environment\FunFunPodID`.

### Step 4: Poll Until Running
```powershell
# ONE tool call — sleep loop inside terminal
$apiKey = Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'Funpod-RunpodGaming'
$podId = 'INSERT_POD_ID'
for ($i=1; $i -le 30; $i++) {
    Start-Sleep 15
    try {
        $r = Invoke-WebRequest -Uri "https://$podId-8080.proxy.runpod.net/" -TimeoutSec 5 -UseBasicParsing
        Write-Output "[Attempt $i] HTTP $($r.StatusCode) - NEKO IS UP"
        break
    } catch {
        Write-Output "[Attempt $i] Not ready: $($_.Exception.Message)"
    }
}
```

### Step 5: Connect & Verify Neko
Open `https://<POD_ID>-8080.proxy.runpod.net` in Chrome. Login: admin/admin. Verify desktop renders.

### Step 6: Install Steam + Three Kingdoms
Inside Neko desktop:
- Open terminal → install Steam if not present
- Login to Steam → install Total War: Three Kingdoms
- Launch at 4K, 144Hz (Neko screen config must match)

### Step 7: PLAY THE FUCKING GAME

## Target Specs
- **Game:** Total War: Three Kingdoms
- **Resolution:** 3840x2160 (4K)
- **Refresh:** 144Hz (monitor native)
- **GPU:** RTX A4000 (16GB VRAM) — may need upgrade to A5000/A6000 for 4K ultra
- **Streaming:** Neko WebRTC via TCP mux on port 8081
- **Access:** `https://<POD_ID>-8080.proxy.runpod.net`

## Windows Env Vars (Registry HKCU:\Environment)

| Var | Purpose |
|---|---|
| `Funpod-RunpodGaming` | RunPod API key |
| `FunFunPodID` | Current pod ID (update after deploy) |
| `Docker-Funpod-Runpod-Gaming` | Docker Hub PAT |

## Neko Credentials
- Admin: `admin` / `admin`
- User: `neko` / `neko`

## What Failed (DO NOT RETRY)
- Moonlight/Sunshine — UDP blocked by RunPod
- Chisel — Windows Defender HackTool flag
- Tailscale/boringtun — no TUN device
- Parsec — no Linux hosting on consumer accounts
- Custom NEKO_CAPTURE_VIDEO_PIPELINE — panic crash
- Pipeline env var set to "" — also crashes
- Restarting existing pod with :latest — node cache = stale
- Xorg/xorg.conf in containers — no GPU modesetting
- nvidia-base without [program:app] — container hangs
- Xvfb on nvidia-base — kills CUDA encoding (suspected)

## GraphQL Terminate Template
```powershell
$apiKey = Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'Funpod-RunpodGaming'
$query = '{"query":"mutation { podTerminate(input: { podId: \"<<<POD_ID>>>\" }) }"}'
Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$apiKey" -Method Post -ContentType 'application/json' -Body $query
```

## BARAHIR Violations (Carry Forward)
- V-009: Week of blind iteration without docs/escalation
- V-008: Screenshot polling loops
- V-007: 2-hour cascading failure without Arena escalation

## Eru's Order
See `ERUS-ORDER.md` in this repo. Pre-Implementation Gate (WHAT/HOW/WHY) is MANDATORY.
2 failed iterations → escalate. No orc waves.

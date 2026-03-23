# HANDOFF — FunFunPod Neko Edition

**Trigger:** `BARAHIR HANDOFF runpod-gaming`

---

## Current State (2026-03-23 Session 2)

- **Image:** `eruilu/funfunpod:latest` — STALE, DO NOT DEPLOY. Awaiting Arena.AI diagnosis before rebuild.
- **Active pod:** NONE — `ihzmzf2xyc7ss0` terminated by Eru. Container never reached running state.
- **Windows registry:** `FunFunPodID` = `ihzmzf2xyc7ss0` (stale)
- **Arena.AI escalation:** IN PROGRESS. Full diagnostic prompt prepared. Eru is getting the answer.
- **Tengwar Voice:** `vad_filter` fixed to `false` in both `config.py` defaults and `config.json`. Exe rebuild launched via `build.ps1`.

## ROOT CAUSE ANALYSIS — Why Container Never Starts

After reading all neko v3 docs and the full codebase, these are the **suspected root causes** (Arena.AI confirming):

1. **No app program in supervisord.conf.** The `nvidia-base` image is a BASE — it has no `[program:app]` section. Neko expects a window manager + application (openbox, xfce, browser, etc.) to be configured. Without it, supervisord may crash or neko has nothing to stream.

2. **Xvfb replacing Xorg kills GPU encoding.** The nvidia-base uses Xorg+EGL for GPU-accelerated rendering. Xvfb is software-only — `nvh264enc` (CUDA encoding) may not work with a software display server. This means the video pipeline crashes silently.

3. **Missing critical v3 env vars.** Zero WebRTC configuration was set. For TCP-only (RunPod blocks UDP), we need at minimum:
   - `NEKO_WEBRTC_TCPMUX=8081`
   - `NEKO_WEBRTC_ICELITE=1`
   - `NEKO_DESKTOP_SCREEN=1920x1080@30`

4. **`set -e` in neko-init.sh** — if `getent passwd neko` fails or `/workspace` has permission issues, the script exits silently and the CMD never reaches supervisord.

5. **pulseaudio in neko-init.sh** — neko's supervisord already manages pulseaudio. Starting it in init may conflict.

## Next Action — THE PLAN

1. **Eru brings Arena.AI response** with corrected Dockerfile + neko-init.sh
2. Station IV implements the fix, commits to repo
3. `build-and-push.ps1` rebuilds and pushes to Docker Hub
4. Deploy fresh pod via GraphQL API
5. Probe `https://<POD_ID>-8080.proxy.runpod.net` — expect Neko login
6. Log in, install Steam, launch game
7. **SECONDARY GOAL:** Feed the entire diagnostic chain into Mandos Code Auditor as a test case for Docker/infra auditing

## Arena.AI Prompt (Already Given to Eru)

Full diagnostic covering: why container fails, Xvfb vs Xorg for GPU encoding, required v3 env vars for TCP-only WebRTC, missing supervisord app program, and request for corrected Dockerfile + neko-init.sh.

## Windows Env Vars (Registry HKCU:\Environment)

| Var | Purpose |
|---|---|
| `Funpod-RunpodGaming` | RunPod API key |
| `FunFunPodID` | Current pod ID |
| `Docker-Funpod-Runpod-Gaming` | Docker Hub PAT |

## Critical Tool Usage Rules

**TERMINAL MCP** — use `& "C:\Program Files\Git\bin\git.exe"` for git. Docker IS on PATH. `build-and-push.ps1` works directly.

**GITHUB MCP** — always `get_file_contents` before `create_or_update_file` to get SHA.

**RUNPOD OPS** — Claude terminates via GraphQL. Claude deploys via GraphQL. API key = `Funpod-RunpodGaming` in registry.

**POLLING** — Use `terminal:run_command` with `Invoke-WebRequest` in a sleep loop. ONE tool call per probe. NEVER screenshot-poll.

**DEPLOY** — ALWAYS deploy brand new pod. Never restart existing (node cache = stale image).

## GraphQL Deploy Template
```powershell
$apiKey = Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'Funpod-RunpodGaming'
$query = '{"query":"mutation { podFindAndDeployOnDemand(input: { name: \"FunFunPod\", imageName: \"eruilu/funfunpod:latest\", gpuTypeId: \"NVIDIA RTX A4000\", cloudType: ALL, gpuCount: 1, volumeInGb: 50, containerDiskInGb: 30, minVcpuCount: 4, minMemoryInGb: 16, ports: \"8080/http,8081/tcp\", dockerArgs: \"\", env: [] }) { id desiredStatus imageName machine { gpuDisplayName } } }"}'
$resp = Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$apiKey" -Method Post -ContentType 'application/json' -Body $query
$resp | ConvertTo-Json -Depth 10
```

## GraphQL Terminate Template
```powershell
$apiKey = Get-ItemPropertyValue -Path 'HKCU:\Environment' -Name 'Funpod-RunpodGaming'
$query = '{"query":"mutation { podTerminate(input: { podId: \"<<<POD_ID>>>\" }) }"}'
Invoke-RestMethod -Uri "https://api.runpod.io/graphql?api_key=$apiKey" -Method Post -ContentType 'application/json' -Body $query
```

## Neko Credentials
- Admin: `admin` / `admin`
- User: `neko` / `neko`

## What Failed (DO NOT RETRY)
- Moonlight/Sunshine — UDP blocked by RunPod at network level
- Chisel — Windows Defender HackTool flag
- Tailscale/boringtun — no TUN device
- Parsec — no Linux hosting on consumer accounts
- Custom `NEKO_CAPTURE_VIDEO_PIPELINE` — panic crash
- Setting pipeline env var to `""` — also crashes
- Restarting existing pod with `:latest` — node cache, pulls stale image
- Xorg / xorg.conf in containers — no GPU modesetting, always fails
- Deploying nvidia-base without a `[program:app]` in supervisord — container hangs/crashes
- Replacing Xorg with Xvfb on nvidia-base — may kill CUDA encoding pipeline

## BARAHIR Violations

### V-009 — 2026-03-23: Week-Long Failure Loop Without Escalation
**Root cause:** Station IV spent a full week iterating on blind Dockerfile fixes without ever reading the neko v3 documentation or understanding what nvidia-base requires. Never escalated to Arena.AI despite V-007 mandate. Deployed pods repeatedly without understanding WHY they fail.
**Correct behavior:** Read the docs FIRST. Understand what the base image provides. Escalate to Arena.AI after 2 failed iterations. Do not deploy until the configuration is understood and validated.

### V-008 — 2026-03-23: Tool Call Exhaustion / Inefficient Polling
**Root cause:** Screenshot polling loops instead of terminal probing.
**Correct behavior:** Poll via `terminal:run_command` with `Invoke-WebRequest`.

### V-007 — 2026-03-22: 2-Hour Cascading Failure Loop
**Root cause:** Did not escalate to Arena.AI after iteration 2.
**Correct behavior:** Escalate at iteration 3. Not optional.

## BARAHIR: Arena Escalation Rule
2 unresolved iterations → escalate to Arena.AI. NOT OPTIONAL.

## Tengwar Voice Fix (This Session)
- **Bug:** `vad_filter: true` in config caused faster-whisper to silently discard audio segments during pauses. User experienced this as "predicting auto-silence" — long dictations got truncated.
- **Fix:** Set `vad_filter: false` in `config.py` defaults AND `config.json` runtime file.
- **Rebuild:** `build.ps1` launched in background. Exe at `dist\TengwarVoice\TengwarVoice.exe` after completion.
- **Always launch via:** `dist\TengwarVoice\TengwarVoice.exe`, never `python app.py`.

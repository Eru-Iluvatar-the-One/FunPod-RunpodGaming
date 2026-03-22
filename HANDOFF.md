# HANDOFF — FunFunPod Neko Edition

**Trigger:** `BARAHIR HANDOFF runpod-gaming`

## Current State (2026-03-22)

- **Image:** `eruilu/funfunpod:latest` on Docker Hub — **STALE, contains crash-causing custom NVENC pipeline**
- **Dockerfile in repo:** FIXED (custom pipeline removed, TCPMUX=8081 retained)
- **Docker Hub NOT rebuilt** — `docker build` fails locally with `docker-credential-desktop` PATH error
- **Active pod:** `6sjdbb0dhktgdi` — 502ing because it pulled the stale image
- **Pure base image test (`ghcr.io/m1k1o/neko/nvidia-base:latest`):** BOOTS AND SERVES HTTP 200. WebRTC "Reconnecting..." without TCPMUX (expected — RunPod blocks UDP).
- **Root cause of all crashes:** `NEKO_CAPTURE_VIDEO_PIPELINE` env var with custom GStreamer pipeline referencing `cudaupload ! cudaconvert ! nvh264enc` — elements don't exist or mismatch in base image's GStreamer build → panic at `desktop/manager.go:57`

## Blockers to Resolve

1. **Docker credential helper:** `docker-credential-desktop` not in PATH → build fails
2. **Image rebuild + push** needed after credential fix
3. **Fresh pod deploy** from rebuilt image (node cache = must be NEW pod, not restart)
4. **Windows env var mismatch:** API key stored as `Funpod-RunpodGaming`, script expects `FunFunPod`
5. **Local FunFunConnect.ps1** at `C:\FunFunPod\` is ancient Parsec version; repo version is correct Neko version

## What Works Confirmed

- Base neko image boots clean on RunPod A40 with default settings
- HTTP proxy `https://<POD_ID>-8080.proxy.runpod.net` serves Neko login
- TCPMUX=8081 is REQUIRED for WebRTC (RunPod blocks all inbound UDP)
- Custom NVENC pipeline MUST be removed (let neko auto-detect)

## Deploy Instructions

New pod settings:
- **Image:** `eruilu/funfunpod:latest` (AFTER rebuild+push)
- **GPU:** A40 1x
- **Container disk:** 75GB
- **Pod volume:** 175GB at `/workspace`
- **Ports:** `8080/http`, `8081/tcp`
- **No env var overrides needed** (all baked into Dockerfile)

## Architecture

- **Stack:** Neko (m1k1o/neko/nvidia-base) + Steam + Proton
- **Transport:** WebRTC over TCP mux port 8081
- **No UDP. No tunnels. No client software.**

## Windows Env Vars (Registry HKCU:\Environment)

| Var | Purpose |
|---|---|
| `Funpod-RunpodGaming` | RunPod API key (NOTE: not `FunFunPod`) |
| `FunFunPodID` | Current pod ID |
| `Docker-Funpod-Runpod-Gaming` | Docker Hub PAT |

## Neko Credentials

- Admin: `admin` / `admin`
- User: `neko` / `neko`

## What Failed Before (DO NOT RETRY)

- Moonlight/Sunshine — UDP required, RunPod blocks all UDP
- Chisel — Windows Defender flags as HackTool
- Tailscale/boringtun — no TUN device in unprivileged containers
- Parsec — no Linux hosting on consumer accounts
- Vast.ai + Moonlight — open UDP but driver instability
- Restarting existing pod with `:latest` tag — Docker caches old image
- Custom NEKO_CAPTURE_VIDEO_PIPELINE — panic crash in DesktopManager
- Setting env vars to empty string "" — Neko parses as invalid pipeline, also crashes

## BARAHIR Violations

### V-007 — 2026-03-22: 2-Hour Cascading Failure Loop
**Severity:** Critical
**Root cause:** Station IV failed to escalate to Arena.AI after iteration 2. Instead burned 5+ pod deployments, multiple SSH failures, credential issues, and Docker build failures across a 2-hour session. User's entire break wasted.
**Specific failures:**
1. Did not discover API key env var name mismatch (`Funpod-RunpodGaming` vs `FunFunPod`) until user intervened
2. Deployed pod via GraphQL instead of delegating to RunPod assistant (user's established workflow)
3. Set pipeline env var to empty string, causing DIFFERENT crash mode
4. Failed to run `build-and-push.ps1` autonomously (Docker credential error unresolved)
5. Could not capture SSH output via terminal MCP (known caveat, should have used Chrome or asked user)
6. Exceeded BARAHIR 2-iteration escalation rule by at least 4 iterations
**Correct behavior:** After confirming base image boots (iteration 1) and identifying pipeline as crash cause (iteration 2), should have immediately escalated to Arena.AI with full context for a clean, tested, shippable solution.

## BARAHIR: Arena Escalation Rule

2 unresolved iterations → escalate to Arena.AI immediately. NOT OPTIONAL.

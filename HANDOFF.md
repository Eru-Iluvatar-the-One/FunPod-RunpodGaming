# HANDOFF — FunFunPod Neko Edition

**Trigger:** `BARAHIR HANDOFF runpod-gaming`

## Current State (2026-03-15)

- **Image:** `eruilu/funfunpod:latest` — public on Docker Hub, built today
- **Last blocker:** `/docker-entrypoint.sh: No such file or directory` — FIXED
- **Fix applied:** `start.sh` now auto-discovers supervisord + conf via `find`, runs `neko-init.sh` first
- **neko-init.sh:** working (confirmed in logs — home detection, symlinks, pulseaudio all good)
- **Next action:** deploy FRESH pod (do not reuse `6t96ama7hd0ots` — stale cache)

## Deploy Instructions

New pod settings:
- **Image:** `eruilu/funfunpod:latest`
- **GPU:** L4 1x (on-demand, $0.39/hr)
- **Container disk:** 75GB
- **Pod volume:** 175GB at `/workspace`
- **Port:** `8080/http`

After deploy, access: `https://<NEW_POD_ID>-8080.proxy.runpod.net`

## Architecture

- **Stack:** Neko (m1k1o/neko/nvidia-base) + NVENC + Steam + Proton
- **Transport:** WebRTC over TCP mux — port `8080` only
- **No UDP. No tunnels. No client software.**

## Windows Env Vars

| Var | Value |
|---|---|
| `FunFunPod` | RunPod API key |
| `FunFunPodID` | set to new pod ID after deploy |
| `DckrRunpod` | Docker Hub PAT |

## Neko Credentials

- Admin: `admin` / `admin`
- User: `neko` / `neko`

## What Failed Before (DO NOT RETRY)

- Moonlight/Sunshine — UDP required, RunPod blocks all UDP
- Chisel — Windows Defender flags as HackTool
- Tailscale/boringtun — no TUN device in unprivileged containers
- Parsec — no Linux hosting on consumer accounts
- Vast.ai + Moonlight — open UDP but driver instability
- Restarting existing pod with `:latest` tag — Docker caches old image, does not re-pull

## BARAHIR: Arena Escalation Rule

3 unresolved iterations → escalate to Arena.AI immediately.

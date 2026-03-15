# HANDOFF — FunFunPod Neko Edition

**Trigger:** `BARAHIR HANDOFF runpod-gaming`

## Active Pod

- **Pod ID:** `6t96ama7hd0ots`
- **URL:** `https://6t96ama7hd0ots-8080.proxy.runpod.net`
- **GPU:** L4 1x @ $0.39/hr (on-demand)
- **Admin:** `admin` / `admin` | **User:** `neko` / `neko`

## Architecture

- **Stack:** Neko (m1k1o/neko) + NVENC + Steam + Proton
- **Transport:** WebRTC over TCP mux — single port `8080/http`
- **No UDP. No tunnels. No client software.**

## Windows Env Vars

| Var | Value |
|---|---|
| `FunFunPod` | RunPod API key |
| `FunFunPodID` | `6t96ama7hd0ots` |

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Pod image — Neko NVENC + Steam + Proton |
| `neko-init.sh` | First-boot: symlinks Steam/saves to `/workspace` |
| `FunFunConnect.ps1` | Windows one-click: starts pod, waits, opens browser |
| `build-and-push.ps1` | One-time rebuild + push to `eruilu/funfunpod:latest` |

## Pending Dockerfile Fixes (apply before next rebuild)

1. Move `dpkg --add-architecture i386` before first `apt-get install`
2. Steam install: `dpkg -i /tmp/steam.deb && apt-get install -y -f`
3. `neko-init.sh`: detect home via `getent passwd neko | cut -d: -f6`
4. Add CPU fallback pipeline via `NEKO_GPU_PIPELINE=0` env var
5. Move passwords to pod env vars instead of baking into image
6. Pin base image — replace `nvidia-base:latest` with specific tag

## First-Time Setup (in browser)

1. Open Xfce terminal
2. Run `steam` — log in, install Total War: Three Kingdoms
3. Set Proton compatibility in Steam settings
4. Launch game once → saves persist to `/workspace` automatically

## What Failed Before (DO NOT RETRY)

- Moonlight/Sunshine — UDP required, RunPod blocks all UDP
- Chisel — Windows Defender flags as HackTool
- Tailscale/boringtun — no TUN device in unprivileged containers
- Parsec — no Linux hosting on consumer accounts
- Vast.ai + Moonlight — open UDP but driver instability

## BARAHIR: Arena Escalation Rule

3 unresolved iterations → escalate to Arena.AI immediately.

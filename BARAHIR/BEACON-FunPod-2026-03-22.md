# BEACON: FunPod 2026-03-22
**Target chat:** 7wiaoroocmfy3q
**Trigger:** `BEACON FunPod 2026-03-22`

## Current State
- **Active pod:** `hupikxf80hscfw` — A40, $0.43/hr, RUNNING
- **Pod volume:** 75GB container / 175GB at `/workspace`
- **Ports:** 8080/http, 8081/tcp, 22/tcp
- **Image:** `eruilu/funfunpod:latest` (just rebuilt)
- **Neko URL:** `https://hupikxf80hscfw-8080.proxy.runpod.net`
- **Neko password:** `neko` (admin: `admin`)
- **FunFunPodID registry:** set to `hupikxf80hscfw`

## Last Fix Applied
Dockerfile: removed xfce4/gstreamer apt installs (were overwriting CUDA GStreamer plugins from base image), added Xwrapper.config (`allowed_users=anybody`), hardcoded supervisord path to `/etc/neko/supervisord.conf`.

## Current Crash
Pod still 502 / neko exit status 2. Neko crashes before port 8080 is ready. Root cause not yet confirmed — likely GStreamer pipeline parse failure (`cudaupload`/`nvh264enc` still missing or supervisord config mismatch). RunPod assistant confirmed: `gave up: neko entered FATAL state`.

## Next Step
1. Paste to RunPod assistant: `What are the last 30 log lines for pod hupikxf80hscfw? Specifically the lines BEFORE the Go stacktrace — what is the first error message neko prints?`
2. If pipeline parse error → strip `NEKO_CAPTURE_VIDEO_PIPELINE` env var from Dockerfile, let neko use its default, rebuild/push
3. If supervisord config not found → check actual path with `find /etc -name supervisord.conf`
4. Redeploy fresh pod after each rebuild (`:latest` tag does not guarantee fresh pull on restart)

## Stack History (what failed)
- Parsec: DRM modesetting, Docker incompatible
- Moonlight/Sunshine: UDP blocked at RunPod network level
- Tailscale: needs /dev/net/tun, unavailable
- Chisel: flagged by Windows Defender
- **Current:** Neko (ghcr.io/m1k1o/neko/nvidia-base) — TCP mux, browser-based

## Files
- `Dockerfile` — main container definition
- `neko-init.sh` — Steam persistence symlinks, pulseaudio start
- `FunFunConnect.ps1` — Windows launcher (resume pod → poll 8080 → open browser)
- `build-and-push.ps1` — local build trigger

## Repo
`Eru-Iluvatar-the-One/FunPod-RunpodGaming` main branch
Docker Hub: `eruilu/funfunpod:latest`

## Session Fixes Done (this session, separate chat)
- Ctrl+Shift+G AHK hotkey → sync-all-repos.ps1 (live)
- sync-all-repos.ps1 dupes deleted (3 copies → 1 canonical at Shared/scripts/)
- MCP config expanded: D:\GitHub added to filesystem paths
- mcp-everything server written (ES CLI)
- mcp-fluent server written (named pipe)
- Both wired into claude_desktop_config.json

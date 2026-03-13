# HANDOFF — Runpod-Gaming
_Trigger phrase: `BARAHIR HANDOFF runpod-gaming`_

## Identity
Station IV. MCP active: filesystem, github, memory. Win10 LTSC client.

## Pod State
- Host: `66.92.198.162` port `11193`
- SSH relay: `ssh by8x28h0ciubu7-64411dcc@ssh.runpod.io`
- GPU: NVIDIA L4, BusID `PCI:0:36:0`, driver `570`
- Image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- Persistent volume: 150GB at `/workspace`
- Container: 75GB, 16 vCPU, 94GB RAM
- Pod ID: `by8x28h0ciubu7`, name: `respective_amber_rhinoceros`

## Repo
`https://github.com/Eru-Iluvatar-the-One/Runpod-Gaming` (public)
One file: `setup.sh`

## Goal
One-shot bash script: Xorg headless + Sunshine + supervisord → Moonlight streaming 4K@144Hz.
Game: Total War: Three Kingdoms (Steam 779340, Feral port).
Save sync: Backblaze B2 bucket `Funfun` via rclone.

## Script Status: v5 — BROKEN
Current failure: container has NO `/usr/bin/curl`, NO `/usr/bin/wget`, NO `/usr/bin/bash`.
- `bash` is at `/bin/bash`
- `curl`/`wget` not installed at all
- Process substitution `bash <(...)` fails because `/usr/bin/bash` missing

**FIX NEEDED in v6:**
Add at very top of script (before any downloads):
```bash
apt-get install -y curl wget 2>/dev/null || true
```
Then run command becomes:
```bash
python3 -c "import urllib.request; open('/tmp/s.sh','wb').write(urllib.request.urlopen('https://raw.githubusercontent.com/Eru-Iluvatar-the-One/Runpod-Gaming/main/setup.sh').read())" && /bin/bash /tmp/s.sh
```

## Script Config Values
- `ROOT_PASS=gondolin123`
- `DISP=:99`
- `LOG_DIR=/workspace/gaming-logs`
- `PKG_CACHE=/tmp/rp_pkgs`
- Sunshine v0.23.1, ubuntu-22.04-amd64.deb
- supervisord pidfile `/tmp/supervisord.pid`, socket `/tmp/supervisor.sock`
- Sunshine port 47989, web UI 47990
- B2: bucket `Funfun`, endpoint `s3.us-east-005.backblazeb2.com`, rclone remote `b2funfun`
- B2 env vars: `B2_KEY_ID`, `B2_APP_KEY` (user sets before running)

## Feral/Proton Paths
- Saves: `/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/Save Games`
- Packs: `/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/packs`
- Proton: `/root/.steam/steam/steamapps/compatdata/779340/pfx/drive_c/users/steamuser/Documents/My Games/Total War THREE KINGDOMS`

## PowerShell Tunnel (Win10 LTSC)
```powershell
ssh -N -L 47984:localhost:47984 -L 47989:localhost:47989 `
   -L 47990:localhost:47990 -L 48010:localhost:48010 `
   root@66.92.198.162 -p 11193 -o StrictHostKeyChecking=no `
   -o ServerAliveInterval=60 -o ServerAliveCountMax=10
```
Then Moonlight → Add PC → `127.0.0.1`
Note: UDP 47998-48000 needed for video — consider Tailscale or force Moonlight TCP.

## Bug History
- v1: `[[ ]] && exec sudo` + `set -e` = silent exit
- v2: LOG_DIR=/var/log (read-only in RunPod)
- v3: `exec &> >(tee ...)` dies silently in `bash <(wget)` context
- v4: wget doesn't exist in image
- v5: curl doesn't exist, bash not at /usr/bin/bash

## Next Action
Push v6: install curl+wget at top, update run command to use python3 download.
Then verify: Xorg OK, Sunshine OK, web UI reachable.
Then: SSH tunnel from Win10, Moonlight pair, launch game.

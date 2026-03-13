#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  RunPod Cloud Gaming Rig — God-Tier One-Shot Setup
#  GPU: NVIDIA L4/L40 | Ubuntu 22.04 | 4K@144Hz via Sunshine → Moonlight
#  Repo: github.com/Eru-Iluvatar-the-One/runpod-gaming-rig
# ═══════════════════════════════════════════════════════════════════════════
set -Eeuo pipefail
trap 'echo -e "\033[0;31m[FATAL] Error on line $LINENO — check ${LOG_DIR}/setup.log\033[0m"; exit 1' ERR

[[ $EUID -ne 0 ]] && exec sudo bash "$0" "$@"

# ─── USER CONFIG ────────────────────────────────────────────────────────────
ROOT_PASS="gondolin123"
DISP=":99"
SUNSHINE_VER="v0.23.1"
SUNSHINE_DEB_URL="https://github.com/LizardByte/Sunshine/releases/download/${SUNSHINE_VER}/sunshine-ubuntu-22.04-amd64.deb"
PKG_CACHE="/tmp/rp_pkgs"
LOG_DIR="/var/log/gaming"

# Backblaze B2 — export these before running, or hardcode here
B2_KEY_ID="${B2_KEY_ID:-}"
B2_APP_KEY="${B2_APP_KEY:-}"
B2_ENDPOINT="${B2_ENDPOINT:-s3.us-east-005.backblazeb2.com}"
B2_BUCKET="Funfun"

# RunPod SSH endpoint (from your Connect panel)
RUNPOD_HOST="66.92.198.162"
RUNPOD_SSH_PORT="11717"

# ─── INTERNALS ──────────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[0;34m'; N='\033[0m'
log()  { echo -e "${G}[$(date +%H:%M:%S)] ▶ $*${N}" | tee -a "${LOG_DIR}/setup.log"; }
warn() { echo -e "${Y}[WARN] $*${N}"                 | tee -a "${LOG_DIR}/setup.log"; }
die()  { echo -e "${R}[FATAL] $*${N}"               | tee -a "${LOG_DIR}/setup.log"; exit 1; }
step() { echo -e "${B}══════ $* ══════${N}"          | tee -a "${LOG_DIR}/setup.log"; }

mkdir -p "$LOG_DIR" "$PKG_CACHE"
exec > >(tee -a "${LOG_DIR}/setup.log") 2>&1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RunPod Gaming Rig — Setup Started @ $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ═══════════════════════════════════════════════════════════════════════════
step "1. SSH HARDENING"
# ═══════════════════════════════════════════════════════════════════════════
echo "root:${ROOT_PASS}" | chpasswd

SSHD_CFG="/etc/ssh/sshd_config"
sed -i 's/^#\?\s*PasswordAuthentication\s.*/PasswordAuthentication yes/'  "$SSHD_CFG"
sed -i 's/^#\?\s*PermitRootLogin\s.*/PermitRootLogin yes/'                "$SSHD_CFG"

grep -q "^PasswordAuthentication yes" "$SSHD_CFG" || echo "PasswordAuthentication yes" >> "$SSHD_CFG"
grep -q "^PermitRootLogin yes"        "$SSHD_CFG" || echo "PermitRootLogin yes"        >> "$SSHD_CFG"

# Restart SSH — handle systemd, sysvinit, and bare containers
service ssh restart 2>/dev/null \
  || systemctl restart ssh 2>/dev/null \
  || /etc/init.d/ssh restart 2>/dev/null \
  || (pkill -HUP sshd; sshd) 2>/dev/null \
  || warn "SSH restart failed — may need manual restart"

log "SSH: root login + password auth enabled (pass: ${ROOT_PASS})"

# ═══════════════════════════════════════════════════════════════════════════
step "2. GPU DETECTION"
# ═══════════════════════════════════════════════════════════════════════════
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 \
           || echo "UNKNOWN")
NVIDIA_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null \
             | head -1 | cut -d. -f1 \
             || echo "550")

log "GPU: ${GPU_NAME}  |  Driver: ${NVIDIA_VER}.x"

# nvidia-smi format: "00000000:00:1E.0"  →  Xorg format: "PCI:0:30:0"
PCI_RAW=$(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader 2>/dev/null \
          | head -1 \
          || lspci -D | grep -i nvidia | head -1 | awk '{print $1}')

# Strip leading domain (e.g. "00000000:")
PCI_CLEAN="${PCI_RAW#*:*:}"   # handles both "domain:bus:dev.fn" and "bus:dev.fn"
PCI_BUS=$(echo "$PCI_RAW" | awk -F'[.:]' '{
    # nvidia-smi gives 4-segment "0000:00:1e.0", lspci -D same
    n = split($0, a, /[.:]/);
    if (n == 4) { print a[2] } else { print a[1] }
}')
PCI_DEV=$(echo "$PCI_RAW" | awk -F'[.:]' '{
    n = split($0, a, /[.:]/);
    if (n == 4) { print a[3] } else { print a[2] }
}')
PCI_FN=$(echo "$PCI_RAW" | awk -F'[.]' '{print $NF}')

BUS_DEC=$((16#${PCI_BUS}))
DEV_DEC=$((16#${PCI_DEV}))
FN_DEC=$((16#${PCI_FN}))
XORG_BUSID="PCI:${BUS_DEC}:${DEV_DEC}:${FN_DEC}"

log "Xorg BusID: ${XORG_BUSID}  (raw: ${PCI_RAW})"

# ═══════════════════════════════════════════════════════════════════════════
step "3. PACKAGE EXTRACTION (EXDEV-safe: dpkg-deb -x)"
# ═══════════════════════════════════════════════════════════════════════════
log "Updating package lists..."
DEBIAN_FRONTEND=noninteractive apt-get update -qq 2>&1 | tail -5

# Helper: apt-get download → dpkg-deb -x into /
# Skips if the binary already exists.
deb_install() {
    local pkg="$1"
    local check_bin="${2:-}"
    if [[ -n "$check_bin" ]] && command -v "$check_bin" &>/dev/null; then
        log "  ✓ ${pkg} (already present)"; return 0
    fi
    local old_dir="$PWD"
    cd "$PKG_CACHE"
    if apt-get download "$pkg" -y 2>/dev/null; then
        local deb_file
        deb_file=$(ls -t "${pkg}"*.deb 2>/dev/null | head -1)
        if [[ -n "$deb_file" ]]; then
            dpkg-deb -x "$deb_file" /
            log "  ✓ ${pkg} extracted"
        else
            warn "  ✗ ${pkg} — deb not found after download"
        fi
    else
        warn "  ✗ ${pkg} — apt-get download failed (skipping)"
    fi
    cd "$old_dir"
}

# Core Xorg stack
deb_install "xserver-xorg-core"                          "Xorg"
deb_install "xserver-xorg-video-nvidia-${NVIDIA_VER}"   ""
deb_install "x11-xserver-utils"                          "xrandr"
deb_install "openbox"                                    "openbox"
deb_install "pulseaudio"                                 "pulseaudio"
deb_install "xkb-data"                                   ""

# ─── Sunshine ─────────────────────────────────────────────────────────────
SUNSHINE_BIN=$(command -v sunshine 2>/dev/null || true)
if [[ -z "$SUNSHINE_BIN" ]]; then
    log "Downloading Sunshine ${SUNSHINE_VER}..."
    cd "$PKG_CACHE"
    wget -q --show-progress -O sunshine.deb "$SUNSHINE_DEB_URL" \
      || die "Failed to download Sunshine — check URL: ${SUNSHINE_DEB_URL}"
    dpkg-deb -x sunshine.deb /
    chmod +x /usr/bin/sunshine 2>/dev/null || true
    SUNSHINE_BIN=$(find / -name sunshine -type f -executable 2>/dev/null | head -1)
    log "  ✓ Sunshine installed at: ${SUNSHINE_BIN}"
else
    log "  ✓ Sunshine already at: ${SUNSHINE_BIN}"
fi

ldconfig

# ═══════════════════════════════════════════════════════════════════════════
step "4. HARDWARE ENCODER: /dev/dri + libnvidia-encode"
# ═══════════════════════════════════════════════════════════════════════════
mkdir -p /dev/dri
[[ -e /dev/dri/card0 ]]      || mknod -m 660 /dev/dri/card0      c 226 0
[[ -e /dev/dri/renderD128 ]] || mknod -m 660 /dev/dri/renderD128 c 226 128
chown root:video /dev/dri/* 2>/dev/null || true
log "/dev/dri/card0 and renderD128 ready"

# Find the actual versioned library and symlink it
LIB_SRC=$(find /usr/lib /usr/local/lib /usr/local/nvidia/lib64 \
          -name "libnvidia-encode.so.*" 2>/dev/null \
          | grep -v "so\.1$" | sort -V | tail -1 || true)

if [[ -n "$LIB_SRC" ]]; then
    LIB_DIR="/usr/lib/x86_64-linux-gnu"
    mkdir -p "$LIB_DIR"
    ln -sf "$LIB_SRC" "${LIB_DIR}/libnvidia-encode.so.1"
    ln -sf "$LIB_SRC" "${LIB_DIR}/libnvidia-encode.so"
    ldconfig
    log "Linked: ${LIB_SRC} → ${LIB_DIR}/libnvidia-encode.so.1"
else
    warn "libnvidia-encode.so.* not found — NVENC encoding may fail"
    warn "Check: find /usr -name 'libnvidia-encode*'"
fi

# ═══════════════════════════════════════════════════════════════════════════
step "5. XORG CONFIGURATION (headless 4K@144)"
# ═══════════════════════════════════════════════════════════════════════════
mkdir -p /etc/X11

# CVT modeline for 3840x2160@144: cvt 3840 2160 144
# Calculated: 1975.68 MHz pixel clock
cat > /etc/X11/xorg.conf <<EOF
Section "ServerLayout"
    Identifier     "Sunshine"
    Screen      0  "Screen0"
    Option         "BlankTime"   "0"
    Option         "StandbyTime" "0"
    Option         "SuspendTime" "0"
    Option         "OffTime"     "0"
EndSection

Section "Device"
    Identifier     "GPU0"
    Driver         "nvidia"
    BusID          "${XORG_BUSID}"
    Option         "AllowEmptyInitialConfiguration" "true"
    Option         "ConnectedMonitor"               "DFP"
    Option         "HardDPMS"                       "false"
EndSection

Section "Monitor"
    Identifier     "VirtualMonitor"
    HorizSync      31.5-140.0
    VertRefresh    120.0-144.0
    Modeline       "3840x2160_144" 1975.68 3840 4152 4576 5312 2160 2163 2168 2237 -hsync +vsync
EndSection

Section "Screen"
    Identifier     "Screen0"
    Device         "GPU0"
    Monitor        "VirtualMonitor"
    DefaultDepth   24
    Option "ModeValidation" "NoMaxPClkCheck,NoEdidMaxPClkCheck,NoEdidDFPMaxSizeCheck,NoHorizSyncCheck,NoVertRefreshCheck,AllowNon60hzDFPModes"
    Option "MetaModes"      "3840x2160_144"
    SubSection "Display"
        Depth      24
        Modes      "3840x2160_144"
    EndSubSection
EndSection
EOF

log "xorg.conf written with BusID=${XORG_BUSID}"

# ═══════════════════════════════════════════════════════════════════════════
step "6. SUNSHINE CONFIG (x11 capture + nvenc)"
# ═══════════════════════════════════════════════════════════════════════════
mkdir -p /root/.config/sunshine

cat > /root/.config/sunshine/sunshine.conf <<EOF
# Sunshine — x11 capture + NVENC encoder
# Docs: https://docs.lizardbyte.dev/projects/sunshine/

capture        = x11
encoder        = nvenc
adapter_name   = /dev/dri/renderD128

# Display
output_name    = 0
resolutions    = [3840x2160, 2560x1440, 1920x1080]
fps            = [144, 60, 30]

# Network — localhost only; use SSH tunnel from Windows
address_family = ipv4
upnp           = disabled
port           = 47989

# Logging
min_log_level  = info
log_path       = ${LOG_DIR}/sunshine.log
EOF

# Set credentials programmatically (avoid interactive first-launch prompt)
if command -v sunshine &>/dev/null; then
    sunshine --creds admin "${ROOT_PASS}" 2>/dev/null \
      || warn "sunshine --creds failed — set credentials at https://<pod-ip>:47990"
fi

log "Sunshine configured: capture=x11, encoder=nvenc"

# ═══════════════════════════════════════════════════════════════════════════
step "7. GAME ASSET MIGRATION (.save + .pack from /workspace)"
# ═══════════════════════════════════════════════════════════════════════════

# Native Linux (Feral Interactive) paths
FERAL_SAVES="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/Save Games"
FERAL_PACKS="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/packs"

# Proton/Wine prefix paths (Steam app ID 779340)
PROTON_BASE="/root/.steam/steam/steamapps/compatdata/779340/pfx/drive_c/users/steamuser/Documents/My Games/Total War THREE KINGDOMS"

mkdir -p "$FERAL_SAVES" "$FERAL_PACKS"
mkdir -p "${PROTON_BASE}/save_games" "${PROTON_BASE}/pack" 2>/dev/null || true

SAVES_COUNT=0; PACKS_COUNT=0

while IFS= read -r -d '' f; do
    cp "$f" "$FERAL_SAVES/" 2>/dev/null || true
    cp "$f" "${PROTON_BASE}/save_games/" 2>/dev/null || true
    ((SAVES_COUNT++))
done < <(find /workspace -maxdepth 4 -name "*.save" -print0 2>/dev/null)

while IFS= read -r -d '' f; do
    cp "$f" "$FERAL_PACKS/" 2>/dev/null || true
    cp "$f" "${PROTON_BASE}/pack/" 2>/dev/null || true
    ((PACKS_COUNT++))
done < <(find /workspace -maxdepth 4 -name "*.pack" -print0 2>/dev/null)

log "Assets migrated: ${SAVES_COUNT} .save files, ${PACKS_COUNT} .pack files"
[[ $SAVES_COUNT -eq 0 ]] && warn "No .save files found in /workspace — place saves there and re-run migration"
[[ $PACKS_COUNT -eq 0 ]] && warn "No .pack files found in /workspace"

# ═══════════════════════════════════════════════════════════════════════════
step "8. BACKBLAZE B2 SYNC (rclone)"
# ═══════════════════════════════════════════════════════════════════════════
if [[ -n "$B2_KEY_ID" && -n "$B2_APP_KEY" ]]; then
    log "Setting up rclone + B2..."

    if ! command -v rclone &>/dev/null; then
        curl -fsSL https://rclone.org/install.sh | bash 2>&1 | tail -5
    fi

    mkdir -p /root/.config/rclone
    cat > /root/.config/rclone/rclone.conf <<EOF
[b2funfun]
type = s3
provider = Other
access_key_id = ${B2_KEY_ID}
secret_access_key = ${B2_APP_KEY}
endpoint = ${B2_ENDPOINT}
acl = private
no_check_bucket = true
EOF

    # Pull existing saves from B2 on startup
    log "  Pulling saves from B2 bucket: ${B2_BUCKET}..."
    rclone copy "b2funfun:${B2_BUCKET}/saves/" "$FERAL_SAVES/" --progress 2>/dev/null \
      || warn "  B2 pull failed (bucket may be empty — first run)"
    rclone copy "b2funfun:${B2_BUCKET}/packs/" "$FERAL_PACKS/" --progress 2>/dev/null || true

    # Sync script for cron + manual use
    cat > /usr/local/bin/b2-sync.sh <<SYNCEOF
#!/usr/bin/env bash
# B2 sync — push saves/packs to Backblaze Funfun bucket
FERAL_SAVES="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/Save Games"
FERAL_PACKS="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/packs"
rclone sync "\$FERAL_SAVES/" "b2funfun:${B2_BUCKET}/saves/" --progress --log-file="${LOG_DIR}/b2-sync.log"
rclone sync "\$FERAL_PACKS/" "b2funfun:${B2_BUCKET}/packs/" --progress --log-file="${LOG_DIR}/b2-sync.log"
echo "[$(date +%H:%M:%S)] B2 sync complete" >> "${LOG_DIR}/b2-sync.log"
SYNCEOF
    chmod +x /usr/local/bin/b2-sync.sh

    # Cron: push saves every 15 minutes
    ( crontab -l 2>/dev/null; \
      echo "*/15 * * * * /usr/local/bin/b2-sync.sh >> ${LOG_DIR}/b2-sync.log 2>&1" \
    ) | sort -u | crontab -

    log "  ✓ B2 sync ready — pushing every 15 min | manual: b2-sync.sh"
else
    warn "B2_KEY_ID / B2_APP_KEY not set — skipping B2 sync"
    warn "To enable: export B2_KEY_ID=<id> B2_APP_KEY=<key>  then re-run"
fi

# ═══════════════════════════════════════════════════════════════════════════
step "9. PULSEAUDIO VIRTUAL SINK"
# ═══════════════════════════════════════════════════════════════════════════
pulseaudio --daemonize --exit-idle-time=-1 2>/dev/null || true
sleep 1
pactl load-module module-null-sink \
    sink_name=virtual_out \
    sink_properties=device.description=VirtualSink 2>/dev/null || true
pactl set-default-sink virtual_out 2>/dev/null || true
log "PulseAudio virtual sink ready"

# ═══════════════════════════════════════════════════════════════════════════
step "10. SUPERVISORD (process persistence — survives terminal close)"
# ═══════════════════════════════════════════════════════════════════════════
pip3 install --quiet supervisor 2>&1 | tail -3

SUPD_BIN=$(command -v supervisord \
    || find /usr/local/bin /root/.local/bin -name supervisord 2>/dev/null | head -1 \
    || die "supervisord not found after pip install")

mkdir -p /etc/supervisor /var/log/supervisor

cat > /etc/supervisor/supervisord.conf <<EOF
[supervisord]
nodaemon          = false
user              = root
logfile           = ${LOG_DIR}/supervisord.log
logfile_maxbytes  = 50MB
loglevel          = info
pidfile           = /var/run/supervisord.pid

[unix_http_server]
file = /var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl = unix:///var/run/supervisor.sock

[program:xorg]
command          = Xorg ${DISP} -noreset +iglx -config /etc/X11/xorg.conf
autostart        = true
autorestart      = true
priority         = 10
startsecs        = 3
stdout_logfile   = ${LOG_DIR}/xorg.log
stderr_logfile   = ${LOG_DIR}/xorg.log
environment      = DISPLAY="${DISP}"

[program:openbox]
command          = openbox --display ${DISP}
autostart        = true
autorestart      = true
priority         = 20
startsecs        = 5
stdout_logfile   = ${LOG_DIR}/openbox.log
stderr_logfile   = ${LOG_DIR}/openbox.log
environment      = DISPLAY="${DISP}"

[program:sunshine]
command          = ${SUNSHINE_BIN:-sunshine} /root/.config/sunshine/sunshine.conf
autostart        = true
autorestart      = true
priority         = 30
startsecs        = 10
stdout_logfile   = ${LOG_DIR}/sunshine.log
stderr_logfile   = ${LOG_DIR}/sunshine.log
environment      = DISPLAY="${DISP}",HOME="/root",PULSE_SERVER="unix:/run/user/0/pulse/native"
EOF

# Kill any stale instances then launch fresh
pkill -f supervisord 2>/dev/null || true
sleep 2

nohup "$SUPD_BIN" -c /etc/supervisor/supervisord.conf \
    >> "${LOG_DIR}/supervisord-boot.log" 2>&1 &
SUPD_PID=$!
disown $SUPD_PID

log "supervisord PID=${SUPD_PID} — daemonized and disowned"

# ═══════════════════════════════════════════════════════════════════════════
step "11. WAIT FOR SERVICES + VERIFY"
# ═══════════════════════════════════════════════════════════════════════════
log "Waiting 15s for services to stabilize..."
sleep 15

XORG_OK=false; SUNSHINE_OK=false; OPENBOX_OK=false
pgrep -x Xorg    &>/dev/null && XORG_OK=true
pgrep -x openbox &>/dev/null && OPENBOX_OK=true
pgrep -f sunshine &>/dev/null && SUNSHINE_OK=true

POD_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "<pod-ip>")

# ═══════════════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RUNPOD GAMING RIG — READY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  GPU       : %s (driver %s)\n"  "$GPU_NAME"  "$NVIDIA_VER"
printf "  BusID     : %s\n"              "$XORG_BUSID"
printf "  Xorg      : %s\n"   "$( $XORG_OK     && echo '✓ Running' || echo '✗ FAILED')"
printf "  Openbox   : %s\n"   "$( $OPENBOX_OK  && echo '✓ Running' || echo '✗ FAILED')"
printf "  Sunshine  : %s\n"   "$( $SUNSHINE_OK && echo '✓ Running' || echo '✗ FAILED')"
printf "  Logs      : %s/\n"  "$LOG_DIR"
echo ""
echo "  ┌── SSH (direct) ───────────────────────────────────────────┐"
echo "  │  ssh root@${RUNPOD_HOST} -p ${RUNPOD_SSH_PORT}                    │"
echo "  │  password: ${ROOT_PASS}                                  │"
echo "  └────────────────────────────────────────────────────────────┘"
echo ""
echo "  ┌── WINDOWS 10 LTSC — PowerShell Tunnel (paste as-is) ──────┐"
cat <<'PSEOF'
  │                                                                  │
  │  ssh -N `                                                        │
  │    -L 47984:localhost:47984 `                                    │
  │    -L 47989:localhost:47989 `                                    │
  │    -L 47990:localhost:47990 `                                    │
  │    -L 48010:localhost:48010 `                                    │
  │    root@66.92.198.162 -p 11717 `                                 │
  │    -o StrictHostKeyChecking=no `                                 │
  │    -o ServerAliveInterval=60 `                                   │
  │    -o ServerAliveCountMax=10                                     │
  │                                                                  │
  │  Then in Moonlight: Add PC → 127.0.0.1                          │
  │                                                                  │
  │  ⚠ UDP WARNING: SSH tunnels TCP only. The Sunshine control      │
  │    ports (above) pair fine. For the actual video/audio stream,   │
  │    Moonlight needs UDP 47998-48000. Options:                     │
  │    1. Tailscale on pod + Windows (recommended, free)            │
  │    2. RunPod "Expose" the UDP port range when creating pod       │
  │    3. Sunshine TCP mode: add "moonlight_encryption = false"      │
  │       and use Moonlight with "Force TCP" in Advanced settings    │
  └──────────────────────────────────────────────────────────────────┘
PSEOF
echo ""
echo "  Sunshine Web UI : https://${POD_IP}:47990"
echo "  Credentials     : admin / ${ROOT_PASS}"
echo "  B2 Manual Sync  : /usr/local/bin/b2-sync.sh"
echo "  Supervisor CTL  : supervisorctl status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

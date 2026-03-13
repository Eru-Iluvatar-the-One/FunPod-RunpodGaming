#!/usr/bin/env bash
###############################################################################
#  RunPod Gaming Rig v7  —  GOD TIER ONE-SHOT
#  NVIDIA L40/L4 | Ubuntu 22.04 | Sunshine → Moonlight | 4K@144Hz
#
#  Fixes: EXDEV, curl/wget missing, NVENC symlink, headless Xorg,
#         terminal auto-close, SSH auth, /dev/dri nodes
###############################################################################

exec > >(tee /workspace/gaming-logs/setup.log) 2>&1
set -uo pipefail   # NOT -e — we handle errors per-command

SECONDS=0
mkdir -p /workspace/gaming-logs

# ═══════════════════════════════════════════════════════════════
#  TUNABLES
# ═══════════════════════════════════════════════════════════════
DISPLAY_NUM=99
export DISPLAY=":${DISPLAY_NUM}"
RES_W=3840; RES_H=2160; RES_HZ=144
ROOT_PASS="gondolin123"
RUNPOD_HOST="66.92.198.162"
RUNPOD_SSH_PORT="11193"
B2_BUCKET="Funfun"
B2_ENDPOINT="${B2_ENDPOINT:-s3.us-east-005.backblazeb2.com}"
B2_KEY_ID="${B2_KEY_ID:-}"
B2_APP_KEY="${B2_APP_KEY:-}"
FERAL_SAVES="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/Save Games"
FERAL_PACKS="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/packs"
PROTON_BASE="/root/.steam/steam/steamapps/compatdata/779340/pfx/drive_c/users/steamuser/Documents/My Games/Total War THREE KINGDOMS"
LOG_DIR="/workspace/gaming-logs"

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[1;34m'; C='\033[0;36m'; N='\033[0m'
log()  { printf "${G}[✓ %s]${N} %s\n" "$(date +%H:%M:%S)" "$*"; }
warn() { printf "${Y}[⚠ %s]${N} %s\n" "$(date +%H:%M:%S)" "$*"; }
err()  { printf "${R}[✗ %s]${N} %s\n" "$(date +%H:%M:%S)" "$*"; }
hdr()  { printf "\n${B}━━━ %s ━━━${N}\n" "$*"; }

# EXDEV-safe installer
# dpkg rename() fails across overlay+bind-mount boundaries.
# Fallback: apt-get install -d downloads debs, dpkg-deb -x extracts via tar (no rename).
safe_install() {
    local pkgs=("$@")
    log "apt install: ${pkgs[*]}"
    if DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${pkgs[@]}" 2>/dev/null; then
        return 0
    fi
    warn "EXDEV fallback for: ${pkgs[*]}"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -d --no-install-recommends "${pkgs[@]}" 2>/dev/null || true
    for pkg in "${pkgs[@]}"; do
        ( cd /tmp && apt-get download "$pkg" 2>/dev/null ) || true
    done
    local n=0
    for deb in /var/cache/apt/archives/*.deb /tmp/*.deb; do
        [ -f "$deb" ] || continue
        dpkg-deb -x "$deb" / 2>/dev/null && ((n++)) || true
    done
    rm -f /tmp/*.deb 2>/dev/null
    ldconfig 2>/dev/null
    log "Extracted ${n} debs via dpkg-deb -x"
}

###############################################################################
hdr "0 — BOOTSTRAP (curl/wget before anything touches the network)"
###############################################################################
apt-get install -y curl wget 2>/dev/null || true
log "curl/wget ensured"

###############################################################################
hdr "1 — SSH  (password: ${ROOT_PASS})"
###############################################################################
echo "root:${ROOT_PASS}" | chpasswd
CFG=/etc/ssh/sshd_config
sed -i \
    -e 's/^#*\s*PasswordAuthentication\s.*/PasswordAuthentication yes/' \
    -e 's/^#*\s*PermitRootLogin\s.*/PermitRootLogin yes/' \
    "$CFG"
grep -q '^PasswordAuthentication yes' "$CFG" || echo 'PasswordAuthentication yes' >> "$CFG"
grep -q '^PermitRootLogin yes'        "$CFG" || echo 'PermitRootLogin yes'        >> "$CFG"
service ssh restart 2>/dev/null \
    || systemctl restart ssh 2>/dev/null \
    || /etc/init.d/ssh restart 2>/dev/null \
    || pkill -x sshd 2>/dev/null && sleep 0.5 && /usr/sbin/sshd 2>/dev/null || true
log "SSHD — PasswordAuthentication yes, PermitRootLogin yes"

###############################################################################
hdr "2 — PACKAGES"
###############################################################################
export DEBIAN_FRONTEND=noninteractive
add-apt-repository -y universe 2>/dev/null || true
apt-get update -qq 2>/dev/null || warn "apt-get update failed"

safe_install xserver-xorg-core x11-xserver-utils x11-utils xinit xterm xdotool openbox dbus-x11
safe_install pulseaudio pulseaudio-utils alsa-utils
safe_install wget curl rsync jq mesa-utils xkb-data xauth

# supervisord via pip3 (apt path often EXDEV in PyTorch image)
pip3 install --quiet supervisor 2>/dev/null || true
SUPD=$(command -v supervisord 2>/dev/null \
    || find /usr/local/bin /root/.local/bin /usr/bin -name supervisord 2>/dev/null | head -1 || true)
[ -z "$SUPD" ] && { safe_install supervisor; SUPD=$(command -v supervisord 2>/dev/null || true); }
[ -z "$SUPD" ] && { err "supervisord not found — cannot continue"; exit 1; }
SUPC=$(command -v supervisorctl 2>/dev/null \
    || find /usr/local/bin /root/.local/bin /usr/bin -name supervisorctl 2>/dev/null | head -1 || true)
[ -n "$SUPC" ] && ln -sf "$SUPC" /usr/local/bin/supervisorctl 2>/dev/null || true
log "supervisord: $SUPD"

mkdir -p /etc/supervisor/conf.d

###############################################################################
hdr "3 — GPU  (BusID + /dev/dri)"
###############################################################################
mkdir -p /dev/dri
[ -e /dev/dri/card0      ] || mknod -m 666 /dev/dri/card0      c 226 0
[ -e /dev/dri/renderD128 ] || mknod -m 666 /dev/dri/renderD128 c 226 128
log "/dev/dri nodes OK"

GPU_NAME=$(nvidia-smi --query-gpu=name           --format=csv,noheader 2>/dev/null | head -1 || echo "UNKNOWN")
DRV_FULL=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "570.0")
DRV_MAJ=$(echo "$DRV_FULL" | cut -d. -f1)
BUS_RAW=$(nvidia-smi --query-gpu=pci.bus_id     --format=csv,noheader 2>/dev/null | head -1 || echo "0000:00:1e.0")
# parse  00000000:41:00.0  →  PCI:65:0:0
BUS_BDF=$(echo "$BUS_RAW" | sed 's/^[0-9A-Fa-f]*://')   # "41:00.0"
B_HEX=$(echo "$BUS_BDF" | cut -d: -f1)
D_HEX=$(echo "$BUS_BDF" | cut -d: -f2 | cut -d. -f1)
F_DEC=$(echo "$BUS_BDF" | cut -d. -f2)
GPU_BUSID="PCI:$((16#${B_HEX})):$((16#${D_HEX})):${F_DEC}"
log "GPU=$GPU_NAME  drv=$DRV_MAJ  BusID=$GPU_BUSID"

# nvidia DDX
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    "xserver-xorg-video-nvidia-${DRV_MAJ}" 2>/dev/null \
    || warn "xserver-xorg-video-nvidia-${DRV_MAJ} not in apt — modesetting fallback"

###############################################################################
hdr "4 — NVENC  (libnvidia-encode.so.1 symlink)"
###############################################################################
NVENC_REAL=""
for sd in /usr/lib/x86_64-linux-gnu /usr/local/nvidia/lib64 /usr/lib64 \
          /usr/local/lib /run/nvidia/driver/usr/lib/x86_64-linux-gnu; do
    c=$(find "$sd" -maxdepth 1 -name "libnvidia-encode.so.*" \
        ! -name "libnvidia-encode.so.1" 2>/dev/null | sort -V | tail -1)
    [ -n "$c" ] && { NVENC_REAL="$c"; break; }
done
LINK_DIR="/usr/lib/x86_64-linux-gnu"
if [ -n "$NVENC_REAL" ]; then
    ln -sf "$NVENC_REAL"                       "${LINK_DIR}/libnvidia-encode.so.1" 2>/dev/null \
        || cp -f "$NVENC_REAL"                 "${LINK_DIR}/libnvidia-encode.so.1"
    ln -sf "${LINK_DIR}/libnvidia-encode.so.1" "${LINK_DIR}/libnvidia-encode.so"
    { echo "$LINK_DIR"; echo "$(dirname "$NVENC_REAL")"; } > /etc/ld.so.conf.d/nvenc.conf
    ldconfig
    log "NVENC → $NVENC_REAL"
else
    err "libnvidia-encode.so not found — NVENC will fail"
fi

CUDA_REAL=$(find /usr/lib/x86_64-linux-gnu /usr/local/nvidia/lib64 /usr/lib64 \
    -maxdepth 1 -name "libcuda.so.*" ! -name "libcuda.so.1" 2>/dev/null | head -1 || true)
[ -n "$CUDA_REAL" ] && { ln -sf "$CUDA_REAL" "${LINK_DIR}/libcuda.so.1" 2>/dev/null; ldconfig; log "libcuda.so.1 linked"; }

###############################################################################
hdr "5 — XORG CONFIG  (${RES_W}×${RES_H}@${RES_HZ}Hz)"
###############################################################################
# Fix nvidia_drv.so cross-device symlinks
for p in /usr/lib/xorg/modules/drivers/nvidia_drv.so \
         /usr/lib/x86_64-linux-gnu/nvidia/xorg/nvidia_drv.so \
         /usr/lib/x86_64-linux-gnu/xorg/extra-modules/nvidia_drv.so; do
    [ -L "$p" ] && { r=$(readlink -f "$p"); cp --remove-destination "$r" "$p" 2>/dev/null && log "Fixed symlink: $p"; }
done

XORG_BIN=$(command -v Xorg 2>/dev/null || find / -name Xorg -type f -executable 2>/dev/null | head -1 || true)
[ -z "$XORG_BIN" ] && { err "Xorg binary not found"; exit 1; }
log "Xorg: $XORG_BIN"

mkdir -p /etc/X11
cat > /etc/X11/xorg.conf << XORGEOF
Section "ServerLayout"
    Identifier     "Layout0"
    Screen      0  "Screen0"
    Option         "BlankTime"   "0"
    Option         "StandbyTime" "0"
    Option         "SuspendTime" "0"
    Option         "OffTime"     "0"
EndSection

Section "Monitor"
    Identifier     "Monitor0"
    HorizSync       30-700
    VertRefresh     50-${RES_HZ}
    Modeline       "${RES_W}x${RES_H}_${RES_HZ}" 1829.25 ${RES_W} 3888 3920 4000 ${RES_H} 2163 2168 2235 +hsync -vsync
    Option         "DPMS" "false"
EndSection

Section "Device"
    Identifier     "Device0"
    Driver         "nvidia"
    BusID          "${GPU_BUSID}"
    Option         "AllowEmptyInitialConfiguration" "True"
    Option         "ConnectedMonitor"  "DP-0"
    Option         "UseDisplayDevice"  "DP-0"
    Option         "UseEDID"           "False"
    Option         "HardDPMS"          "False"
    Option         "ModeValidation"    "NoMaxPClkCheck,NoEdidMaxPClkCheck,NoMaxSizeCheck,NoHorizSyncCheck,NoVertRefreshCheck,NoVirtualSizeCheck,NoExtendedGpuCapabilitiesCheck,NoTotalSizeCheck,NoDualLinkDVICheck,NoDisplayPortBandwidthCheck,AllowNon3DVisionModes"
EndSection

Section "Screen"
    Identifier     "Screen0"
    Device         "Device0"
    Monitor        "Monitor0"
    DefaultDepth    24
    Option         "MetaModes"   "DP-0: ${RES_W}x${RES_H}_${RES_HZ} +0+0"
    Option         "TripleBuffer" "on"
    SubSection     "Display"
        Depth       24
        Modes      "${RES_W}x${RES_H}_${RES_HZ}" "${RES_W}x${RES_H}" "2560x1440" "1920x1080"
    EndSubSection
EndSection
XORGEOF
log "xorg.conf written ($GPU_BUSID)"

###############################################################################
hdr "6 — SUNSHINE"
###############################################################################
if ! command -v sunshine &>/dev/null; then
    log "Downloading Sunshine..."
    # Try latest release from GitHub API, fall back to known-good
    SUN_URL=$(curl -fsSL https://api.github.com/repos/LizardByte/Sunshine/releases/latest 2>/dev/null \
        | python3 -c "import sys,json; r=json.load(sys.stdin); \
          print(next((a['browser_download_url'] for a in r['assets'] \
          if 'ubuntu-22.04-amd64' in a['name'] and a['name'].endswith('.deb')),''))" 2>/dev/null || true)
    [ -z "$SUN_URL" ] && \
        SUN_URL="https://github.com/LizardByte/Sunshine/releases/download/v0.23.1/sunshine-ubuntu-22.04-amd64.deb"
    curl -fsSL "$SUN_URL" -o /tmp/sunshine.deb
    dpkg -i /tmp/sunshine.deb 2>/dev/null || { warn "dpkg -i EXDEV — extracting"; dpkg-deb -x /tmp/sunshine.deb /; ldconfig; }
    rm -f /tmp/sunshine.deb
fi
SUN_BIN=$(command -v sunshine 2>/dev/null \
    || find /usr/bin /usr/local/bin -name sunshine -type f 2>/dev/null | head -1 || true)
[ -z "$SUN_BIN" ] && { err "sunshine binary not found"; exit 1; }
log "Sunshine: $SUN_BIN"

mkdir -p /root/.config/sunshine
cat > /root/.config/sunshine/sunshine.conf << 'SUNEOF'
bind_address     = 127.0.0.1
port             = 47989
upnp             = off
origin_web_ui_allowed = pc
address_family   = ipv4
capture          = x11
encoder          = nvenc
adapter_name     = /dev/dri/renderD128
output_name      = 0
resolutions      = [3840x2160, 2560x1440, 1920x1080]
fps              = [144, 60, 30]
nv_preset        = p4
nv_tune          = ll
nv_rc            = cbr
min_log_level    = info
SUNEOF

"$SUN_BIN" --creds admin gondolin123 2>/dev/null || warn "sunshine --creds failed — set in web UI"
log "Sunshine configured (admin / gondolin123)"

###############################################################################
hdr "7 — GAME ASSETS"
###############################################################################
mkdir -p "$FERAL_SAVES" "$FERAL_PACKS" "${PROTON_BASE}/save_games" "${PROTON_BASE}/pack"
SC=0; PC=0
while IFS= read -r -d '' f; do
    cp "$f" "$FERAL_SAVES/"              2>/dev/null || true
    cp "$f" "${PROTON_BASE}/save_games/" 2>/dev/null || true
    ((SC++))
done < <(find /workspace -maxdepth 4 -name "*.save" -print0 2>/dev/null || true)
while IFS= read -r -d '' f; do
    cp "$f" "$FERAL_PACKS/"        2>/dev/null || true
    cp "$f" "${PROTON_BASE}/pack/" 2>/dev/null || true
    ((PC++))
done < <(find /workspace -maxdepth 4 -name "*.pack" -print0 2>/dev/null || true)
log "Assets: $SC .save  $PC .pack"

###############################################################################
hdr "8 — B2 SYNC"
###############################################################################
if [ -n "$B2_KEY_ID" ] && [ -n "$B2_APP_KEY" ]; then
    command -v rclone &>/dev/null || curl -fsSL https://rclone.org/install.sh | bash 2>/dev/null
    mkdir -p /root/.config/rclone
    cat > /root/.config/rclone/rclone.conf << RCONF
[b2funfun]
type = s3
provider = Other
access_key_id = ${B2_KEY_ID}
secret_access_key = ${B2_APP_KEY}
endpoint = ${B2_ENDPOINT}
acl = private
no_check_bucket = true
RCONF
    rclone copy "b2funfun:${B2_BUCKET}/saves/" "$FERAL_SAVES/" 2>/dev/null || warn "B2 pull empty"
    rclone copy "b2funfun:${B2_BUCKET}/packs/" "$FERAL_PACKS/" 2>/dev/null || true
    cat > /usr/local/bin/b2-sync.sh << SYNC
#!/usr/bin/env bash
rclone sync "${FERAL_SAVES}/" "b2funfun:${B2_BUCKET}/saves/" --log-file="${LOG_DIR}/b2.log"
rclone sync "${FERAL_PACKS}/" "b2funfun:${B2_BUCKET}/packs/" --log-file="${LOG_DIR}/b2.log"
echo "[B2 \$(date +%H:%M:%S)] done" >> "${LOG_DIR}/b2.log"
SYNC
    chmod +x /usr/local/bin/b2-sync.sh
    (crontab -l 2>/dev/null; echo "*/15 * * * * /usr/local/bin/b2-sync.sh") | sort -u | crontab -
    log "B2 configured"
else
    warn "B2 skipped — export B2_KEY_ID + B2_APP_KEY to enable"
fi

###############################################################################
hdr "9 — PULSEAUDIO"
###############################################################################
pulseaudio --daemonize --exit-idle-time=-1 2>/dev/null || true
sleep 1
pactl load-module module-null-sink sink_name=virtual_out 2>/dev/null || true
pactl set-default-sink virtual_out 2>/dev/null || true
log "PulseAudio virtual sink ready"

###############################################################################
hdr "10 — SUPERVISOR"
###############################################################################
pkill -x supervisord 2>/dev/null; sleep 1
pkill -x Xorg       2>/dev/null || true
pkill -x sunshine   2>/dev/null || true

mkdir -p /run/user/0; chmod 700 /run/user/0

cat > /etc/supervisor/supervisord.conf << SUPCONF
[supervisord]
nodaemon=false
user=root
logfile=${LOG_DIR}/supervisord.log
logfile_maxbytes=20MB
loglevel=info
pidfile=/tmp/supervisord.pid

[unix_http_server]
file=/tmp/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

[include]
files = /etc/supervisor/conf.d/*.conf
SUPCONF

cat > /etc/supervisor/conf.d/pulseaudio.conf << 'EOF'
[program:pulseaudio]
command=/usr/bin/pulseaudio --system --disallow-exit --exit-idle-time=-1 --log-target=stderr
user=root
autorestart=true
startretries=99
startsecs=2
priority=5
stdout_logfile=/workspace/gaming-logs/pulse.log
stderr_logfile=/workspace/gaming-logs/pulse.log
environment=HOME="/root"
EOF

cat > /etc/supervisor/conf.d/xorg.conf << XSEOF
[program:xorg]
command=${XORG_BIN} :${DISPLAY_NUM} -noreset +extension GLX +extension RANDR +extension RENDER -config /etc/X11/xorg.conf -logfile ${LOG_DIR}/Xorg.${DISPLAY_NUM}.log
user=root
autorestart=true
startretries=10
startsecs=3
priority=10
stdout_logfile=${LOG_DIR}/xorg.log
stderr_logfile=${LOG_DIR}/xorg.log
environment=HOME="/root"
XSEOF

cat > /etc/supervisor/conf.d/openbox.conf << OBSEOF
[program:openbox]
command=/usr/bin/openbox-session
user=root
autorestart=true
startretries=5
startsecs=3
priority=15
stdout_logfile=${LOG_DIR}/openbox.log
stderr_logfile=${LOG_DIR}/openbox.log
environment=DISPLAY=":${DISPLAY_NUM}",HOME="/root"
OBSEOF

cat > /etc/supervisor/conf.d/sunshine.conf << SSEOF
[program:sunshine]
command=${SUN_BIN} /root/.config/sunshine/sunshine.conf
user=root
autorestart=true
startretries=10
startsecs=8
priority=20
stdout_logfile=${LOG_DIR}/sunshine.log
stderr_logfile=${LOG_DIR}/sunshine.log
environment=DISPLAY=":${DISPLAY_NUM}",HOME="/root",XDG_RUNTIME_DIR="/run/user/0",LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib64"
SSEOF

###############################################################################
hdr "11 — LAUNCH  (daemonized — survives terminal close)"
###############################################################################
nohup "$SUPD" -c /etc/supervisor/supervisord.conf >> "${LOG_DIR}/supervisord-boot.log" 2>&1 &
disown

log "supervisord launched — waiting 20s for services..."
sleep 20

supervisorctl -c /etc/supervisor/supervisord.conf status 2>/dev/null | sed 's/^/    /' \
    || warn "supervisorctl not responding yet"

###############################################################################
hdr "12 — VERIFY"
###############################################################################
PASS=0; FAIL=0
pgrep -x sshd    &>/dev/null && { printf "  ${G}✓${N}  SSHD\n"; ((PASS++)); } || { printf "  ${R}✗${N}  SSHD\n"; ((FAIL++)); }
xdpyinfo -display ":${DISPLAY_NUM}" &>/dev/null && { MODE=$(DISPLAY=":${DISPLAY_NUM}" xrandr 2>/dev/null | grep '\*' | awk '{print $1}' | head -1); printf "  ${G}✓${N}  Xorg :${DISPLAY_NUM} — ${MODE:-?}\n"; ((PASS++)); } || { printf "  ${R}✗${N}  Xorg :${DISPLAY_NUM}\n"; ((FAIL++)); warn "check ${LOG_DIR}/Xorg.${DISPLAY_NUM}.log"; }
ldconfig -p 2>/dev/null | grep -q libnvidia-encode.so.1 && { printf "  ${G}✓${N}  NVENC in ldconfig\n"; ((PASS++)); } || { printf "  ${Y}⚠${N}  NVENC not in ldconfig\n"; ((FAIL++)); }
[ -c /dev/dri/renderD128 ] && { printf "  ${G}✓${N}  /dev/dri/renderD128\n"; ((PASS++)); } || { printf "  ${R}✗${N}  /dev/dri/renderD128\n"; ((FAIL++)); }
pgrep -f sunshine &>/dev/null && { printf "  ${G}✓${N}  Sunshine (127.0.0.1:47989)\n"; ((PASS++)); } || { printf "  ${R}✗${N}  Sunshine\n"; ((FAIL++)); warn "check ${LOG_DIR}/sunshine.log"; }
printf "  ${G}✓${N}  GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)\n"
echo ""
printf "  Result: ${G}${PASS} passed${N} / "
[ "$FAIL" -gt 0 ] && printf "${R}${FAIL} failed${N}\n" || printf "${G}0 failed${N}\n"

###############################################################################
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " DONE  —  RunPod Gaming Rig v7  —  ${SECONDS}s"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SSH:     ssh root@${RUNPOD_HOST} -p ${RUNPOD_SSH_PORT}"
echo " Pass:    ${ROOT_PASS}"
echo ""
echo " PowerShell tunnel:"
echo "   ssh -N -L 47984:localhost:47984 -L 47989:localhost:47989 \\"
echo "      -L 47990:localhost:47990 -L 48010:localhost:48010 \\"
echo "      root@${RUNPOD_HOST} -p ${RUNPOD_SSH_PORT} -o StrictHostKeyChecking=no"
echo ""
echo " Moonlight: Add PC → 127.0.0.1"
echo " Web UI:    https://127.0.0.1:47990  (admin / gondolin123)"
echo ""
echo " Logs:"
echo "   supervisorctl -c /etc/supervisor/supervisord.conf status"
echo "   tail -f ${LOG_DIR}/sunshine.log"
echo "   tail -f ${LOG_DIR}/Xorg.${DISPLAY_NUM}.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
###############################################################################

# Keep Jupyter terminal open so you can read output
if [ -n "${JUPYTER_TOKEN:-}" ] || [ -n "${JUPYTER_RUNTIME_DIR:-}" ] || [ -n "${JPY_PARENT_PID:-}" ]; then
    log "Jupyter detected — terminal staying open (services are daemonized)"
    exec sleep infinity
fi

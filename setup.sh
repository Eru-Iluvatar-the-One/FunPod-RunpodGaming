#!/usr/bin/env bash
# RunPod Gaming Rig v6
# NVIDIA L4 | Ubuntu 22.04 | Sunshine -> Moonlight | 4K@144Hz

set -e

LOG_DIR="/workspace/gaming-logs"
PKG_CACHE="/tmp/rp_pkgs"
mkdir -p "$LOG_DIR" "$PKG_CACHE"
LOG="$LOG_DIR/setup.log"

step() { echo "=== $* ==="; echo "=== $* ===" >> "$LOG"; }
log()  { echo "[OK] $*";    echo "[OK] $*"    >> "$LOG"; }
warn() { echo "[WARN] $*";  echo "[WARN] $*"  >> "$LOG"; }
die()  { echo "[FATAL] $*"; echo "[FATAL] $*" >> "$LOG"; exit 1; }

echo "============================================"
echo " RunPod Gaming Rig v6 -- $(date)"
echo " Log: $LOG"
echo "============================================"

# CONFIG
ROOT_PASS="gondolin123"
DISP=":99"
SUNSHINE_VER="v0.23.1"
SUNSHINE_URL="https://github.com/LizardByte/Sunshine/releases/download/${SUNSHINE_VER}/sunshine-ubuntu-22.04-amd64.deb"
RUNPOD_HOST="66.92.198.162"
RUNPOD_SSH_PORT="11193"
B2_BUCKET="Funfun"
B2_ENDPOINT="${B2_ENDPOINT:-s3.us-east-005.backblazeb2.com}"
B2_KEY_ID="${B2_KEY_ID:-}"
B2_APP_KEY="${B2_APP_KEY:-}"
FERAL_SAVES="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/Save Games"
FERAL_PACKS="/root/.local/share/feral-interactive/Total War THREE KINGDOMS/User Data/packs"
PROTON_BASE="/root/.steam/steam/steamapps/compatdata/779340/pfx/drive_c/users/steamuser/Documents/My Games/Total War THREE KINGDOMS"

# 0. BOOTSTRAP TOOLS
step "0. BOOTSTRAP TOOLS"
apt-get install -y curl wget 2>/dev/null || true
log "curl/wget ensured"

# 1. SSH
step "1. SSH"
echo "root:${ROOT_PASS}" | chpasswd >> "$LOG" 2>&1
CFG=/etc/ssh/sshd_config
sed -i 's/^#*\s*PasswordAuthentication\s.*/PasswordAuthentication yes/' "$CFG"
sed -i 's/^#*\s*PermitRootLogin\s.*/PermitRootLogin yes/' "$CFG"
grep -q "^PasswordAuthentication yes" "$CFG" || echo "PasswordAuthentication yes" >> "$CFG"
grep -q "^PermitRootLogin yes"        "$CFG" || echo "PermitRootLogin yes"        >> "$CFG"
service ssh restart >> "$LOG" 2>&1 \
  || systemctl restart ssh >> "$LOG" 2>&1 \
  || /etc/init.d/ssh restart >> "$LOG" 2>&1 \
  || warn "SSH restart failed"
log "SSH OK (root:${ROOT_PASS})"

# 2. GPU
step "2. GPU DETECTION"
GPU_NAME=$(nvidia-smi --query-gpu=name           --format=csv,noheader 2>/dev/null | head -1 || echo "UNKNOWN")
DRV_FULL=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "570.0")
DRV_MAJ=$(echo "$DRV_FULL" | cut -d. -f1)
PCI_RAW=$(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader 2>/dev/null | head -1 \
          || echo "0000:00:1e.0")
BUS=$(echo "$PCI_RAW" | awk -F: '{if(NF==4)print $2; else print $1}' | tr -d ' ')
DEV=$(echo "$PCI_RAW" | awk -F: '{if(NF==4)print $3; else print $2}' | cut -d. -f1 | tr -d ' ')
FUN=$(echo "$PCI_RAW" | awk -F. '{print $NF}' | tr -d ' ')
XORG_BUSID="PCI:$((16#$BUS)):$((16#$DEV)):$((16#$FUN))"
log "GPU=$GPU_NAME  DRV=$DRV_MAJ  BusID=$XORG_BUSID"

# 3. PACKAGES
step "3. PACKAGES"
# Enable universe for openbox/pulseaudio
add-apt-repository -y universe >> "$LOG" 2>&1 || true
DEBIAN_FRONTEND=noninteractive apt-get update -qq >> "$LOG" 2>&1 || warn "apt-get update failed"

apt_install() {
  local pkg="$1" chk="${2:-}"
  [ -n "$chk" ] && command -v "$chk" >/dev/null 2>&1 && { log "  skip $pkg"; return 0; }
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$pkg" >> "$LOG" 2>&1 \
    && log "  installed $pkg" \
    || warn "  failed $pkg"
}

apt_install "xserver-xorg-core"    "Xorg"
apt_install "x11-xserver-utils"    "xrandr"
apt_install "openbox"              "openbox"
apt_install "pulseaudio"           "pulseaudio"
apt_install "xkb-data"             ""
apt_install "xauth"                ""
# nvidia DDX — version-matched; warn-only if missing (host driver handles rendering)
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  "xserver-xorg-video-nvidia-${DRV_MAJ}" >> "$LOG" 2>&1 \
  || warn "xserver-xorg-video-nvidia-${DRV_MAJ} not in apt — Xorg will use modesetting driver"

# Sunshine — curl, not wget
if ! command -v sunshine >/dev/null 2>&1; then
  log "Downloading Sunshine ${SUNSHINE_VER}..."
  curl -fsSL -o "$PKG_CACHE/sunshine.deb" "$SUNSHINE_URL" \
    || die "Sunshine download failed"
  # dpkg install tries hardlinks across filesystems if /tmp != / — use -x to extract directly
  dpkg-deb -x "$PKG_CACHE/sunshine.deb" / >> "$LOG" 2>&1
  chmod +x /usr/bin/sunshine 2>/dev/null || true
fi
SUNSHINE_BIN=$(command -v sunshine 2>/dev/null \
  || find /usr/bin /usr/local/bin -name sunshine 2>/dev/null | head -1 || true)
[ -z "$SUNSHINE_BIN" ] && die "sunshine binary not found"
ldconfig >> "$LOG" 2>&1
log "Sunshine at $SUNSHINE_BIN"

# 4. HARDWARE ENCODER
step "4. HARDWARE ENCODER"
mkdir -p /dev/dri
[ -e /dev/dri/card0 ]      || mknod -m 660 /dev/dri/card0      c 226 0
[ -e /dev/dri/renderD128 ] || mknod -m 660 /dev/dri/renderD128 c 226 128
chown root:video /dev/dri/* 2>/dev/null || true
log "/dev/dri nodes OK"

NVENC=$(find /usr/lib /usr/local/lib /usr/local/nvidia/lib64 \
  -name "libnvidia-encode.so.*" 2>/dev/null | grep -v 'so\.1$' | sort -V | tail -1 || true)
if [ -n "$NVENC" ]; then
  mkdir -p /usr/lib/x86_64-linux-gnu
  ln -sf "$NVENC" /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1
  ln -sf "$NVENC" /usr/lib/x86_64-linux-gnu/libnvidia-encode.so
  ldconfig >> "$LOG" 2>&1
  log "libnvidia-encode -> $NVENC"
else
  warn "libnvidia-encode not found — NVENC may fail"
fi

# 5. XORG CONFIG
step "5. XORG CONFIG"
mkdir -p /etc/X11
cat > /etc/X11/xorg.conf << XORGEOF
Section "ServerLayout"
    Identifier "Sunshine"
    Screen 0 "Screen0"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection

Section "Device"
    Identifier "GPU0"
    Driver "nvidia"
    BusID "${XORG_BUSID}"
    Option "AllowEmptyInitialConfiguration" "true"
    Option "ConnectedMonitor" "DFP"
    Option "HardDPMS" "false"
EndSection

Section "Monitor"
    Identifier "VirtualMonitor"
    HorizSync  31.5-140.0
    VertRefresh 120.0-144.0
    Modeline "3840x2160_144" 1975.68 3840 4152 4576 5312 2160 2163 2168 2237 -hsync +vsync
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "GPU0"
    Monitor "VirtualMonitor"
    DefaultDepth 24
    Option "ModeValidation" "NoMaxPClkCheck,NoEdidMaxPClkCheck,NoEdidDFPMaxSizeCheck,NoHorizSyncCheck,NoVertRefreshCheck,AllowNon60hzDFPModes"
    Option "MetaModes" "3840x2160_144"
    SubSection "Display"
        Depth 24
        Modes "3840x2160_144"
    EndSubSection
EndSection
XORGEOF
log "xorg.conf written (BusID=$XORG_BUSID)"

# 6. SUNSHINE CONFIG
step "6. SUNSHINE CONFIG"
mkdir -p /root/.config/sunshine
cat > /root/.config/sunshine/sunshine.conf << SCONF
capture       = x11
encoder       = nvenc
adapter_name  = /dev/dri/renderD128
output_name   = 0
resolutions   = [3840x2160, 2560x1440, 1920x1080]
fps           = [144, 60, 30]
address_family = ipv4
upnp          = disabled
port          = 47989
min_log_level = info
SCONF
"$SUNSHINE_BIN" --creds admin "${ROOT_PASS}" >> "$LOG" 2>&1 || warn "sunshine --creds failed — set via web UI"
log "Sunshine configured"

# 7. GAME ASSETS
step "7. GAME ASSETS"
mkdir -p "$FERAL_SAVES" "$FERAL_PACKS" "${PROTON_BASE}/save_games" "${PROTON_BASE}/pack"
SC=0; PC=0
while IFS= read -r -d '' f; do
  cp "$f" "$FERAL_SAVES/"              2>/dev/null || true
  cp "$f" "${PROTON_BASE}/save_games/" 2>/dev/null || true
  SC=$((SC+1))
done < <(find /workspace -maxdepth 4 -name "*.save" -print0 2>/dev/null || true)
while IFS= read -r -d '' f; do
  cp "$f" "$FERAL_PACKS/"        2>/dev/null || true
  cp "$f" "${PROTON_BASE}/pack/" 2>/dev/null || true
  PC=$((PC+1))
done < <(find /workspace -maxdepth 4 -name "*.pack" -print0 2>/dev/null || true)
log "Assets: $SC .save  $PC .pack"

# 8. B2 SYNC
step "8. B2 SYNC"
if [ -n "$B2_KEY_ID" ] && [ -n "$B2_APP_KEY" ]; then
  command -v rclone >/dev/null 2>&1 || curl -fsSL https://rclone.org/install.sh | bash >> "$LOG" 2>&1
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
rclone sync "$FERAL_SAVES/" "b2funfun:${B2_BUCKET}/saves/" --log-file="$LOG_DIR/b2.log"
rclone sync "$FERAL_PACKS/" "b2funfun:${B2_BUCKET}/packs/" --log-file="$LOG_DIR/b2.log"
echo "[B2 \$(date +%H:%M:%S)] done" >> "$LOG_DIR/b2.log"
SYNC
  chmod +x /usr/local/bin/b2-sync.sh
  (crontab -l 2>/dev/null; echo "*/15 * * * * /usr/local/bin/b2-sync.sh") | sort -u | crontab -
  log "B2 configured"
else
  warn "B2 skipped — export B2_KEY_ID + B2_APP_KEY"
fi

# 9. PULSEAUDIO
step "9. PULSEAUDIO"
pulseaudio --daemonize --exit-idle-time=-1 >> "$LOG" 2>&1 || true
sleep 1
pactl load-module module-null-sink sink_name=virtual_out >> "$LOG" 2>&1 || true
pactl set-default-sink virtual_out >> "$LOG" 2>&1 || true
log "PulseAudio virtual sink ready"

# 10. SUPERVISORD
step "10. SUPERVISORD"
pip3 install --quiet supervisor >> "$LOG" 2>&1
SUPD=$(command -v supervisord 2>/dev/null \
  || find /usr/local/bin /root/.local/bin /usr/bin -name supervisord 2>/dev/null | head -1 || true)
[ -z "$SUPD" ] && die "supervisord not found after pip3 install"
SUPC=$(command -v supervisorctl 2>/dev/null \
  || find /usr/local/bin /root/.local/bin /usr/bin -name supervisorctl 2>/dev/null | head -1 || true)
[ -n "$SUPC" ] && ln -sf "$SUPC" /usr/local/bin/supervisorctl 2>/dev/null || true

mkdir -p /etc/supervisor
cat > /etc/supervisor/supervisord.conf << SUPCONF
[supervisord]
nodaemon=false
user=root
logfile=$LOG_DIR/supervisord.log
logfile_maxbytes=20MB
loglevel=info
pidfile=/tmp/supervisord.pid

[unix_http_server]
file=/tmp/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

[program:xorg]
command=Xorg ${DISP} -noreset +iglx -config /etc/X11/xorg.conf
autostart=true
autorestart=true
priority=10
startsecs=3
stdout_logfile=$LOG_DIR/xorg.log
stderr_logfile=$LOG_DIR/xorg.log
environment=DISPLAY="${DISP}"

[program:openbox]
command=openbox --display ${DISP}
autostart=true
autorestart=true
priority=20
startsecs=5
stdout_logfile=$LOG_DIR/openbox.log
stderr_logfile=$LOG_DIR/openbox.log
environment=DISPLAY="${DISP}"

[program:sunshine]
command=${SUNSHINE_BIN}
autostart=true
autorestart=true
priority=30
startsecs=8
stdout_logfile=$LOG_DIR/sunshine.log
stderr_logfile=$LOG_DIR/sunshine.log
environment=DISPLAY="${DISP}",HOME="/root"
SUPCONF

pkill -f supervisord >> "$LOG" 2>&1 || true
sleep 1
nohup "$SUPD" -c /etc/supervisor/supervisord.conf >> "$LOG_DIR/supervisord-boot.log" 2>&1 &
SPID=$!
disown $SPID
log "supervisord PID=$SPID disowned"

# 11. VERIFY
step "11. VERIFY"
sleep 15
XS="FAIL"; OS="FAIL"; SS="FAIL"
pgrep -x Xorg     >/dev/null 2>&1 && XS="OK"
pgrep -x openbox  >/dev/null 2>&1 && OS="OK"
pgrep -f sunshine >/dev/null 2>&1 && SS="OK"
POD_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "?")

echo ""
echo "============================================"
echo " DONE -- RunPod Gaming Rig v6"
echo "============================================"
echo " GPU      : $GPU_NAME (drv $DRV_MAJ)"
echo " BusID    : $XORG_BUSID"
echo " Xorg     : $XS  |  Openbox: $OS  |  Sunshine: $SS"
echo " Logs     : $LOG_DIR/"
echo ""
echo " SSH      : ssh root@${RUNPOD_HOST} -p ${RUNPOD_SSH_PORT}"
echo " Password : ${ROOT_PASS}"
echo " Web UI   : https://${POD_IP}:47990  (admin / ${ROOT_PASS})"
echo ""
echo " PowerShell tunnel:"
echo "   ssh -N -L 47984:localhost:47984 -L 47989:localhost:47989 \\"
echo "      -L 47990:localhost:47990 -L 48010:localhost:48010 \\"
echo "      root@${RUNPOD_HOST} -p ${RUNPOD_SSH_PORT} -o StrictHostKeyChecking=no"
echo "   -> Moonlight: Add PC -> 127.0.0.1"
echo ""
echo " supervisorctl -c /etc/supervisor/supervisord.conf status"
echo " tail -f $LOG_DIR/sunshine.log"
echo " tail -f $LOG_DIR/xorg.log"
echo "============================================"

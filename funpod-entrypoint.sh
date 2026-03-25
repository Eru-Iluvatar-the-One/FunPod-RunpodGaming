#!/bin/bash
# FunPod entrypoint — runs neko + SSH on RunPod
# Must be PID 1 foreground process (exec supervisord -n)

set -e

# ── SSH setup (RunPod injects PUBLIC_KEY env var) ─────────────────
if [[ -n "$PUBLIC_KEY" ]]; then
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    service ssh start 2>/dev/null || /usr/sbin/sshd 2>/dev/null || true
    echo "[FunPod] SSH started"
fi

# ── Export RunPod env vars for child processes ────────────────────
printenv | grep -E '^RUNPOD_' >> /etc/rp_environment 2>/dev/null || true
echo 'source /etc/rp_environment' >> ~/.bashrc 2>/dev/null || true

# ── Dynamic WebRTC config for RunPod port mapping ─────────────────
# RunPod maps 59000/tcp to a random external port.
# Neko needs the REAL external IP + port for ICE candidates.
if [[ -n "$RUNPOD_PUBLIC_IP" ]]; then
    echo "[FunPod] Public IP: $RUNPOD_PUBLIC_IP"
    sed -i "s/# nat1to1_placeholder/nat1to1:\n      - \"${RUNPOD_PUBLIC_IP}\"/" /etc/neko/neko.yaml 2>/dev/null || true
fi

if [[ -n "$RUNPOD_TCP_PORT_59000" ]]; then
    echo "[FunPod] External TCPMUX port: $RUNPOD_TCP_PORT_59000"
    # Neko must LISTEN on the external port so ICE candidates advertise it.
    # RunPod forwards external:$RUNPOD_TCP_PORT_59000 → container:59000.
    # socat bridges container:59000 → container:$RUNPOD_TCP_PORT_59000 (where neko listens).
    sed -i "s/tcpmux: 59000/tcpmux: ${RUNPOD_TCP_PORT_59000}/" /etc/neko/neko.yaml 2>/dev/null || true
    socat TCP-LISTEN:59000,fork,reuseaddr TCP:127.0.0.1:${RUNPOD_TCP_PORT_59000} &
    echo "[FunPod] socat bridge: container:59000 → container:${RUNPOD_TCP_PORT_59000}"
fi

# ── Steam persistence ────────────────────────────────────────────
echo "[FunPod] Running neko-init.sh..."
/usr/local/bin/neko-init.sh || true

# ── Start supervisord FOREGROUND (PID 1 — keeps container alive) ─
echo "[FunPod] Starting supervisord (foreground)..."
exec /usr/bin/supervisord -n -c /etc/neko/supervisord.conf

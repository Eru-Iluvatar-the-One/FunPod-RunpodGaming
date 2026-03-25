FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

# ── Gaming deps (Steam, Vulkan, 32-bit libs) ─────────────────────
RUN dpkg --add-architecture i386 && apt-get update && \
    apt-get install -y --no-install-recommends \
      wget curl ca-certificates dos2unix \
      lib32gcc-s1 lib32stdc++6 libc6-i386 \
      libvulkan1 libvulkan1:i386 \
      mesa-vulkan-drivers mesa-vulkan-drivers:i386 \
      libgbm1 libxcomposite1 libxdamage1 \
      libxfixes3 libxrandr2 libxrender1 libxtst6 \
      python3 xdg-utils rclone && \
    wget -q https://cdn.akamai.steamstatic.com/client/installer/steam.deb \
      -O /tmp/steam.deb && \
    (dpkg -i /tmp/steam.deb || true) && \
    apt-get install -y -f && \
    rm -f /tmp/steam.deb && \
    rm -rf /var/lib/apt/lists/*

# ── Neko config: TCP-only WebRTC (RunPod has NO UDP) ─────────────
# Let neko auto-detect video encoder (no custom pipeline = no crash)
RUN cat > /etc/neko/neko.yaml << 'YAMLEOF'
desktop:
  screen: "1920x1080@60"

server:
  bind: ":8080"

member:
  provider: "multiuser"
  multiuser:
    admin_password: "admin"
    user_password: "neko"

session:
  merciful_reconnect: true
  implicit_hosting: true
  inactive_cursors: true

webrtc:
  icelite: true
  tcpmux: 59000
  iceservers:
    frontend:
      - urls: ["stun:stun.l.google.com:19305"]
YAMLEOF

# ── Steam persistence script ─────────────────────────────────────
COPY neko-init.sh /usr/local/bin/neko-init.sh
RUN chmod +x /usr/local/bin/neko-init.sh

# ── Entrypoint wrapper ───────────────────────────────────────────
RUN cat > /usr/local/bin/funpod-entrypoint.sh << 'ENTRYEOF'
#!/bin/bash
echo "[FunPod] Running neko-init.sh..."
/usr/local/bin/neko-init.sh || true
echo "[FunPod] Starting supervisord..."
exec /usr/bin/supervisord -c /etc/neko/supervisord.conf
ENTRYEOF
RUN chmod +x /usr/local/bin/funpod-entrypoint.sh

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

EXPOSE 8080/tcp
EXPOSE 59000/tcp

# nvidia-base ENTRYPOINT sets up GPU env, then runs CMD
ENTRYPOINT ["/opt/nvidia/nvidia_entrypoint.sh"]
CMD ["/usr/local/bin/funpod-entrypoint.sh"]

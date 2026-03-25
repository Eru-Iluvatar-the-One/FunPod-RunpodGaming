FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

# ── Gaming deps (Steam, Vulkan, 32-bit libs) ─────────────────────
RUN dpkg --add-architecture i386 && apt-get update && \
    apt-get install -y --no-install-recommends \
      wget curl ca-certificates dos2unix openssh-server \
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

# ── SSH config (RunPod injects PUBLIC_KEY at runtime) ─────────────
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# ── Neko config: TCP-only WebRTC (RunPod has NO UDP) ─────────────
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
  # nat1to1_placeholder
  iceservers:
    frontend:
      - urls: ["stun:stun.l.google.com:19305"]
YAMLEOF

# ── Fix Xorg "Only console users" crash ──────────────────────────────
# supervisord.conf runs: /usr/bin/X :99 ... as user neko
# /usr/bin/X → Xorg.wrap → rejects non-console users in containers
# Fix: point supervisord at /usr/lib/xorg/Xorg (real binary, no wrapper)
RUN sed -i 's|/usr/bin/X |/usr/lib/xorg/Xorg |' /etc/neko/supervisord.conf && \
    mkdir -p /etc/X11 && \
    printf 'allowed_users=anybody\nneeds_root_rights=yes\n' \
      > /etc/X11/Xwrapper.config

# ── Scripts (dos2unix fixes Windows CRLF line endings) ────────────
COPY neko-init.sh /usr/local/bin/neko-init.sh
COPY funpod-entrypoint.sh /usr/local/bin/funpod-entrypoint.sh
RUN dos2unix /usr/local/bin/neko-init.sh /usr/local/bin/funpod-entrypoint.sh && \
    chmod +x /usr/local/bin/*.sh

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

EXPOSE 8080/tcp
EXPOSE 59000/tcp

# CRITICAL: Clear inherited ENTRYPOINT so RunPod doesn't conflict
ENTRYPOINT []
CMD ["/usr/local/bin/funpod-entrypoint.sh"]

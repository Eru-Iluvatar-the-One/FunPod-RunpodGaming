FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /etc/X11 && printf "allowed_users=anybody\nneeds_root_rights=yes\n" > /etc/X11/Xwrapper.config

# Steam deps + utilities — do NOT install gstreamer packages (overwrites CUDA plugins from base)
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y \
    dbus-x11 \
    pulseaudio pulseaudio-utils \
    wget curl ca-certificates software-properties-common dos2unix \
    lib32gcc-s1 lib32stdc++6 libc6-i386 \
    libvulkan1 mesa-vulkan-drivers \
    libgbm1 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libxrender1 libxtst6 \
    python3 xdg-utils rclone \
    && rm -rf /var/lib/apt/lists/*

# Steam
RUN apt-get update && \
    wget -q https://cdn.akamai.steamstatic.com/client/installer/steam.deb -O /tmp/steam.deb && \
    dpkg -i /tmp/steam.deb || true && \
    apt-get install -y -f && \
    rm -f /tmp/steam.deb && \
    rm -rf /var/lib/apt/lists/*

COPY neko-init.sh /neko-init.sh
RUN dos2unix /neko-init.sh && chmod +x /neko-init.sh

RUN printf '#!/bin/bash\nset -e\n/neko-init.sh\nexec /usr/bin/supervisord -c /etc/neko/supervisord.conf\n' > /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

EXPOSE 8080
EXPOSE 8081

# TCPMUX required — RunPod blocks all inbound UDP
# NO custom NEKO_CAPTURE_VIDEO_PIPELINE — let neko auto-detect encoder
ENV NEKO_DESKTOP_SCREEN="1920x1080@30" \
    NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD="admin" \
    NEKO_MEMBER_MULTIUSER_USER_PASSWORD="neko" \
    NEKO_WEBRTC_TCPMUX=8081 \
    NEKO_WEBRTC_ICELITE=true \
    NEKO_CAPTURE_VIDEO_CODEC="h264"

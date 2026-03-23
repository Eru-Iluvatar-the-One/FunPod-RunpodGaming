FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

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
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Steam
RUN apt-get update && \
    wget -q https://cdn.akamai.steamstatic.com/client/installer/steam.deb -O /tmp/steam.deb && \
    dpkg -i /tmp/steam.deb || true && \
    apt-get install -y -f && \
    rm -f /tmp/steam.deb && \
    rm -rf /var/lib/apt/lists/*

# Patch supervisord: replace entire x-server command line with Xvfb
# Print the block first for build-time verification, then patch
RUN echo "=== x-server block before patch ===" && \
    grep -A5 '\[program:x-server\]' /etc/neko/supervisord.conf && \
    sed -i '/^\[program:x-server\]/,/^\[/{s|^command=.*|command=/usr/bin/Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset|}' \
    /etc/neko/supervisord.conf && \
    echo "=== x-server block after patch ===" && \
    grep -A5 '\[program:x-server\]' /etc/neko/supervisord.conf

COPY neko-init.sh /neko-init.sh
RUN dos2unix /neko-init.sh && chmod +x /neko-init.sh

EXPOSE 8080
EXPOSE 8081

ENV NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD="admin" \
    NEKO_MEMBER_MULTIUSER_USER_PASSWORD="neko"

CMD ["/bin/bash", "-c", "/neko-init.sh; exec /usr/bin/supervisord -c /etc/neko/supervisord.conf"]

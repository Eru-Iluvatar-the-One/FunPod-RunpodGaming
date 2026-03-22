FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

# Allow Xorg to run as root in container
RUN mkdir -p /etc/X11 && printf "allowed_users=anybody\nneeds_root_rights=yes\n" > /etc/X11/Xwrapper.config

# Install Steam deps + utilities — do NOT install gstreamer packages (would overwrite CUDA plugins from base)
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

ENV NEKO_DESKTOP_SCREEN="1920x1080@30" \
    NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD="admin" \
    NEKO_MEMBER_MULTIUSER_USER_PASSWORD="neko" \
    NEKO_WEBRTC_TCPMUX=8081 \
    NEKO_WEBRTC_ICELITE=true \
    NEKO_CAPTURE_VIDEO_CODEC="h264" \
    NEKO_CAPTURE_VIDEO_PIPELINE="ximagesrc display-name={display} show-pointer=true use-damage=false ! video/x-raw,framerate=30/1 ! cudaupload ! cudaconvert ! video/x-raw(memory:CUDAMemory),format=NV12 ! nvh264enc name=encoder preset=2 gop-size=25 spatial-aq=true temporal-aq=true bitrate=6000 vbv-buffer-size=6000 rc-mode=6 ! h264parse config-interval=-1 ! video/x-h264,stream-format=byte-stream ! appsink name=appsink"

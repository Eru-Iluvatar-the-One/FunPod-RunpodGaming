FROM ghcr.io/m1k1o/neko/nvidia-base:latest

ENV DEBIAN_FRONTEND=noninteractive

# Desktop + Steam deps + rclone
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-terminal dbus-x11 \
    pulseaudio pulseaudio-utils \
    wget curl ca-certificates software-properties-common \
    lib32gcc-s1 lib32stdc++6 libc6-i386 \
    libgl1-mesa-dri libgl1-mesa-glx libvulkan1 mesa-vulkan-drivers \
    libgbm1 libx11-6 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxrandr2 libxrender1 libxtst6 \
    python3 xdg-utils rclone \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    && rm -rf /var/lib/apt/lists/*

# Steam
RUN dpkg --add-architecture i386 && apt-get update && \
    wget -q https://cdn.akamai.steamstatic.com/client/installer/steam.deb -O /tmp/steam.deb && \
    apt-get install -y /tmp/steam.deb || apt-get install -fy && \
    rm /tmp/steam.deb && rm -rf /var/lib/apt/lists/*

# Workspace dirs — /workspace is the RunPod network volume mount point
RUN mkdir -p /workspace/steam_data /workspace/steam_saves

# Copy init script
COPY neko-init.sh /neko-init.sh
RUN chmod +x /neko-init.sh

EXPOSE 8080

# Neko config
# NVENC over GStreamer — cudaupload path for modern GPUs
# If CUDA < 11 or nvh264enc fails, drop cudaupload/cudaconvert and feed NV12 direct
ENV NEKO_DESKTOP_SCREEN="1920x1080@30" \
    NEKO_MEMBER_MULTIUSER_USER_PASSWORD="neko" \
    NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD="admin" \
    NEKO_WEBRTC_TCPMUX=8080 \
    NEKO_WEBRTC_ICELITE=true \
    NEKO_CAPTURE_VIDEO_CODEC="h264" \
    NEKO_CAPTURE_VIDEO_PIPELINE="ximagesrc display-name={display} show-pointer=true use-damage=false ! video/x-raw,framerate=30/1 ! videoconvert ! queue ! video/x-raw,format=NV12 ! cudaupload ! cudaconvert ! video/x-raw(memory:CUDAMemory),format=NV12 ! nvh264enc name=encoder preset=2 gop-size=25 spatial-aq=true temporal-aq=true bitrate=6000 vbv-buffer-size=6000 rc-mode=6 ! h264parse config-interval=-1 ! video/x-h264,stream-format=byte-stream ! appsink name=appsink"

# Run init then hand off to neko's default entrypoint
ENTRYPOINT ["/bin/bash", "-c", "/neko-init.sh && exec /docker-entrypoint.sh"]

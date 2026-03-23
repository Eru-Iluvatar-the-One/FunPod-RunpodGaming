FROM ghcr.io/m1k1o/neko/nvidia-xfce:latest

ENV DEBIAN_FRONTEND=noninteractive

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

RUN mkdir -p /etc/X11 && \
    printf 'allowed_users=anybody\nneeds_root_rights=yes\n' \
      > /etc/X11/Xwrapper.config

RUN cat > /etc/neko/xorg.conf << 'XORGEOF'
Section "ServerFlags"
    Option "DontVTSwitch"        "true"
    Option "AllowMouseOpenFail"  "true"
    Option "PciForceNone"        "true"
    Option "AutoEnableDevices"   "false"
    Option "AutoAddDevices"      "false"
EndSection
Section "InputDevice"
    Identifier "NekoDrv"
    Driver     "neko"
EndSection
Section "Monitor"
    Identifier  "Monitor0"
    HorizSync   30-300
    VertRefresh  48-165
    Modeline "3840x2160@144" 2183.54 3840 4152 4576 5312 2160 2161 2164 2235 -HSync +VSync
EndSection
Section "Device"
    Identifier "Device0"
    Driver     "dummy"
    VideoRam   65536
EndSection
Section "Screen"
    Identifier "Screen0"
    Device     "Device0"
    Monitor    "Monitor0"
    DefaultDepth 24
    SubSection "Display"
        Depth   24
        Modes   "3840x2160@144"
    EndSubSection
EndSection
Section "ServerLayout"
    Identifier  "Layout0"
    Screen      "Screen0"
    InputDevice "NekoDrv" "CorePointer"
EndSection
XORGEOF

RUN cat > /etc/neko/neko.yaml << 'YAMLEOF'
desktop:
  screen: "3840x2160@144"

capture:
  audio:
    codec: "opus"
  video:
    codec: "h264"
    pipeline: |
      ximagesrc display-name={display} show-pointer=true use-damage=false !
      video/x-raw,framerate=30/1 !
      videoconvert !
      queue !
      video/x-raw,format=NV12 !
      cudaupload !
      cudaconvert !
      video/x-raw(memory:CUDAMemory),format=NV12 !
      nvh264enc name=encoder preset=2 gop-size=25 spatial-aq=true temporal-aq=true bitrate=8192 vbv-buffer-size=8192 rc-mode=6 !
      h264parse config-interval=-1 !
      video/x-h264,stream-format=byte-stream !
      appsink name=appsink
  screencast:
    enabled: false

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

plugins:
  enabled: true
  dir: "/etc/neko/plugins/"
YAMLEOF

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV VGL_DISPLAY=egl

EXPOSE 8080/tcp
EXPOSE 59000/tcp

ENTRYPOINT ["/opt/nvidia/nvidia_entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/neko/supervisord.conf"]

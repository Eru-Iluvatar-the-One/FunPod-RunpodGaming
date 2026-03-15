#!/bin/bash
# Runs once at container start before neko launches.
# Symlinks Steam data to /workspace (RunPod network volume) for persistence.

set -e

STEAM_HOME="/home/neko/.steam"
STEAM_SAVES="/home/neko/.local/share/Steam/steamapps/compatdata"
WORKSPACE_STEAM="/workspace/steam_data"
WORKSPACE_SAVES="/workspace/steam_saves/compatdata"

echo "[neko-init] Setting up Steam persistence..."

# Steam home -> /workspace/steam_data
if [ ! -L "$STEAM_HOME" ]; then
    rm -rf "$STEAM_HOME"
    mkdir -p "$WORKSPACE_STEAM"
    ln -sf "$WORKSPACE_STEAM" "$STEAM_HOME"
    echo "[neko-init] Linked ~/.steam -> $WORKSPACE_STEAM"
fi

# Proton compatdata (save-adjacent) -> /workspace/steam_saves/compatdata
mkdir -p "$(dirname "$STEAM_SAVES")"
if [ ! -L "$STEAM_SAVES" ]; then
    rm -rf "$STEAM_SAVES"
    mkdir -p "$WORKSPACE_SAVES"
    ln -sf "$WORKSPACE_SAVES" "$STEAM_SAVES"
    echo "[neko-init] Linked compatdata -> $WORKSPACE_SAVES"
fi

# PulseAudio (neko needs it running)
pulseaudio --start --log-target=file:/tmp/pulse.log 2>/dev/null || true

echo "[neko-init] Done."

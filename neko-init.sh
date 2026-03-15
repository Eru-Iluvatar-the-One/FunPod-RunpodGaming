#!/bin/bash
# Runs once at container start. Symlinks Steam to /workspace for persistence.
set -e

NEKO_HOME=$(getent passwd neko | cut -d: -f6 2>/dev/null || echo "/home/neko")
STEAM_HOME="$NEKO_HOME/.steam"
STEAM_SAVES="$NEKO_HOME/.local/share/Steam/steamapps/compatdata"
WORKSPACE_STEAM="/workspace/steam_data"
WORKSPACE_SAVES="/workspace/steam_saves/compatdata"

echo "[neko-init] Home: $NEKO_HOME"
echo "[neko-init] Setting up Steam persistence..."

mkdir -p "$WORKSPACE_STEAM" "$WORKSPACE_SAVES"

if [ ! -L "$STEAM_HOME" ]; then
    rm -rf "$STEAM_HOME"
    ln -sf "$WORKSPACE_STEAM" "$STEAM_HOME"
    echo "[neko-init] Linked ~/.steam -> $WORKSPACE_STEAM"
fi

mkdir -p "$(dirname "$STEAM_SAVES")"
if [ ! -L "$STEAM_SAVES" ]; then
    rm -rf "$STEAM_SAVES"
    ln -sf "$WORKSPACE_SAVES" "$STEAM_SAVES"
    echo "[neko-init] Linked compatdata -> $WORKSPACE_SAVES"
fi

pulseaudio --start --log-target=file:/tmp/pulse.log 2>/dev/null || true
echo "[neko-init] Done."

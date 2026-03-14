#!/bin/bash
# healthcheck.sh -- Container Health Check
# Verifies: GPU, Xorg, PulseAudio, Sunshine
# HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD /home/gamer/healthcheck.sh
set -uo pipefail
FAIL=0

# 1. GPU
if nvidia-smi > /dev/null 2>&1; then
    GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "GPU: ${GPU}"
else
    echo "FAIL: nvidia-smi cannot detect GPU"
    FAIL=1
fi

# 2. Xorg
if pgrep -x Xorg > /dev/null 2>&1; then
    if DISPLAY=:0 xdpyinfo > /dev/null 2>&1; then
        echo "Xorg: running on :0"
    else
        echo "FAIL: Xorg process exists but DISPLAY=:0 not responsive"
        FAIL=1
    fi
else
    echo "FAIL: Xorg is not running"
    FAIL=1
fi

# 3. PulseAudio
if pgrep -u gamer -x pulseaudio > /dev/null 2>&1; then
    if su - gamer -c "pactl info" > /dev/null 2>&1; then
        echo "PulseAudio: active for user gamer"
    else
        echo "FAIL: PulseAudio not responding"
        FAIL=1
    fi
else
    echo "FAIL: PulseAudio not running for gamer"
    FAIL=1
fi

# 4. Sunshine
if ss -tlnp 2>/dev/null | grep -q ':47989\b'; then
    HTTP_CODE=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 5 https://localhost:47990 2>/dev/null || echo "000")
    echo "Sunshine: listening on :47989 | Web UI :47990 (HTTP ${HTTP_CODE})"
else
    echo "FAIL: Sunshine NOT listening on TCP 47989"
    FAIL=1
fi

if [ "${FAIL}" -eq 0 ]; then
    echo "ALL CHECKS PASSED"
    exit 0
else
    echo "ONE OR MORE CHECKS FAILED"
    exit 1
fi

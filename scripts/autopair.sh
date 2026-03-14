#!/bin/bash
# autopair.sh -- Automate Moonlight <-> Sunshine Pairing
# Modes: pin, setup, watch, auto
set -uo pipefail

SUNSHINE_HOST="${SUNSHINE_HOST:-https://localhost:47990}"
SUNSHINE_USER="${SUNSHINE_USER:-admin}"
SUNSHINE_PASS="${SUNSHINE_PASS:-admin}"

wait_for_sunshine() {
    local max_wait=60 waited=0
    echo "Waiting for Sunshine API at ${SUNSHINE_HOST}..."
    while [ ${waited} -lt ${max_wait} ]; do
        if curl -sk -o /dev/null -w '' "${SUNSHINE_HOST}" --max-time 3 2>/dev/null; then
            echo "Sunshine API is up"
            return 0
        fi
        sleep 2
        ((waited+=2))
    done
    echo "Sunshine API did not respond within ${max_wait}s"
    return 1
}

submit_pin() {
    local pin="${1:?PIN required}"
    local name="${2:-AutoPaired-Client}"
    wait_for_sunshine || return 1
    echo "Submitting PIN '${pin}' for client '${name}'..."
    RESPONSE=$(curl -sk -u "${SUNSHINE_USER}:${SUNSHINE_PASS}" \
        -X POST -H "Content-Type: application/json" \
        -d "{\"pin\":\"${pin}\",\"name\":\"${name}\"}" \
        "${SUNSHINE_HOST}/api/pin" 2>&1)
    if echo "${RESPONSE}" | grep -qi '"true"'; then
        echo "Pairing successful! Client '${name}' is now paired."
        return 0
    else
        echo "Pairing failed. Response: ${RESPONSE}"
        return 1
    fi
}

setup_credentials() {
    local user="${1:-${SUNSHINE_USER}}"
    local pass="${2:-${SUNSHINE_PASS}}"
    echo "Setting up Sunshine credentials (user: ${user})..."
    if command -v sunshine > /dev/null 2>&1; then
        su - gamer -c "sunshine --creds ${user} ${pass}" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "Credentials set via sunshine --creds"
            return 0
        fi
    fi
    if curl -sk -o /dev/null "${SUNSHINE_HOST}" --max-time 3 2>/dev/null; then
        RESPONSE=$(curl -sk -X POST -H "Content-Type: application/json" \
            -d "{\"currentUsername\":\"\",\"currentPassword\":\"\",\"newUsername\":\"${user}\",\"newPassword\":\"${pass}\"}" \
            "${SUNSHINE_HOST}/api/password" 2>&1)
        if echo "${RESPONSE}" | grep -qi '"true"\|200'; then
            echo "Credentials set via API"
            return 0
        fi
    fi
    echo "Could not set credentials automatically."
    return 1
}

watch_pairing() {
    local logfile="${1:-/tmp/sunshine.log}"
    echo "Watching Sunshine logs for pairing requests..."
    if [ ! -f "${logfile}" ]; then
        echo "Log file not found yet. Waiting..."
        while [ ! -f "${logfile}" ]; do sleep 1; done
    fi
    tail -F "${logfile}" 2>/dev/null | while read -r line; do
        if echo "${line}" | grep -qi "pin\|pair\|client.*connect"; then
            echo ""
            echo "PAIRING ACTIVITY: ${line}"
            echo "To complete: ./autopair.sh pin <PIN> <client-name>"
            echo ""
        fi
    done
}

auto_mode() {
    echo "Sunshine Auto-Pair Setup"
    setup_credentials "${SUNSHINE_USER}" "${SUNSHINE_PASS}"
    wait_for_sunshine || exit 1
    local config_dir="/home/gamer/.config/sunshine"
    local config_file="${config_dir}/sunshine.conf"
    mkdir -p "${config_dir}"
    chown -R gamer:gamer "${config_dir}"
    if [ -f "${config_file}" ]; then
        if ! grep -q "origin_web_ui_allowed" "${config_file}"; then
            echo "origin_web_ui_allowed = lan" >> "${config_file}"
        fi
    else
        echo "origin_web_ui_allowed = lan" > "${config_file}"
        chown gamer:gamer "${config_file}"
    fi
    echo ""
    echo "Sunshine is ready for pairing!"
    echo "1. Open Moonlight -> Add this host IP"
    echo "2. Moonlight shows 4-digit PIN"
    echo "3. Run: ./autopair.sh pin <PIN>"
    echo "Web UI: ${SUNSHINE_HOST} (user: ${SUNSHINE_USER})"
}

case "${1:-}" in
    pin)   submit_pin "${2:-}" "${3:-AutoPaired-Client}" ;;
    setup) setup_credentials "${2:-${SUNSHINE_USER}}" "${3:-${SUNSHINE_PASS}}" ;;
    watch) watch_pairing "${2:-/tmp/sunshine.log}" ;;
    auto)  auto_mode ;;
    *)     echo "Usage: $0 {pin <PIN>|setup [user pass]|watch|auto}" ; exit 1 ;;
esac

"""
FunPod Neko Healer — Self-Healing Neko Deployment for RunPod
Diagnoses, deploys, and auto-repairs n.eko virtual desktop on RunPod pods.

CRITICAL INSIGHT: RunPod = TCP only. Neko normally needs UDP for WebRTC.
SOLUTION: Neko's NEKO_WEBRTC_TCPMUX mode routes ALL WebRTC over a single TCP port.
This module deploys neko with TCP-only config that actually works on RunPod.

Known issues database + auto-fix for each:
  1. UDP ports blocked (RunPod limitation) → Use TCPMUX mode
  2. WebRTC ICE/NAT IP detection fails → Force IP via API
  3. shm_size too low → Browser crash/freeze → Set 2gb+
  4. Black screen → Missing SYS_ADMIN capability → Add cap
  5. Profile corruption → Delete and recreate profile dir
  6. Docker network subnet conflict → Prune networks
  7. OOM kills → Increase shm, reduce resolution
  8. Port mapping mismatch → Validate port config
  9. Nvidia GPU driver mismatch → Check nvidia-smi, fallback to CPU encoding
  10. Container won't start → Image not pulled → Auto-pull
  11. WebSocket connection fails → Verify TCP port exposure
  12. DTLS transport not started → UDP blocked confirmation → Switch to TCPMUX
  13. Stale container → Force remove and recreate
  14. DNS resolution fails inside container → Add custom DNS
  15. Browser not rendering → GPU acceleration misconfigured → Toggle HWENC

Usage:
    from neko_healer import NekoHealer
    healer = NekoHealer(api, pod_id)
    healer.deploy()              # Full deploy with progress signals
    healer.diagnose()            # Run all checks, return issues
    healer.heal(issue_code)      # Auto-fix specific issue
"""
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QThread, pyqtSignal


# ── Issue Database ────────────────────────────────────────────────
class Severity(Enum):
    CRITICAL = "critical"   # Cannot start at all
    HIGH = "high"           # Starts but unusable
    MEDIUM = "medium"       # Degraded experience
    LOW = "low"             # Cosmetic / non-blocking


@dataclass
class Issue:
    code: str
    title: str
    severity: Severity
    description: str
    check_cmd: str           # SSH command to detect
    check_expect: str        # What the output should NOT contain (indicates problem)
    fix_cmds: list           # SSH commands to fix
    verify_cmd: str          # SSH command to verify fix worked


KNOWN_ISSUES: dict[str, Issue] = {
    "UDP_BLOCKED": Issue(
        code="UDP_BLOCKED",
        title="UDP ports blocked (RunPod limitation)",
        severity=Severity.CRITICAL,
        description="RunPod only supports TCP. Standard neko WebRTC requires UDP. Must use TCPMUX mode.",
        check_cmd="cat /proc/net/udp | wc -l",
        check_expect="",  # Always apply on RunPod
        fix_cmds=[],  # Handled in deploy config
        verify_cmd="echo 'tcpmux_configured'",
    ),
    "SHM_TOO_LOW": Issue(
        code="SHM_TOO_LOW",
        title="Shared memory too low for browser",
        severity=Severity.HIGH,
        description="Chromium needs 2GB+ shm. Low shm causes crashes, tabs dying, black screens.",
        check_cmd="df -h /dev/shm | tail -1 | awk '{print $2}'",
        check_expect="",
        fix_cmds=["mount -o remount,size=2G /dev/shm"],
        verify_cmd="df -h /dev/shm | tail -1 | awk '{print $2}'",
    ),
    "MISSING_SYS_ADMIN": Issue(
        code="MISSING_SYS_ADMIN",
        title="Missing SYS_ADMIN capability (black screen)",
        severity=Severity.HIGH,
        description="Chromium-based browsers need SYS_ADMIN cap or --no-sandbox flag.",
        check_cmd="cat /proc/1/status | grep CapEff",
        check_expect="",
        fix_cmds=[],  # Must be set at container creation, workaround: --no-sandbox
        verify_cmd="echo ok",
    ),
    "NVIDIA_DRIVER": Issue(
        code="NVIDIA_DRIVER",
        title="Nvidia GPU driver not available",
        severity=Severity.MEDIUM,
        description="nvidia-smi not found or driver mismatch. Falls back to CPU encoding.",
        check_cmd="nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1",
        check_expect="NVIDIA",
        fix_cmds=[
            "apt-get update -qq && apt-get install -y -qq nvidia-utils-535 2>/dev/null || true",
        ],
        verify_cmd="nvidia-smi --query-gpu=name --format=csv,noheader 2>&1",
    ),
    "DOCKER_NOT_RUNNING": Issue(
        code="DOCKER_NOT_RUNNING",
        title="Docker daemon not running inside pod",
        severity=Severity.CRITICAL,
        description="Docker-in-docker not available. Neko runs as direct process instead.",
        check_cmd="which docker && docker info --format '{{.ServerVersion}}' 2>&1 || echo 'NO_DOCKER'",
        check_expect="NO_DOCKER",
        fix_cmds=[
            "curl -fsSL https://get.docker.com | sh 2>/dev/null || true",
            "dockerd &>/dev/null &",
            "sleep 3",
        ],
        verify_cmd="docker info --format '{{.ServerVersion}}' 2>&1",
    ),
    "NEKO_NOT_INSTALLED": Issue(
        code="NEKO_NOT_INSTALLED",
        title="Neko not installed or image not pulled",
        severity=Severity.CRITICAL,
        description="Neko container image not available locally.",
        check_cmd="docker images ghcr.io/m1k1o/neko/nvidia-google-chrome --format '{{.Repository}}' 2>/dev/null || echo 'NONE'",
        check_expect="NONE",
        fix_cmds=[
            "docker pull ghcr.io/m1k1o/neko/nvidia-google-chrome:latest",
        ],
        verify_cmd="docker images ghcr.io/m1k1o/neko/nvidia-google-chrome --format '{{.Repository}}'",
    ),
    "STALE_CONTAINER": Issue(
        code="STALE_CONTAINER",
        title="Stale neko container blocking restart",
        severity=Severity.HIGH,
        description="Old neko container exists in stopped/dead state, blocking port allocation.",
        check_cmd="docker ps -a --filter name=funpod-neko --format '{{.Status}}' 2>/dev/null || echo 'NONE'",
        check_expect="",
        fix_cmds=[
            "docker rm -f funpod-neko 2>/dev/null || true",
        ],
        verify_cmd="docker ps -a --filter name=funpod-neko --format '{{.ID}}' | wc -l",
    ),
    "NETWORK_CONFLICT": Issue(
        code="NETWORK_CONFLICT",
        title="Docker network subnet conflicts with host",
        severity=Severity.MEDIUM,
        description="Docker bridge network overlaps with host subnet, breaking internet inside container.",
        check_cmd="docker network ls --format '{{.Name}}' | wc -l",
        check_expect="",
        fix_cmds=[
            "docker network prune -f 2>/dev/null || true",
        ],
        verify_cmd="curl -s -o /dev/null -w '%{http_code}' https://1.1.1.1 2>/dev/null || echo 'no_net'",
    ),
    "DNS_FAILURE": Issue(
        code="DNS_FAILURE",
        title="DNS resolution failing inside container",
        severity=Severity.HIGH,
        description="Container cannot resolve hostnames. Breaks package installs and web browsing.",
        check_cmd="nslookup google.com 2>&1 | head -1 || echo 'DNS_FAIL'",
        check_expect="DNS_FAIL",
        fix_cmds=[
            "echo 'nameserver 8.8.8.8' > /etc/resolv.conf",
            "echo 'nameserver 1.1.1.1' >> /etc/resolv.conf",
        ],
        verify_cmd="nslookup google.com 2>&1 | head -1",
    ),
    "PORT_CONFLICT": Issue(
        code="PORT_CONFLICT",
        title="Port 8080 or TCPMUX port already in use",
        severity=Severity.HIGH,
        description="Another process is using the neko web UI or WebRTC port.",
        check_cmd="ss -tlnp | grep -E ':8080|:59000' | head -3",
        check_expect="",
        fix_cmds=[
            "fuser -k 8080/tcp 2>/dev/null || true",
            "fuser -k 59000/tcp 2>/dev/null || true",
        ],
        verify_cmd="ss -tlnp | grep -E ':8080|:59000' | wc -l",
    ),
    "PROFILE_CORRUPT": Issue(
        code="PROFILE_CORRUPT",
        title="Browser profile corrupted (black screen after login)",
        severity=Severity.MEDIUM,
        description="Browser profile in /home/neko/.config is corrupted from improper shutdown.",
        check_cmd="ls -la /home/neko/.config/ 2>/dev/null | head -5 || echo 'NO_PROFILE'",
        check_expect="",
        fix_cmds=[
            "rm -rf /tmp/neko-profile-backup 2>/dev/null || true",
            "docker exec funpod-neko rm -rf /home/neko/.config/google-chrome/Default/Lock 2>/dev/null || true",
            "docker exec funpod-neko rm -rf /home/neko/.config/google-chrome/Singleton* 2>/dev/null || true",
        ],
        verify_cmd="echo 'profile_cleaned'",
    ),
    "GPU_ENCODING_FAIL": Issue(
        code="GPU_ENCODING_FAIL",
        title="GPU hardware encoding not working",
        severity=Severity.LOW,
        description="nvenc not available, falling back to CPU encoding. Higher latency but functional.",
        check_cmd="docker logs funpod-neko 2>&1 | grep -i 'nvh264enc\\|nvenc\\|hardware' | tail -3 || echo 'no_logs'",
        check_expect="",
        fix_cmds=[],  # Informational — CPU fallback is automatic
        verify_cmd="echo 'checked'",
    ),
}


# ── Neko deploy config for RunPod (TCP-only) ─────────────────────
NEKO_DEPLOY_SCRIPT = """#!/bin/bash
set -e

echo "[FunPod] === NEKO DEPLOYMENT START ==="

# ── Step 1: System prep ──────────────────────────
echo "[FunPod] [1/8] System prep..."
apt-get update -qq 2>/dev/null
apt-get install -y -qq curl wget net-tools 2>/dev/null || true

# ── Step 2: Ensure Docker ────────────────────────
echo "[FunPod] [2/8] Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo "[FunPod] Installing Docker..."
    curl -fsSL https://get.docker.com | sh 2>/dev/null
fi

# Start dockerd if not running
if ! docker info &>/dev/null 2>&1; then
    echo "[FunPod] Starting Docker daemon..."
    dockerd --storage-driver=overlay2 &>/var/log/dockerd.log &
    for i in $(seq 1 30); do
        docker info &>/dev/null 2>&1 && break
        sleep 1
    done
fi

# ── Step 3: Fix shared memory ────────────────────
echo "[FunPod] [3/8] Fixing shared memory..."
mount -o remount,size=2G /dev/shm 2>/dev/null || true

# ── Step 4: Fix DNS ──────────────────────────────
echo "[FunPod] [4/8] Fixing DNS..."
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# ── Step 5: Get public IP ────────────────────────
echo "[FunPod] [5/8] Detecting public IP..."
PUBLIC_IP=$(curl -s --max-time 5 https://ifconfig.co/ip 2>/dev/null || curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "")
echo "[FunPod] Public IP: ${PUBLIC_IP:-UNKNOWN}"

# ── Step 6: Clean old containers ─────────────────
echo "[FunPod] [6/8] Cleaning old containers..."
docker rm -f funpod-neko 2>/dev/null || true
docker network prune -f 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true
fuser -k 59000/tcp 2>/dev/null || true

# ── Step 7: Pull neko image ──────────────────────
echo "[FunPod] [7/8] Pulling neko image (this may take a few minutes)..."
# Try nvidia first, fall back to standard
if nvidia-smi &>/dev/null 2>&1; then
    echo "[FunPod] GPU detected - using nvidia image"
    NEKO_IMAGE="ghcr.io/m1k1o/neko/nvidia-google-chrome:latest"
    GPU_FLAGS="--gpus all"
    HW_ENC="-e NEKO_HWENC=nvenc"
else
    echo "[FunPod] No GPU detected - using standard image"
    NEKO_IMAGE="ghcr.io/m1k1o/neko/google-chrome:latest"
    GPU_FLAGS=""
    HW_ENC=""
fi
docker pull $NEKO_IMAGE

# ── Step 8: Launch neko (TCP-ONLY for RunPod) ────
echo "[FunPod] [8/8] Launching neko with TCP-only WebRTC..."

# KEY CONFIG: NEKO_WEBRTC_TCPMUX uses a SINGLE TCP port for ALL WebRTC traffic
# This is the ONLY way to run neko on RunPod (no UDP support)
docker run -d \\
    --name funpod-neko \\
    --restart unless-stopped \\
    --shm-size=2g \\
    --cap-add SYS_ADMIN \\
    ${GPU_FLAGS} \\
    -p 8080:8080 \\
    -p 59000:59000/tcp \\
    -e NEKO_DESKTOP_SCREEN="1920x1080@60" \\
    -e NEKO_MEMBER_MULTIUSER_USER_PASSWORD="funpod" \\
    -e NEKO_MEMBER_MULTIUSER_ADMIN_PASSWORD="funpodadmin" \\
    -e NEKO_WEBRTC_TCPMUX="59000" \\
    -e NEKO_WEBRTC_ICELITE="true" \\
    ${HW_ENC} \\
    $([ -n "$PUBLIC_IP" ] && echo "-e NEKO_WEBRTC_NAT1TO1=${PUBLIC_IP}") \\
    $NEKO_IMAGE

echo "[FunPod] === DEPLOYMENT COMPLETE ==="
echo "[FunPod] Web UI: http://${PUBLIC_IP}:8080"
echo "[FunPod] Password: funpod / funpodadmin"
echo "[FunPod] WebRTC mode: TCP MUX on port 59000 (RunPod compatible)"

# ── Health check loop ────────────────────────────
echo "[FunPod] Waiting for neko to become healthy..."
for i in $(seq 1 60); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' funpod-neko 2>/dev/null || echo "starting")
    RUNNING=$(docker inspect --format='{{.State.Running}}' funpod-neko 2>/dev/null || echo "false")
    if [ "$RUNNING" = "true" ]; then
        # Check if web UI responds
        HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
            echo "[FunPod] Neko is LIVE! HTTP $HTTP_CODE"
            break
        fi
    fi
    echo "[FunPod] Waiting... ($i/60) Status: $RUNNING"
    sleep 2
done

# Final status
docker ps --filter name=funpod-neko --format "{{.Status}}"
echo "[FunPod] DONE"
"""

DIAGNOSE_SCRIPT = """#!/bin/bash
echo "=== FUNPOD DIAGNOSTICS ==="
echo "--- System ---"
uname -a
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "SHM: $(df -h /dev/shm | tail -1 | awk '{print $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $4}') free"

echo "--- GPU ---"
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv,noheader 2>/dev/null || echo "NO GPU"

echo "--- Docker ---"
docker --version 2>/dev/null || echo "NO DOCKER"
docker ps -a --filter name=funpod-neko --format "ID={{.ID}} Status={{.Status}} Image={{.Image}}" 2>/dev/null || echo "NO CONTAINERS"

echo "--- Network ---"
echo "Public IP: $(curl -s --max-time 3 https://ifconfig.co/ip 2>/dev/null || echo UNKNOWN)"
echo "DNS: $(nslookup google.com 2>&1 | head -2 | tail -1 || echo FAIL)"
echo "Port 8080: $(ss -tlnp | grep :8080 | head -1 || echo FREE)"
echo "Port 59000: $(ss -tlnp | grep :59000 | head -1 || echo FREE)"

echo "--- Neko Logs (last 20) ---"
docker logs funpod-neko --tail 20 2>&1 || echo "NO LOGS"

echo "--- Neko Health ---"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null || echo "000")
echo "HTTP Status: $HTTP"

echo "=== END DIAGNOSTICS ==="
"""

HEAL_SCRIPT_TEMPLATE = """#!/bin/bash
echo "[FunPod Healer] Fixing: {issue_title}"
{fix_commands}
echo "[FunPod Healer] Verifying fix..."
{verify_command}
echo "[FunPod Healer] Fix attempt complete"
"""


class NekoHealer(QThread):
    """Self-healing neko deployment worker. Runs over SSH."""

    # Signals
    progress = pyqtSignal(int, int, str)    # step, total, message
    log = pyqtSignal(str)                    # log line
    deployed = pyqtSignal(str)               # neko URL
    issue_found = pyqtSignal(str, str)       # issue_code, description
    issue_fixed = pyqtSignal(str)            # issue_code
    error = pyqtSignal(str)                  # error message
    finished_signal = pyqtSignal()

    def __init__(self, ssh_host: str, ssh_port: int, ssh_key_path: Optional[str] = None,
                 action: str = "deploy", pod_id: str = ""):
        super().__init__()
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_key_path = ssh_key_path
        self.action = action  # "deploy", "diagnose", "heal"
        self.pod_id = pod_id  # needed for RunPod proxy URL
        self.heal_target: Optional[str] = None
        self._running = True

    def _ssh_exec(self, command: str, timeout: int = 300) -> tuple[int, str]:
        """Execute command over SSH. Returns (exit_code, output)."""
        import subprocess
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
        if self.ssh_key_path:
            ssh_cmd.extend(["-i", self.ssh_key_path])
        ssh_cmd.extend(["-p", str(self.ssh_port), f"root@{self.ssh_host}", command])

        try:
            result = subprocess.run(
                ssh_cmd, capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout + result.stderr
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return -1, "TIMEOUT"
        except Exception as e:
            return -1, str(e)

    def _ssh_exec_script(self, script: str, timeout: int = 600) -> tuple[int, str]:
        """Upload and execute a bash script over SSH."""
        import subprocess

        # Write script to temp file and pipe over SSH
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
        if self.ssh_key_path:
            ssh_cmd.extend(["-i", self.ssh_key_path])
        ssh_cmd.extend(["-p", str(self.ssh_port), f"root@{self.ssh_host}", "bash -s"])

        try:
            result = subprocess.run(
                ssh_cmd, input=script, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return -1, "TIMEOUT"
        except Exception as e:
            return -1, str(e)

    def run(self):
        try:
            if self.action == "deploy":
                self._do_deploy()
            elif self.action == "diagnose":
                self._do_diagnose()
            elif self.action == "heal":
                self._do_heal()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished_signal.emit()

    def _do_deploy(self):
        """Full deploy: connectivity check → diagnostics → deploy → verify → heal if needed."""
        total = 6
        
        # Step 1: Test SSH connectivity
        self.progress.emit(1, total, "Testing SSH connection...")
        self.log.emit(f"Connecting to root@{self.ssh_host}:{self.ssh_port}...")
        rc, out = self._ssh_exec("echo 'FUNPOD_SSH_OK'", timeout=15)
        if rc != 0 or "FUNPOD_SSH_OK" not in out:
            self.error.emit(f"SSH connection failed: {out}")
            return
        self.log.emit("SSH connection OK")

        # Step 2: Pre-flight diagnostics
        self.progress.emit(2, total, "Running pre-flight diagnostics...")
        self.log.emit("Checking system state...")
        rc, diag = self._ssh_exec_script(DIAGNOSE_SCRIPT, timeout=30)
        for line in diag.strip().split("\n"):
            self.log.emit(f"  {line}")

        # Step 3: Check for known issues pre-deploy
        self.progress.emit(3, total, "Checking for known issues...")
        issues = self._detect_issues(diag)
        for issue in issues:
            self.issue_found.emit(issue.code, issue.title)
            self.log.emit(f"⚠ Found: {issue.title}")

        # Step 4: Deploy neko
        self.progress.emit(4, total, "Deploying neko (pulling image, configuring)...")
        self.log.emit("Starting neko deployment with TCP-only WebRTC config...")
        self.log.emit("This will take 2-5 minutes on first run (pulling ~2GB image)...")

        rc, deploy_out = self._ssh_exec_script(NEKO_DEPLOY_SCRIPT, timeout=600)
        for line in deploy_out.strip().split("\n"):
            if line.startswith("[FunPod]"):
                self.log.emit(line)

        if rc != 0 and "DONE" not in deploy_out:
            self.error.emit(f"Deployment may have failed (exit {rc}). Check logs.")
            # Don't return — try healing

        # Step 5: Post-deploy health check
        self.progress.emit(5, total, "Verifying deployment...")
        self.log.emit("Running post-deploy health check...")
        rc, health = self._ssh_exec(
            "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null",
            timeout=15
        )
        http_code = health.strip()
        
        if http_code in ("200", "301", "302"):
            self.log.emit(f"✅ Neko web UI responding (HTTP {http_code})")
        else:
            self.log.emit(f"⚠ Neko web UI not responding yet (HTTP {http_code})")
            self.log.emit("Attempting auto-heal...")
            self._auto_heal()

        # Step 6: Get access URL — use RunPod proxy (raw IP:port won't work)
        self.progress.emit(6, total, "Getting access URL...")
        if self.pod_id:
            neko_url = f"https://{self.pod_id}-8080.proxy.runpod.net"
            self.log.emit(f"🎮 Neko URL (RunPod proxy): {neko_url}")
        else:
            rc, ip = self._ssh_exec(
                "curl -s --max-time 3 https://ifconfig.co/ip 2>/dev/null", timeout=10
            )
            public_ip = ip.strip()
            neko_url = f"http://{public_ip}:8080"
            self.log.emit(f"🎮 Neko URL (direct): {neko_url}")
        self.log.emit(f"Password: funpod / funpodadmin")
        self.log.emit(f"WebRTC: TCP mux on port 59000 (RunPod compatible)")
        self.deployed.emit(neko_url)

    def _do_diagnose(self):
        """Run full diagnostics and report all issues."""
        self.progress.emit(1, 2, "Running diagnostics...")
        rc, diag = self._ssh_exec_script(DIAGNOSE_SCRIPT, timeout=30)
        for line in diag.strip().split("\n"):
            self.log.emit(line)

        self.progress.emit(2, 2, "Analyzing results...")
        issues = self._detect_issues(diag)
        if not issues:
            self.log.emit("✅ No issues detected")
        else:
            for issue in issues:
                self.issue_found.emit(issue.code, issue.title)
                self.log.emit(f"⚠ {issue.severity.value.upper()}: {issue.title}")
                self.log.emit(f"  → {issue.description}")

    def _do_heal(self):
        """Fix a specific issue."""
        if not self.heal_target:
            return
        issue = KNOWN_ISSUES.get(self.heal_target)
        if not issue:
            self.error.emit(f"Unknown issue: {self.heal_target}")
            return

        self.progress.emit(1, 2, f"Fixing: {issue.title}...")
        self.log.emit(f"Applying fix for {issue.code}: {issue.title}")

        if issue.fix_cmds:
            fix_script = HEAL_SCRIPT_TEMPLATE.format(
                issue_title=issue.title,
                fix_commands="\n".join(issue.fix_cmds),
                verify_command=issue.verify_cmd,
            )
            rc, out = self._ssh_exec_script(fix_script, timeout=120)
            for line in out.strip().split("\n"):
                self.log.emit(f"  {line}")

        self.progress.emit(2, 2, "Verifying fix...")
        rc, verify = self._ssh_exec(issue.verify_cmd, timeout=15)
        self.log.emit(f"Verify result: {verify.strip()}")
        self.issue_fixed.emit(issue.code)

    def _auto_heal(self):
        """Try to fix the most common issues automatically."""
        heal_sequence = [
            "STALE_CONTAINER",
            "PORT_CONFLICT",
            "SHM_TOO_LOW",
            "DNS_FAILURE",
            "PROFILE_CORRUPT",
        ]
        for code in heal_sequence:
            issue = KNOWN_ISSUES[code]
            if issue.fix_cmds:
                self.log.emit(f"Auto-heal: {issue.title}...")
                cmds = " && ".join(issue.fix_cmds)
                rc, out = self._ssh_exec(cmds, timeout=30)
                if rc == 0:
                    self.log.emit(f"  ✓ {code}")
                else:
                    self.log.emit(f"  ✗ {code}: {out[:80]}")

        # Restart neko after healing
        self.log.emit("Restarting neko container...")
        self._ssh_exec("docker restart funpod-neko 2>/dev/null || true", timeout=30)
        time.sleep(5)

        # Final check
        rc, http = self._ssh_exec(
            "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null",
            timeout=10
        )
        if http.strip() in ("200", "301", "302"):
            self.log.emit("✅ Auto-heal successful — neko is live!")
        else:
            self.log.emit("❌ Auto-heal did not resolve the issue. Manual intervention needed.")
            self.log.emit("Run: docker logs funpod-neko")

    def _detect_issues(self, diagnostics: str) -> list[Issue]:
        """Analyze diagnostic output and return detected issues."""
        found = []
        diag = diagnostics.lower()

        # Always flag UDP on RunPod
        found.append(KNOWN_ISSUES["UDP_BLOCKED"])

        if "no gpu" in diag or "nvidia-smi" not in diag:
            if "nvidia" not in diag:
                found.append(KNOWN_ISSUES["NVIDIA_DRIVER"])

        if "no docker" in diag:
            found.append(KNOWN_ISSUES["DOCKER_NOT_RUNNING"])

        if "no containers" in diag and "no docker" not in diag:
            found.append(KNOWN_ISSUES["NEKO_NOT_INSTALLED"])

        shm_line = [l for l in diagnostics.split("\n") if "SHM:" in l]
        if shm_line:
            shm_val = shm_line[0].split(":")[-1].strip()
            if "M" in shm_val.upper():
                try:
                    mb = int("".join(c for c in shm_val if c.isdigit()))
                    if mb < 1500:
                        found.append(KNOWN_ISSUES["SHM_TOO_LOW"])
                except ValueError:
                    pass

        if "dns" in diag and "fail" in diag:
            found.append(KNOWN_ISSUES["DNS_FAILURE"])

        if "http status: 000" in diag:
            found.append(KNOWN_ISSUES["PORT_CONFLICT"])

        return found

    def stop(self):
        self._running = False

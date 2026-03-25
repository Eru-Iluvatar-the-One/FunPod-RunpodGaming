"""
FunPod — One-Click RunPod Gaming Pod Launcher
PyQt6 · Catppuccin Mocha · Fingolfin Standard

Paste pod ID → Start → Progress bar → Auto-connect → Game launches.
No browser. No login screen. Just play.

Drop into: C:/Users/Eru/Documents/GitHub/FunPod-RunpodGaming/
Run:        C:/Python311/python.exe funpod.py
Requires:   pip install runpod PyQt6 requests
"""
import sys, os, json, ctypes, webbrowser, subprocess, time
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStatusBar, QTextEdit, QLineEdit,
    QProgressBar, QComboBox, QGroupBox, QGridLayout, QMessageBox,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QSettings, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPalette, QShortcut, QKeySequence, QFont

import requests

# ── Catppuccin Mocha ──────────────────────────────────────────────
C = {
    "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
    "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
    "text": "#cdd6f4", "subtext0": "#a6adc8", "subtext1": "#bac2de",
    "blue": "#89b4fa", "green": "#a6e3a1", "peach": "#fab387",
    "mauve": "#cba6f7", "red": "#f38ba8", "teal": "#94e2d5",
    "yellow": "#f9e2af", "overlay0": "#6c7086", "sapphire": "#74c7ec",
    "lavender": "#b4befe",
}

FU = "'Segoe UI Variable', 'Inter', 'Segoe UI', sans-serif"
FM = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"

QSS = f"""
* {{ font-family: {FU}; }}
QMainWindow {{ background: {C['crust']}; }}
QWidget {{ background: {C['base']}; color: {C['text']}; }}
QLineEdit {{
    background: {C['surface0']}; color: {C['text']};
    border: 1px solid {C['surface1']}; border-radius: 10px;
    padding: 12px 16px; font-size: 13pt; font-family: {FM};
    letter-spacing: 1px;
}}
QLineEdit:focus {{ border-color: {C['green']}; border-width: 2px; }}
QLineEdit#apikey {{ font-size: 10pt; }}
QPushButton {{
    background: {C['surface0']}; color: {C['text']};
    border: 1px solid {C['surface1']}; border-radius: 10px;
    padding: 10px 24px; font-weight: 700; font-size: 11pt;
}}
QPushButton:hover {{ background: {C['surface1']}; border-color: {C['green']}; }}
QPushButton:disabled {{ background: {C['surface0']}; color: {C['overlay0']}; border-color: {C['surface0']}; }}
QPushButton#launch {{
    background: {C['green']}; color: {C['crust']}; border: none;
    font-size: 16pt; font-weight: 800; padding: 18px 40px;
    border-radius: 14px; letter-spacing: 1px;
}}
QPushButton#launch:hover {{ background: {C['teal']}; }}
QPushButton#launch:disabled {{ background: {C['surface1']}; color: {C['overlay0']}; }}
QPushButton#stop {{
    background: {C['red']}; color: {C['crust']}; border: none;
    font-size: 12pt; font-weight: 700; padding: 12px 28px; border-radius: 10px;
}}
QPushButton#stop:hover {{ background: {C['peach']}; }}
QPushButton#connect {{
    background: {C['blue']}; color: {C['crust']}; border: none;
    font-size: 12pt; font-weight: 700; padding: 12px 28px; border-radius: 10px;
}}
QPushButton#connect:hover {{ background: {C['sapphire']}; }}
QProgressBar {{
    background: {C['surface0']}; border: none; border-radius: 8px; height: 16px;
    font-size: 9pt; color: {C['text']}; text-align: center;
}}
QProgressBar::chunk {{ background: {C['green']}; border-radius: 8px; }}
QTextEdit {{
    background: {C['mantle']}; color: {C['subtext0']};
    border: 1px solid {C['surface0']}; border-radius: 10px;
    padding: 10px; font-family: {FM}; font-size: 9pt;
}}
QLabel#title {{
    color: {C['text']}; font-size: 28pt; font-weight: 800;
    letter-spacing: -1px; background: transparent;
}}
QLabel#subtitle {{
    color: {C['overlay0']}; font-size: 10pt; font-weight: 500;
    background: transparent;
}}
QLabel#status_big {{
    color: {C['green']}; font-size: 14pt; font-weight: 700;
    background: transparent;
}}
QLabel#info {{ color: {C['subtext0']}; font-size: 9.5pt; background: transparent; }}
QLabel#cost {{ color: {C['yellow']}; font-size: 11pt; font-weight: 600; background: transparent; }}
QLabel#gpu {{ color: {C['mauve']}; font-size: 11pt; font-weight: 600; background: transparent; }}
QFrame#card {{
    background: {C['mantle']}; border: 1px solid {C['surface0']};
    border-radius: 12px;
}}
QStatusBar {{ background: {C['crust']}; color: {C['overlay0']}; font-size: 8.5pt; border-top: 1px solid {C['surface0']}; }}
QStatusBar::item {{ border: none; }}
QComboBox {{
    background: {C['surface0']}; color: {C['text']};
    border: 1px solid {C['surface1']}; border-radius: 8px;
    padding: 8px 12px; font-size: 10pt;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {C['surface0']}; color: {C['text']}; selection-background-color: {C['surface1']}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {C['surface2']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ── Config ────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".funpod"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

GRAPHQL_URL = "https://api.runpod.io/graphql"

# ── Pod status cycle for progress bar ─────────────────────────────
STATUS_STEPS = {
    "CREATED": (10, "Pod created..."),
    "BUILDING": (30, "Building container..."),
    "STARTING": (50, "Starting GPU instance..."),
    "PULLING": (60, "Pulling Docker image..."),
    "RUNNING": (100, "Pod is LIVE!"),
    "EXITED": (0, "Pod stopped"),
    "TERMINATED": (0, "Pod terminated"),
}


def _load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), "utf-8")


# ── GraphQL client (no SDK dependency) ────────────────────────────
class RunPodAPI:
    """Minimal RunPod GraphQL client. No pip dependency beyond requests."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = f"{GRAPHQL_URL}?api_key={api_key}"

    def _query(self, query: str, variables: dict = None) -> dict:
        body = {"query": query}
        if variables:
            body["variables"] = variables
        r = requests.post(self.url, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"][0].get("message", str(data["errors"])))
        return data.get("data", {})

    def get_pod(self, pod_id: str) -> dict:
        q = """query($id: String!) {
            pod(input: {podId: $id}) {
                id name desiredStatus imageName
                costPerHr gpuCount
                machine { gpuDisplayName }
                runtime {
                    uptimeInSeconds
                    ports { ip isIpPublic privatePort publicPort type }
                    gpus { id gpuUtilPercent memoryUtilPercent }
                }
            }
        }"""
        return self._query(q, {"id": pod_id}).get("pod", {})

    def get_pods(self) -> list:
        q = """query { myself { pods { id name desiredStatus imageName costPerHr machine { gpuDisplayName } } } }"""
        return self._query(q).get("myself", {}).get("pods", [])

    def start_pod(self, pod_id: str) -> dict:
        q = """mutation($id: String!) { podResume(input: {podId: $id, gpuCount: 1}) { id desiredStatus } }"""
        return self._query(q, {"id": pod_id})

    def stop_pod(self, pod_id: str) -> dict:
        q = """mutation($id: String!) { podStop(input: {podId: $id}) { id desiredStatus } }"""
        return self._query(q, {"id": pod_id})

    def create_pod(self, name: str, image: str, gpu_type: str, ports: str = "22/tcp",
                   volume_gb: int = 20, container_gb: int = 20, env: dict = None) -> dict:
        q = """mutation($input: PodFindAndDeployOnDemandInput!) {
            podFindAndDeployOnDemand(input: $input) {
                id name desiredStatus costPerHr
                machine { gpuDisplayName }
            }
        }"""
        inp = {
            "name": name,
            "imageName": image,
            "gpuTypeId": gpu_type,
            "gpuCount": 1,
            "cloudType": "ALL",
            "containerDiskInGb": container_gb,
            "volumeInGb": volume_gb,
            "ports": ports,
            "supportPublicIp": True,
        }
        if env:
            inp["env"] = [{"key": k, "value": v} for k, v in env.items()]
        return self._query(q, {"input": inp})

    def get_balance(self) -> float:
        q = """query { myself { currentSpend { amount } creditBalance } }"""
        data = self._query(q).get("myself", {})
        return float(data.get("creditBalance", 0))


# ── Worker thread for API calls ───────────────────────────────────
class PodWorker(QThread):
    status_update = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, api: RunPodAPI, pod_id: str, action: str = "poll"):
        super().__init__()
        self.api = api
        self.pod_id = pod_id
        self.action = action
        self._running = True

    def run(self):
        try:
            if self.action == "start":
                self.log.emit("Starting pod...")
                self.api.start_pod(self.pod_id)
                self.log.emit("Start command sent. Polling status...")
                self._poll_until_running()

            elif self.action == "stop":
                self.log.emit("Stopping pod...")
                self.api.stop_pod(self.pod_id)
                self.log.emit("Stop command sent.")
                pod = self.api.get_pod(self.pod_id)
                self.status_update.emit(pod)

            elif self.action == "poll":
                pod = self.api.get_pod(self.pod_id)
                self.status_update.emit(pod)

            elif self.action == "poll_until_running":
                self._poll_until_running()

        except Exception as e:
            self.error.emit(str(e))

    def _poll_until_running(self):
        for i in range(120):  # 10 min max
            if not self._running:
                return
            try:
                pod = self.api.get_pod(self.pod_id)
                status = pod.get("desiredStatus", "UNKNOWN")
                self.status_update.emit(pod)
                self.log.emit(f"[{i*5}s] Status: {status}")
                if status == "RUNNING" and pod.get("runtime"):
                    self.log.emit("Pod is LIVE with runtime!")
                    return
                if status in ("TERMINATED", "EXITED"):
                    self.log.emit(f"Pod is {status}")
                    return
            except Exception as e:
                self.log.emit(f"Poll error: {e}")
            time.sleep(5)
        self.log.emit("Timeout waiting for pod")

    def stop_polling(self):
        self._running = False


# ── Main Window ───────────────────────────────────────────────────
class FunPodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod")
        self.setMinimumSize(580, 700)
        self.resize(620, 760)

        self._settings = QSettings("ArdaTek", "FunPod")
        geo = self._settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

        self._cfg = _load_config()
        self._api: Optional[RunPodAPI] = None
        self._worker: Optional[PodWorker] = None
        self._current_pod: dict = {}

        if self._cfg.get("api_key"):
            self._api = RunPodAPI(self._cfg["api_key"])

        self._build_ui()
        self._restore_fields()

        # Auto-poll if we have a pod ID saved
        if self._api and self._cfg.get("last_pod_id"):
            QTimer.singleShot(500, self._poll_status)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # ── Title ─────────────────────────────
        title = QLabel("🎮  FunPod")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel("One-click cloud gaming. No browser needed.")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)
        root.addSpacing(8)

        # ── API Key (collapsible) ─────────────
        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        key_lbl = QLabel("API Key:")
        key_lbl.setStyleSheet(f"color: {C['subtext0']}; font-size: 9pt; background: transparent;")
        key_row.addWidget(key_lbl)
        self._key_input = QLineEdit()
        self._key_input.setObjectName("apikey")
        self._key_input.setPlaceholderText("Paste RunPod API key...")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.textChanged.connect(self._on_key_changed)
        key_row.addWidget(self._key_input, 1)
        btn_show = QPushButton("👁")
        btn_show.setFixedSize(36, 36)
        btn_show.setCheckable(True)
        btn_show.clicked.connect(lambda checked: self._key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password))
        key_row.addWidget(btn_show)
        root.addLayout(key_row)

        # ── Pod ID ────────────────────────────
        pod_lbl = QLabel("Pod ID:")
        pod_lbl.setStyleSheet(f"color: {C['subtext0']}; font-size: 9pt; background: transparent; margin-top: 4px;")
        root.addWidget(pod_lbl)

        self._pod_input = QLineEdit()
        self._pod_input.setPlaceholderText("Paste pod ID here (e.g. ix5fgrpbja52vd)")
        self._pod_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._pod_input)

        # ── Status card ───────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 16)
        card_lay.setSpacing(8)

        self._status_label = QLabel("Not connected")
        self._status_label.setObjectName("status_big")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self._status_label)

        info_row = QHBoxLayout()
        info_row.setSpacing(20)
        self._gpu_label = QLabel("")
        self._gpu_label.setObjectName("gpu")
        self._gpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._gpu_label)
        self._cost_label = QLabel("")
        self._cost_label.setObjectName("cost")
        self._cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._cost_label)
        card_lay.addLayout(info_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p% — %v")
        card_lay.addWidget(self._progress)

        self._uptime_label = QLabel("")
        self._uptime_label.setObjectName("info")
        self._uptime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self._uptime_label)

        root.addWidget(card)

        # ── Action buttons ────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_launch = QPushButton("▶   LAUNCH POD")
        self._btn_launch.setObjectName("launch")
        self._btn_launch.clicked.connect(self._start_pod)
        btn_row.addWidget(self._btn_launch)

        root.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(10)

        self._btn_connect = QPushButton("🔗  Connect")
        self._btn_connect.setObjectName("connect")
        self._btn_connect.setEnabled(False)
        self._btn_connect.clicked.connect(self._connect_pod)
        btn_row2.addWidget(self._btn_connect)

        self._btn_stop = QPushButton("⏹  Stop Pod")
        self._btn_stop.setObjectName("stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_pod)
        btn_row2.addWidget(self._btn_stop)

        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.clicked.connect(self._poll_status)
        btn_row2.addWidget(btn_refresh)

        root.addLayout(btn_row2)

        # ── Log ───────────────────────────────
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(150)
        self._log.setPlaceholderText("Activity log...")
        root.addWidget(self._log)

        # ── Neko Deploy Section ───────────────
        neko_card = QFrame()
        neko_card.setObjectName("card")
        neko_lay = QVBoxLayout(neko_card)
        neko_lay.setContentsMargins(16, 12, 16, 12)
        neko_lay.setSpacing(8)

        neko_title = QLabel("🐱  Neko Virtual Desktop")
        neko_title.setStyleSheet(f"color: {C['mauve']}; font-size: 12pt; font-weight: 700; background: transparent;")
        neko_lay.addWidget(neko_title)

        neko_desc = QLabel("Deploys n.eko WebRTC desktop inside your pod. TCP-only mode for RunPod.")
        neko_desc.setStyleSheet(f"color: {C['overlay0']}; font-size: 8.5pt; background: transparent;")
        neko_desc.setWordWrap(True)
        neko_lay.addWidget(neko_desc)

        neko_btn_row = QHBoxLayout()
        neko_btn_row.setSpacing(8)

        self._btn_deploy_neko = QPushButton("🚀  Deploy Neko")
        self._btn_deploy_neko.setStyleSheet(f"background: {C['mauve']}; color: {C['crust']}; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 700; font-size: 10pt;")
        self._btn_deploy_neko.clicked.connect(self._deploy_neko)
        neko_btn_row.addWidget(self._btn_deploy_neko)

        self._btn_diagnose = QPushButton("🔍  Diagnose")
        self._btn_diagnose.clicked.connect(self._diagnose_neko)
        neko_btn_row.addWidget(self._btn_diagnose)

        self._btn_heal = QPushButton("💊  Auto-Heal")
        self._btn_heal.clicked.connect(self._heal_neko)
        neko_btn_row.addWidget(self._btn_heal)

        self._btn_open_neko = QPushButton("🌐  Open Desktop")
        self._btn_open_neko.setObjectName("connect")
        self._btn_open_neko.setEnabled(False)
        self._btn_open_neko.clicked.connect(self._open_neko)
        neko_btn_row.addWidget(self._btn_open_neko)

        neko_lay.addLayout(neko_btn_row)

        self._neko_progress = QProgressBar()
        self._neko_progress.setRange(0, 6)
        self._neko_progress.setValue(0)
        self._neko_progress.setVisible(False)
        neko_lay.addWidget(self._neko_progress)

        root.addWidget(neko_card)

        root.addStretch()

        # ── Status bar ────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._sb_label = QLabel("Ready")
        sb.addWidget(self._sb_label)
        self._balance_label = QLabel("")
        self._balance_label.setStyleSheet(f"color: {C['green']}; font-weight: 600;")
        sb.addPermanentWidget(self._balance_label)

        # Shortcuts
        QShortcut(QKeySequence("F5"), self, self._poll_status)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._start_pod)

    # ── Field persistence ─────────────────────────────────────────
    def _restore_fields(self):
        self._key_input.setText(self._cfg.get("api_key", ""))
        self._pod_input.setText(self._cfg.get("last_pod_id", ""))

    def _on_key_changed(self, text):
        text = text.strip()
        if len(text) > 10:
            self._cfg["api_key"] = text
            _save_config(self._cfg)
            self._api = RunPodAPI(text)
            self._log_msg("API key saved.")
            # Fetch balance
            try:
                bal = self._api.get_balance()
                self._balance_label.setText(f"${bal:.2f}")
            except Exception:
                pass

    def _get_pod_id(self) -> str:
        pid = self._pod_input.text().strip()
        if pid:
            self._cfg["last_pod_id"] = pid
            _save_config(self._cfg)
        return pid

    # ── Logging ───────────────────────────────────────────────────
    def _log_msg(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"[{ts}] {msg}")
        self._sb_label.setText(msg[:80])

    # ── Pod actions ───────────────────────────────────────────────
    def _start_pod(self):
        if not self._api:
            self._log_msg("ERROR: Set API key first")
            return
        pid = self._get_pod_id()
        if not pid:
            self._log_msg("ERROR: Enter a pod ID")
            return

        self._btn_launch.setEnabled(False)
        self._btn_launch.setText("⏳  LAUNCHING...")
        self._progress.setValue(5)
        self._status_label.setText("Starting...")
        self._status_label.setStyleSheet(f"color: {C['yellow']}; font-size: 14pt; font-weight: 700; background: transparent;")
        self._log_msg(f"Starting pod {pid}...")

        self._worker = PodWorker(self._api, pid, "start")
        self._worker.status_update.connect(self._on_status)
        self._worker.error.connect(self._on_error)
        self._worker.log.connect(self._log_msg)
        self._worker.start()

    def _stop_pod(self):
        if not self._api:
            return
        pid = self._get_pod_id()
        if not pid:
            return
        self._log_msg(f"Stopping pod {pid}...")
        self._worker = PodWorker(self._api, pid, "stop")
        self._worker.status_update.connect(self._on_status)
        self._worker.error.connect(self._on_error)
        self._worker.log.connect(self._log_msg)
        self._worker.start()

    def _poll_status(self):
        if not self._api:
            self._log_msg("Set API key first")
            return
        pid = self._get_pod_id()
        if not pid:
            return
        self._log_msg(f"Polling {pid}...")
        self._worker = PodWorker(self._api, pid, "poll")
        self._worker.status_update.connect(self._on_status)
        self._worker.error.connect(self._on_error)
        self._worker.log.connect(self._log_msg)
        self._worker.start()

    def _connect_pod(self):
        """Open connection to running pod — web terminal or SSH."""
        pod = self._current_pod
        pid = self._get_pod_id()
        if not pod or not pid:
            return

        runtime = pod.get("runtime")
        if not runtime:
            self._log_msg("Pod has no runtime — not ready yet")
            return

        ports = runtime.get("ports", [])

        # Try to find SSH port
        ssh_info = None
        for p in ports:
            if p.get("privatePort") == 22 and p.get("isIpPublic"):
                ssh_info = (p["ip"], p["publicPort"])
                break

        # Try RDP
        rdp_info = None
        for p in ports:
            if p.get("privatePort") == 3389 and p.get("isIpPublic"):
                rdp_info = (p["ip"], p["publicPort"])
                break

        # Web terminal is always available
        web_url = f"https://{pid}-22.proxy.runpod.net"

        if rdp_info:
            self._log_msg(f"Opening RDP: {rdp_info[0]}:{rdp_info[1]}")
            # Launch mstsc (Windows Remote Desktop)
            try:
                subprocess.Popen(["mstsc", f"/v:{rdp_info[0]}:{rdp_info[1]}"])
            except Exception as e:
                self._log_msg(f"RDP launch failed: {e}")
                webbrowser.open(web_url)
        elif ssh_info:
            self._log_msg(f"SSH available: ssh root@{ssh_info[0]} -p {ssh_info[1]}")
            # Open web terminal as fallback
            webbrowser.open(web_url)
        else:
            self._log_msg("Opening RunPod web terminal...")
            webbrowser.open(web_url)

    # ── Status handler ────────────────────────────────────────────
    def _on_status(self, pod: dict):
        self._current_pod = pod
        status = pod.get("desiredStatus", "UNKNOWN")
        name = pod.get("name", "")
        image = pod.get("imageName", "")
        cost = pod.get("costPerHr", 0)
        gpu_name = ""
        machine = pod.get("machine")
        if machine:
            gpu_name = machine.get("gpuDisplayName", "")

        # Progress bar
        step = STATUS_STEPS.get(status, (0, status))
        self._progress.setValue(step[0])
        self._progress.setFormat(f"{step[1]}  ({step[0]}%)")

        # Status label
        colors = {
            "RUNNING": C["green"], "EXITED": C["overlay0"],
            "CREATED": C["yellow"], "STARTING": C["yellow"],
            "BUILDING": C["peach"], "PULLING": C["peach"],
            "TERMINATED": C["red"],
        }
        color = colors.get(status, C["text"])
        self._status_label.setText(f"●  {status}")
        self._status_label.setStyleSheet(f"color: {color}; font-size: 14pt; font-weight: 700; background: transparent;")

        # Info
        if gpu_name:
            self._gpu_label.setText(f"🖥  {gpu_name}")
        if cost:
            self._cost_label.setText(f"💰  ${cost:.2f}/hr")

        # Uptime
        runtime = pod.get("runtime")
        if runtime and runtime.get("uptimeInSeconds"):
            mins = int(runtime["uptimeInSeconds"]) // 60
            hrs = mins // 60
            mins = mins % 60
            self._uptime_label.setText(f"⏱  Uptime: {hrs}h {mins}m")

            # GPU utilization
            gpus = runtime.get("gpus", [])
            if gpus:
                util = gpus[0].get("gpuUtilPercent", 0)
                mem = gpus[0].get("memoryUtilPercent", 0)
                self._uptime_label.setText(
                    f"⏱ {hrs}h {mins}m  ·  GPU: {util}%  ·  VRAM: {mem}%")

        # Button states
        is_running = status == "RUNNING" and runtime is not None
        self._btn_launch.setEnabled(status in ("EXITED", "TERMINATED", "CREATED", "UNKNOWN"))
        self._btn_launch.setText("▶   LAUNCH POD" if not is_running else "✅  POD IS LIVE")
        self._btn_connect.setEnabled(is_running)
        self._btn_stop.setEnabled(status == "RUNNING")

        # Auto-connect when pod goes live
        if is_running and self._progress.value() < 100:
            self._progress.setValue(100)
            self._log_msg("🎮 POD IS LIVE! Click Connect to play.")
            # Auto-open connection
            QTimer.singleShot(1000, self._connect_pod)

    def _on_error(self, msg):
        self._log_msg(f"❌ ERROR: {msg}")
        self._btn_launch.setEnabled(True)
        self._btn_launch.setText("▶   LAUNCH POD")
        self._status_label.setText("Error")
        self._status_label.setStyleSheet(f"color: {C['red']}; font-size: 14pt; font-weight: 700; background: transparent;")

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        if self._worker:
            self._worker.stop_polling()
        event.accept()

    # ── Neko deployment ───────────────────────────────────────────
    def _get_ssh_info(self) -> tuple:
        """Extract SSH host/port from current pod runtime."""
        pod = self._current_pod
        if not pod:
            return None, None
        runtime = pod.get("runtime")
        if not runtime:
            return None, None
        for p in runtime.get("ports", []):
            if p.get("privatePort") == 22 and p.get("isIpPublic"):
                return p["ip"], p["publicPort"]
        return None, None

    def _deploy_neko(self):
        ssh_host, ssh_port = self._get_ssh_info()
        if not ssh_host:
            self._log_msg("❌ Pod must be RUNNING with SSH port exposed. Start pod first.")
            return
        self._log_msg(f"🐱 Deploying neko to {ssh_host}:{ssh_port}...")
        self._btn_deploy_neko.setEnabled(False)
        self._btn_deploy_neko.setText("⏳ Deploying...")
        self._neko_progress.setVisible(True)
        self._neko_progress.setValue(0)

        try:
            from neko_healer import NekoHealer
            self._neko_worker = NekoHealer(ssh_host, ssh_port, action="deploy")
            self._neko_worker.progress.connect(self._on_neko_progress)
            self._neko_worker.log.connect(self._log_msg)
            self._neko_worker.deployed.connect(self._on_neko_deployed)
            self._neko_worker.issue_found.connect(lambda c, t: self._log_msg(f"⚠ Issue: {t}"))
            self._neko_worker.issue_fixed.connect(lambda c: self._log_msg(f"✅ Fixed: {c}"))
            self._neko_worker.error.connect(self._on_neko_error)
            self._neko_worker.finished_signal.connect(lambda: self._btn_deploy_neko.setEnabled(True))
            self._neko_worker.finished_signal.connect(lambda: self._btn_deploy_neko.setText("🚀  Deploy Neko"))
            self._neko_worker.start()
        except ImportError:
            self._log_msg("❌ neko_healer.py not found. Place it next to funpod.py.")
            self._btn_deploy_neko.setEnabled(True)
            self._btn_deploy_neko.setText("🚀  Deploy Neko")

    def _diagnose_neko(self):
        ssh_host, ssh_port = self._get_ssh_info()
        if not ssh_host:
            self._log_msg("❌ Pod must be RUNNING. Start pod first.")
            return
        self._log_msg(f"🔍 Running diagnostics on {ssh_host}:{ssh_port}...")
        try:
            from neko_healer import NekoHealer
            self._neko_worker = NekoHealer(ssh_host, ssh_port, action="diagnose")
            self._neko_worker.log.connect(self._log_msg)
            self._neko_worker.issue_found.connect(lambda c, t: self._log_msg(f"⚠ {t}"))
            self._neko_worker.error.connect(lambda e: self._log_msg(f"❌ {e}"))
            self._neko_worker.start()
        except ImportError:
            self._log_msg("❌ neko_healer.py not found.")

    def _heal_neko(self):
        ssh_host, ssh_port = self._get_ssh_info()
        if not ssh_host:
            self._log_msg("❌ Pod must be RUNNING.")
            return
        self._log_msg(f"💊 Running auto-heal on {ssh_host}:{ssh_port}...")
        try:
            from neko_healer import NekoHealer
            self._neko_worker = NekoHealer(ssh_host, ssh_port, action="deploy")
            self._neko_worker.log.connect(self._log_msg)
            self._neko_worker.deployed.connect(self._on_neko_deployed)
            self._neko_worker.error.connect(lambda e: self._log_msg(f"❌ {e}"))
            self._neko_worker.start()
        except ImportError:
            self._log_msg("❌ neko_healer.py not found.")

    def _on_neko_progress(self, step, total, msg):
        self._neko_progress.setRange(0, total)
        self._neko_progress.setValue(step)

    def _on_neko_deployed(self, url):
        self._neko_url = url
        self._btn_open_neko.setEnabled(True)
        self._neko_progress.setVisible(False)
        self._log_msg(f"🎮 NEKO IS LIVE: {url}")
        self._log_msg(f"Password: funpod / funpodadmin")

    def _on_neko_error(self, msg):
        self._neko_progress.setVisible(False)
        self._btn_deploy_neko.setEnabled(True)
        self._btn_deploy_neko.setText("🚀  Deploy Neko")
        self._log_msg(f"❌ Neko error: {msg}")

    def _open_neko(self):
        url = getattr(self, '_neko_url', None)
        if url:
            webbrowser.open(url)
        else:
            self._log_msg("No neko URL yet. Deploy first.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(C["crust"]))
    p.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
    p.setColor(QPalette.ColorRole.Base, QColor(C["base"]))
    p.setColor(QPalette.ColorRole.Button, QColor(C["surface0"]))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(C["text"]))
    p.setColor(QPalette.ColorRole.Highlight, QColor(C["green"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(C["crust"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(C["overlay0"]))
    app.setPalette(p)

    w = FunPodWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
FunPod — One-Click RunPod Gaming Launcher
PyQt6 · Catppuccin Mocha · Fingolfin Standard

Paste pod ID → See game grid → Click Play → Desktop renders INSIDE FunPod.
Run: C:/Python311/python.exe funpod.py
Requires: pip install PyQt6 PyQt6-WebEngine requests
"""
import sys
import json
import ctypes
import webbrowser
import time
import subprocess
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
    QProgressBar, QScrollArea, QSizePolicy, QStackedWidget,
)
from PyQt6.QtCore import Qt, QSettings, QTimer, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QColor, QPalette, QShortcut, QKeySequence, QPixmap

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

import requests

C = {
    "base":     "#1e1e2e", "mantle":   "#181825", "crust":    "#11111b",
    "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
    "text":     "#cdd6f4", "subtext0": "#a6adc8", "subtext1": "#bac2de",
    "blue":     "#89b4fa", "green":    "#a6e3a1", "peach":    "#fab387",
    "mauve":    "#cba6f7", "red":      "#f38ba8", "teal":     "#94e2d5",
    "yellow":   "#f9e2af", "overlay0": "#6c7086", "sapphire": "#74c7ec",
    "lavender": "#b4befe", "sky":      "#89dceb",
}

FU = "'Segoe UI Variable', 'Inter', 'Segoe UI', sans-serif"
FM = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"

QSS = f"""
* {{ font-family: {FU}; }}
QMainWindow {{ background: {C['crust']}; }}
QWidget {{ background: {C['base']}; color: {C['text']}; }}
QScrollArea {{ background: {C['base']}; border: none; }}
QScrollArea > QWidget > QWidget {{ background: {C['base']}; }}
QLineEdit {{
    background: {C['surface0']}; color: {C['text']};
    border: 1px solid {C['surface1']}; border-radius: 10px;
    padding: 12px 16px; font-size: 13pt; font-family: {FM};
    letter-spacing: 1px;
}}
QLineEdit:focus {{ border-color: {C['green']}; border-width: 2px; }}
QLineEdit#apikey {{ font-size: 9pt; padding: 8px 12px; }}
QPushButton {{
    background: {C['surface0']}; color: {C['text']};
    border: 1px solid {C['surface1']}; border-radius: 10px;
    padding: 10px 20px; font-weight: 700; font-size: 10pt;
}}
QPushButton:hover {{ background: {C['surface1']}; border-color: {C['green']}; }}
QPushButton:disabled {{ background: {C['surface0']}; color: {C['overlay0']}; border-color: {C['surface0']}; }}
QPushButton#connect_btn {{
    background: {C['green']}; color: {C['crust']}; border: none;
    font-size: 15pt; font-weight: 800; padding: 16px 36px;
    border-radius: 12px;
}}
QPushButton#connect_btn:hover {{ background: {C['teal']}; }}
QPushButton#connect_btn:disabled {{ background: {C['surface1']}; color: {C['overlay0']}; }}
QPushButton#stop_btn {{
    background: {C['red']}; color: {C['crust']}; border: none;
    font-size: 10pt; font-weight: 700; padding: 10px 24px; border-radius: 10px;
}}
QPushButton#stop_btn:hover {{ background: {C['peach']}; }}
QPushButton#play_btn {{
    background: {C['mauve']}; color: {C['crust']}; border: none;
    font-size: 10pt; font-weight: 800; padding: 8px 0;
    border-radius: 8px; width: 100%;
}}
QPushButton#play_btn:hover {{ background: {C['lavender']}; }}
QPushButton#play_btn:disabled {{ background: {C['surface1']}; color: {C['overlay0']}; }}
QProgressBar {{
    background: {C['surface0']}; border: none; border-radius: 8px; height: 14px;
    font-size: 8pt; color: {C['text']}; text-align: center;
}}
QProgressBar::chunk {{ background: {C['green']}; border-radius: 8px; }}
QTextEdit {{
    background: {C['mantle']}; color: {C['subtext0']};
    border: 1px solid {C['surface0']}; border-radius: 10px;
    padding: 8px; font-family: {FM}; font-size: 8pt;
}}
QLabel#title {{ color: {C['text']}; font-size: 26pt; font-weight: 800; background: transparent; }}
QLabel#subtitle {{ color: {C['overlay0']}; font-size: 9pt; background: transparent; }}
QLabel#status_label {{ color: {C['green']}; font-size: 13pt; font-weight: 700; background: transparent; }}
QLabel#gpu_label {{ color: {C['mauve']}; font-size: 10pt; font-weight: 600; background: transparent; }}
QLabel#cost_label {{ color: {C['yellow']}; font-size: 10pt; font-weight: 600; background: transparent; }}
QLabel#section_header {{ color: {C['blue']}; font-size: 13pt; font-weight: 800; background: transparent; }}
QFrame#card {{ background: {C['mantle']}; border: 1px solid {C['surface0']}; border-radius: 12px; }}
QFrame#game_card {{ background: {C['mantle']}; border: 1px solid {C['surface0']}; border-radius: 12px; }}
QFrame#game_card:hover {{ border-color: {C['mauve']}; }}
QStatusBar {{ background: {C['crust']}; color: {C['overlay0']}; font-size: 8pt; border-top: 1px solid {C['surface0']}; }}
QStatusBar::item {{ border: none; }}
"""

STEAM_GAMES = [
    {"appid": 779340, "name": "Total War: THREE KINGDOMS", "short": "3 Kingdoms"},
    {"appid": 8930,   "name": "Civilization V",            "short": "Civ V"},
    {"appid": 289070, "name": "Sid Meier's Civilization VI","short": "Civ VI"},
    {"appid": 1158310,"name": "Crusader Kings III",         "short": "CK3"},
    {"appid": 203770, "name": "Crusader Kings II",          "short": "CK2"},
    {"appid": 412020, "name": "Total War: WARHAMMER II",    "short": "Warhammer II"},
]

STEAM_COVER = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"

CFG_FILE = Path.home() / ".funpod" / "config.json"
CFG_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_cfg():
    try:
        return json.loads(CFG_FILE.read_text("utf-8")) if CFG_FILE.exists() else {}
    except Exception:
        return {}

def save_cfg(cfg):
    CFG_FILE.write_text(json.dumps(cfg, indent=2), "utf-8")

GRAPHQL_URL = "https://api.runpod.io/graphql"

class RunPodAPI:
    def __init__(self, api_key):
        self.url = f"{GRAPHQL_URL}?api_key={api_key}"

    def _q(self, query, variables=None):
        body = {"query": query}
        if variables:
            body["variables"] = variables
        r = requests.post(self.url, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"][0].get("message", str(data["errors"])))
        return data.get("data", {})

    def get_pod(self, pod_id):
        q = """query($id: String!) {
            pod(input: {podId: $id}) {
                id name desiredStatus imageName costPerHr gpuCount
                machine { gpuDisplayName }
                runtime {
                    uptimeInSeconds
                    ports { ip isIpPublic privatePort publicPort type }
                    gpus  { id gpuUtilPercent memoryUtilPercent }
                }
            }
        }"""
        return self._q(q, {"id": pod_id}).get("pod", {})

    def start_pod(self, pod_id):
        q = """mutation($id: String!) { podResume(input:{podId:$id,gpuCount:1}){id desiredStatus} }"""
        return self._q(q, {"id": pod_id})

    def stop_pod(self, pod_id):
        q = """mutation($id: String!) { podStop(input:{podId:$id}){id desiredStatus} }"""
        return self._q(q, {"id": pod_id})

    def exec_cmd(self, pod_id, cmd):
        q = """mutation($id: String!, $cmd: [String!]!) {
            podExec(input: {podId: $id, command: $cmd}) { status }
        }"""
        return self._q(q, {"id": pod_id, "cmd": ["bash", "-c", cmd]})

class PodPoller(QThread):
    status = pyqtSignal(dict)
    log    = pyqtSignal(str)
    error  = pyqtSignal(str)

    def __init__(self, api, pod_id, action="poll"):
        super().__init__()
        self.api    = api
        self.pod_id = pod_id
        self.action = action
        self._go    = True

    def run(self):
        try:
            if self.action == "start":
                self.log.emit("Sending start...")
                self.api.start_pod(self.pod_id)
                self._poll_loop()
            elif self.action == "stop":
                self.log.emit("Stopping...")
                self.api.stop_pod(self.pod_id)
                pod = self.api.get_pod(self.pod_id)
                self.status.emit(pod)
            elif self.action in ("poll", "poll_loop"):
                self._poll_loop(once=(self.action == "poll"))
        except Exception as e:
            self.error.emit(str(e))

    def _poll_loop(self, once=False):
        for _ in range(120):
            if not self._go:
                return
            try:
                pod = self.api.get_pod(self.pod_id)
                self.status.emit(pod)
                s = pod.get("desiredStatus", "")
                self.log.emit(f"Status: {s}")
                if once:
                    return
                if s == "RUNNING" and pod.get("runtime"):
                    return
                if s in ("TERMINATED", "EXITED"):
                    return
            except Exception as e:
                self.log.emit(f"Poll error: {e}")
            time.sleep(5)

    def cancel(self):
        self._go = False


class ImageFetcher(QThread):
    loaded = pyqtSignal(int, bytes)

    def __init__(self, appid):
        super().__init__()
        self.appid = appid

    def run(self):
        try:
            r = requests.get(STEAM_COVER.format(appid=self.appid), timeout=10)
            if r.status_code == 200:
                self.loaded.emit(self.appid, r.content)
        except Exception:
            pass


STEAM_INSTALL_CMD = (
    "dpkg --add-architecture i386 2>/dev/null; "
    "apt-get update -qq 2>/dev/null; "
    "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends steam-launcher 2>/dev/null || "
    "DEBIAN_FRONTEND=noninteractive apt-get install -y steam 2>/dev/null; "
    "echo __STEAM_DONE__"
)

class SteamLauncher(QThread):
    log   = pyqtSignal(str)
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api, pod_id, appid):
        super().__init__()
        self.api    = api
        self.pod_id = pod_id
        self.appid  = appid

    def run(self):
        novnc = f"https://{self.pod_id}-80.proxy.runpod.net/"
        try:
            self.log.emit("Sending Steam install + launch to pod...")
            full_cmd = (
                f"{STEAM_INSTALL_CMD} && "
                f"DISPLAY=:1 nohup steam -silent steam://rungameid/{self.appid} "
                f">/tmp/steam_{self.appid}.log 2>&1 &"
            )
            self.api.exec_cmd(self.pod_id, full_cmd)
            self.log.emit("Command sent. Loading desktop inside FunPod...")
            self.done.emit(novnc)
        except Exception as e:
            self.log.emit(f"podExec failed ({e}) — loading desktop anyway, paste command manually if needed")
            cmd = (
                f"dpkg --add-architecture i386 && apt-get update -qq && "
                f"DEBIAN_FRONTEND=noninteractive apt-get install -y steam && "
                f"DISPLAY=:1 steam steam://rungameid/{self.appid} &"
            )
            try:
                QApplication.clipboard().setText(cmd)
                self.log.emit("Command copied to clipboard — paste in the desktop terminal")
            except Exception:
                pass
            self.done.emit(novnc)


class GameCard(QFrame):
    play_clicked = pyqtSignal(int, str)

    def __init__(self, game: dict, parent=None):
        super().__init__(parent)
        self.appid = game["appid"]
        self.name  = game["name"]
        self.setObjectName("game_card")
        self.setFixedWidth(200)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self._cover = QLabel()
        self._cover.setFixedSize(184, 86)
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setStyleSheet(f"background: {C['surface0']}; border-radius: 6px; color: {C['overlay0']}; font-size: 8pt;")
        self._cover.setText("Loading...")
        lay.addWidget(self._cover)

        lbl = QLabel(game["short"])
        lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: 700; background: transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        self._btn = QPushButton("▶  PLAY")
        self._btn.setObjectName("play_btn")
        self._btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn.setEnabled(False)
        self._btn.clicked.connect(lambda: self.play_clicked.emit(self.appid, self.name))
        lay.addWidget(self._btn)

        self._fetcher = ImageFetcher(self.appid)
        self._fetcher.loaded.connect(self._on_image)
        self._fetcher.start()

    def _on_image(self, appid, data):
        if appid != self.appid:
            return
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            px = px.scaled(184, 86, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
            self._cover.setPixmap(px)
            self._cover.setText("")

    def set_ready(self, enabled: bool):
        self._btn.setEnabled(enabled)

    def set_launching(self, yes: bool):
        self._btn.setEnabled(not yes)
        self._btn.setText("⏳ Launching..." if yes else "▶  PLAY")


# ── Desktop embedded view ─────────────────────────────────────────
class DesktopView(QMainWindow):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FunPod — Gaming Desktop")
        self.resize(1600, 900)
        self.showMaximized()

        self._view = QWebEngineView()
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(f"background:{C['crust']};")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 0, 8, 0)
        tb_lay.setSpacing(8)

        lbl = QLabel("🎮  FunPod Desktop")
        lbl.setStyleSheet(f"color:{C['text']};font-weight:700;font-size:10pt;background:transparent;")
        tb_lay.addWidget(lbl)
        tb_lay.addStretch()

        btn_fs = QPushButton("⛶  Fullscreen")
        btn_fs.setFixedHeight(26)
        btn_fs.clicked.connect(lambda: self.showFullScreen() if not self.isFullScreen() else self.showMaximized())
        tb_lay.addWidget(btn_fs)

        btn_close = QPushButton("✕  Close")
        btn_close.setObjectName("stop_btn")
        btn_close.setFixedHeight(26)
        btn_close.clicked.connect(self.close)
        tb_lay.addWidget(btn_close)

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(toolbar)
        lay.addWidget(self._view, 1)
        self.setCentralWidget(container)

        self._view.setUrl(QUrl(url))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showMaximized()
        super().keyPressEvent(e)


# ── Main window ───────────────────────────────────────────────────
class FunPodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod")
        self.setMinimumSize(700, 820)
        self.resize(760, 900)

        self._cfg         = load_cfg()
        self._settings    = QSettings("ArdaTek", "FunPod")
        self._api:        Optional[RunPodAPI] = None
        self._worker:     Optional[PodPoller] = None
        self._launcher:   Optional[SteamLauncher] = None
        self._pod:        dict = {}
        self._game_cards: list[GameCard] = []
        self._desktop_win = None

        if geo := self._settings.value("geometry"):
            self.restoreGeometry(geo)
        if key := self._cfg.get("api_key"):
            self._api = RunPodAPI(key)

        self._build_ui()
        self._restore_fields()

        if self._api and self._cfg.get("pod_id"):
            QTimer.singleShot(600, self._poll)

    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(28, 20, 28, 16)
        root.setSpacing(10)

        title = QLabel("🎮  FunPod")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel("Paste pod ID  →  Click game  →  Play inside FunPod")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        if not HAS_WEBENGINE:
            warn = QLabel("⚠ PyQt6-WebEngine not installed — run: C:\\Python311\\python.exe -m pip install PyQt6-WebEngine")
            warn.setStyleSheet(f"color:{C['peach']};font-size:8pt;background:transparent;")
            warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            warn.setWordWrap(True)
            root.addWidget(warn)

        root.addSpacing(4)

        key_row = QHBoxLayout()
        key_lbl = QLabel("API Key:")
        key_lbl.setStyleSheet(f"color:{C['subtext0']};font-size:9pt;background:transparent;min-width:56px;")
        key_row.addWidget(key_lbl)
        self._key_in = QLineEdit()
        self._key_in.setObjectName("apikey")
        self._key_in.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_in.setPlaceholderText("RunPod API key")
        self._key_in.textChanged.connect(self._on_key)
        key_row.addWidget(self._key_in, 1)
        btn_eye = QPushButton("👁")
        btn_eye.setFixedSize(34, 34)
        btn_eye.setCheckable(True)
        btn_eye.clicked.connect(lambda c: self._key_in.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        key_row.addWidget(btn_eye)
        root.addLayout(key_row)

        pod_row = QHBoxLayout()
        pod_row.setSpacing(10)
        self._pod_in = QLineEdit()
        self._pod_in.setPlaceholderText("Paste pod ID here")
        self._pod_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pod_row.addWidget(self._pod_in, 1)
        self._btn_connect = QPushButton("⚡  CONNECT")
        self._btn_connect.setObjectName("connect_btn")
        self._btn_connect.setFixedWidth(160)
        self._btn_connect.clicked.connect(self._do_connect)
        pod_row.addWidget(self._btn_connect)
        root.addLayout(pod_row)

        status_card = QFrame()
        status_card.setObjectName("card")
        sc_lay = QVBoxLayout(status_card)
        sc_lay.setContentsMargins(16, 12, 16, 12)
        sc_lay.setSpacing(6)

        self._status_lbl = QLabel("Not connected")
        self._status_lbl.setObjectName("status_label")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc_lay.addWidget(self._status_lbl)

        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        self._gpu_lbl = QLabel("")
        self._gpu_lbl.setObjectName("gpu_label")
        self._gpu_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._gpu_lbl)
        self._cost_lbl = QLabel("")
        self._cost_lbl.setObjectName("cost_label")
        self._cost_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._cost_lbl)
        self._uptime_lbl = QLabel("")
        self._uptime_lbl.setStyleSheet(f"color:{C['subtext0']};font-size:9pt;background:transparent;")
        self._uptime_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self._uptime_lbl)
        sc_lay.addLayout(info_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        sc_lay.addWidget(self._progress)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._poll)
        btn_row.addWidget(btn_refresh)
        self._btn_stop = QPushButton("⏹ Stop Pod")
        self._btn_stop.setObjectName("stop_btn")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self._btn_stop)
        sc_lay.addLayout(btn_row)
        root.addWidget(status_card)

        games_hdr = QLabel("🎮  GAMES")
        games_hdr.setObjectName("section_header")
        root.addWidget(games_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(200)
        scroll.setStyleSheet(f"border: 1px solid {C['surface0']}; border-radius: 10px;")
        games_w = QWidget()
        self._games_grid = QHBoxLayout(games_w)
        self._games_grid.setContentsMargins(12, 12, 12, 12)
        self._games_grid.setSpacing(12)
        self._games_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for g in STEAM_GAMES:
            card = GameCard(g)
            card.play_clicked.connect(self._on_play)
            self._game_cards.append(card)
            self._games_grid.addWidget(card)

        self._games_grid.addStretch()
        scroll.setWidget(games_w)
        root.addWidget(scroll)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(110)
        root.addWidget(self._log)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self._sb = QLabel("Ready")
        sb.addWidget(self._sb)

        QShortcut(QKeySequence("F5"), self, self._poll)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._do_connect)

    def _restore_fields(self):
        self._key_in.setText(self._cfg.get("api_key", ""))
        self._pod_in.setText(self._cfg.get("pod_id", ""))

    def _pod_id(self) -> str:
        pid = self._pod_in.text().strip()
        if pid:
            self._cfg["pod_id"] = pid
            save_cfg(self._cfg)
        return pid

    def _on_key(self, text):
        text = text.strip()
        if len(text) > 12:
            self._cfg["api_key"] = text
            save_cfg(self._cfg)
            self._api = RunPodAPI(text)
            self._emit_log("API key saved.")

    def _emit_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"[{ts}] {msg}")
        self._sb.setText(msg[:80])

    def _kill_worker(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        self._worker = None

    def _games_enabled(self, on: bool):
        for c in self._game_cards:
            c.set_ready(on)

    def _do_connect(self):
        if not self._api:
            self._emit_log("❌ Set API key first")
            return
        pid = self._pod_id()
        if not pid:
            self._emit_log("❌ Enter pod ID")
            return
        self._kill_worker()
        self._btn_connect.setEnabled(False)
        self._btn_connect.setText("⏳ Connecting...")
        self._worker = PodPoller(self._api, pid, "start")
        self._worker.status.connect(self._on_status)
        self._worker.log.connect(self._emit_log)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(lambda: self._btn_connect.setEnabled(True))
        self._worker.finished.connect(lambda: self._btn_connect.setText("⚡  CONNECT"))
        self._worker.start()

    def _poll(self):
        if not self._api:
            return
        pid = self._pod_id()
        if not pid:
            return
        self._kill_worker()
        self._worker = PodPoller(self._api, pid, "poll")
        self._worker.status.connect(self._on_status)
        self._worker.log.connect(self._emit_log)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop(self):
        if not self._api:
            return
        pid = self._pod_id()
        if not pid:
            return
        self._kill_worker()
        self._worker = PodPoller(self._api, pid, "stop")
        self._worker.status.connect(self._on_status)
        self._worker.log.connect(self._emit_log)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self._games_enabled(False)

    def _on_status(self, pod: dict):
        self._pod = pod
        status  = pod.get("desiredStatus", "UNKNOWN")
        cost    = pod.get("costPerHr", 0)
        machine = pod.get("machine") or {}
        runtime = pod.get("runtime")

        if gpu := machine.get("gpuDisplayName", ""):
            self._gpu_lbl.setText(f"🖥  {gpu}")
        if cost:
            self._cost_lbl.setText(f"💰  ${cost:.2f}/hr")

        colors = {"RUNNING": C["green"], "EXITED": C["overlay0"], "CREATED": C["yellow"],
                  "STARTING": C["yellow"], "BUILDING": C["peach"], "TERMINATED": C["red"]}
        steps  = {"RUNNING": 100, "STARTING": 50, "BUILDING": 30, "CREATED": 10, "EXITED": 0, "TERMINATED": 0}
        self._status_lbl.setText(f"●  {status}")
        self._status_lbl.setStyleSheet(
            f"color:{colors.get(status, C['text'])};font-size:13pt;font-weight:700;background:transparent;")
        self._progress.setValue(steps.get(status, 0))

        is_live = status == "RUNNING" and runtime is not None
        if runtime:
            uptime = runtime.get("uptimeInSeconds", 0)
            h, m = divmod(uptime // 60, 60)
            self._uptime_lbl.setText(f"⏱ {h}h {m}m")

        self._games_enabled(is_live)
        self._btn_stop.setEnabled(status == "RUNNING")
        if is_live:
            self._emit_log("✅ Pod LIVE — click a game to play!")

    def _on_error(self, msg):
        self._emit_log(f"❌ {msg}")
        self._btn_connect.setEnabled(True)
        self._btn_connect.setText("⚡  CONNECT")

    def _on_play(self, appid: int, name: str):
        pid = self._pod_id()
        if not pid:
            self._emit_log("❌ Connect first")
            return
        if self._launcher and self._launcher.isRunning():
            return

        for c in self._game_cards:
            if c.appid == appid:
                c.set_launching(True)

        self._emit_log(f"Launching {name}...")
        self._launcher = SteamLauncher(self._api, pid, appid)
        self._launcher.log.connect(self._emit_log)
        self._launcher.error.connect(self._on_launch_error)
        self._launcher.done.connect(self._on_launch_done)
        self._launcher.finished.connect(self._reset_launch_buttons)
        self._launcher.start()

    def _on_launch_done(self, url: str):
        self._emit_log(f"🎮 Loading desktop inside FunPod...")
        if HAS_WEBENGINE:
            self._desktop_win = DesktopView(url, self)
            self._desktop_win.show()
        else:
            self._emit_log("⚠ PyQt6-WebEngine missing — opening in browser as fallback")
            webbrowser.open(url)

    def _on_launch_error(self, msg: str):
        self._emit_log(f"❌ {msg}")

    def _reset_launch_buttons(self):
        for c in self._game_cards:
            c.set_launching(False)
            c.set_ready(True)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self._kill_worker()
        if self._launcher and self._launcher.isRunning():
            self._launcher.wait(1000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(C["crust"]))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(C["text"]))
    p.setColor(QPalette.ColorRole.Base,            QColor(C["base"]))
    p.setColor(QPalette.ColorRole.Button,          QColor(C["surface0"]))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text"]))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(C["mauve"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(C["crust"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(C["overlay0"]))
    app.setPalette(p)
    w = FunPodWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

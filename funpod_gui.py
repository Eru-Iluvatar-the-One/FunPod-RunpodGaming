"""FunPod — RunPod Gaming GUI. PyQt6 + Catppuccin Mocha."""

import sys
import webbrowser
from typing import Any

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

C: dict[str, str] = {
    "base": "#1e1e2e", "surface": "#313244", "text": "#cdd6f4",
    "accent": "#89b4fa", "overlay": "#45475a", "green": "#a6e3a1",
    "red": "#f38ba8", "yellow": "#f9e2af", "peach": "#fab387",
}

QSS: str = f"""
QMainWindow {{ background: {C['base']}; color: {C['text']}; }}
QTabWidget::pane {{ border: 1px solid {C['overlay']}; background: {C['base']}; }}
QTabBar::tab {{
    background: {C['surface']}; color: {C['text']}; padding: 8px 16px;
    border: 1px solid {C['overlay']}; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{ background: {C['base']}; color: {C['accent']}; }}
QLineEdit {{
    background: {C['surface']}; color: {C['text']};
    border: 1px solid {C['overlay']}; border-radius: 6px; padding: 6px 10px;
}}
QLineEdit:focus {{ border-color: {C['accent']}; }}
QPushButton {{
    background: {C['surface']}; color: {C['text']};
    border: 1px solid {C['overlay']}; border-radius: 6px;
    padding: 6px 14px; font-weight: bold;
}}
QPushButton:hover {{ background: {C['overlay']}; border-color: {C['accent']}; }}
QPushButton:pressed {{ background: {C['accent']}; color: {C['base']}; }}
QLabel {{ color: {C['text']}; }}
QFrame#gamecard {{
    background: {C['surface']}; border: 1px solid {C['overlay']};
    border-radius: 10px; padding: 12px;
}}
QFrame#gamecard:hover {{ border-color: {C['accent']}; }}
QListWidget {{
    background: {C['surface']}; color: {C['text']};
    border: 1px solid {C['overlay']}; border-radius: 6px;
}}
QListWidget::item {{ padding: 6px; border-bottom: 1px solid {C['overlay']}; }}
QListWidget::item:selected {{ background: {C['accent']}; color: {C['base']}; }}
QStatusBar {{
    background: {C['surface']}; color: {C['text']};
    border-top: 1px solid {C['overlay']};
}}
"""

GAMES: list[dict[str, str]] = [
    {"title": "Total War: Three Kingdoms", "id": "tw3k", "status": "Not Installed", "icon": "⚔"},
    {"title": "Total War: Shogun 2", "id": "twsh", "status": "Not Installed", "icon": "🏯"},
    {"title": "Total War: Rome 2", "id": "twr2", "status": "Not Installed", "icon": "🏛"},
    {"title": "Total War: Warhammer 3", "id": "tww3", "status": "Not Installed", "icon": "🐉"},
]

MODS: list[dict[str, Any]] = [
    {"name": "Better AI Recruitment", "enabled": True},
    {"name": "Historical Battles Expanded", "enabled": True},
    {"name": "Radious Total Overhaul", "enabled": False},
    {"name": "Custom Unit Cards HD", "enabled": True},
    {"name": "Campaign Map Enhancement", "enabled": False},
]


class GameCard(QFrame):
    """A card widget representing a single game."""

    def __init__(self, game: dict[str, str]) -> None:
        super().__init__()
        self.setObjectName("gamecard")
        self.setFixedSize(280, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        icon = QLabel(game["icon"])
        icon.setStyleSheet(f"font-size:32px;color:{C['accent']};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(game["title"])
        title.setStyleSheet("font-size:13px;font-weight:bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        self.status_lbl = QLabel(game["status"])
        installed = "Installed" in game["status"] and "Not" not in game["status"]
        sc = C["green"] if installed else C["overlay"]
        self.status_lbl.setStyleSheet(f"font-size:11px;color:{sc};")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        self.install_btn = QPushButton("📥 Install")
        self.install_btn.clicked.connect(lambda: self._install(game))
        btn_row.addWidget(self.play_btn)
        btn_row.addWidget(self.install_btn)
        layout.addLayout(btn_row)

    def _install(self, game: dict[str, str]) -> None:
        self.status_lbl.setText("Installed")
        self.status_lbl.setStyleSheet(f"font-size:11px;color:{C['green']};")
        self.play_btn.setEnabled(True)
        self.install_btn.setEnabled(False)


class FunPodApp(QMainWindow):
    """Main FunPod application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FunPod — RunPod Gaming")
        self.setMinimumSize(800, 550)
        s = QSettings("ArdaTek", "FunPodGUI")
        g = s.value("geometry")
        if g:
            self.restoreGeometry(g)
        else:
            self.resize(950, 650)
        self.pod_connected: bool = False
        self.pomodoro_seconds: int = 25 * 60
        self.pomodoro_running: bool = False
        self.pomodoro_is_work: bool = True
        self._build_ui()
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()

        # --- Tab 1: Pod Control ---
        pod_w = QWidget()
        pl = QVBoxLayout(pod_w)
        pl.setContentsMargins(16, 16, 16, 16)
        pl.setSpacing(12)

        conn_row = QHBoxLayout()
        self.pod_id = QLineEdit()
        self.pod_id.setPlaceholderText("Pod ID")
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("RunPod API Key")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_connect = QPushButton("🔌 Connect")
        self.btn_connect.clicked.connect(self._toggle_connect)
        conn_row.addWidget(QLabel("Pod:"))
        conn_row.addWidget(self.pod_id, 1)
        conn_row.addWidget(QLabel("Key:"))
        conn_row.addWidget(self.api_key, 1)
        conn_row.addWidget(self.btn_connect)
        pl.addLayout(conn_row)

        self.status_indicator = QLabel("● Disconnected")
        self.status_indicator.setStyleSheet(
            f"font-size:16px;font-weight:bold;color:{C['red']};"
        )
        pl.addWidget(self.status_indicator)

        ctrl_row = QHBoxLayout()
        for icon, text in [("▶", "Start"), ("⏹", "Stop"), ("🔄", "Restart")]:
            btn = QPushButton(f"{icon} {text}")
            btn.setEnabled(False)
            ctrl_row.addWidget(btn)
            if text == "Start":
                self.btn_start = btn
            elif text == "Stop":
                self.btn_stop = btn
            else:
                self.btn_restart = btn
        pl.addLayout(ctrl_row)

        info_grid = QGridLayout()
        self.lbl_gpu = QLabel("GPU: —")
        self.lbl_cost = QLabel("Cost: —")
        self.lbl_uptime = QLabel("Uptime: —")
        info_grid.addWidget(self.lbl_gpu, 0, 0)
        info_grid.addWidget(self.lbl_cost, 0, 1)
        info_grid.addWidget(self.lbl_uptime, 0, 2)
        pl.addLayout(info_grid)
        pl.addStretch()
        self.tabs.addTab(pod_w, "🖥 Pod Control")

        # --- Tab 2: Games ---
        games_w = QWidget()
        gl = QVBoxLayout(games_w)
        gl.setContentsMargins(16, 16, 16, 16)
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, game in enumerate(GAMES):
            card = GameCard(game)
            grid.addWidget(card, i // 2, i % 2)
        gl.addLayout(grid)
        gl.addStretch()
        self.tabs.addTab(games_w, "🎮 Games")

        # --- Tab 3: Mods ---
        mods_w = QWidget()
        ml = QVBoxLayout(mods_w)
        ml.setContentsMargins(16, 16, 16, 16)
        ml.setSpacing(8)
        self.mod_list = QListWidget()
        for mod in MODS:
            mark = "✅" if mod["enabled"] else "❌"
            self.mod_list.addItem(f"{mark} {mod['name']}")
        ml.addWidget(self.mod_list, 1)
        mod_btns = QHBoxLayout()
        for text in ["📥 Install Mod", "⬆ Move Up", "⬇ Move Down", "🔄 Toggle"]:
            btn = QPushButton(text)
            mod_btns.addWidget(btn)
        ml.addLayout(mod_btns)
        self.tabs.addTab(mods_w, "🔧 Mods")

        # --- Tab 4: VNC ---
        vnc_w = QWidget()
        vl = QVBoxLayout(vnc_w)
        vl.setContentsMargins(16, 16, 16, 16)
        vl.setSpacing(12)
        vl.addStretch()
        self.vnc_url_label = QLabel(
            "noVNC URL: https://<pod-id>-80.proxy.runpod.net/"
        )
        self.vnc_url_label.setStyleSheet("font-size:14px;")
        self.vnc_url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(self.vnc_url_label)
        vnc_btn = QPushButton("🌐 Open in Browser")
        vnc_btn.clicked.connect(self._open_vnc)
        vl.addWidget(vnc_btn)
        vl.addStretch()
        self.tabs.addTab(vnc_w, "🖥 VNC")

        main.addWidget(self.tabs, 1)

        # --- Pomodoro bar ---
        pomo_row = QHBoxLayout()
        self.pomo_label = QLabel("🍅 25:00 [WORK]")
        self.pomo_label.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{C['peach']};"
        )
        self.pomo_start = QPushButton("Start")
        self.pomo_start.clicked.connect(self._pomo_toggle)
        self.pomo_reset = QPushButton("Reset")
        self.pomo_reset.clicked.connect(self._pomo_reset)
        pomo_row.addStretch()
        pomo_row.addWidget(self.pomo_label)
        pomo_row.addWidget(self.pomo_start)
        pomo_row.addWidget(self.pomo_reset)
        main.addLayout(pomo_row)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Disconnected | No pod")

        self.pomo_timer = QTimer()
        self.pomo_timer.setInterval(1000)
        self.pomo_timer.timeout.connect(self._pomo_tick)

    def _toggle_connect(self) -> None:
        if not self.pod_connected:
            pid = self.pod_id.text().strip()
            if not pid:
                return
            self.pod_connected = True
            self.btn_connect.setText("🔌 Disconnect")
            self.status_indicator.setText("● Connected")
            self.status_indicator.setStyleSheet(
                f"font-size:16px;font-weight:bold;color:{C['green']};"
            )
            self.lbl_gpu.setText("GPU: RTX 4090")
            self.lbl_cost.setText("Cost: $0.69/hr")
            self.lbl_uptime.setText("Uptime: 0h 0m")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_restart.setEnabled(True)
            self.vnc_url_label.setText(
                f"noVNC URL: https://{pid}-80.proxy.runpod.net/"
            )
            self.status.showMessage(
                f"Connected to {pid} | RTX 4090 | $0.69/hr"
            )
        else:
            self.pod_connected = False
            self.btn_connect.setText("🔌 Connect")
            self.status_indicator.setText("● Disconnected")
            self.status_indicator.setStyleSheet(
                f"font-size:16px;font-weight:bold;color:{C['red']};"
            )
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_restart.setEnabled(False)
            self.status.showMessage("Disconnected")

    def _open_vnc(self) -> None:
        pid = self.pod_id.text().strip()
        if pid:
            webbrowser.open(f"https://{pid}-80.proxy.runpod.net/")

    def _pomo_toggle(self) -> None:
        self.pomodoro_running = not self.pomodoro_running
        if self.pomodoro_running:
            self.pomo_timer.start()
            self.pomo_start.setText("Pause")
        else:
            self.pomo_timer.stop()
            self.pomo_start.setText("Start")

    def _pomo_reset(self) -> None:
        self.pomo_timer.stop()
        self.pomodoro_running = False
        self.pomodoro_is_work = True
        self.pomodoro_seconds = 25 * 60
        self.pomo_start.setText("Start")
        self.pomo_label.setText("🍅 25:00 [WORK]")
        self.pomo_label.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{C['peach']};"
        )

    def _pomo_tick(self) -> None:
        self.pomodoro_seconds -= 1
        if self.pomodoro_seconds <= 0:
            self.pomodoro_is_work = not self.pomodoro_is_work
            self.pomodoro_seconds = (
                5 * 60 if not self.pomodoro_is_work else 25 * 60
            )
        m, s = divmod(self.pomodoro_seconds, 60)
        mode = "WORK" if self.pomodoro_is_work else "BREAK"
        color = C["peach"] if self.pomodoro_is_work else C["green"]
        self.pomo_label.setText(f"🍅 {m:02d}:{s:02d} [{mode}]")
        self.pomo_label.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{color};"
        )

    def closeEvent(self, e: Any) -> None:
        QSettings("ArdaTek", "FunPodGUI").setValue(
            "geometry", self.saveGeometry()
        )
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    win = FunPodApp()
    win.show()
    sys.exit(app.exec())

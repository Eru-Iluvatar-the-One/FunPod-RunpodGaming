
"""
funpod.py — FunPod Gaming Launcher
Arena Pasta #1 output, deployed to repo. Needs arda_theme wiring + Fingolfin polish pass.
PyQt6 + paramiko + requests. RunPod API integration.
"""
import sys, os, time, json, webbrowser
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import paramiko, requests
from arda_theme import ThemeEngine

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
    def run(self):
        try: self.finished.emit(self.fn(*self.args, **self.kwargs))
        except Exception as e: self.error.emit(str(e))

class FunPodApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("ArdaTek", "FunPod")
        self.current_ip, self.current_ssh_port = "", 22
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_pod)
        self.timer.start(10000)

    def init_ui(self):
        self.setWindowTitle("FunPod Gaming Launcher")
        self.resize(1100, 700)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        self.stack = QStackedWidget()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)
        for text, idx in [("🚀 Pod Management", 0), ("🧩 Mod Manager", 1), ("⚙️ Settings", 2)]:
            btn = QPushButton(text)
            btn.setObjectName("sidebar_button")
            btn.clicked.connect(lambda checked, i=idx: self.stack.setCurrentIndex(i))
            sidebar_layout.addWidget(btn)
        sidebar_layout.addStretch()
        self.setup_pod_page()
        self.setup_mod_page()
        self.setup_settings_page()
        self.status_bar = self.statusBar()
        self.lbl_ticker = QLabel("Pod: None | GPU: N/A | $0.00/hr | Total: $0.00")
        self.status_bar.addWidget(self.lbl_ticker)
        QShortcut(QKeySequence("Ctrl+L"), self, self.launch_desktop)
        QShortcut(QKeySequence("Ctrl+S"), self, self.start_pod)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def setup_pod_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 30, 30, 30)
        h_layout = QHBoxLayout()
        self.inp_pod_id = QLineEdit(self.settings.value("pod_id", ""))
        self.inp_pod_id.setPlaceholderText("Enter Pod ID...")
        btn_save_pod = QPushButton("Save ID"); btn_save_pod.clicked.connect(lambda: self.settings.setValue("pod_id", self.inp_pod_id.text()))
        h_layout.addWidget(QLabel("Target Pod ID:")); h_layout.addWidget(self.inp_pod_id); h_layout.addWidget(btn_save_pod)
        layout.addLayout(h_layout)
        self.lbl_pod_status = QLabel("Status: Unknown")
        self.lbl_pod_status.setObjectName("status_label")
        layout.addWidget(self.lbl_pod_status)
        action_layout = QHBoxLayout()
        for text, object_name, fn in [("Start Pod", "success", self.start_pod), ("Stop Pod", "warning", self.stop_pod), ("Destroy Pod", "danger", self.destroy_pod)]:
            b = QPushButton(text); b.setObjectName(object_name); b.clicked.connect(fn)
            action_layout.addWidget(b)
        layout.addLayout(action_layout)
        tool_layout = QHBoxLayout()
        for text, fn in [("🖥️ Launch Desktop", self.launch_desktop),
                         ("🎮 Install Steam", lambda: self.exec_ssh("dpkg --add-architecture i386 && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y steam-launcher")),
                         ("⚔️ Install Three Kingdoms", lambda: self.exec_ssh("steamcmd +login anonymous +app_update 779340 +quit"))]:
            b = QPushButton(text); b.clicked.connect(fn); tool_layout.addWidget(b)
        layout.addLayout(tool_layout); layout.addStretch()
        self.stack.addWidget(page)

    def setup_mod_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(30, 30, 30, 30)
        layout.addWidget(QLabel("Installed Mods (/workspace/mods/)"))
        self.list_mods = QListWidget(); layout.addWidget(self.list_mods)
        btn_layout = QHBoxLayout()
        for text, fn in [("Refresh", self.refresh_mods), ("Upload Mod", self.upload_mod), ("Toggle", self.toggle_mod)]:
            b = QPushButton(text); b.clicked.connect(fn); btn_layout.addWidget(b)
        layout.addLayout(btn_layout)
        self.stack.addWidget(page)

    def setup_settings_page(self):
        page = QWidget(); layout = QFormLayout(page); layout.setContentsMargins(30, 30, 30, 30)
        self.inp_api = QLineEdit(self.settings.value("api_key", os.environ.get("RUNPOD_API_KEY", "")))
        self.inp_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_ssh = QLineEdit(self.settings.value("ssh_key", os.path.expanduser("~/.ssh/id_ed25519")))
        btn_save = QPushButton("Save Settings"); btn_save.clicked.connect(self.save_settings)
        layout.addRow("RunPod API Key:", self.inp_api)
        layout.addRow("SSH Key Path:", self.inp_ssh)
        layout.addRow("", btn_save)
        self.stack.addWidget(page)

    def save_settings(self):
        self.settings.setValue("api_key", self.inp_api.text()); self.settings.setValue("ssh_key", self.inp_ssh.text())
        self.status_bar.showMessage("Settings saved.", 3000)

    def _api_headers(self):
        return {"Authorization": f"Bearer {self.inp_api.text()}"}

    def _graphql(self, query):
        r = requests.post("https://api.runpod.io/graphql", json={"query": query}, headers=self._api_headers(), timeout=15)
        r.raise_for_status()
        return r.json()

    def poll_pod(self):
        pid = self.inp_pod_id.text()
        if not pid or not self.inp_api.text(): return
        q = f'{{ pod(input: {{podId: "{pid}"}}) {{ id desiredStatus runtime {{ gpuDisplayName uptimeInSeconds ports {{ ip isIpPublic privatePort publicPort type }} }} costPerHr machine {{ gpuDisplayName }} }} }}'
        self.w_poll = Worker(self._graphql, q)
        self.w_poll.finished.connect(self._on_poll)
        self.w_poll.error.connect(lambda e: self.status_bar.showMessage(f"Poll error: {e}", 3000))
        self.w_poll.start()

    def _on_poll(self, data):
        pod = data.get("data", {}).get("pod")
        if not pod: return
        rt = pod.get("runtime") or {}
        ports = rt.get("ports") or []
        for p in ports:
            if p.get("privatePort") == 22 and p.get("isIpPublic"):
                self.current_ip = p.get("ip", "")
                self.current_ssh_port = p.get("publicPort", 22)
        gpu = rt.get("gpuDisplayName") or pod.get("machine", {}).get("gpuDisplayName", "?")
        cost = pod.get("costPerHr", 0)
        uptime = rt.get("uptimeInSeconds", 0)
        total = cost * uptime / 3600
        self.lbl_pod_status.setText(f"Status: {pod.get('desiredStatus','?')} | {self.current_ip}:{self.current_ssh_port}")
        self.lbl_ticker.setText(f"Pod: {pod['id']} | GPU: {gpu} | ${cost:.2f}/hr | Total: ${total:.2f}")

    def start_pod(self):
        pid = self.inp_pod_id.text()
        self.w_act = Worker(self._graphql, f'mutation {{ podResume(input: {{podId: "{pid}"}}) {{ id }} }}')
        self.w_act.finished.connect(lambda d: self.status_bar.showMessage("Start sent.", 3000)); self.w_act.start()

    def stop_pod(self):
        pid = self.inp_pod_id.text()
        self.w_act = Worker(self._graphql, f'mutation {{ podStop(input: {{podId: "{pid}"}}) {{ id }} }}')
        self.w_act.finished.connect(lambda d: self.status_bar.showMessage("Stop sent.", 3000)); self.w_act.start()

    def destroy_pod(self):
        if QMessageBox.question(self, "Destroy", "Delete pod and all data?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            pid = self.inp_pod_id.text()
            self.w_act = Worker(self._graphql, f'mutation {{ podTerminate(input: {{podId: "{pid}"}}) }}')
            self.w_act.finished.connect(lambda d: self.status_bar.showMessage("Destroyed.", 3000)); self.w_act.start()

    def launch_desktop(self):
        pid = self.inp_pod_id.text()
        if pid: webbrowser.open(f"https://{pid}-80.proxy.runpod.net")

    def _ssh_client(self):
        if not self.current_ip: raise Exception("No pod IP yet — wait for poll.")
        k = paramiko.Ed25519Key.from_private_key_file(self.inp_ssh.text())
        c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(self.current_ip, port=int(self.current_ssh_port), username="root", pkey=k, timeout=15)
        return c

    def _ssh_run(self, cmd):
        c = self._ssh_client(); _, stdout, stderr = c.exec_command(cmd, timeout=300)
        out = stdout.read().decode(); c.close(); return out

    def exec_ssh(self, cmd):
        self.status_bar.showMessage(f"SSH: {cmd[:40]}...")
        self.w_ssh = Worker(self._ssh_run, cmd)
        self.w_ssh.finished.connect(lambda d: self.status_bar.showMessage("Done.", 3000))
        self.w_ssh.error.connect(lambda e: self.status_bar.showMessage(f"SSH err: {e}", 5000))
        self.w_ssh.start()

    def refresh_mods(self):
        self.w_ls = Worker(self._ssh_run, "mkdir -p /workspace/mods && ls -1 /workspace/mods")
        self.w_ls.finished.connect(lambda d: [self.list_mods.clear(), self.list_mods.addItems([m for m in d.split('\n') if m.strip()])])
        self.w_ls.start()

    def upload_mod(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Mod", "", "ZIP (*.zip)")
        if not f: return
        def _up():
            c = self._ssh_client(); sftp = c.open_sftp()
            sftp.put(f, f"/workspace/mods/{os.path.basename(f)}")
            sftp.close(); c.close()
        self.w_up = Worker(_up); self.w_up.finished.connect(lambda d: self.refresh_mods()); self.w_up.start()

    def toggle_mod(self):
        item = self.list_mods.currentItem()
        if not item: return
        n = item.text()
        new = n.replace(".disabled", "") if n.endswith(".disabled") else n + ".disabled"
        self.exec_ssh(f"mv /workspace/mods/{n} /workspace/mods/{new}")
        QTimer.singleShot(1500, self.refresh_mods)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    theme_engine = ThemeEngine(app, "arda_theme.py")
    theme_engine.apply("Catppuccin Mocha")
    w = FunPodApp(); w.show(); sys.exit(app.exec())

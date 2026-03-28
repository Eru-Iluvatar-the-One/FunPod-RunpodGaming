import sys
import os
import json
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QScrollArea, QFrame, QLabel, QPushButton, QDialog, QLineEdit,
    QComboBox, QGridLayout, QMessageBox, QTreeView, QFileSystemModel,
    QCheckBox, QStatusBar, QTextEdit
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QColor
import requests
import paramiko
from arda_theme import ThemeEngine

RUNPOD_API_KEY = "" # Will be loaded from config

LIST_PODS = """query { myself { pods { id name runtime { uptimeInSeconds gpus { id gpuUtilPerc memoryUtilPerc } ports { ip isIpPublic privatePort publicPort type } } desiredStatus costPerHr imageName machine { gpuDisplayName } } } }"""
START_POD = """mutation($podId: String!) { podResume(input: {podId: $podId}) { id desiredStatus } }"""
STOP_POD = """mutation($podId: String!) { podStop(input: {podId: $podId}) { id desiredStatus } }"""
DELETE_POD = """mutation($podId: String!) { podTerminate(input: {podId: $podId}) }"""

class RunPodAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.graphql_url = f"https://api.runpod.io/graphql?api_key={self.api_key}"

    def _query(self, query, variables=None):
        try:
            response = requests.post(self.graphql_url, json={'query': query, 'variables': variables})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def list_pods(self):
        return self._query(LIST_PODS)

    def start_pod(self, pod_id):
        return self._query(START_POD, {'podId': pod_id})

    def stop_pod(self, pod_id):
        return self._query(STOP_POD, {'podId': pod_id})

    def delete_pod(self, pod_id):
        return self._query(DELETE_POD, {'podId': pod_id})

class SSHClient:
    def __init__(self, host, port, username, key_filename):
        self.host = host
        self.port = port
        self.username = username
        self.key_filename = os.path.expanduser(key_filename)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        try:
            self.client.connect(hostname=self.host, port=self.port, username=self.username, key_filename=self.key_filename)
            return True
        except Exception as e:
            print(f"SSH connection failed: {e}")
            return False

    def exec_command_stream(self, command):
        if not self.client.get_transport() or not self.client.get_transport().is_active():
            if not self.connect():
                yield "Failed to connect to SSH."
                return

        stdin, stdout, stderr = self.client.exec_command(command)
        for line in iter(stdout.readline, ""):
            yield line.strip()
        for line in iter(stderr.readline, ""):
            yield f"ERROR: {line.strip()}"

    def close(self):
        self.client.close()

class Worker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    ssh_output = pyqtSignal(str)

    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            if self.target.__name__ == "exec_command_stream":
                 for output in self.target(*self.args, **self.kwargs):
                    self.ssh_output.emit(output)
            else:
                res = self.target(*self.args, **self.kwargs)
                self.result.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class FunPodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod — Gaming Pod Manager")
        self.setMinimumSize(1200, 800)

        self.config_path = os.path.expanduser("~/.funpod/config.json")
        self.load_config()

        self.api = RunPodAPI(RUNPOD_API_KEY)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_desktop_tab()
        self.create_steam_tab()
        self.create_mods_tab()
        self.create_settings_tab()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.active_pods_label = QLabel("Active Pods: 0")
        self.total_cost_label = QLabel("Total Cost/hr: $0.00")
        self.connection_label = QLabel("Disconnected")
        self.status_bar.addPermanentWidget(self.active_pods_label)
        self.status_bar.addPermanentWidget(self.total_cost_label)
        self.status_bar.addPermanentWidget(self.connection_label)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(5000)
        self.refresh_dashboard()

    def load_config(self):
        global RUNPOD_API_KEY
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                RUNPOD_API_KEY = config.get("api_key", "")
                self.default_gpu = config.get("default_gpu", "RTX 4090")
                self.vnc_password = config.get("vnc_password", "gaming123")
                self.ssh_key_path = config.get("ssh_key_path", "~/.ssh/id_ed25519")
        else:
            RUNPOD_API_KEY = ""
            self.default_gpu = "RTX 4090"
            self.vnc_password = "gaming123"
            self.ssh_key_path = "~/.ssh/id_ed25519"

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        config = {
            "api_key": RUNPOD_API_KEY,
            "default_gpu": self.default_gpu,
            "vnc_password": self.vnc_password,
            "ssh_key_path": self.ssh_key_path
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)
        QMessageBox.information(self, "Settings Saved", "Configuration saved successfully.")

    def create_dashboard_tab(self):
        self.dashboard_tab = QWidget()
        layout = QVBoxLayout(self.dashboard_tab)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.pod_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)

        create_pod_button = QPushButton("Create Pod")
        create_pod_button.clicked.connect(self.show_create_pod_dialog)
        layout.addWidget(create_pod_button)
        layout.addWidget(self.scroll_area)
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

    def refresh_dashboard(self):
        if not RUNPOD_API_KEY:
            self.connection_label.setText("Disconnected: No API Key")
            return

        self.worker = Worker(self.api.list_pods)
        self.worker.result.connect(self.update_dashboard_ui)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_dashboard_ui(self, data):
        if 'error' in data:
            self.show_error(f"API Error: {data['error']}")
            self.connection_label.setText("Disconnected")
            return

        self.connection_label.setText("Connected")
        for i in reversed(range(self.pod_layout.count())):
            self.pod_layout.itemAt(i).widget().setParent(None)

        pods = data.get('data', {}).get('myself', {}).get('pods', [])
        active_pods = 0
        total_cost = 0.0

        for pod in pods:
            if pod['desiredStatus'] == "RUNNING":
                active_pods += 1
                total_cost += pod.get('costPerHr', 0.0)

            card = self.create_pod_card(pod)
            self.pod_layout.addWidget(card)

        self.active_pods_label.setText(f"Active Pods: {active_pods}")
        self.total_cost_label.setText(f"Total Cost/hr: ${total_cost:.2f}")

    def create_pod_card(self, pod):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QGridLayout(card)

        name_label = QLabel(f"<b>{pod['name']}</b>")
        gpu_label = QLabel(pod.get('machine', {}).get('gpuDisplayName', 'N/A'))
        status_indicator = QLabel()
        status_color = "green" if pod['desiredStatus'] == "RUNNING" else "red"
        status_indicator.setStyleSheet(f"background-color: {status_color}; border-radius: 5px; min-width: 10px; min-height: 10px;")
        cost_label = QLabel(f"${pod.get('costPerHr', 0.0):.2f}/hr")
        uptime_label = QLabel(f"Uptime: {pod.get('runtime', {}).get('uptimeInSeconds', 0) // 3600}h")

        start_button = QPushButton("Start")
        start_button.setStyleSheet("background-color: green;")
        start_button.clicked.connect(lambda: self.start_pod(pod['id'] الشكل ))

        stop_button = QPushButton("Stop")
        stop_button.setStyleSheet("background-color: yellow;")
        stop_button.clicked.connect(lambda: self.stop_pod(pod['id']))

        destroy_button = QPushButton("Destroy")
        destroy_button.setStyleSheet("background-color: red;")
        destroy_button.clicked.connect(lambda: self.destroy_pod(pod['id']))

        layout.addWidget(status_indicator, 0, 0)
        layout.addWidget(name_label, 0, 1)
        layout.addWidget(gpu_label, 1, 1)
        layout.addWidget(cost_label, 0, 2)
        layout.addWidget(uptime_label, 1, 2)
        layout.addWidget(start_button, 0, 3)
        layout.addWidget(stop_button, 1, 3)
        layout.addWidget(destroy_button, 0, 4, 2, 1)

        return card

    def start_pod(self, pod_id):
        self.worker = Worker(self.api.start_pod, pod_id)
        self.worker.result.connect(self.refresh_dashboard)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def stop_pod(self, pod_id):
        self.worker = Worker(self.api.stop_pod, pod_id)
        self.worker.result.connect(self.refresh_dashboard)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def destroy_pod(self, pod_id):
        reply = QMessageBox.question(self, 'Destroy Pod', "Are you sure you want to destroy this pod?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.worker = Worker(self.api.delete_pod, pod_id)
            self.worker.result.connect(self.refresh_dashboard)
            self.worker.error.connect(self.show_error)
            self.worker.start()

    def show_create_pod_dialog(self):
        # Dummy dialog for now
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Pod")
        layout = QGridLayout(dialog)
        layout.addWidget(QLabel("Name:"), 0, 0)
        layout.addWidget(QLineEdit(), 0, 1)
        layout.addWidget(QLabel("GPU Type:"), 1, 0)
        gpu_combo = QComboBox()
        gpu_combo.addItems(["RTX 4090", "A40", "A100", "H100"])
        layout.addWidget(gpu_combo, 1, 1)
        # ... other fields
        ok_button = QPushButton("Create")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button, 2, 1)
        dialog.exec()

    def create_desktop_tab(self):
        self.desktop_tab = QWidget()
        layout = QVBoxLayout(self.desktop_tab)
        self.pod_selector_desktop = QComboBox()
        layout.addWidget(self.pod_selector_desktop)
        launch_vnc_button = QPushButton("Launch VNC")
        launch_vnc_button.clicked.connect(self.launch_vnc)
        layout.addWidget(launch_vnc_button)
        self.vnc_password_edit = QLineEdit(self.vnc_password)
        layout.addWidget(self.vnc_password_edit)
        self.tabs.addTab(self.desktop_tab, "Desktop")

    def launch_vnc(self):
        pod_id = self.pod_selector_desktop.currentData()
        if pod_id:
            webbrowser.open(f"https://{pod_id}-80.proxy.runpod.net")

    def create_steam_tab(self):
        self.steam_tab = QWidget()
        layout = QVBoxLayout(self.steam_tab)
        self.pod_selector_steam = QComboBox()
        layout.addWidget(self.pod_selector_steam)

        install_steam_button = QPushButton("Install Steam")
        install_steam_button.clicked.connect(self.install_steam)
        layout.addWidget(install_steam_button)

        install_game_layout = QGridLayout()
        self.app_id_edit = QLineEdit("779340")
        install_game_button = QPushButton("Install Game")
        install_game_button.clicked.connect(self.install_game)
        install_game_layout.addWidget(QLabel("Steam App ID:"), 0, 0)
        install_game_layout.addWidget(self.app_id_edit, 0, 1)
        install_game_layout.addWidget(install_game_button, 0, 2)
        layout.addLayout(install_game_layout)

        self.ssh_log = QTextEdit()
        self.ssh_log.setReadOnly(True)
        layout.addWidget(self.ssh_log)

        self.tabs.addTab(self.steam_tab, "Steam")

    def install_steam(self):
        commands = [
            "apt-get update",
            "apt-get install -y wget software-properties-common",
            "wget https://cdn.cloudflare.steamstatic.com/client/installer/steam.deb",
            "dpkg -i steam.deb || apt-get install -f -y",
        ]
        self.run_ssh_commands(commands)

    def install_game(self):
        app_id = self.app_id_edit.text()
        command = f"steamcmd +@sSteamCmdForcePlatformType linux +login anonymous +app_update {app_id} validate +quit"
        self.run_ssh_commands([command])

    def run_ssh_commands(self, commands):
        pod_id = self.pod_selector_steam.currentData()
        # Find pod ip and port from the list of pods
        # ... This part needs the pod list data ...
        # For now, placeholder:
        # ssh = SSHClient("host", port, "user", self.ssh_key_path)
        # self.ssh_worker = Worker(ssh.exec_command_stream, '; '.join(commands))
        # self.ssh_worker.ssh_output.connect(self.ssh_log.append)
        # self.ssh_worker.start()
        self.ssh_log.append("SSH functionality not fully implemented yet.")

    def create_mods_tab(self):
        self.mods_tab = QWidget()
        layout = QVBoxLayout(self.mods_tab)

        mods_dir = os.path.expanduser("~/.funpod/local_mods/")
        os.makedirs(mods_dir, exist_ok=True)

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(mods_dir)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(mods_dir))
        layout.addWidget(self.tree_view)

        upload_button = QPushButton("Upload to Pod")
        layout.addWidget(upload_button)

        self.tabs.addTab(self.mods_tab, "Mods")

    def create_settings_tab(self):
        self.settings_tab = QWidget()
        layout = QGridLayout(self.settings_tab)

        layout.addWidget(QLabel("RunPod API Key:"), 0, 0)
        self.api_key_edit = QLineEdit(RUNPOD_API_KEY)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_key_edit, 0, 1)

        layout.addWidget(QLabel("SSH Key Path:"), 1, 0)
        self.ssh_key_edit = QLineEdit(self.ssh_key_path)
        layout.addWidget(self.ssh_key_edit, 1, 1)

        layout.addWidget(QLabel("Default GPU:"), 2, 0)
        self.default_gpu_combo = QComboBox()
        self.default_gpu_combo.addItems(["RTX 4090", "A40", "A100", "H100"])
        self.default_gpu_combo.setCurrentText(self.default_gpu)
        layout.addWidget(self.default_gpu_combo, 2, 1)

        layout.addWidget(QLabel("VNC Password:"), 3, 0)
        self.vnc_password_settings_edit = QLineEdit(self.vnc_password)
        layout.addWidget(self.vnc_password_settings_edit, 3, 1)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.update_settings)
        layout.addWidget(save_button, 4, 1)

        self.tabs.addTab(self.settings_tab, "Settings")

    def update_settings(self):
        global RUNPOD_API_KEY
        RUNPOD_API_KEY = self.api_key_edit.text()
        self.api.api_key = RUNPOD_API_KEY
        self.default_gpu = self.default_gpu_combo.currentText()
        self.vnc_password = self.vnc_password_settings_edit.text()
        self.ssh_key_path = self.ssh_key_edit.text()
        self.save_config()
        self.refresh_dashboard()

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ThemeEngine.apply(app)
    window = FunPodWindow()
    window.show()
    sys.exit(app.exec())

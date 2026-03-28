import sys
import os
import requests
import json
import paramiko
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QScrollArea, QFrame,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox
)
from arda_theme import ThemeEngine

class RunPodAPI(QObject):
    pods_listed = pyqtSignal(dict)
    error = pyqtSignal(str)

    LIST_PODS_QUERY = """query { myself { pods { id name runtime { uptimeInSeconds gpus { id gpuUtilPerc memoryUtilPerc } ports { ip isIpPublic privatePort publicPort type } } desiredStatus costPerHr imageName machine { gpuDisplayName } } } }"""
    START_POD_MUTATION = """mutation($podId: String!) { podResume(input: {podId: $podId}) { id desiredStatus } }"""
    STOP_POD_MUTATION = """mutation($podId: String!) { podStop(input: {podId: $podId}) { id desiredStatus } }"""
    DELETE_POD_MUTATION = """mutation($podId: String!) { podTerminate(input: {podId: $podId}) }"""

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.graphql_url = f"https://api.runpod.io/graphql?api_key={self.api_key}"

    def list_pods(self):
        if not self.api_key:
            self.error.emit("RUNPOD_API_KEY environment variable not set.")
            return
        try:
            response = requests.post(self.graphql_url, json={"query": self.LIST_PODS_QUERY})
            response.raise_for_status()
            self.pods_listed.emit(response.json())
        except requests.exceptions.RequestException as e:
            self.error.emit(str(e))

class SSHClient(QObject):
    output_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, hostname, username, key_filename):
        super().__init__()
        self.hostname = hostname
        self.username = username
        self.key_filename = key_filename
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        try:
            self.client.connect(self.hostname, username=self.username, key_filename=self.key_filename)
        except Exception as e:
            self.error.emit(str(e))

    def execute_command(self, command):
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            for line in iter(stdout.readline, ""):
                self.output_received.emit(line.strip())
            for line in iter(stderr.readline, ""):
                self.error.emit(line.strip())
        except Exception as e:
            self.error.emit(str(e))

    def disconnect(self):
        self.client.close()

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(Exception)

    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._target(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)

class PodCard(QFrame):
    def __init__(self, pod_data):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.pod_data = pod_data

        layout = QVBoxLayout()
        self.setLayout(layout)

        name_label = QLabel(f"<b>{pod_data["name"]}</b>")
        gpu_label = QLabel(pod_data["machine"]["gpuDisplayName"])
        cost_label = QLabel(f"${pod_data["costPerHr"]:.2f}/hr")
        status_label = QLabel(f"Status: {pod_data["desiredStatus"]}")

        layout.addWidget(name_label)
        layout.addWidget(gpu_label)
        layout.addWidget(cost_label)
        layout.addWidget(status_label)

        button_layout = QHBoxLayout()
        start_button = QPushButton("Start")
        stop_button = QPushButton("Stop")
        destroy_button = QPushButton("Destroy")

        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)
        button_layout.addWidget(destroy_button)

        layout.addLayout(button_layout)


class FunPodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod — Gaming Pod Manager")
        self.setGeometry(100, 100, 1200, 800)

        self.config_path = Path.home() / ".funpod" / "config.json"
        self.config = self.load_config()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard_tab = QWidget()
        self.desktop_tab = QWidget()
        self.steam_tab = QWidget()
        self.mods_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.desktop_tab, "Desktop")
        self.tabs.addTab(self.steam_tab, "Steam")
        self.tabs.addTab(self.mods_tab, "Mods")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setup_dashboard()
        self.setup_settings()
        self.setup_steam_tab()

        self.api = RunPodAPI(self.config.get("runpod_api_key"))
        self.api.pods_listed.connect(self.update_dashboard)
        self.api.error.connect(self.show_error)

        self.list_pods()
    
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {}

    def save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    def setup_settings(self):
        layout = QVBoxLayout()
        self.settings_tab.setLayout(layout)

        api_key_label = QLabel("RunPod API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.get("runpod_api_key", ""))

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)

        layout.addWidget(api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addWidget(save_button)

    def save_settings(self):
        self.config["runpod_api_key"] = self.api_key_input.text()
        self.save_config()
        # Update the API key in the RunPodAPI instance
        self.api.api_key = self.config.get("runpod_api_key")
        self.api.graphql_url = f"https://api.runpod.io/graphql?api_key={self.api.api_key}"
        self.list_pods()
    
    def setup_dashboard(self):
        layout = QVBoxLayout()
        self.dashboard_tab.setLayout(layout)

        create_pod_button = QPushButton("Create Pod")
        layout.addWidget(create_pod_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        self.pod_card_container = QWidget()
        self.pod_card_layout = QVBoxLayout()
        self.pod_card_container.setLayout(self.pod_card_layout)

        self.scroll_area.setWidget(self.pod_card_container)

    def list_pods(self):
        # Clear the dashboard before listing pods
        for i in reversed(range(self.pod_card_layout.count())):
            self.pod_card_layout.itemAt(i).widget().setParent(None)

        self.worker = Worker(self.api.list_pods)
        self.worker.start()

    def update_dashboard(self, pods_data):
        if "errors" in pods_data:
            self.show_error(pods_data["errors"][0]["message"])
            return
        
        self.steam_pod_selector.clear()
        self.pods = pods_data["data"]["myself"]["pods"]
        for pod in self.pods:
            card = PodCard(pod)
            self.pod_card_layout.addWidget(card)
            self.steam_pod_selector.addItem(pod["name"], pod)

    def show_error(self, error_message):
        print(f"Error: {error_message}") # Placeholder

    def setup_steam_tab(self):
        layout = QVBoxLayout()
        self.steam_tab.setLayout(layout)

        pod_selector_layout = QHBoxLayout()
        pod_selector_label = QLabel("Select Pod:")
        self.steam_pod_selector = QComboBox()
        pod_selector_layout.addWidget(pod_selector_label)
        pod_selector_layout.addWidget(self.steam_pod_selector)
        layout.addLayout(pod_selector_layout)

        install_steam_button = QPushButton("Install Steam")
        install_steam_button.clicked.connect(self.install_steam)
        layout.addWidget(install_steam_button)

        install_game_layout = QHBoxLayout()
        install_game_button = QPushButton("Install Game")
        install_game_button.clicked.connect(self.install_game)
        self.game_id_input = QLineEdit()
        self.game_id_input.setPlaceholderText("Steam App ID (e.g., 779340)")
        install_game_layout.addWidget(self.game_id_input)
        install_game_layout.addWidget(install_game_button)
        layout.addLayout(install_game_layout)

        self.steam_output = QTextEdit()
        self.steam_output.setReadOnly(True)
        layout.addWidget(self.steam_output)

    def install_steam(self):
        pod = self.steam_pod_selector.currentData()
        if not pod:
            return

        commands = [
            "apt-get update",
            "apt-get install -y wget software-properties-common",
            "wget https://cdn.cloudflare.steamstatic.com/client/installer/steam.deb",
            "dpkg -i steam.deb || apt-get install -f -y",
        ]
        command = " && ".join(commands)

        self.execute_ssh_command(pod, command)

    def install_game(self):
        pod = self.steam_pod_selector.currentData()
        if not pod:
            return

        app_id = self.game_id_input.text() or "779340"
        command = f"steamcmd +@sSteamCmdForcePlatformType linux +login anonymous +app_update {app_id} validate +quit"

        self.execute_ssh_command(pod, command)

    def execute_ssh_command(self, pod, command):
        ip = None
        for port in pod["runtime"]["ports"]:
            if port["isIpPublic"]:
                ip = port["ip"]
                break
        
        if not ip:
            self.show_error("Public IP not found for the selected pod.")
            return

        ssh_key_path = str(Path.home() / ".ssh" / "id_ed25519")
        self.ssh_client = SSHClient(hostname=ip, username="root", key_filename=ssh_key_path)
        self.ssh_client.output_received.connect(self.steam_output.append)
        self.ssh_client.error.connect(self.steam_output.append)

        self.worker = Worker(self.ssh_client.execute_command, command)
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ThemeEngine.apply(app)
    window = FunPodWindow()
    window.show()
    sys.exit(app.exec())

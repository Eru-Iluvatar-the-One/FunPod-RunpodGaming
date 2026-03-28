# FunPod: A RunPod Gaming Manager

import sys
import os
import json
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QScrollArea, QFrame, QLabel, QPushButton, QDialog, QLineEdit, 
    QComboBox, QTextEdit, QFileSystemModel, QTreeView, QCheckBox, 
    QMessageBox, QStatusBar, QGridLayout, QSplitter, QTextBrowser
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont, QColor
import requests
import paramiko
from uuid import uuid4

# Assuming arda_theme.py is in the same directory or in sys.path
from arda_theme import ThemeEngine

# GraphQL Queries
LIST_PODS = 'query { myself { pods { id name runtime { uptimeInSeconds gpus { id gpuUtilPerc memoryUtilPerc } ports { ip isIpPublic privatePort publicPort type } } desiredStatus costPerHr imageName machine { gpuDisplayName } } } }'
START_POD = 'mutation($podId: String!) { podResume(input: {podId: $podId}) { id desiredStatus } }'
STOP_POD = 'mutation($podId: String!) { podStop(input: {podId: $podId}) { id desiredStatus } }'
DELETE_POD = 'mutation($podId: String!) { podTerminate(input: {podId: $podId}) }'

class RunPodAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = f"https://api.runpod.io/graphql?api_key={self.api_key}"

    def _query(self, query, variables=None):
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        response = requests.post(self.endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    def list_pods(self):
        return self._query(LIST_PODS)

    def start_pod(self, pod_id):
        return self._query(START_POD, {"podId": pod_id})

    def stop_pod(self, pod_id):
        return self._query(STOP_POD, {"podId": pod_id})

    def delete_pod(self, pod_id):
        return self._query(DELETE_POD, {"podId": pod_id})

class SSHClient:
    def __init__(self, host, port, username, key_path):
        self.host = host
        self.port = port
        self.username = username
        self.key_path = os.path.expanduser(key_path)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        self.client.connect(self.host, self.port, self.username, key_filename=self.key_path)

    def exec_command(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    def close(self):
        self.client.close()

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class FunPodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod — Gaming Pod Manager")
        self.setGeometry(100, 100, 1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_desktop_tab()
        self.create_steam_tab()
        self.create_mods_tab()
        self.create_settings_tab()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Disconnected")

        self.load_config()
        self.api = RunPodAPI(self.config.get("api_key", ""))

    def load_config(self):
        self.config_path = os.path.expanduser("~/.funpod/config.json")
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    def create_dashboard_tab(self):
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        layout = QVBoxLayout(self.dashboard_tab)

        create_pod_button = QPushButton("Create Pod")
        layout.addWidget(create_pod_button)

        self.scroll_area = QScrollArea()
        layout.addWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)
        self.pod_layout = QGridLayout(self.scroll_content)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_pods)
        self.refresh_timer.start(5000)

    def refresh_pods(self):
        self.worker = Worker(self.api.list_pods)
        self.worker.finished.connect(self.update_dashboard)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_dashboard(self, data):
        for i in reversed(range(self.pod_layout.count())):
            self.pod_layout.itemAt(i).widget().setParent(None)

        if data and "data" in data and data["data"]["myself"]:
            pods = data["data"]["myself"]["pods"]
            row, col = 0, 0
            for pod in pods:
                card = self.create_pod_card(pod)
                self.pod_layout.addWidget(card, row, col)
                col += 1
                if col > 2:
                    col = 0
                    row += 1
            self.status_bar.showMessage(f"Connected | Active Pods: {len(pods)}")
        else:
            self.status_bar.showMessage("Connected | No Pods Found")


    def create_pod_card(self, pod):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)

        name_label = QLabel(f"<b>{pod["name"]}</b>")
        layout.addWidget(name_label)

        status_indicator = QLabel()
        if pod["desiredStatus"] == "RUNNING":
            status_indicator.setText("<font color=\"green\">●</font> Running")
        else:
            status_indicator.setText("<font color=\"red\">●</font> Stopped")
        layout.addWidget(status_indicator)

        gpu_label = QLabel(pod["machine"]["gpuDisplayName"])
        layout.addWidget(gpu_label)
        
        cost_label = QLabel(f"${pod["costPerHr"]}/hr")
        layout.addWidget(cost_label)

        uptime_label = QLabel(f"Uptime: {pod["runtime"]["uptimeInSeconds"]}s")
        layout.addWidget(uptime_label)

        start_button = QPushButton("Start")
        start_button.clicked.connect(lambda: self.start_pod(pod["id"]))
        layout.addWidget(start_button)

        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(lambda: self.stop_pod(pod["id"]))
        layout.addWidget(stop_button)

        destroy_button = QPushButton("Destroy")
        destroy_button.clicked.connect(lambda: self.delete_pod(pod["id"]))
        layout.addWidget(destroy_button)

        return card

    def start_pod(self, pod_id):
        self.worker = Worker(self.api.start_pod, pod_id)
        self.worker.finished.connect(self.refresh_pods)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def stop_pod(self, pod_id):
        self.worker = Worker(self.api.stop_pod, pod_id)
        self.worker.finished.connect(self.refresh_pods)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def delete_pod(self, pod_id):
        reply = QMessageBox.question(self, "Delete Pod", "Are you sure you want to delete this pod?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.worker = Worker(self.api.delete_pod, pod_id)
            self.worker.finished.connect(self.refresh_pods)
            self.worker.error.connect(self.show_error)
            self.worker.start()
    
    def create_desktop_tab(self):
        self.desktop_tab = QWidget()
        self.tabs.addTab(self.desktop_tab, "Desktop")
        layout = QVBoxLayout(self.desktop_tab)

        self.pod_selector = QComboBox()
        layout.addWidget(self.pod_selector)

        self.vnc_password = QLineEdit("gaming123")
        layout.addWidget(self.vnc_password)

        launch_vnc_button = QPushButton("Launch VNC")
        launch_vnc_button.clicked.connect(self.launch_vnc)
        layout.addWidget(launch_vnc_button)

    def launch_vnc(self):
        pod_id = self.pod_selector.currentData()
        if pod_id:
            url = f"https://{pod_id}-80.proxy.runpod.net"
            webbrowser.open(url)

    def create_steam_tab(self):
        self.steam_tab = QWidget()
        self.tabs.addTab(self.steam_tab, "Steam")
        layout = QVBoxLayout(self.steam_tab)

        self.steam_pod_selector = QComboBox()
        layout.addWidget(self.steam_pod_selector)

        install_steam_button = QPushButton("Install Steam")
        layout.addWidget(install_steam_button)

        self.steam_app_id = QLineEdit("779340")
        layout.addWidget(self.steam_app_id)

        install_game_button = QPushButton("Install Game")
        layout.addWidget(install_game_button)

        self.ssh_output_log = QTextEdit()
        self.ssh_output_log.setReadOnly(True)
        layout.addWidget(self.ssh_output_log)

    def create_mods_tab(self):
        self.mods_tab = QWidget()
        self.tabs.addTab(self.mods_tab, "Mods")
        layout = QVBoxLayout(self.mods_tab)

        self.mod_model = QFileSystemModel()
        self.mod_model.setRootPath(os.path.expanduser("~/.funpod/local_mods/"))
        
        self.mod_tree = QTreeView()
        self.mod_tree.setModel(self.mod_model)
        self.mod_tree.setRootIndex(self.mod_model.index(os.path.expanduser("~/.funpod/local_mods/")))
        layout.addWidget(self.mod_tree)

        upload_button = QPushButton("Upload to Pod")
        layout.addWidget(upload_button)

    def create_settings_tab(self):
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        layout = QGridLayout(self.settings_tab)

        layout.addWidget(QLabel("RunPod API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_key_input, 0, 1)

        layout.addWidget(QLabel("SSH Key Path:"), 1, 0)
        self.ssh_key_path_input = QLineEdit(os.path.expanduser("~/.ssh/id_ed25519"))
        layout.addWidget(self.ssh_key_path_input, 1, 1)

        layout.addWidget(QLabel("Default GPU:"), 2, 0)
        self.default_gpu_input = QComboBox()
        self.default_gpu_input.addItems(["RTX 4090", "A40", "A100", "H100"])
        layout.addWidget(self.default_gpu_input, 2, 1)

        layout.addWidget(QLabel("VNC Password:"), 3, 0)
        self.vnc_password_input = QLineEdit("gaming123")
        layout.addWidget(self.vnc_password_input, 3, 1)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button, 4, 1)

        self.load_settings()

    def load_settings(self):
        self.api_key_input.setText(self.config.get("api_key", ""))
        self.ssh_key_path_input.setText(self.config.get("ssh_key_path", os.path.expanduser("~/.ssh/id_ed25519")))
        self.default_gpu_input.setCurrentText(self.config.get("default_gpu", "RTX 4090"))
        self.vnc_password_input.setText(self.config.get("vnc_password", "gaming123"))

    def save_settings(self):
        self.config["api_key"] = self.api_key_input.text()
        self.config["ssh_key_path"] = self.ssh_key_path_input.text()
        self.config["default_gpu"] = self.default_gpu_input.currentText()
        self.config["vnc_password"] = self.vnc_password_input.text()
        self.save_config()
        self.api = RunPodAPI(self.config["api_key"])
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")


    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ThemeEngine.apply(app)
    window = FunPodWindow()
    window.show()
    sys.exit(app.exec())

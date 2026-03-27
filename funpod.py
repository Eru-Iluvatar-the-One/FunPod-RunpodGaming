import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton, QLineEdit, QGridLayout
from PyQt6.QtCore import QTimer

try:
    from arda_theme import ThemeEngine, Theme
except ImportError:
    ThemeEngine = None

class PomodoroTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.time_label = QLabel("25:00")
        self.layout.addWidget(self.time_label)
        self.start_button = QPushButton("Start")
        self.layout.addWidget(self.start_button)
        self.timer = QTimer()
        self.time_left = 25 * 60

        self.start_button.clicked.connect(self.start_timer)
        self.timer.timeout.connect(self.update_time)

    def start_timer(self):
        self.timer.start(1000)

    def update_time(self):
        self.time_left -= 1
        mins, secs = divmod(self.time_left, 60)
        self.time_label.setText(f"{mins:02d}:{secs:02d}")
        if self.time_left == 0:
            self.timer.stop()

class FunPodGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FunPod Runpod Gaming")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.pod_control_tab = QWidget()
        self.games_tab = QWidget()
        self.mods_tab = QWidget()
        self.vnc_tab = QWidget()

        self.tabs.addTab(self.pod_control_tab, "Pod Control")
        self.tabs.addTab(self.games_tab, "Games")
        self.tabs.addTab(self.mods_tab, "Mods")
        self.tabs.addTab(self.vnc_tab, "VNC")

        # Pod Control Tab
        self.pod_control_layout = QVBoxLayout(self.pod_control_tab)
        self.pod_control_layout.addWidget(QLabel("RunPod API integration would be here."))
        self.pod_control_layout.addWidget(PomodoroTimer())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if ThemeEngine:
        ThemeEngine.apply_theme(Theme.CATPPUCCIN_MOCHA)
    window = FunPodGUI()
    window.show()
    sys.exit(app.exec())

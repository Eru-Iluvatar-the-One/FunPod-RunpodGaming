"""
arda_theme.py — Shared theme engine for ArdaTek ecosystem apps.
Catppuccin Mocha + 5 additional themes. Theme bar widget for PyQt6.
Drop into any repo root. Import: from arda_theme import ThemeEngine, ThemeBar, THEMES
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

THEMES = {
    "Catppuccin Mocha": {
        "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
        "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
        "text": "#cdd6f4", "subtext0": "#a6adc8", "subtext1": "#bac2de",
        "blue": "#89b4fa", "green": "#a6e3a1", "peach": "#fab387",
        "mauve": "#cba6f7", "red": "#f38ba8", "teal": "#94e2d5",
        "yellow": "#f9e2af", "overlay0": "#6c7086", "sapphire": "#74c7ec",
        "lavender": "#b4befe", "pink": "#f5c2e7",
    },
    "Dracula": {
        "base": "#282a36", "mantle": "#21222c", "crust": "#191a21",
        "surface0": "#44475a", "surface1": "#4d5066", "surface2": "#565973",
        "text": "#f8f8f2", "subtext0": "#bfbfbf", "subtext1": "#d9d9d9",
        "blue": "#8be9fd", "green": "#50fa7b", "peach": "#ffb86c",
        "mauve": "#bd93f9", "red": "#ff5555", "teal": "#8be9fd",
        "yellow": "#f1fa8c", "overlay0": "#6272a4", "sapphire": "#8be9fd",
        "lavender": "#bd93f9", "pink": "#ff79c6",
    },
    "Mordor": {
        "base": "#0D0A08", "mantle": "#0A0806", "crust": "#060504",
        "surface0": "#1a1510", "surface1": "#2a2218", "surface2": "#3a2f20",
        "text": "#e8d5b0", "subtext0": "#b8a080", "subtext1": "#c8b090",
        "blue": "#FFD700", "green": "#8B4513", "peach": "#FF4500",
        "mauve": "#B22222", "red": "#DC143C", "teal": "#DAA520",
        "yellow": "#FFD700", "overlay0": "#5a4a30", "sapphire": "#CD853F",
        "lavender": "#D2691E", "pink": "#FF6347",
    },
    "Fingolfin": {
        "base": "#050810", "mantle": "#030508", "crust": "#010204",
        "surface0": "#0f1520", "surface1": "#1a2535", "surface2": "#25354a",
        "text": "#e8eef8", "subtext0": "#a0b0c8", "subtext1": "#c0d0e8",
        "blue": "#7EC8E3", "green": "#90c0a0", "peach": "#c0a090",
        "mauve": "#9090d0", "red": "#c07080", "teal": "#70c0c0",
        "yellow": "#d0d0a0", "overlay0": "#405060", "sapphire": "#7EC8E3",
        "lavender": "#a0a0e0", "pink": "#d0a0c0",
    },
    "Tokyo Night": {
        "base": "#1a1b26", "mantle": "#16161e", "crust": "#12121a",
        "surface0": "#24283b", "surface1": "#2f3449", "surface2": "#3b4057",
        "text": "#c0caf5", "subtext0": "#9aa5ce", "subtext1": "#a9b1d6",
        "blue": "#7aa2f7", "green": "#9ece6a", "peach": "#ff9e64",
        "mauve": "#bb9af7", "red": "#f7768e", "teal": "#73daca",
        "yellow": "#e0af68", "overlay0": "#565f89", "sapphire": "#7dcfff",
        "lavender": "#bb9af7", "pink": "#ff007c",
    },
    "Gruvbox": {
        "base": "#1d2021", "mantle": "#191b1c", "crust": "#141617",
        "surface0": "#282828", "surface1": "#3c3836", "surface2": "#504945",
        "text": "#ebdbb2", "subtext0": "#bdae93", "subtext1": "#d5c4a1",
        "blue": "#83a598", "green": "#b8bb26", "peach": "#fe8019",
        "mauve": "#d3869b", "red": "#fb4934", "teal": "#8ec07c",
        "yellow": "#fabd2f", "overlay0": "#665c54", "sapphire": "#83a598",
        "lavender": "#d3869b", "pink": "#d3869b",
    },
}


class ThemeEngine:
    """Apply a named theme to a QApplication."""

    @staticmethod
    def apply(app: QApplication, theme_name: str):
        t = THEMES.get(theme_name, THEMES["Catppuccin Mocha"])
        p = app.palette()
        p.setColor(QPalette.ColorRole.Window, QColor(t["crust"]))
        p.setColor(QPalette.ColorRole.WindowText, QColor(t["text"]))
        p.setColor(QPalette.ColorRole.Base, QColor(t["base"]))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor(t["mantle"]))
        p.setColor(QPalette.ColorRole.Text, QColor(t["text"]))
        p.setColor(QPalette.ColorRole.Button, QColor(t["surface0"]))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(t["text"]))
        p.setColor(QPalette.ColorRole.Highlight, QColor(t["blue"]))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(t["crust"]))
        app.setPalette(p)
        return t

    @staticmethod
    def get_qss(theme_name: str) -> str:
        t = THEMES.get(theme_name, THEMES["Catppuccin Mocha"])
        fu = "'Segoe UI Variable', 'Inter', 'Segoe UI', sans-serif"
        fm = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"
        return f"""
* {{ font-family: {fu}; }}
QMainWindow {{ background: {t['crust']}; }}
QWidget {{ background: {t['base']}; color: {t['text']}; }}
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: {t['crust']}; border: none; qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {t['overlay0']}; border: none; border-bottom: 2px solid transparent; padding: 8px 18px; font-size: 10pt; font-weight: 600; }}
QTabBar::tab:selected {{ color: {t['text']}; border-bottom-color: {t['blue']}; }}
QTabBar::tab:hover:!selected {{ color: {t['subtext1']}; }}
QPushButton {{ background: {t['surface0']}; color: {t['text']}; border: 1px solid {t['surface1']}; border-radius: 8px; padding: 6px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {t['surface1']}; border-color: {t['blue']}; }}
QLineEdit {{ background: {t['surface0']}; color: {t['text']}; border: 1px solid {t['surface1']}; border-radius: 8px; padding: 6px 10px; }}
QLineEdit:focus {{ border-color: {t['blue']}; }}
QTextEdit {{ background: {t['mantle']}; color: {t['text']}; border: 1px solid {t['surface0']}; border-radius: 8px; padding: 10px; font-family: {fm}; }}
QStatusBar {{ background: {t['crust']}; color: {t['overlay0']}; border-top: 1px solid {t['surface0']}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {t['surface2']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class ThemeBar(QWidget):
    """Row of frosted-glass theme circles for the toolbar."""
    theme_changed = pyqtSignal(str)

    CIRCLE_COLORS = {
        "Catppuccin Mocha": "#89b4fa",
        "Dracula": "#bd93f9",
        "Mordor": "#FFD700",
        "Fingolfin": "#7EC8E3",
        "Tokyo Night": "#7aa2f7",
        "Gruvbox": "#fabd2f",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "Catppuccin Mocha"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        for name, color in self.CIRCLE_COLORS.items():
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}40;
                    border: 2px solid {color}60;
                    border-radius: 11px;
                }}
                QPushButton:hover {{
                    background: {color}80;
                    border-color: {color};
                    /* scale effect via padding trick */
                }}
            """)
            btn.clicked.connect(lambda _, n=name: self._select(n))
            lay.addWidget(btn)

        self.setStyleSheet("background: transparent;")

    def _select(self, name):
        self._current = name
        self.theme_changed.emit(name)

    def current(self) -> str:
        return self._current

"""
arda_theme.py — Shared Circles Theme System for ALL PyQt6 Apps
6 themes: Catppuccin Mocha, Dracula, Mordor, Fingolfin vs Morgoth, Tokyo Night, Gruvbox Material Dark.
Frosted-glass circle buttons in top bar. Hot-swap QSS. 200ms CSS transition emulation.
Import into ANY PyQt6 app: from arda_theme import ThemeEngine, ThemeBar
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QApplication, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSettings, QSize
from PyQt6.QtGui import QColor, QPalette, QPainter, QBrush, QPen

# ── THEME DEFINITIONS ────────────────────────────────────────────────
THEMES: dict[str, dict[str, str]] = {
    "Catppuccin Mocha": {
        "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
        "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
        "overlay0": "#6c7086", "overlay1": "#7f849c",
        "text": "#cdd6f4", "subtext0": "#a6adc8", "subtext1": "#bac2de",
        "red": "#f38ba8", "green": "#a6e3a1", "yellow": "#f9e2af",
        "blue": "#89b4fa", "mauve": "#cba6f7", "peach": "#fab387",
        "teal": "#94e2d5", "sky": "#89dceb", "sapphire": "#74c7ec",
        "lavender": "#b4befe", "pink": "#f5c2e7",
        "accent": "#89b4fa", "circle": "#89b4fa",
    },
    "Dracula": {
        "base": "#282a36", "mantle": "#21222c", "crust": "#191a21",
        "surface0": "#44475a", "surface1": "#4e5166", "surface2": "#585d73",
        "overlay0": "#6272a4", "overlay1": "#7384b0",
        "text": "#f8f8f2", "subtext0": "#bfbfbf", "subtext1": "#d4d4d4",
        "red": "#ff5555", "green": "#50fa7b", "yellow": "#f1fa8c",
        "blue": "#6272a4", "mauve": "#bd93f9", "peach": "#ffb86c",
        "teal": "#8be9fd", "sky": "#8be9fd", "sapphire": "#6272a4",
        "lavender": "#bd93f9", "pink": "#ff79c6",
        "accent": "#bd93f9", "circle": "#bd93f9",
    },
    "Mordor": {
        "base": "#0D0A08", "mantle": "#0a0806", "crust": "#060504",
        "surface0": "#2a1f14", "surface1": "#3d2d1a", "surface2": "#503c20",
        "overlay0": "#7a6040", "overlay1": "#8f7550",
        "text": "#e8d5b0", "subtext0": "#b8a080", "subtext1": "#d0b898",
        "red": "#c41e1e", "green": "#8a9a3a", "yellow": "#FFD700",
        "blue": "#8b6914", "mauve": "#a05020", "peach": "#e07020",
        "teal": "#b08030", "sky": "#d4a040", "sapphire": "#c49030",
        "lavender": "#d09040", "pink": "#c04030",
        "accent": "#FFD700", "circle": "#FFD700",
    },
    "Fingolfin vs Morgoth": {
        "base": "#050810", "mantle": "#030508", "crust": "#010204",
        "surface0": "#0f1525", "surface1": "#161e35", "surface2": "#1e2845",
        "overlay0": "#3a4a6a", "overlay1": "#4a5a80",
        "text": "#e8eaf0", "subtext0": "#a0a8c0", "subtext1": "#c0c8e0",
        "red": "#c04050", "green": "#60c090", "yellow": "#d0c070",
        "blue": "#7EC8E3", "mauve": "#9090d0", "peach": "#c0a070",
        "teal": "#60b0c0", "sky": "#7EC8E3", "sapphire": "#5090c0",
        "lavender": "#a0a0e0", "pink": "#c080b0",
        "accent": "#7EC8E3", "circle": "#FFFFFF",
    },
    "Tokyo Night": {
        "base": "#1a1b26", "mantle": "#16161e", "crust": "#101014",
        "surface0": "#24283b", "surface1": "#2f3451", "surface2": "#3b4067",
        "overlay0": "#565f89", "overlay1": "#6b749d",
        "text": "#c0caf5", "subtext0": "#9aa5ce", "subtext1": "#a9b1d6",
        "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68",
        "blue": "#7aa2f7", "mauve": "#bb9af7", "peach": "#ff9e64",
        "teal": "#73daca", "sky": "#7dcfff", "sapphire": "#2ac3de",
        "lavender": "#bb9af7", "pink": "#f7768e",
        "accent": "#7aa2f7", "circle": "#7aa2f7",
    },
    "Gruvbox Material Dark": {
        "base": "#1d2021", "mantle": "#191b1c", "crust": "#141617",
        "surface0": "#32302f", "surface1": "#3c3836", "surface2": "#504945",
        "overlay0": "#665c54", "overlay1": "#7c6f64",
        "text": "#ebdbb2", "subtext0": "#bdae93", "subtext1": "#d5c4a1",
        "red": "#fb4934", "green": "#b8bb26", "yellow": "#fabd2f",
        "blue": "#83a598", "mauve": "#d3869b", "peach": "#fe8019",
        "teal": "#8ec07c", "sky": "#83a598", "sapphire": "#689d6a",
        "lavender": "#d3869b", "pink": "#d3869b",
        "accent": "#fabd2f", "circle": "#fabd2f",
    },
}

DEFAULT_THEME = "Catppuccin Mocha"


def generate_qss(c: dict[str, str]) -> str:
    """Generate complete QSS stylesheet from a theme color dict."""
    return f"""
QMainWindow {{ background: {c['base']}; }}
QWidget {{ background: {c['base']}; color: {c['text']}; font-family: 'Segoe UI'; font-size: 10pt; }}
QTabWidget::pane {{ border: 1px solid {c['surface0']}; border-top: none; background: {c['base']}; }}
QTabBar::tab {{
    background: {c['crust']};
    color: {c['overlay0']};
    border: none;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 10pt;
    min-width: 100px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom: 2px solid {c['accent']}; background: {c['base']}; }}
QTabBar::tab:hover {{ color: {c['text']}; background: {c['surface0']}; }}
QTableWidget {{
    background: {c['mantle']};
    alternate-background-color: {c['crust']};
    color: {c['text']};
    border: 1px solid {c['surface0']};
    border-radius: 6px;
    gridline-color: {c['surface0']};
    font-size: 9pt;
}}
QTableWidget::item {{ padding: 4px 8px; }}
QTableWidget::item:selected {{ background: {c['surface1']}; color: {c['accent']}; }}
QHeaderView::section {{
    background: {c['crust']};
    color: {c['subtext0']};
    border: none;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 9pt;
    border-bottom: 1px solid {c['surface0']};
    border-right: 1px solid {c['surface0']};
}}
QPushButton {{
    background: {c['surface0']};
    color: {c['text']};
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 9pt;
}}
QPushButton:hover {{ background: {c['surface1']}; color: {c['accent']}; }}
QPushButton:pressed {{ background: {c['surface2']}; }}
QPushButton#primary {{ background: {c['accent']}; color: {c['crust']}; font-size: 10pt; }}
QPushButton#primary:hover {{ background: {c['sapphire']}; }}
QPushButton#primaryBtn {{ background: {c['accent']}; color: {c['crust']}; }}
QPushButton#primaryBtn:hover {{ background: {c['sapphire']}; }}
QPushButton#success {{ background: {c['green']}; color: {c['crust']}; }}
QPushButton#success:hover {{ background: {c['teal']}; }}
QPushButton#warning {{ background: {c['peach']}; color: {c['crust']}; }}
QPushButton#warning:hover {{ background: {c['yellow']}; color: {c['crust']}; }}
QPushButton#danger {{ background: {c['surface0']}; color: {c['red']}; }}
QPushButton#danger:hover {{ background: {c['red']}; color: {c['crust']}; }}
QComboBox {{
    background: {c['surface0']};
    color: {c['text']};
    border: 1px solid {c['surface1']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 9pt;
    min-width: 90px;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {c['surface0']};
    color: {c['text']};
    border: 1px solid {c['surface1']};
    selection-background-color: {c['surface1']};
}}
QLineEdit {{
    background: {c['surface0']};
    color: {c['text']};
    border: 1px solid {c['surface1']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 9pt;
}}
QLineEdit:focus {{ border-color: {c['accent']}; }}
QTextEdit, QPlainTextEdit {{
    background: {c['mantle']};
    color: {c['text']};
    border: 1px solid {c['surface0']};
    border-radius: 6px;
    padding: 8px;
    font-family: 'Cascadia Code', 'Consolas';
    font-size: 9pt;
}}
QGroupBox {{
    background: {c['mantle']};
    border: 1px solid {c['surface0']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: {c['subtext0']};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
QStatusBar {{
    background: {c['crust']};
    color: {c['overlay0']};
    font-size: 8pt;
    border-top: 1px solid {c['surface0']};
}}
QProgressBar {{
    background: {c['surface0']};
    border: none;
    border-radius: 4px;
    height: 6px;
}}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 4px; }}
QFrame#titleBar {{ background: {c['mantle']}; border-bottom: 1px solid {c['surface0']}; }}
QFrame#statCard {{
    background: {c['mantle']};
    border: 1px solid {c['surface0']};
    border-radius: 10px;
    padding: 16px;
}}
QFrame#heartbeatCard {{
    background: {c['mantle']};
    border: 1px solid {c['surface0']};
    border-radius: 12px;
    padding: 16px;
}}
QLabel#cardValue {{ font-size: 28pt; font-weight: 800; }}
QLabel#cardLabel {{ font-size: 9pt; color: {c['overlay0']}; }}
QLabel#sectionTitle {{ font-size: 11pt; font-weight: 700; color: {c['accent']}; }}
QLabel#titleLabel {{ font-size: 12pt; font-weight: 700; color: {c['accent']}; }}
QLabel#leadName {{ font-size: 18pt; font-weight: 700; color: {c['text']}; }}
QTreeWidget {{
    background: {c['mantle']};
    color: {c['text']};
    border: 1px solid {c['surface0']};
    border-radius: 6px;
    alternate-background-color: {c['crust']};
    font-size: 9pt;
}}
QTreeWidget::item {{ padding: 4px; }}
QTreeWidget::item:selected {{ background: {c['surface1']}; color: {c['accent']}; }}
QTreeWidget::item:hover {{ background: {c['surface0']}; }}
QSplitter::handle {{ background: {c['surface0']}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}
QToolButton {{
    background: transparent;
    color: {c['overlay0']};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 10pt;
}}
QToolButton:hover {{ background: {c['surface0']}; color: {c['text']}; }}
QMenu {{
    background-color: {c['surface0']};
    color: {c['text']};
    border: 1px solid {c['surface1']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {c['surface1']}; color: {c['accent']}; }}
QMenu::separator {{ height: 1px; background: {c['surface1']}; margin: 4px 8px; }}
QDialog {{ background: {c['base']}; }}
"""


class CircleButton(QPushButton):
    """Frosted-glass circle button for theme selection."""

    def __init__(self, theme_name: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme_name = theme_name
        self._color = color
        self._active = False
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(theme_name)
        self._update_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def _update_style(self) -> None:
        ring = f"border: 2px solid {self._color};" if self._active else "border: 2px solid transparent;"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._color};
                {ring}
                border-radius: 12px;
                min-width: 24px; max-width: 24px;
                min-height: 24px; max-height: 24px;
            }}
            QPushButton:hover {{
                border: 2px solid {self._color};
                min-width: 26px; max-width: 26px;
                min-height: 26px; max-height: 26px;
                border-radius: 13px;
            }}
        """)


class ThemeBar(QWidget):
    """Horizontal row of frosted-glass circle buttons for theme switching."""

    def __init__(self, engine: "ThemeEngine", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._buttons: list[CircleButton] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        for name, colors in THEMES.items():
            btn = CircleButton(name, colors["circle"], self)
            btn.clicked.connect(lambda checked, n=name: self._engine.apply(n))
            self._buttons.append(btn)
            layout.addWidget(btn)

        self.setFixedHeight(34)
        self.setStyleSheet("background: transparent;")

    def update_active(self, theme_name: str) -> None:
        for btn in self._buttons:
            btn.set_active(btn.theme_name == theme_name)


class ThemeEngine:
    """Manages theme state, QSS generation, palette application, and persistence."""

    def __init__(self, app: QApplication, settings_key: str = "theme") -> None:
        self._app = app
        self._settings = QSettings("ArdaTek", "ThemeEngine")
        self._settings_key = settings_key
        self._current = self._settings.value(settings_key, DEFAULT_THEME)
        if self._current not in THEMES:
            self._current = DEFAULT_THEME
        self._bars: list[ThemeBar] = []
        self._callbacks: list[Callable[[str, dict[str, str]], None]] = []

    @property
    def current_name(self) -> str:
        return self._current

    @property
    def current_colors(self) -> dict[str, str]:
        return THEMES[self._current]

    def create_bar(self, parent: QWidget | None = None) -> ThemeBar:
        bar = ThemeBar(self, parent)
        bar.update_active(self._current)
        self._bars.append(bar)
        return bar

    def on_change(self, callback: Callable[[str, dict[str, str]], None]) -> None:
        self._callbacks.append(callback)

    def apply(self, theme_name: str) -> None:
        if theme_name not in THEMES:
            return
        self._current = theme_name
        self._settings.setValue(self._settings_key, theme_name)
        c = THEMES[theme_name]

        # Apply QSS
        self._app.setStyleSheet(generate_qss(c))

        # Apply palette
        palette = self._app.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(c["base"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(c["mantle"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(c["surface0"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(c["accent"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(c["crust"]))
        self._app.setPalette(palette)

        # Update all bars
        for bar in self._bars:
            bar.update_active(theme_name)

        # Fire callbacks
        for cb in self._callbacks:
            cb(theme_name, c)

    def apply_current(self) -> None:
        self.apply(self._current)

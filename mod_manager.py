"""
FunPod Mod Manager — Mod Management Tab
PyQt6 · Catppuccin Mocha · Fingolfin Standard

Mod = zip archive with manifest.json:
  {"name": "...", "game": "...", "version": "...", "files": [...], "install_path": "..."}

Features:
- Browse/install/enable/disable mods
- Drag-sort mod order
- Conflict detection
- Deploy to pod via SSH on launch
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

# Catppuccin Mocha
C = {
    "base": "#1e1e2e", "mantle": "#181825", "crust": "#11111b",
    "surface0": "#313244", "surface1": "#45475a", "surface2": "#585b70",
    "text": "#cdd6f4", "subtext0": "#a6adc8",
    "blue": "#89b4fa", "green": "#a6e3a1", "red": "#f38ba8",
    "peach": "#fab387", "yellow": "#f9e2af", "overlay0": "#6c7086",
    "teal": "#94e2d5", "mauve": "#cba6f7",
}

MODS_DIR = Path.home() / ".funpod" / "mods"
MODS_DIR.mkdir(parents=True, exist_ok=True)
MOD_CONFIG = MODS_DIR / "mod_config.json"


class ModManifest:
    """Parsed mod manifest from zip archive."""

    def __init__(
        self,
        name: str = "",
        game: str = "",
        version: str = "1.0",
        files: Optional[list[str]] = None,
        install_path: str = "",
        enabled: bool = True,
        order: int = 0,
        zip_path: str = "",
    ) -> None:
        self.name = name
        self.game = game
        self.version = version
        self.files = files or []
        self.install_path = install_path
        self.enabled = enabled
        self.order = order
        self.zip_path = zip_path

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        return {
            "name": self.name,
            "game": self.game,
            "version": self.version,
            "files": self.files,
            "install_path": self.install_path,
            "enabled": self.enabled,
            "order": self.order,
            "zip_path": self.zip_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModManifest":
        """Deserialize from dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class ModListItem(QListWidgetItem):
    """Custom list item showing mod info with enable/disable state."""

    def __init__(self, mod: ModManifest, parent: Optional[QListWidget] = None) -> None:
        display = f"{'✅' if mod.enabled else '❌'}  {mod.name} v{mod.version}  [{mod.game}]"
        super().__init__(display, parent)
        self.mod = mod
        self._update_colors()

    def _update_colors(self) -> None:
        if self.mod.enabled:
            self.setForeground(QColor(C["green"]))
        else:
            self.setForeground(QColor(C["overlay0"]))

    def refresh(self) -> None:
        """Update display text after state change."""
        prefix = "✅" if self.mod.enabled else "❌"
        self.setText(f"{prefix}  {self.mod.name} v{self.mod.version}  [{self.mod.game}]")
        self._update_colors()


class ModManagerTab(QWidget):
    """Complete mod management tab for FunPod GUI."""

    mods_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._mods: list[ModManifest] = []
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎮  Mod Manager")
        title.setStyleSheet(
            f"color: {C['text']}; font-size: 16pt; font-weight: 700;"
            f" background: transparent;"
        )
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("0 mods")
        self._count_label.setStyleSheet(
            f"color: {C['overlay0']}; font-size: 10pt; background: transparent;"
        )
        header.addWidget(self._count_label)
        root.addLayout(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_add = QPushButton("📦  Install Mod")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._install_mod)
        toolbar.addWidget(btn_add)

        btn_enable = QPushButton("✅  Enable")
        btn_enable.clicked.connect(self._toggle_selected)
        toolbar.addWidget(btn_enable)

        btn_up = QPushButton("⬆")
        btn_up.setFixedWidth(40)
        btn_up.clicked.connect(self._move_up)
        toolbar.addWidget(btn_up)

        btn_down = QPushButton("⬇")
        btn_down.setFixedWidth(40)
        btn_down.clicked.connect(self._move_down)
        toolbar.addWidget(btn_down)

        toolbar.addStretch()

        btn_conflicts = QPushButton("⚠  Check Conflicts")
        btn_conflicts.clicked.connect(self._check_conflicts)
        toolbar.addWidget(btn_conflicts)

        btn_remove = QPushButton("🗑  Remove")
        btn_remove.setObjectName("danger")
        btn_remove.clicked.connect(self._remove_selected)
        toolbar.addWidget(btn_remove)

        root.addLayout(toolbar)

        # Mod list
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setAlternatingRowColors(True)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {C['mantle']};
                color: {C['text']};
                border: 1px solid {C['surface0']};
                border-radius: 8px;
                font-size: 11pt;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-bottom: 1px solid {C['surface0']};
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background: {C['surface1']};
                color: {C['blue']};
            }}
            QListWidget::item:hover {{
                background: {C['surface0']};
            }}
        """)
        self._list.itemDoubleClicked.connect(self._toggle_item)
        root.addWidget(self._list, 1)

        # Info bar
        self._info = QLabel("Double-click to toggle. Drag to reorder. Mods deploy to pod on launch.")
        self._info.setStyleSheet(
            f"color: {C['overlay0']}; font-size: 9pt; background: transparent;"
        )
        root.addWidget(self._info)

    def _install_mod(self) -> None:
        """Browse for a mod zip and install it."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Install Mod", "", "Mod Archives (*.zip);;All Files (*)"
        )
        if not path:
            return

        zip_path = Path(path)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if "manifest.json" not in names:
                    QMessageBox.warning(
                        self, "Invalid Mod",
                        "No manifest.json found in archive."
                    )
                    return
                manifest_data = json.loads(zf.read("manifest.json"))
        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
            QMessageBox.warning(self, "Invalid Mod", f"Could not read mod: {exc}")
            return

        # Copy zip to mods dir
        dest = MODS_DIR / zip_path.name
        if dest.exists():
            resp = QMessageBox.question(
                self, "Mod Exists",
                f"{zip_path.name} already installed. Replace?",
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
        shutil.copy2(zip_path, dest)

        mod = ModManifest(
            name=manifest_data.get("name", zip_path.stem),
            game=manifest_data.get("game", "Unknown"),
            version=manifest_data.get("version", "1.0"),
            files=manifest_data.get("files", []),
            install_path=manifest_data.get("install_path", ""),
            enabled=True,
            order=len(self._mods),
            zip_path=str(dest),
        )
        self._mods.append(mod)
        ModListItem(mod, self._list)
        self._save_config()
        self._update_count()
        self._info.setText(f"✅ Installed: {mod.name} v{mod.version}")

    def _toggle_selected(self) -> None:
        """Toggle enable/disable on selected mod."""
        item = self._list.currentItem()
        if isinstance(item, ModListItem):
            self._toggle_item(item)

    def _toggle_item(self, item: QListWidgetItem) -> None:
        """Toggle a specific mod item."""
        if isinstance(item, ModListItem):
            item.mod.enabled = not item.mod.enabled
            item.refresh()
            self._save_config()

    def _move_up(self) -> None:
        """Move selected mod up in load order."""
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._list.setCurrentRow(row - 1)
        self._reorder()

    def _move_down(self) -> None:
        """Move selected mod down in load order."""
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._list.setCurrentRow(row + 1)
        self._reorder()

    def _reorder(self) -> None:
        """Sync internal order with list widget order."""
        self._mods.clear()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if isinstance(item, ModListItem):
                item.mod.order = i
                self._mods.append(item.mod)
        self._save_config()

    def _remove_selected(self) -> None:
        """Remove selected mod."""
        row = self._list.currentRow()
        if row < 0:
            return
        item = self._list.item(row)
        if not isinstance(item, ModListItem):
            return

        resp = QMessageBox.question(
            self, "Remove Mod",
            f"Remove {item.mod.name}? The zip file will also be deleted.",
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        # Delete zip
        zip_path = Path(item.mod.zip_path)
        if zip_path.exists():
            zip_path.unlink()

        self._mods = [m for m in self._mods if m.name != item.mod.name]
        self._list.takeItem(row)
        self._save_config()
        self._update_count()
        self._info.setText(f"🗑 Removed: {item.mod.name}")

    def _check_conflicts(self) -> None:
        """Detect file conflicts between enabled mods."""
        file_map: dict[str, list[str]] = {}
        for mod in self._mods:
            if not mod.enabled:
                continue
            for f in mod.files:
                file_map.setdefault(f, []).append(mod.name)

        conflicts = {f: mods for f, mods in file_map.items() if len(mods) > 1}
        if not conflicts:
            self._info.setText("✅ No conflicts detected between enabled mods.")
            self._info.setStyleSheet(
                f"color: {C['green']}; font-size: 9pt; background: transparent;"
            )
            return

        lines = []
        for filepath, mod_names in conflicts.items():
            lines.append(f"  {filepath} → {', '.join(mod_names)}")
        msg = "⚠ File conflicts found:\n" + "\n".join(lines)
        QMessageBox.warning(self, "Mod Conflicts", msg)
        self._info.setText(f"⚠ {len(conflicts)} file conflict(s) detected")
        self._info.setStyleSheet(
            f"color: {C['yellow']}; font-size: 9pt; background: transparent;"
        )

    def get_enabled_mods(self) -> list[ModManifest]:
        """Return enabled mods in load order for deployment."""
        return [m for m in self._mods if m.enabled]

    def _update_count(self) -> None:
        enabled = sum(1 for m in self._mods if m.enabled)
        total = len(self._mods)
        self._count_label.setText(f"{enabled}/{total} mods enabled")

    def _save_config(self) -> None:
        """Persist mod config to JSON."""
        data = [m.to_dict() for m in self._mods]
        MOD_CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.mods_changed.emit()

    def _load_config(self) -> None:
        """Load mod config from JSON."""
        if not MOD_CONFIG.exists():
            return
        try:
            data = json.loads(MOD_CONFIG.read_text(encoding="utf-8"))
            for item in data:
                mod = ModManifest.from_dict(item)
                self._mods.append(mod)
                ModListItem(mod, self._list)
            self._update_count()
        except (json.JSONDecodeError, TypeError):
            pass

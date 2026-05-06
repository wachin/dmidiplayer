"""Persistent application settings."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QSettings, QStandardPaths


class AppSettings:
    RECENT_FILES_LIMIT = 10

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or app_config_dir()
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.base_dir = fallback_config_dir()
            self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "settings.ini"
        self._settings = QSettings(str(self.path), QSettings.Format.IniFormat)

    def last_folder(self, fallback: Path) -> Path:
        value = self._settings.value("files/last_folder", "", str)
        path = Path(value) if value else fallback
        return path if path.exists() else fallback

    def set_last_folder(self, folder: str | Path) -> None:
        path = Path(folder)
        if path.exists():
            self._settings.setValue("files/last_folder", str(path))
            self._settings.sync()

    def recent_files(self) -> list[Path]:
        value = self._settings.value("files/recent", [], list)
        if isinstance(value, str):
            values = [value]
        else:
            values = [str(item) for item in value]
        return [Path(item) for item in values if item]

    def add_recent_file(self, file_name: str | Path) -> None:
        path = Path(file_name)
        if not path.exists():
            return
        recent = [item for item in self.recent_files() if item != path]
        recent.insert(0, path)
        self._settings.setValue("files/recent", [str(item) for item in recent[: self.RECENT_FILES_LIMIT]])
        self._settings.sync()

    def clear_recent_files(self) -> None:
        self._settings.remove("files/recent")
        self._settings.sync()

    def midi_destination(self) -> str:
        return self._settings.value("midi/destination", "", str)

    def set_midi_destination(self, destination: str) -> None:
        if destination:
            self._settings.setValue("midi/destination", destination)
        else:
            self._settings.remove("midi/destination")
        self._settings.sync()


def app_config_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    if location:
        return Path(location)
    return Path.home() / ".config" / "dmidiplayer" / "dmidiplayer-py"


def fallback_config_dir() -> Path:
    return Path(tempfile.gettempdir()) / "dmidiplayer-py"

"""Persistent application settings."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QSettings, QStandardPaths

WindowGeometry = tuple[int, int, int, int]


class AppSettings:
    RECENT_FILES_LIMIT = 10
    DEFAULT_PERCUSSION_CHANNEL = 10
    DEFAULT_AUTO_PLAY_ON_LOAD = False
    DEFAULT_PLAYLIST_AUTO_ADVANCE = True
    DEFAULT_AUTO_SONG_SETTINGS = False
    DEFAULT_QT_STYLE = "system"
    DEFAULT_FORCE_DARK_MODE = False
    DEFAULT_USE_INTERNAL_ICON_THEME = False
    DEFAULT_SOLO_VOLUME_REDUCTION = 50
    DEFAULT_MIDI_RESET_BEFORE_PLAYBACK = False
    DEFAULT_PIANOLA_COLOR_MODE = "blue"
    DEFAULT_PIANOLA_SINGLE_COLOR = "#1d4ed8"
    DEFAULT_PIANOLA_VELOCITY_TINTING = True
    DEFAULT_PIANOLA_NOTE_LABEL_MODE = "never"
    DEFAULT_PIANOLA_OCTAVE_DESIGNATION = "scientific"
    DEFAULT_PIANOLA_NOTE_FONT_FAMILY = "Sans Serif"
    DEFAULT_PIANOLA_NOTE_FONT_SIZE = 8
    DEFAULT_LYRICS_FONT_FAMILY = "Sans Serif"
    DEFAULT_LYRICS_FONT_SIZE = 10
    DEFAULT_LYRICS_FUTURE_COLOR = "#2563eb"
    DEFAULT_LYRICS_PAST_COLOR = "#6b7280"

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

    def window_geometry(self) -> WindowGeometry | None:
        width = self._settings.value("window/width", 0, int)
        height = self._settings.value("window/height", 0, int)
        x = self._settings.value("window/x", 0, int)
        y = self._settings.value("window/y", 0, int)
        if width <= 0 or height <= 0:
            return None
        return (x, y, width, height)

    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        self._settings.setValue("window/x", x)
        self._settings.setValue("window/y", y)
        self._settings.setValue("window/width", width)
        self._settings.setValue("window/height", height)
        self._settings.sync()

    def percussion_channel(self) -> int:
        value = self._settings.value("general/percussion_channel", self.DEFAULT_PERCUSSION_CHANNEL, int)
        return max(1, min(16, value))

    def set_percussion_channel(self, channel: int) -> None:
        self._settings.setValue("general/percussion_channel", max(1, min(16, channel)))
        self._settings.sync()

    def auto_play_on_load(self) -> bool:
        return self._settings.value("playback/auto_play_on_load", self.DEFAULT_AUTO_PLAY_ON_LOAD, bool)

    def set_auto_play_on_load(self, enabled: bool) -> None:
        self._settings.setValue("playback/auto_play_on_load", bool(enabled))
        self._settings.sync()

    def playlist_auto_advance(self) -> bool:
        return self._settings.value(
            "playback/playlist_auto_advance",
            self.DEFAULT_PLAYLIST_AUTO_ADVANCE,
            bool,
        )

    def set_playlist_auto_advance(self, enabled: bool) -> None:
        self._settings.setValue("playback/playlist_auto_advance", bool(enabled))
        self._settings.sync()

    def auto_song_settings(self) -> bool:
        return self._settings.value("general/auto_song_settings", self.DEFAULT_AUTO_SONG_SETTINGS, bool)

    def set_auto_song_settings(self, enabled: bool) -> None:
        self._settings.setValue("general/auto_song_settings", bool(enabled))
        self._settings.sync()

    def qt_style(self) -> str:
        value = self._settings.value("general/qt_style", self.DEFAULT_QT_STYLE, str)
        return value or self.DEFAULT_QT_STYLE

    def set_qt_style(self, style_name: str) -> None:
        self._settings.setValue("general/qt_style", style_name or self.DEFAULT_QT_STYLE)
        self._settings.sync()

    def force_dark_mode(self) -> bool:
        return self._settings.value("general/force_dark_mode", self.DEFAULT_FORCE_DARK_MODE, bool)

    def set_force_dark_mode(self, enabled: bool) -> None:
        self._settings.setValue("general/force_dark_mode", bool(enabled))
        self._settings.sync()

    def use_internal_icon_theme(self) -> bool:
        return self._settings.value(
            "general/use_internal_icon_theme",
            self.DEFAULT_USE_INTERNAL_ICON_THEME,
            bool,
        )

    def set_use_internal_icon_theme(self, enabled: bool) -> None:
        self._settings.setValue("general/use_internal_icon_theme", bool(enabled))
        self._settings.sync()

    def solo_volume_reduction(self) -> int:
        value = self._settings.value("general/solo_volume_reduction", self.DEFAULT_SOLO_VOLUME_REDUCTION, int)
        return max(0, min(100, value))

    def set_solo_volume_reduction(self, value: int) -> None:
        self._settings.setValue("general/solo_volume_reduction", max(0, min(100, value)))
        self._settings.sync()

    def midi_reset_before_playback(self) -> bool:
        return self._settings.value(
            "general/midi_reset_before_playback",
            self.DEFAULT_MIDI_RESET_BEFORE_PLAYBACK,
            bool,
        )

    def set_midi_reset_before_playback(self, enabled: bool) -> None:
        self._settings.setValue("general/midi_reset_before_playback", bool(enabled))
        self._settings.sync()

    def pianola_color_mode(self) -> str:
        value = self._settings.value("pianola/color_mode", self.DEFAULT_PIANOLA_COLOR_MODE, str)
        return value if value in {"blue", "channel"} else self.DEFAULT_PIANOLA_COLOR_MODE

    def set_pianola_color_mode(self, mode: str) -> None:
        value = mode if mode in {"blue", "channel"} else self.DEFAULT_PIANOLA_COLOR_MODE
        self._settings.setValue("pianola/color_mode", value)
        self._settings.sync()

    def pianola_single_color(self) -> str:
        value = self._settings.value("pianola/single_color", self.DEFAULT_PIANOLA_SINGLE_COLOR, str)
        return value or self.DEFAULT_PIANOLA_SINGLE_COLOR

    def set_pianola_single_color(self, color: str) -> None:
        self._settings.setValue("pianola/single_color", color or self.DEFAULT_PIANOLA_SINGLE_COLOR)
        self._settings.sync()

    def pianola_velocity_tinting(self) -> bool:
        return self._settings.value("pianola/velocity_tinting", self.DEFAULT_PIANOLA_VELOCITY_TINTING, bool)

    def set_pianola_velocity_tinting(self, enabled: bool) -> None:
        self._settings.setValue("pianola/velocity_tinting", bool(enabled))
        self._settings.sync()

    def pianola_note_label_mode(self) -> str:
        value = self._settings.value("pianola/note_label_mode", self.DEFAULT_PIANOLA_NOTE_LABEL_MODE, str)
        return value if value in {"never", "minimal", "active", "always"} else self.DEFAULT_PIANOLA_NOTE_LABEL_MODE

    def set_pianola_note_label_mode(self, mode: str) -> None:
        value = mode if mode in {"never", "minimal", "active", "always"} else self.DEFAULT_PIANOLA_NOTE_LABEL_MODE
        self._settings.setValue("pianola/note_label_mode", value)
        self._settings.sync()

    def pianola_octave_designation(self) -> str:
        value = self._settings.value(
            "pianola/octave_designation",
            self.DEFAULT_PIANOLA_OCTAVE_DESIGNATION,
            str,
        )
        return value if value in {"scientific", "yamaha"} else self.DEFAULT_PIANOLA_OCTAVE_DESIGNATION

    def set_pianola_octave_designation(self, mode: str) -> None:
        value = mode if mode in {"scientific", "yamaha"} else self.DEFAULT_PIANOLA_OCTAVE_DESIGNATION
        self._settings.setValue("pianola/octave_designation", value)
        self._settings.sync()

    def pianola_note_font_family(self) -> str:
        value = self._settings.value("pianola/note_font_family", self.DEFAULT_PIANOLA_NOTE_FONT_FAMILY, str)
        return value or self.DEFAULT_PIANOLA_NOTE_FONT_FAMILY

    def set_pianola_note_font_family(self, family: str) -> None:
        self._settings.setValue("pianola/note_font_family", family or self.DEFAULT_PIANOLA_NOTE_FONT_FAMILY)
        self._settings.sync()

    def pianola_note_font_size(self) -> int:
        value = self._settings.value("pianola/note_font_size", self.DEFAULT_PIANOLA_NOTE_FONT_SIZE, int)
        return max(6, min(24, value))

    def set_pianola_note_font_size(self, size: int) -> None:
        self._settings.setValue("pianola/note_font_size", max(6, min(24, size)))
        self._settings.sync()

    def lyrics_font_family(self) -> str:
        value = self._settings.value("lyrics/font_family", self.DEFAULT_LYRICS_FONT_FAMILY, str)
        return value or self.DEFAULT_LYRICS_FONT_FAMILY

    def set_lyrics_font_family(self, family: str) -> None:
        self._settings.setValue("lyrics/font_family", family or self.DEFAULT_LYRICS_FONT_FAMILY)
        self._settings.sync()

    def lyrics_font_size(self) -> int:
        value = self._settings.value("lyrics/font_size", self.DEFAULT_LYRICS_FONT_SIZE, int)
        return max(6, min(48, value))

    def set_lyrics_font_size(self, size: int) -> None:
        self._settings.setValue("lyrics/font_size", max(6, min(48, size)))
        self._settings.sync()

    def lyrics_future_color(self) -> str:
        value = self._settings.value("lyrics/future_color", self.DEFAULT_LYRICS_FUTURE_COLOR, str)
        return value or self.DEFAULT_LYRICS_FUTURE_COLOR

    def set_lyrics_future_color(self, color: str) -> None:
        self._settings.setValue("lyrics/future_color", color or self.DEFAULT_LYRICS_FUTURE_COLOR)
        self._settings.sync()

    def lyrics_past_color(self) -> str:
        value = self._settings.value("lyrics/past_color", self.DEFAULT_LYRICS_PAST_COLOR, str)
        return value or self.DEFAULT_LYRICS_PAST_COLOR

    def set_lyrics_past_color(self, color: str) -> None:
        self._settings.setValue("lyrics/past_color", color or self.DEFAULT_LYRICS_PAST_COLOR)
        self._settings.sync()

    def playlist_path(self) -> Path | None:
        value = self._settings.value("playlist/path", "", str)
        if not value:
            return None
        path = Path(value)
        return path if path.exists() else None

    def set_playlist_path(self, playlist_path: str | Path) -> None:
        if playlist_path:
            self._settings.setValue("playlist/path", str(Path(playlist_path)))
        else:
            self._settings.remove("playlist/path")
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

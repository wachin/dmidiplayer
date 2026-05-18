from __future__ import annotations

import argparse
import configparser
import os
import random
import sys
from pathlib import Path

from PyQt6.QtCore import QLocale, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QCloseEvent, QDragEnterEvent, QDropEvent, QFont, QIcon, QKeySequence, QPalette
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontDialog,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QStyleFactory,
)

from drumstick_py import BackendManager, MidiEvent, MidiFileError, MidiOutputError, PianoKeyboard, read_smf
from .i18n import install_translator
from .player import SequencePlayer
from .settings import AppSettings


MIDI_FILE_SUFFIXES = {".kar", ".mid", ".midi", ".rmi"}
OPENABLE_SONG_FILE_SUFFIXES = MIDI_FILE_SUFFIXES | {".wrk"}
PLAYLIST_FILE_SUFFIXES = {".lst"}
APP_TITLE = "dmidiplayer PyQt6"
HELP_DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
ICONS_DIR = Path(__file__).resolve().parents[1] / "icons"
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
GENERAL_MIDI_PROGRAMS = (
    "Acoustic Grand Piano",
    "Bright Acoustic Piano",
    "Electric Grand Piano",
    "Honky-tonk Piano",
    "Electric Piano 1",
    "Electric Piano 2",
    "Harpsichord",
    "Clavinet",
    "Celesta",
    "Glockenspiel",
    "Music Box",
    "Vibraphone",
    "Marimba",
    "Xylophone",
    "Tubular Bells",
    "Dulcimer",
    "Drawbar Organ",
    "Percussive Organ",
    "Rock Organ",
    "Church Organ",
    "Reed Organ",
    "Accordion",
    "Harmonica",
    "Tango Accordion",
    "Acoustic Guitar (nylon)",
    "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)",
    "Electric Guitar (clean)",
    "Electric Guitar (muted)",
    "Overdriven Guitar",
    "Distortion Guitar",
    "Guitar Harmonics",
    "Acoustic Bass",
    "Electric Bass (finger)",
    "Electric Bass (pick)",
    "Fretless Bass",
    "Slap Bass 1",
    "Slap Bass 2",
    "Synth Bass 1",
    "Synth Bass 2",
    "Violin",
    "Viola",
    "Cello",
    "Contrabass",
    "Tremolo Strings",
    "Pizzicato Strings",
    "Orchestral Harp",
    "Timpani",
    "String Ensemble 1",
    "String Ensemble 2",
    "Synth Strings 1",
    "Synth Strings 2",
    "Choir Aahs",
    "Voice Oohs",
    "Synth Choir",
    "Orchestra Hit",
    "Trumpet",
    "Trombone",
    "Tuba",
    "Muted Trumpet",
    "French Horn",
    "Brass Section",
    "Synth Brass 1",
    "Synth Brass 2",
    "Soprano Sax",
    "Alto Sax",
    "Tenor Sax",
    "Baritone Sax",
    "Oboe",
    "English Horn",
    "Bassoon",
    "Clarinet",
    "Piccolo",
    "Flute",
    "Recorder",
    "Pan Flute",
    "Blown Bottle",
    "Shakuhachi",
    "Whistle",
    "Ocarina",
    "Lead 1 (square)",
    "Lead 2 (sawtooth)",
    "Lead 3 (calliope)",
    "Lead 4 (chiff)",
    "Lead 5 (charang)",
    "Lead 6 (voice)",
    "Lead 7 (fifths)",
    "Lead 8 (bass + lead)",
    "Pad 1 (new age)",
    "Pad 2 (warm)",
    "Pad 3 (polysynth)",
    "Pad 4 (choir)",
    "Pad 5 (bowed)",
    "Pad 6 (metallic)",
    "Pad 7 (halo)",
    "Pad 8 (sweep)",
    "FX 1 (rain)",
    "FX 2 (soundtrack)",
    "FX 3 (crystal)",
    "FX 4 (atmosphere)",
    "FX 5 (brightness)",
    "FX 6 (goblins)",
    "FX 7 (echoes)",
    "FX 8 (sci-fi)",
    "Sitar",
    "Banjo",
    "Shamisen",
    "Koto",
    "Kalimba",
    "Bag Pipe",
    "Fiddle",
    "Shanai",
    "Tinkle Bell",
    "Agogo",
    "Steel Drums",
    "Woodblock",
    "Taiko Drum",
    "Melodic Tom",
    "Synth Drum",
    "Reverse Cymbal",
    "Guitar Fret Noise",
    "Breath Noise",
    "Seashore",
    "Bird Tweet",
    "Telephone Ring",
    "Helicopter",
    "Applause",
    "Gunshot",
)

CHANNEL_COLOR_PALETTES = (
    ("#fee2e2", "#dc2626", "#991b1b", "#fca5a5"),
    ("#ffedd5", "#ea580c", "#9a3412", "#fdba74"),
    ("#fef3c7", "#d97706", "#92400e", "#fcd34d"),
    ("#ecfccb", "#65a30d", "#365314", "#bef264"),
    ("#dcfce7", "#16a34a", "#166534", "#86efac"),
    ("#cffafe", "#0891b2", "#155e75", "#67e8f9"),
    ("#dbeafe", "#2563eb", "#1e3a8a", "#93c5fd"),
    ("#e0e7ff", "#4f46e5", "#312e81", "#a5b4fc"),
    ("#ede9fe", "#7c3aed", "#4c1d95", "#c4b5fd"),
    ("#fae8ff", "#c026d3", "#86198f", "#e879f9"),
    ("#fce7f3", "#db2777", "#9d174d", "#f9a8d4"),
    ("#ffe4e6", "#e11d48", "#9f1239", "#fda4af"),
    ("#f3f4f6", "#4b5563", "#111827", "#d1d5db"),
    ("#ede9fe", "#6d28d9", "#581c87", "#ddd6fe"),
    ("#ecfeff", "#0f766e", "#134e4a", "#99f6e4"),
    ("#fef2f2", "#b91c1c", "#7f1d1d", "#fecaca"),
)


def gm_program_label(program: int) -> str:
    program = max(0, min(127, program))
    return f"{program}: {GENERAL_MIDI_PROGRAMS[program]}"


TEXT_EVENT_LABELS = {
    0x01: "Text",
    0x02: "Copyright",
    0x03: "Track Name",
    0x04: "Instrument",
    0x05: "Lyric",
    0x06: "Marker",
    0x07: "Cue Point",
}

LYRICS_COLOR_PRESETS = (
    ("Blue", "#2563eb"),
    ("Gray", "#6b7280"),
    ("Slate", "#9ca3af"),
    ("Green", "#16a34a"),
    ("Amber", "#d97706"),
    ("Rose", "#e11d48"),
)

PIANOLA_COLOR_PRESETS = (
    ("Blue", "#1d4ed8"),
    ("Green", "#16a34a"),
    ("Amber", "#d97706"),
    ("Rose", "#e11d48"),
    ("Violet", "#7c3aed"),
    ("Slate", "#4b5563"),
)


def single_highlight_palette(color_value: str) -> tuple[str, str, str, str, str]:
    qcolor = QColor(color_value)
    if not qcolor.isValid():
        qcolor = QColor(AppSettings.DEFAULT_PIANOLA_SINGLE_COLOR)
    white_low = qcolor.lighter(190).name()
    white_high = qcolor.name()
    black_low = qcolor.darker(115).name()
    black_high = qcolor.lighter(150).name()
    black_idle = qcolor.darker(260).name()
    return (white_low, white_high, black_low, black_high, black_idle)


def available_qt_styles() -> list[str]:
    return sorted(QStyleFactory.keys(), key=str.casefold)


def dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f9fafb"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f9fafb"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f9fafb"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#374151"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f9fafb"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#60a5fa"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#9ca3af"))
    return palette


def bundled_icon(icon_name: str) -> QIcon:
    for suffix in (".png", ".svg", ".ico"):
        path = ICONS_DIR / f"{icon_name}{suffix}"
        if path.exists():
            return QIcon(str(path))
    return QIcon()


ACTION_ICONS = {
    "open_action": ("document-open", "document-open"),
    "open_playlist_action": ("document-open", "view-media-playlist"),
    "save_playlist_action": ("document-save", "document-save"),
    "save_playlist_as_action": ("document-save", "document-save"),
    "load_song_settings_action": ("document-open", "document-open"),
    "save_song_settings_action": ("document-save", "document-save"),
    "exit_action": ("system-shutdown", "system-shutdown"),
    "clear_recent_action": ("edit-delete", "edit-delete"),
    "refresh_midi_action": ("view-refresh", "midi"),
    "connect_midi_action": ("audio-midi", "audio-midi"),
    "disconnect_midi_action": ("window-close", "window-close"),
    "preferences_action": ("settings", "settings"),
    "remove_selected_action": ("edit-delete", "list-remove"),
    "move_up_action": ("go-up", "go-up"),
    "move_down_action": ("go-down", "go-down"),
    "sort_playlist_action": ("view-sort-ascending", "view-media-playlist"),
    "clear_playlist_action": ("edit-clear", "edit-clear"),
    "help_contents_action": ("help-contents", "help-contents"),
    "user_guide_action": ("viewhtml", "viewhtml"),
    "about_action": ("help-about", "help-about"),
    "previous_action": ("media-skip-backward", "media-skip-backward"),
    "play_action": ("media-playback-start", "media-playback-start"),
    "pause_action": ("media-playback-pause", "media-playback-pause"),
    "stop_action": ("media-playback-stop", "media-playback-stop"),
    "next_action": ("media-skip-forward", "media-skip-forward"),
    "previous_bar_action": ("media-seek-backward", "media-seek-backward"),
    "next_bar_action": ("media-seek-forward", "media-seek-forward"),
    "jump_bar_action": ("go-jump", "go-jump"),
    "repeat_playlist_action": ("media-playlist-repeat", "media-playlist-repeat"),
    "shuffle_playlist_action": ("media-playlist-shuffle", "media-playlist-shuffle"),
    "channels_action": ("audio-midi", "audio-midi"),
    "pianola_action": ("application-menu", "application-menu"),
    "lyrics_action": ("view-media-lyrics", "view-media-lyrics"),
}

TOOLBAR_BUTTON_STYLES = {
    "icon_only": Qt.ToolButtonStyle.ToolButtonIconOnly,
    "text_only": Qt.ToolButtonStyle.ToolButtonTextOnly,
    "text_beside": Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
    "text_under": Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
    "follow_style": Qt.ToolButtonStyle.ToolButtonFollowStyle,
}

DEFAULT_TOOLBAR_ACTION_ORDER = list(AppSettings.DEFAULT_TOOLBAR_ACTIONS)


class PreferencesDialog(QDialog):
    def __init__(self, parent: QWidget | None, settings: AppSettings) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("Preferences"))

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("preferences_tabs")
        layout.addWidget(self.tabs)

        general_tab = QWidget(self.tabs)
        general_tab.setObjectName("general_preferences_tab")
        general_form = QFormLayout(general_tab)
        self.general_percussion_channel = QSpinBox(general_tab)
        self.general_percussion_channel.setObjectName("general_percussion_channel")
        self.general_percussion_channel.setRange(1, 16)
        general_form.addRow(self.tr("Percussion channel:"), self.general_percussion_channel)

        self.general_solo_volume_reduction = QSpinBox(general_tab)
        self.general_solo_volume_reduction.setObjectName("general_solo_volume_reduction")
        self.general_solo_volume_reduction.setRange(0, 100)
        self.general_solo_volume_reduction.setSuffix("%")
        general_form.addRow(self.tr("Solo volume reduction:"), self.general_solo_volume_reduction)

        self.general_auto_play_on_load = QCheckBox(self.tr("Auto-play after loading a file"), general_tab)
        self.general_auto_play_on_load.setObjectName("general_auto_play_on_load")
        general_form.addRow("", self.general_auto_play_on_load)

        self.general_playlist_auto_advance = QCheckBox(self.tr("Auto-advance to the next playlist item"), general_tab)
        self.general_playlist_auto_advance.setObjectName("general_playlist_auto_advance")
        general_form.addRow("", self.general_playlist_auto_advance)

        self.general_auto_song_settings = QCheckBox(self.tr("Automatically load and save song settings"), general_tab)
        self.general_auto_song_settings.setObjectName("general_auto_song_settings")
        general_form.addRow("", self.general_auto_song_settings)

        self.general_force_dark_mode = QCheckBox(self.tr("Force dark mode"), general_tab)
        self.general_force_dark_mode.setObjectName("general_force_dark_mode")
        general_form.addRow("", self.general_force_dark_mode)

        self.general_use_internal_icon_theme = QCheckBox(self.tr("Use internal icon theme"), general_tab)
        self.general_use_internal_icon_theme.setObjectName("general_use_internal_icon_theme")
        general_form.addRow("", self.general_use_internal_icon_theme)

        self.general_qt_style = QComboBox(general_tab)
        self.general_qt_style.setObjectName("general_qt_style")
        self.general_qt_style.addItem(self.tr("System"), "system")
        for style_name in available_qt_styles():
            self.general_qt_style.addItem(style_name, style_name)
        general_form.addRow(self.tr("Qt Widgets style:"), self.general_qt_style)

        self.general_midi_reset_before_playback = QCheckBox(self.tr("Send GM reset before playback"), general_tab)
        self.general_midi_reset_before_playback.setObjectName("general_midi_reset_before_playback")
        general_form.addRow("", self.general_midi_reset_before_playback)
        self.tabs.addTab(general_tab, self.tr("General"))

        lyrics_tab = QWidget(self.tabs)
        lyrics_tab.setObjectName("lyrics_preferences_tab")
        lyrics_form = QFormLayout(lyrics_tab)
        self.lyrics_font_family = QFontComboBox(lyrics_tab)
        self.lyrics_font_family.setObjectName("lyrics_font_family")
        lyrics_form.addRow(self.tr("Font:"), self.lyrics_font_family)
        self.lyrics_font_size = QSpinBox(lyrics_tab)
        self.lyrics_font_size.setObjectName("lyrics_font_size")
        self.lyrics_font_size.setRange(6, 48)
        lyrics_form.addRow(self.tr("Font size:"), self.lyrics_font_size)
        self.lyrics_future_color = QComboBox(lyrics_tab)
        self.lyrics_future_color.setObjectName("lyrics_future_color")
        self.lyrics_past_color = QComboBox(lyrics_tab)
        self.lyrics_past_color.setObjectName("lyrics_past_color")
        for label, value in LYRICS_COLOR_PRESETS:
            self.lyrics_future_color.addItem(self.tr(label), value)
            self.lyrics_past_color.addItem(self.tr(label), value)
        lyrics_form.addRow(self.tr("Future text color:"), self.lyrics_future_color)
        lyrics_form.addRow(self.tr("Past text color:"), self.lyrics_past_color)
        self.tabs.addTab(lyrics_tab, self.tr("Lyrics"))

        pianola_tab = QWidget(self.tabs)
        pianola_tab.setObjectName("pianola_preferences_tab")
        pianola_form = QFormLayout(pianola_tab)
        self.pianola_color_mode = QComboBox(pianola_tab)
        self.pianola_color_mode.setObjectName("pianola_color_mode")
        self.pianola_color_mode.addItem(self.tr("Single color"), "blue")
        self.pianola_color_mode.addItem(self.tr("By channel"), "channel")
        pianola_form.addRow(self.tr("Highlight colors:"), self.pianola_color_mode)
        self.pianola_single_color = QComboBox(pianola_tab)
        self.pianola_single_color.setObjectName("pianola_single_color")
        for label, value in PIANOLA_COLOR_PRESETS:
            self.pianola_single_color.addItem(self.tr(label), value)
        pianola_form.addRow(self.tr("Single highlight color:"), self.pianola_single_color)
        self.pianola_velocity_tinting = QCheckBox(self.tr("Use note velocity for highlight strength"), pianola_tab)
        self.pianola_velocity_tinting.setObjectName("pianola_velocity_tinting")
        pianola_form.addRow("", self.pianola_velocity_tinting)

        self.pianola_note_label_mode = QComboBox(pianola_tab)
        self.pianola_note_label_mode.setObjectName("pianola_note_label_mode")
        self.pianola_note_label_mode.addItem(self.tr("Never"), "never")
        self.pianola_note_label_mode.addItem(self.tr("Minimal"), "minimal")
        self.pianola_note_label_mode.addItem(self.tr("When active"), "active")
        self.pianola_note_label_mode.addItem(self.tr("Always"), "always")
        pianola_form.addRow(self.tr("Note names:"), self.pianola_note_label_mode)

        self.pianola_note_font_family = QFontComboBox(pianola_tab)
        self.pianola_note_font_family.setObjectName("pianola_note_font_family")
        pianola_form.addRow(self.tr("Note-name font:"), self.pianola_note_font_family)
        self.pianola_note_font_size = QSpinBox(pianola_tab)
        self.pianola_note_font_size.setObjectName("pianola_note_font_size")
        self.pianola_note_font_size.setRange(6, 24)
        pianola_form.addRow(self.tr("Note-name size:"), self.pianola_note_font_size)

        self.pianola_octave_designation = QComboBox(pianola_tab)
        self.pianola_octave_designation.setObjectName("pianola_octave_designation")
        self.pianola_octave_designation.addItem(self.tr("Scientific"), "scientific")
        self.pianola_octave_designation.addItem(self.tr("Yamaha"), "yamaha")
        pianola_form.addRow(self.tr("Octave designation:"), self.pianola_octave_designation)
        self.tabs.addTab(pianola_tab, self.tr("Player Piano"))

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        restore_button = self.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if restore_button is not None:
            restore_button.clicked.connect(self.restore_defaults)
        layout.addWidget(self.buttons)

        self.load_from_settings()
        self.resize(420, 220)

    def load_from_settings(self) -> None:
        self.general_percussion_channel.setValue(self._settings.percussion_channel())
        self.general_solo_volume_reduction.setValue(self._settings.solo_volume_reduction())
        self.general_auto_play_on_load.setChecked(self._settings.auto_play_on_load())
        self.general_playlist_auto_advance.setChecked(self._settings.playlist_auto_advance())
        self.general_auto_song_settings.setChecked(self._settings.auto_song_settings())
        self.general_force_dark_mode.setChecked(self._settings.force_dark_mode())
        self.general_use_internal_icon_theme.setChecked(self._settings.use_internal_icon_theme())
        self.general_qt_style.setCurrentIndex(max(0, self.general_qt_style.findData(self._settings.qt_style())))
        self.general_midi_reset_before_playback.setChecked(self._settings.midi_reset_before_playback())
        self.lyrics_font_family.setCurrentFont(QFont(self._settings.lyrics_font_family()))
        self.lyrics_font_size.setValue(self._settings.lyrics_font_size())
        self.lyrics_future_color.setCurrentIndex(
            self.lyrics_future_color.findData(self._settings.lyrics_future_color())
        )
        self.lyrics_past_color.setCurrentIndex(self.lyrics_past_color.findData(self._settings.lyrics_past_color()))
        self.pianola_color_mode.setCurrentIndex(self.pianola_color_mode.findData(self._settings.pianola_color_mode()))
        self.pianola_single_color.setCurrentIndex(
            self.pianola_single_color.findData(self._settings.pianola_single_color())
        )
        self.pianola_velocity_tinting.setChecked(self._settings.pianola_velocity_tinting())
        self.pianola_note_label_mode.setCurrentIndex(
            self.pianola_note_label_mode.findData(self._settings.pianola_note_label_mode())
        )
        self.pianola_note_font_family.setCurrentFont(QFont(self._settings.pianola_note_font_family()))
        self.pianola_note_font_size.setValue(self._settings.pianola_note_font_size())
        self.pianola_octave_designation.setCurrentIndex(
            self.pianola_octave_designation.findData(self._settings.pianola_octave_designation())
        )

    def restore_defaults(self) -> None:
        self.general_percussion_channel.setValue(AppSettings.DEFAULT_PERCUSSION_CHANNEL)
        self.general_solo_volume_reduction.setValue(AppSettings.DEFAULT_SOLO_VOLUME_REDUCTION)
        self.general_auto_play_on_load.setChecked(AppSettings.DEFAULT_AUTO_PLAY_ON_LOAD)
        self.general_playlist_auto_advance.setChecked(AppSettings.DEFAULT_PLAYLIST_AUTO_ADVANCE)
        self.general_auto_song_settings.setChecked(AppSettings.DEFAULT_AUTO_SONG_SETTINGS)
        self.general_force_dark_mode.setChecked(AppSettings.DEFAULT_FORCE_DARK_MODE)
        self.general_use_internal_icon_theme.setChecked(AppSettings.DEFAULT_USE_INTERNAL_ICON_THEME)
        self.general_qt_style.setCurrentIndex(max(0, self.general_qt_style.findData(AppSettings.DEFAULT_QT_STYLE)))
        self.general_midi_reset_before_playback.setChecked(AppSettings.DEFAULT_MIDI_RESET_BEFORE_PLAYBACK)
        self.lyrics_font_family.setCurrentFont(QFont(AppSettings.DEFAULT_LYRICS_FONT_FAMILY))
        self.lyrics_font_size.setValue(AppSettings.DEFAULT_LYRICS_FONT_SIZE)
        self.lyrics_future_color.setCurrentIndex(
            self.lyrics_future_color.findData(AppSettings.DEFAULT_LYRICS_FUTURE_COLOR)
        )
        self.lyrics_past_color.setCurrentIndex(self.lyrics_past_color.findData(AppSettings.DEFAULT_LYRICS_PAST_COLOR))
        self.pianola_color_mode.setCurrentIndex(
            self.pianola_color_mode.findData(AppSettings.DEFAULT_PIANOLA_COLOR_MODE)
        )
        self.pianola_single_color.setCurrentIndex(
            self.pianola_single_color.findData(AppSettings.DEFAULT_PIANOLA_SINGLE_COLOR)
        )
        self.pianola_velocity_tinting.setChecked(AppSettings.DEFAULT_PIANOLA_VELOCITY_TINTING)
        self.pianola_note_label_mode.setCurrentIndex(
            self.pianola_note_label_mode.findData(AppSettings.DEFAULT_PIANOLA_NOTE_LABEL_MODE)
        )
        self.pianola_note_font_family.setCurrentFont(QFont(AppSettings.DEFAULT_PIANOLA_NOTE_FONT_FAMILY))
        self.pianola_note_font_size.setValue(AppSettings.DEFAULT_PIANOLA_NOTE_FONT_SIZE)
        self.pianola_octave_designation.setCurrentIndex(
            self.pianola_octave_designation.findData(AppSettings.DEFAULT_PIANOLA_OCTAVE_DESIGNATION)
        )

    def preferences(self) -> tuple[object, ...]:
        return (
            self.general_percussion_channel.value(),
            self.general_solo_volume_reduction.value(),
            self.general_auto_play_on_load.isChecked(),
            self.general_playlist_auto_advance.isChecked(),
            self.general_auto_song_settings.isChecked(),
            self.general_force_dark_mode.isChecked(),
            self.general_use_internal_icon_theme.isChecked(),
            str(self.general_qt_style.currentData()),
            self.general_midi_reset_before_playback.isChecked(),
            self.lyrics_font_family.currentFont().family(),
            self.lyrics_font_size.value(),
            str(self.lyrics_future_color.currentData()),
            str(self.lyrics_past_color.currentData()),
            str(self.pianola_color_mode.currentData()),
            str(self.pianola_single_color.currentData()),
            self.pianola_velocity_tinting.isChecked(),
            str(self.pianola_note_label_mode.currentData()),
            self.pianola_note_font_family.currentFont().family(),
            self.pianola_note_font_size.value(),
            str(self.pianola_octave_designation.currentData()),
        )


class ToolbarCustomizationDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        available_actions: list[tuple[str, str]],
        selected_action_ids: list[str],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Customize Toolbar"))
        self._available_actions = {action_id: label for action_id, label in available_actions}

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row)

        left_column = QVBoxLayout()
        left_column.addWidget(QLabel(self.tr("Available Actions"), self))
        self.available_list = QListWidget(self)
        self.available_list.setObjectName("toolbar_available_actions")
        left_column.addWidget(self.available_list)
        row.addLayout(left_column)

        buttons_column = QVBoxLayout()
        buttons_column.addStretch(1)
        self.add_button = QPushButton(self.tr("Add"), self)
        self.add_button.setObjectName("toolbar_add_action")
        self.add_button.clicked.connect(self.add_selected_action)
        buttons_column.addWidget(self.add_button)
        self.remove_button = QPushButton(self.tr("Remove"), self)
        self.remove_button.setObjectName("toolbar_remove_action")
        self.remove_button.clicked.connect(self.remove_selected_action)
        buttons_column.addWidget(self.remove_button)
        buttons_column.addStretch(1)
        row.addLayout(buttons_column)

        right_column = QVBoxLayout()
        right_column.addWidget(QLabel(self.tr("Selected Actions"), self))
        self.selected_list = QListWidget(self)
        self.selected_list.setObjectName("toolbar_selected_actions")
        right_column.addWidget(self.selected_list)
        move_row = QHBoxLayout()
        self.move_up_button = QPushButton(self.tr("Move Up"), self)
        self.move_up_button.setObjectName("toolbar_move_up_action")
        self.move_up_button.clicked.connect(lambda: self.move_selected_action(-1))
        move_row.addWidget(self.move_up_button)
        self.move_down_button = QPushButton(self.tr("Move Down"), self)
        self.move_down_button.setObjectName("toolbar_move_down_action")
        self.move_down_button.clicked.connect(lambda: self.move_selected_action(1))
        move_row.addWidget(self.move_down_button)
        right_column.addLayout(move_row)
        row.addLayout(right_column)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self._populate_lists(selected_action_ids)
        self.resize(560, 360)

    def _populate_lists(self, selected_action_ids: list[str]) -> None:
        selected = [action_id for action_id in selected_action_ids if action_id in self._available_actions]
        remaining = [action_id for action_id in self._available_actions if action_id not in selected]
        self.available_list.clear()
        self.selected_list.clear()
        for action_id in remaining:
            item = QListWidgetItem(self._available_actions[action_id])
            item.setData(Qt.ItemDataRole.UserRole, action_id)
            self.available_list.addItem(item)
        for action_id in selected:
            item = QListWidgetItem(self._available_actions[action_id])
            item.setData(Qt.ItemDataRole.UserRole, action_id)
            self.selected_list.addItem(item)

    def add_selected_action(self) -> None:
        row = self.available_list.currentRow()
        if row < 0:
            return
        item = self.available_list.takeItem(row)
        self.selected_list.addItem(item)
        self.selected_list.setCurrentItem(item)

    def remove_selected_action(self) -> None:
        row = self.selected_list.currentRow()
        if row < 0:
            return
        item = self.selected_list.takeItem(row)
        self.available_list.addItem(item)
        self.available_list.setCurrentItem(item)

    def move_selected_action(self, delta: int) -> None:
        row = self.selected_list.currentRow()
        if row < 0:
            return
        target = row + delta
        if target < 0 or target >= self.selected_list.count():
            return
        item = self.selected_list.takeItem(row)
        self.selected_list.insertItem(target, item)
        self.selected_list.setCurrentItem(item)

    def selected_action_ids(self) -> list[str]:
        result: list[str] = []
        for index in range(self.selected_list.count()):
            item = self.selected_list.item(index)
            action_id = item.data(Qt.ItemDataRole.UserRole)
            if action_id:
                result.append(str(action_id))
        return result


class PlaylistDialog(QDialog):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.window = window
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        layout.addLayout(row, 1)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("playlist_dialog_list")
        self.list_widget.currentRowChanged.connect(self._row_changed)
        self.list_widget.itemDoubleClicked.connect(self._load_selected_item)
        row.addWidget(self.list_widget, 1)

        button_column = QVBoxLayout()
        row.addLayout(button_column)
        self.add_button = QPushButton(self.tr("Add"), self)
        self.add_button.setObjectName("playlist_dialog_add_button")
        self.add_button.clicked.connect(self.window.open_files)
        button_column.addWidget(self.add_button)
        self.remove_button = QPushButton(self.tr("Remove"), self)
        self.remove_button.setObjectName("playlist_dialog_remove_button")
        self.remove_button.clicked.connect(self.window.remove_selected_action.trigger)
        button_column.addWidget(self.remove_button)
        self.move_up_button = QPushButton(self.tr("Move Up"), self)
        self.move_up_button.setObjectName("playlist_dialog_move_up_button")
        self.move_up_button.clicked.connect(self.window.move_up_action.trigger)
        button_column.addWidget(self.move_up_button)
        self.move_down_button = QPushButton(self.tr("Move Down"), self)
        self.move_down_button.setObjectName("playlist_dialog_move_down_button")
        self.move_down_button.clicked.connect(self.window.move_down_action.trigger)
        button_column.addWidget(self.move_down_button)
        self.randomize_button = QPushButton(self.tr("Randomize"), self)
        self.randomize_button.setObjectName("playlist_dialog_randomize_button")
        self.randomize_button.clicked.connect(self.window._randomize_playlist)
        button_column.addWidget(self.randomize_button)
        self.clear_button = QPushButton(self.tr("Clear"), self)
        self.clear_button.setObjectName("playlist_dialog_clear_button")
        self.clear_button.clicked.connect(self.window.clear_playlist_action.trigger)
        button_column.addWidget(self.clear_button)
        button_column.addStretch(1)

        bottom_row = QHBoxLayout()
        self.accept_button = QPushButton(self.tr("Accept"), self)
        self.accept_button.setObjectName("playlist_dialog_accept_button")
        self.accept_button.clicked.connect(self.accept)
        bottom_row.addWidget(self.accept_button)
        self.open_playlist_button = QPushButton(self.tr("Open"), self)
        self.open_playlist_button.setObjectName("playlist_dialog_open_playlist_button")
        self.open_playlist_button.clicked.connect(self.window.open_playlist_action.trigger)
        bottom_row.addWidget(self.open_playlist_button)
        self.save_as_button = QPushButton(self.tr("Save As"), self)
        self.save_as_button.setObjectName("playlist_dialog_save_as_button")
        self.save_as_button.clicked.connect(self.window.save_playlist_as_action.trigger)
        bottom_row.addWidget(self.save_as_button)
        self.cancel_button = QPushButton(self.tr("Cancel"), self)
        self.cancel_button.setObjectName("playlist_dialog_cancel_button")
        self.cancel_button.clicked.connect(self.reject)
        bottom_row.addWidget(self.cancel_button)
        layout.addLayout(bottom_row)

        self.refresh_from_window()
        self.resize(560, 420)

    def refresh_from_window(self) -> None:
        current_row = self.window.playlist.currentRow()
        with QSignalBlocker(self.list_widget):
            self.list_widget.clear()
            for row in range(self.window.playlist.count()):
                source_item = self.window.playlist.item(row)
                if source_item is None:
                    continue
                item = QListWidgetItem(source_item.text())
                item.setData(Qt.ItemDataRole.UserRole, source_item.data(Qt.ItemDataRole.UserRole))
                item.setToolTip(source_item.toolTip())
                self.list_widget.addItem(item)
            self.list_widget.setCurrentRow(current_row)
        self.setWindowTitle(self.window._playlist_dialog_title())
        self._update_button_state()

    def _row_changed(self, row: int) -> None:
        if row != self.window.playlist.currentRow():
            self.window.playlist.setCurrentRow(row)
        self._update_button_state()

    def _load_current_row(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.window._load_playlist_row(row)

    def _load_selected_item(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row >= 0:
            self.window._load_playlist_row(row)

    def _update_button_state(self) -> None:
        self.remove_button.setEnabled(self.window.remove_selected_action.isEnabled())
        self.accept_button.setEnabled(True)
        self.move_up_button.setEnabled(self.window.move_up_action.isEnabled())
        self.move_down_button.setEnabled(self.window.move_down_action.isEnabled())
        self.randomize_button.setEnabled(self.window.playlist.count() > 1)
        self.clear_button.setEnabled(self.window.clear_playlist_action.isEnabled())
        self.save_as_button.setEnabled(self.window.save_playlist_as_action.isEnabled())


class RhythmView(QWidget):
    MAX_BEATS = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rhythm_view")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.summary_label = QLabel(self.tr("Rhythm: 4/4 - Bar 1 Beat 1 - 120 BPM"), self)
        self.summary_label.setObjectName("rhythm_summary_label")
        layout.addWidget(self.summary_label)

        beats_row = QWidget(self)
        beats_row.setObjectName("rhythm_beats_row")
        beats_layout = QHBoxLayout(beats_row)
        beats_layout.setContentsMargins(0, 0, 0, 0)
        beats_layout.setSpacing(4)
        self.beat_labels: list[QLabel] = []
        for index in range(self.MAX_BEATS):
            label = QLabel(str(index + 1), beats_row)
            label.setObjectName(f"rhythm_beat_{index + 1}")
            label.setMinimumWidth(24)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFrameShape(QFrame.Shape.Box)
            beats_layout.addWidget(label)
            self.beat_labels.append(label)
        beats_layout.addStretch(1)
        layout.addWidget(beats_row)

        self.update_state(4, 4, 1, 1, 120.0)

    def update_state(self, numerator: int, denominator: int, bar: int, beat: int, bpm: float) -> None:
        visible_beats = max(1, min(self.MAX_BEATS, numerator))
        current_beat = max(1, min(visible_beats, beat))
        self.summary_label.setText(
            self.tr("Rhythm: {numerator}/{denominator} - Bar {bar} Beat {beat} - {bpm:.0f} BPM").format(
                numerator=numerator,
                denominator=denominator,
                bar=bar,
                beat=current_beat,
                bpm=bpm,
            )
        )
        for index, label in enumerate(self.beat_labels):
            beat_number = index + 1
            is_visible = beat_number <= visible_beats
            label.setVisible(is_visible)
            if not is_visible:
                continue
            marker = "X" if beat_number == current_beat else "-"
            label.setText(f"{beat_number}:{marker}")

    def clear(self) -> None:
        self.update_state(4, 4, 1, 1, 120.0)


class ChannelsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("MIDI Channels"))
        self.channel_rows: dict[int, int] = {}
        self._label_changed_callback: object | None = None
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 7, self)
        self.table.setObjectName("channels_table")
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Channel"),
                self.tr("Label"),
                self.tr("Mute"),
                self.tr("Solo"),
                self.tr("Level"),
                self.tr("Lock"),
                self.tr("Program"),
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)
        self.resize(640, 320)

    def set_channels(
        self,
        channels: list[int],
        muted_channels: set[int] | None = None,
        solo_channels: set[int] | None = None,
        channel_programs: dict[int, int] | None = None,
        locked_channels: set[int] | None = None,
        channel_volumes: dict[int, int] | None = None,
        channel_labels: dict[int, str] | None = None,
        label_changed: object | None = None,
        mute_changed: object | None = None,
        solo_changed: object | None = None,
        program_changed: object | None = None,
        lock_changed: object | None = None,
        volume_changed: object | None = None,
    ) -> None:
        muted_channels = muted_channels or set()
        solo_channels = solo_channels or set()
        channel_programs = channel_programs or {}
        locked_channels = locked_channels or set()
        channel_volumes = channel_volumes or {}
        channel_labels = channel_labels or {}
        self._label_changed_callback = label_changed
        with QSignalBlocker(self.table):
            self.table.setRowCount(0)
            self.channel_rows.clear()
            for row, channel in enumerate(channels):
                self.table.insertRow(row)
                channel_item = QTableWidgetItem(str(channel + 1))
                channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, channel_item)
                label_edit = QLineEdit(
                    channel_labels.get(channel, self.tr("Channel {number}").format(number=channel + 1)),
                    self.table,
                )
                label_edit.setObjectName(f"channel_label_{channel + 1}")
                if label_changed is not None:
                    label_edit.editingFinished.connect(
                        lambda ch=channel, editor=label_edit: label_changed(ch, editor.text())
                    )
                self.table.setCellWidget(row, 1, label_edit)
                mute_checkbox = QCheckBox(self.table)
                mute_checkbox.setObjectName(f"channel_mute_{channel + 1}")
                mute_checkbox.setChecked(channel in muted_channels)
                mute_checkbox.setStyleSheet("QCheckBox::indicator:checked { background-color: #7f1d1d; border: 1px solid #7f1d1d; }")
                if mute_changed is not None:
                    mute_checkbox.toggled.connect(lambda checked, ch=channel: mute_changed(ch, checked))
                self.table.setCellWidget(row, 2, mute_checkbox)
                solo_checkbox = QCheckBox(self.table)
                solo_checkbox.setObjectName(f"channel_solo_{channel + 1}")
                solo_checkbox.setChecked(channel in solo_channels)
                solo_checkbox.setStyleSheet("QCheckBox::indicator:checked { background-color: #166534; border: 1px solid #166534; }")
                if solo_changed is not None:
                    solo_checkbox.toggled.connect(lambda checked, ch=channel: solo_changed(ch, checked))
                self.table.setCellWidget(row, 3, solo_checkbox)
                level_widget = QWidget(self.table)
                level_widget.setObjectName(f"channel_level_widget_{channel + 1}")
                level_layout = QGridLayout(level_widget)
                level_layout.setContentsMargins(0, 0, 0, 0)
                level_layout.setHorizontalSpacing(0)
                level_layout.setVerticalSpacing(0)
                level = QProgressBar(level_widget)
                level.setObjectName(f"channel_level_bar_{channel + 1}")
                level.setRange(0, 127)
                level.setValue(0)
                level.setTextVisible(False)
                level.setStyleSheet(
                    "QProgressBar { border: 1px solid #4b5563; background: #111827; } "
                    "QProgressBar::chunk { background-color: #22c55e; }"
                )
                level_slider = QSlider(Qt.Orientation.Horizontal, level_widget)
                level_slider.setObjectName(f"channel_volume_slider_{channel + 1}")
                level_slider.setRange(0, 200)
                level_slider.setValue(channel_volumes.get(channel, 100))
                level_slider.setStyleSheet("QSlider { background: transparent; }")
                if volume_changed is not None:
                    level_slider.valueChanged.connect(lambda value, ch=channel: volume_changed(ch, value))
                level_layout.addWidget(level, 0, 0)
                level_layout.addWidget(level_slider, 0, 0)
                self.table.setCellWidget(row, 4, level_widget)
                lock_checkbox = QCheckBox(self.table)
                lock_checkbox.setObjectName(f"channel_lock_{channel + 1}")
                lock_checkbox.setChecked(channel in locked_channels)
                if lock_changed is not None:
                    lock_checkbox.toggled.connect(lambda checked, ch=channel: lock_changed(ch, checked))
                self.table.setCellWidget(row, 5, lock_checkbox)
                program_combo = QComboBox(self.table)
                program_combo.setObjectName(f"channel_program_{channel + 1}")
                for program in range(128):
                    program_combo.addItem(gm_program_label(program), program)
                program_combo.setCurrentIndex(channel_programs.get(channel, 0))
                if program_changed is not None:
                    program_combo.currentIndexChanged.connect(lambda value, ch=channel: program_changed(ch, value))
                self.table.setCellWidget(row, 6, program_combo)
                self.channel_rows[channel] = row
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(6, 220)

    def clear_levels(self) -> None:
        for row in self.channel_rows.values():
            level_widget = self.table.cellWidget(row, 4)
            level = level_widget.findChild(QProgressBar) if isinstance(level_widget, QWidget) else None
            if isinstance(level, QProgressBar):
                level.setValue(0)

    def set_channel_level(self, channel: int, value: int) -> None:
        row = self.channel_rows.get(channel)
        if row is None:
            return
        level_widget = self.table.cellWidget(row, 4)
        level = level_widget.findChild(QProgressBar) if isinstance(level_widget, QWidget) else None
        if isinstance(level, QProgressBar):
            level.setValue(max(0, min(127, value)))


class PianolaDialog(QDialog):
    trackVisibilityChanged = pyqtSignal(int, bool)
    allTracksVisibilityChanged = pyqtSignal(bool)
    rangeModeChanged = pyqtSignal(str)
    noteLabelModeChanged = pyqtSignal(str)
    colorModeChanged = pyqtSignal(str)
    octaveDesignationChanged = pyqtSignal(str)
    manualNoteOn = pyqtSignal(int, int, int)
    manualNoteOff = pyqtSignal(int, int)
    TRACKS_PER_TAB = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Piano Player"))
        self._track_keyboards: dict[int, PianoKeyboard] = {}
        self._track_channels: dict[int, set[int]] = {}
        self._track_visibility: dict[int, QCheckBox] = {}
        self._track_keyboard_containers: dict[int, QWidget] = {}
        self._track_note_ranges: dict[int, tuple[int, int]] = {}
        self._track_primary_channels: dict[int, int | None] = {}
        self._range_mode = "exact"
        self._note_label_mode = "never"
        self._color_mode = "blue"
        self._single_highlight_color = AppSettings.DEFAULT_PIANOLA_SINGLE_COLOR
        self._velocity_tinting = AppSettings.DEFAULT_PIANOLA_VELOCITY_TINTING
        self._octave_designation = "scientific"
        self._note_label_font = QFont("Sans Serif", 8)
        layout = QVBoxLayout(self)
        button_row = QHBoxLayout()
        button_row.addWidget(QLabel(self.tr("Range:"), self))
        self.range_mode_combo = QComboBox(self)
        self.range_mode_combo.setObjectName("pianola_range_mode_combo")
        self.range_mode_combo.addItem(self.tr("Exact"), "exact")
        self.range_mode_combo.addItem(self.tr("Used octaves"), "octaves")
        self.range_mode_combo.currentIndexChanged.connect(self._range_mode_changed)
        button_row.addWidget(self.range_mode_combo)
        button_row.addWidget(QLabel(self.tr("Labels:"), self))
        self.note_labels_combo = QComboBox(self)
        self.note_labels_combo.setObjectName("pianola_note_labels_combo")
        self.note_labels_combo.addItem(self.tr("Never"), "never")
        self.note_labels_combo.addItem(self.tr("Minimal"), "minimal")
        self.note_labels_combo.addItem(self.tr("When active"), "active")
        self.note_labels_combo.addItem(self.tr("Always"), "always")
        self.note_labels_combo.currentIndexChanged.connect(self._note_label_mode_changed)
        button_row.addWidget(self.note_labels_combo)
        button_row.addWidget(QLabel(self.tr("Octaves:"), self))
        self.octave_designation_combo = QComboBox(self)
        self.octave_designation_combo.setObjectName("pianola_octave_designation_combo")
        self.octave_designation_combo.addItem(self.tr("Scientific"), "scientific")
        self.octave_designation_combo.addItem(self.tr("Yamaha"), "yamaha")
        self.octave_designation_combo.currentIndexChanged.connect(self._octave_designation_changed)
        button_row.addWidget(self.octave_designation_combo)
        button_row.addWidget(QLabel(self.tr("Colors:"), self))
        self.color_mode_combo = QComboBox(self)
        self.color_mode_combo.setObjectName("pianola_color_mode_combo")
        self.color_mode_combo.addItem(self.tr("Single color"), "blue")
        self.color_mode_combo.addItem(self.tr("By channel"), "channel")
        self.color_mode_combo.currentIndexChanged.connect(self._color_mode_changed)
        button_row.addWidget(self.color_mode_combo)
        button_row.addStretch(1)
        self.show_all_button = QPushButton(self.tr("Show All"), self)
        self.show_all_button.setObjectName("pianola_show_all_button")
        self.show_all_button.clicked.connect(self.show_all_tracks)
        button_row.addWidget(self.show_all_button)
        self.hide_all_button = QPushButton(self.tr("Hide All"), self)
        self.hide_all_button.setObjectName("pianola_hide_all_button")
        self.hide_all_button.clicked.connect(self.hide_all_tracks)
        button_row.addWidget(self.hide_all_button)
        self.fullscreen_button = QPushButton(self.tr("Fullscreen"), self)
        self.fullscreen_button.setObjectName("pianola_fullscreen_button")
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.toggled.connect(self.set_fullscreen_enabled)
        button_row.addWidget(self.fullscreen_button)
        layout.addLayout(button_row)
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("pianola_tabs")
        layout.addWidget(self.tabs)
        self.resize(780, 520)

    def set_display_preferences(
        self,
        color_mode: str,
        single_highlight_color: str,
        velocity_tinting: bool,
        note_label_mode: str,
        note_font_family: str,
        note_font_size: int,
        octave_designation: str,
    ) -> None:
        with QSignalBlocker(self.color_mode_combo):
            index = self.color_mode_combo.findData(color_mode)
            self.color_mode_combo.setCurrentIndex(max(0, index))
        self._color_mode = color_mode if color_mode in {"blue", "channel"} else "blue"
        self._single_highlight_color = single_highlight_color or AppSettings.DEFAULT_PIANOLA_SINGLE_COLOR
        self._velocity_tinting = bool(velocity_tinting)
        with QSignalBlocker(self.note_labels_combo):
            index = self.note_labels_combo.findData(note_label_mode)
            self.note_labels_combo.setCurrentIndex(max(0, index))
        self._note_label_mode = note_label_mode if note_label_mode in {"never", "minimal", "active", "always"} else "never"
        self._note_label_font = QFont(note_font_family, max(6, min(24, note_font_size)))
        with QSignalBlocker(self.octave_designation_combo):
            index = self.octave_designation_combo.findData(octave_designation)
            self.octave_designation_combo.setCurrentIndex(max(0, index))
        self._octave_designation = octave_designation if octave_designation in {"scientific", "yamaha"} else "scientific"
        for keyboard in self._track_keyboards.values():
            keyboard.set_note_label_mode(self._note_label_mode)
            keyboard.set_note_label_font(self._note_label_font)
            keyboard.set_velocity_tinting_enabled(self._velocity_tinting)
            keyboard.set_octave_offset(-1 if self._octave_designation == "scientific" else -2)
        self._apply_track_colors()

    def _format_track_heading(self, track_number: int, title: str) -> str:
        if title:
            return self.tr("Track {number} - {title}").format(number=track_number + 1, title=title)
        return self.tr("Track {number}").format(number=track_number + 1)

    def _format_channel_summary(self, channels: set[int]) -> str:
        labels = ", ".join(str(channel + 1) for channel in sorted(channels))
        return self.tr("Channels: {channels}").format(channels=labels)

    def _effective_note_range(self, min_note: int, max_note: int) -> tuple[int, int]:
        if self._range_mode == "octaves":
            return ((min_note // 12) * 12, min(127, ((max_note // 12) * 12) + 11))
        return (min_note, max_note)

    def set_tracks(self, tracks: list[dict[str, object]]) -> None:
        self._track_keyboards.clear()
        self._track_visibility.clear()
        self._track_keyboard_containers.clear()
        self._track_note_ranges.clear()
        self._track_primary_channels.clear()
        self._track_channels = {
            int(track["track"]): set(track["channels"]) for track in tracks
        }
        self.tabs.clear()
        if not tracks:
            empty = QLabel(self.tr("No MIDI tracks available"), self)
            empty.setObjectName("pianola_empty_label")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabs.addTab(empty, self.tr("Tracks 1-8"))
            return
        for tab_index in range(0, len(tracks), self.TRACKS_PER_TAB):
            chunk = tracks[tab_index : tab_index + self.TRACKS_PER_TAB]
            page = QWidget(self.tabs)
            page_layout = QVBoxLayout(page)
            for track in chunk:
                track_number = int(track["track"])
                channels = set(track["channels"])
                title = str(track.get("title", ""))
                min_note = int(track.get("min_note", 21))
                max_note = int(track.get("max_note", 108))
                display_min_note, display_max_note = self._effective_note_range(min_note, max_note)
                row = QWidget(page)
                row_layout = QVBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(2)
                header = QWidget(row)
                header_layout = QHBoxLayout(header)
                header_layout.setContentsMargins(0, 0, 0, 0)
                header_layout.setSpacing(6)
                visible_checkbox = QCheckBox(self.tr("Show"), header)
                visible_checkbox.setObjectName(f"pianola_track_visible_{track_number + 1}")
                visible_checkbox.setChecked(True)
                header_layout.addWidget(visible_checkbox)
                label = QLabel(self._format_track_heading(track_number, title), row)
                label.setObjectName(f"pianola_track_label_{track_number + 1}")
                header_layout.addWidget(label)
                header_layout.addStretch(1)
                detail = QLabel(self._format_channel_summary(channels), row)
                detail.setObjectName(f"pianola_track_detail_{track_number + 1}")
                header_layout.addWidget(detail)
                row_layout.addWidget(header)
                keyboard_container = QWidget(row)
                keyboard_layout = QVBoxLayout(keyboard_container)
                keyboard_layout.setContentsMargins(0, 0, 0, 0)
                keyboard_layout.setSpacing(0)
                keyboard = PianoKeyboard(row)
                keyboard.setObjectName(f"pianola_track_keyboard_{track_number + 1}")
                keyboard.set_note_range(display_min_note, display_max_note)
                keyboard.set_note_label_mode(self._note_label_mode)
                keyboard.set_note_label_font(self._note_label_font)
                keyboard.set_velocity_tinting_enabled(self._velocity_tinting)
                keyboard.set_octave_offset(-1 if self._octave_designation == "scientific" else -2)
                keyboard_layout.addWidget(keyboard)
                row_layout.addWidget(keyboard_container)
                page_layout.addWidget(row)
                self._track_keyboards[track_number] = keyboard
                self._track_visibility[track_number] = visible_checkbox
                self._track_keyboard_containers[track_number] = keyboard_container
                self._track_note_ranges[track_number] = (min_note, max_note)
                self._track_primary_channels[track_number] = min(channels) if channels else None
                primary_channel = self._track_primary_channels[track_number]
                if primary_channel is not None:
                    keyboard.notePressed.connect(
                        lambda note, velocity, channel=primary_channel: self.manualNoteOn.emit(channel, note, velocity)
                    )
                    keyboard.noteReleased.connect(
                        lambda note, channel=primary_channel: self.manualNoteOff.emit(channel, note)
                    )
                visible_checkbox.toggled.connect(
                    lambda checked, track=track_number: self._set_track_visible(track, checked, emit_signal=True)
                )
            page_layout.addStretch(1)
            start = tab_index + 1
            end = tab_index + len(chunk)
            self.tabs.addTab(page, self.tr("Tracks {start}-{end}").format(start=start, end=end))
        self._apply_track_colors()
        self.tabs.setCurrentIndex(0)

    def _set_track_visible(self, track_number: int, visible: bool, emit_signal: bool) -> None:
        checkbox = self._track_visibility.get(track_number)
        if checkbox is not None and checkbox.isChecked() != visible:
            with QSignalBlocker(checkbox):
                checkbox.setChecked(visible)
        container = self._track_keyboard_containers.get(track_number)
        if container is not None:
            container.setVisible(visible)
        if emit_signal:
            self.trackVisibilityChanged.emit(track_number, visible)

    def show_all_tracks(self) -> None:
        for track_number in list(self._track_visibility):
            self._set_track_visible(track_number, True, emit_signal=False)
        self.allTracksVisibilityChanged.emit(True)

    def hide_all_tracks(self) -> None:
        for track_number in list(self._track_visibility):
            self._set_track_visible(track_number, False, emit_signal=False)
        self.allTracksVisibilityChanged.emit(False)

    def _range_mode_changed(self, index: int) -> None:
        self._range_mode = str(self.range_mode_combo.itemData(index) or "exact")
        self._apply_track_ranges()
        self.rangeModeChanged.emit(self._range_mode)

    def _apply_track_ranges(self) -> None:
        for track_number, keyboard in self._track_keyboards.items():
            min_note, max_note = self._track_note_ranges.get(track_number, (21, 108))
            display_min_note, display_max_note = self._effective_note_range(min_note, max_note)
            keyboard.set_note_range(display_min_note, display_max_note)

    def _note_label_mode_changed(self, index: int) -> None:
        self._note_label_mode = str(self.note_labels_combo.itemData(index) or "never")
        for keyboard in self._track_keyboards.values():
            keyboard.set_note_label_mode(self._note_label_mode)
        self.noteLabelModeChanged.emit(self._note_label_mode)

    def _octave_designation_changed(self, index: int) -> None:
        self._octave_designation = str(self.octave_designation_combo.itemData(index) or "scientific")
        offset = -1 if self._octave_designation == "scientific" else -2
        for keyboard in self._track_keyboards.values():
            keyboard.set_octave_offset(offset)
        self.octaveDesignationChanged.emit(self._octave_designation)

    def _color_mode_changed(self, index: int) -> None:
        self._color_mode = str(self.color_mode_combo.itemData(index) or "blue")
        self._apply_track_colors()
        self.colorModeChanged.emit(self._color_mode)

    def _apply_track_colors(self) -> None:
        for track_number, keyboard in self._track_keyboards.items():
            channel = self._track_primary_channels.get(track_number)
            if self._color_mode == "channel" and channel is not None:
                white_low, white_high, black_low, black_high = CHANNEL_COLOR_PALETTES[channel % len(CHANNEL_COLOR_PALETTES)]
                keyboard.set_active_colors(
                    white_low=white_low,
                    white_high=white_high,
                    black_low=black_low,
                    black_high=black_high,
                )
            else:
                white_low, white_high, black_low, black_high, black_idle = single_highlight_palette(
                    self._single_highlight_color
                )
                keyboard.set_active_colors(
                    white_low=white_low,
                    white_high=white_high,
                    black_low=black_low,
                    black_high=black_high,
                    black_idle=black_idle,
                )

    def set_fullscreen_enabled(self, enabled: bool) -> None:
        if enabled:
            self.showFullScreen()
            self.fullscreen_button.setText(self.tr("Window"))
        else:
            self.showNormal()
            self.fullscreen_button.setText(self.tr("Fullscreen"))

    def note_on(self, channel: int, note: int, velocity: int = 127) -> None:
        for track_number, channels in self._track_channels.items():
            if channel in channels and track_number in self._track_keyboards:
                self._track_keyboards[track_number].note_on(note, velocity)

    def note_off(self, channel: int, note: int) -> None:
        for track_number, channels in self._track_channels.items():
            if channel in channels and track_number in self._track_keyboards:
                self._track_keyboards[track_number].note_off(note)

    def clear(self) -> None:
        for keyboard in self._track_keyboards.values():
            keyboard.clear()

    def keyPressEvent(self, event: object) -> None:
        if getattr(event, "key", lambda: None)() == int(Qt.Key.Key_Escape) and self.isFullScreen():
            self.fullscreen_button.setChecked(False)
            return
        super().keyPressEvent(event)


class LyricsDialog(QDialog):
    textPrinted = pyqtSignal()
    textSaved = pyqtSignal(str, str)
    FILTERS = (
        ("all", "All"),
        ("lyrics", "Lyrics"),
        ("text", "Text"),
        ("marker", "Marker"),
        ("cue", "Cue Point"),
        ("other", "Other"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Lyrics and Texts"))
        self._text_events: list[object] = []
        self._track_counts: dict[int, int] = {}
        self._current_tick = 0
        self._visible_events: list[object] = []
        self._past_color = "#6b7280"
        self._future_color = "#2563eb"
        layout = QVBoxLayout(self)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(self.tr("Track:")))
        self.track_combo = QComboBox(self)
        self.track_combo.setObjectName("lyrics_track_combo")
        self.track_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.track_combo)
        filter_row.addWidget(QLabel(self.tr("Type:")))
        self.filter_combo = QComboBox(self)
        self.filter_combo.setObjectName("lyrics_filter_combo")
        for key, label in self.FILTERS:
            self.filter_combo.addItem(self.tr(label), key)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_combo)
        self.encoding_combo = QComboBox(self)
        self.encoding_combo.setObjectName("lyrics_encoding_combo")
        self.encoding_combo.addItem(self.tr("Auto"), None)
        self.encoding_combo.addItem("UTF-8", "utf-8")
        self.encoding_combo.addItem("Latin-1", "latin-1")
        self.encoding_combo.addItem("CP1252", "cp1252")
        self.encoding_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(QLabel(self.tr("Encoding:")))
        filter_row.addWidget(self.encoding_combo)
        filter_row.addStretch(1)
        self.save_button = QPushButton(self.tr("Save"), self)
        self.save_button.setObjectName("lyrics_save_button")
        self.save_button.clicked.connect(self.save_to_file)
        self.print_button = QPushButton(self.tr("Print"), self)
        self.print_button.setObjectName("lyrics_print_button")
        self.print_button.clicked.connect(self.print_text)
        self.copy_button = QPushButton(self.tr("Copy"), self)
        self.copy_button.setObjectName("lyrics_copy_button")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.font_button = QPushButton(self.tr("Font"), self)
        self.font_button.setObjectName("lyrics_font_button")
        self.font_button.clicked.connect(self.choose_font)
        self.fullscreen_button = QPushButton(self.tr("Fullscreen"), self)
        self.fullscreen_button.setObjectName("lyrics_fullscreen_button")
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.toggled.connect(self.set_fullscreen_enabled)
        self.copy_action = QAction(self.tr("Copy to Clipboard"), self)
        self.copy_action.triggered.connect(self.copy_to_clipboard)
        self.save_action = QAction(self.tr("Save to File..."), self)
        self.save_action.triggered.connect(self.save_to_file)
        self.print_action = QAction(self.tr("Print..."), self)
        self.print_action.triggered.connect(self.print_text)
        self.fullscreen_action = QAction(self.tr("Fullscreen"), self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.toggled.connect(self.fullscreen_button.setChecked)
        self.font_action = QAction(self.tr("Font..."), self)
        self.font_action.triggered.connect(self.choose_font)
        self.menu_button = QToolButton(self)
        self.menu_button.setObjectName("lyrics_menu_button")
        self.menu_button.setText("≡")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.menu_button)
        menu.addAction(self.copy_action)
        menu.addAction(self.save_action)
        menu.addAction(self.print_action)
        menu.addAction(self.fullscreen_action)
        menu.addAction(self.font_action)
        self.menu_button.setMenu(menu)
        filter_row.addWidget(self.menu_button)
        layout.addLayout(filter_row)
        self.browser = QTextBrowser(self)
        self.browser.setObjectName("lyrics_browser")
        layout.addWidget(self.browser)
        button_row = QHBoxLayout()
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.print_button)
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.font_button)
        button_row.addWidget(self.fullscreen_button)
        button_row.addStretch(1)
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(0)
        button_row_widget = QWidget(self)
        button_row_widget.setObjectName("lyrics_hidden_button_row")
        button_row_widget.setVisible(False)
        button_row_widget.setLayout(button_row)
        layout.addWidget(button_row_widget)
        self.resize(560, 420)

    def set_display_preferences(self, font_family: str, font_size: int, future_color: str, past_color: str) -> None:
        self.browser.setFont(QFont(font_family, max(6, min(48, font_size))))
        self._future_color = future_color or "#2563eb"
        self._past_color = past_color or "#6b7280"
        self._apply_filter()

    def set_text_events(self, text_events: list[object]) -> None:
        self._text_events = list(text_events)
        self._current_tick = 0
        self._track_counts = self._count_tracks()
        self._rebuild_track_filter()
        self._apply_filter()

    def set_current_tick(self, tick: int) -> None:
        self._current_tick = max(0, tick)
        self._apply_filter()

    def _apply_filter(self) -> None:
        category = self.filter_combo.currentData()
        track = self.track_combo.currentData()
        self._visible_events = self._filtered_text_events(track, category)
        self.browser.setHtml(self._highlighted_html(self._visible_events))

    def _count_tracks(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for event in self._text_events:
            track = getattr(event, "track", 0)
            counts[track] = counts.get(track, 0) + 1
        return counts

    def _rebuild_track_filter(self) -> None:
        current_track = self.track_combo.currentData()
        with QSignalBlocker(self.track_combo):
            self.track_combo.clear()
            self.track_combo.addItem(self.tr("All tracks"), None)
            for track in sorted(self._track_counts):
                self.track_combo.addItem(
                    self.tr("Track {number}").format(number=track + 1),
                    track,
                )
            if current_track in self._track_counts:
                index = self.track_combo.findData(current_track)
            else:
                index = self.track_combo.findData(self._preferred_track())
            self.track_combo.setCurrentIndex(max(0, index))

    def _preferred_track(self) -> int | None:
        if not self._track_counts:
            return None
        lyric_counts: dict[int, int] = {}
        for event in self._text_events:
            if getattr(event, "meta_type", None) != 0x05:
                continue
            track = getattr(event, "track", 0)
            lyric_counts[track] = lyric_counts.get(track, 0) + 1
        if lyric_counts:
            return max(lyric_counts, key=lambda track: (lyric_counts[track], -track))
        return max(self._track_counts, key=lambda track: (self._track_counts[track], -track))

    def _filtered_text_events(self, track: int | None, category: str) -> list[object]:
        events = list(self._text_events)
        if track is not None:
            events = [event for event in events if getattr(event, "track", None) == track]
        if category == "lyrics":
            return [event for event in events if getattr(event, "meta_type", None) == 0x05]
        if category == "text":
            return [event for event in events if getattr(event, "meta_type", None) == 0x01]
        if category == "marker":
            return [event for event in events if getattr(event, "meta_type", None) == 0x06]
        if category == "cue":
            return [event for event in events if getattr(event, "meta_type", None) == 0x07]
        if category == "other":
            return [event for event in events if getattr(event, "meta_type", None) in (0x02, 0x03, 0x04)]
        return events

    def _format_text_event(self, event: object) -> str:
        meta_type = getattr(event, "meta_type", 0x01)
        label = self.tr(TEXT_EVENT_LABELS.get(meta_type, "Text"))
        text = self._decoded_text(event)
        track = getattr(event, "track", None)
        if track is None or len(self._track_counts) <= 1 or self.track_combo.currentData() is not None:
            return f"{label}: {text}"
        return self.tr("Track {number} - {label}: {text}").format(number=track + 1, label=label, text=text)

    def _event_state(self, index: int, events: list[object]) -> str:
        if not events:
            return "future"
        current_index = None
        for candidate, event in enumerate(events):
            if getattr(event, "tick", 0) <= self._current_tick:
                current_index = candidate
            else:
                break
        if current_index is None:
            return "future"
        if index < current_index:
            return "past"
        if index == current_index:
            return "current"
        return "future"

    def _highlighted_html(self, events: list[object]) -> str:
        blocks = [
            "<html><body style='font-family:sans-serif;'>",
            "<style>"
            ".lyrics-line { margin: 0 0 8px 0; }"
            f".past {{ color: {self._past_color}; }}"
            ".current { color: #111827; background-color: #fde68a; font-weight: 700; }"
            f".future {{ color: {self._future_color}; }}"
            "</style>",
        ]
        for index, event in enumerate(events):
            state = self._event_state(index, events)
            text = self._format_text_event(event)
            escaped = (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br/>")
            )
            blocks.append(f"<p class='lyrics-line {state}'>{escaped}</p>")
        blocks.append("</body></html>")
        return "".join(blocks)

    def _decoded_text(self, event: object) -> str:
        preferred_encoding = self.selected_encoding()
        decoder = getattr(event, "decoded_text", None)
        if callable(decoder):
            return decoder(preferred_encoding)
        return getattr(event, "text", "")

    def current_text(self) -> str:
        return self.browser.toPlainText()

    def selected_encoding(self) -> str | None:
        return self.encoding_combo.currentData()

    def set_selected_encoding(self, encoding: str | None) -> None:
        index = self.encoding_combo.findData(encoding)
        self.encoding_combo.setCurrentIndex(max(0, index))

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.current_text())

    def choose_font(self) -> None:
        font, accepted = QFontDialog.getFont(self.browser.font(), self, self.tr("Lyrics Font"))
        if accepted:
            self.browser.setFont(font)

    def set_fullscreen_enabled(self, enabled: bool) -> None:
        if enabled:
            self.showFullScreen()
            self.fullscreen_button.setText(self.tr("Window"))
        else:
            self.showNormal()
            self.fullscreen_button.setText(self.tr("Fullscreen"))
        with QSignalBlocker(self.fullscreen_action):
            self.fullscreen_action.setChecked(enabled)

    def save_to_file(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Lyrics"),
            "lyrics.txt",
            self.tr("Text files (*.txt);;All files (*)"),
        )
        if not file_name:
            return
        encoding = str(self.selected_encoding() or "utf-8")
        try:
            Path(file_name).write_text(self.current_text(), encoding=encoding)
        except OSError as exc:
            QMessageBox.warning(self, self.tr("Save Lyrics"), str(exc))
            return
        self.textSaved.emit(file_name, encoding)

    def _print_document(self, printer: QPrinter) -> None:
        self.browser.document().print(printer)

    def print_text(self) -> None:
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return
        self._print_document(printer)
        self.textPrinted.emit()

    def keyPressEvent(self, event: object) -> None:
        if getattr(event, "key", lambda: None)() == int(Qt.Key.Key_Escape) and self.isFullScreen():
            self.fullscreen_button.setChecked(False)
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, start_files: list[str]) -> None:
        super().__init__()
        self.setWindowTitle(self.tr(APP_TITLE))
        self.resize(900, 520)
        self.setAcceptDrops(True)
        self.settings = AppSettings()
        self._restore_window_geometry()
        self._system_qt_style = QApplication.style().objectName() or "Fusion"
        self._system_palette = QPalette(QApplication.palette())
        self.manager = BackendManager(self)
        self.output = self._create_midi_output()
        self.player = SequencePlayer(self.output, self)
        self.player.set_percussion_channel(self.settings.percussion_channel())
        self.player.set_send_reset_before_playback(self.settings.midi_reset_before_playback())
        self.player.set_solo_volume_reduction(self.settings.solo_volume_reduction())
        self.player.started.connect(self._playback_started)
        self.player.stopped.connect(self._playback_stopped)
        self.player.positionChanged.connect(self._update_position)
        self.player.eventPlayed.connect(self._event_played)
        self.player.outputError.connect(self._output_error)
        self.player.finished.connect(self._finished)
        self.auto_play_on_load = self.settings.auto_play_on_load()
        self.auto_advance_playlist = self.settings.playlist_auto_advance()
        self.auto_song_settings = self.settings.auto_song_settings()
        self.force_dark_mode = self.settings.force_dark_mode()
        self.use_internal_icon_theme = self.settings.use_internal_icon_theme()
        self.toolbar_button_style = self.settings.toolbar_button_style()
        self.toolbar_action_ids = self.settings.toolbar_actions()
        self.qt_style = self.settings.qt_style()
        self.solo_volume_reduction = self.settings.solo_volume_reduction()
        self.lyrics_font_family = self.settings.lyrics_font_family()
        self.lyrics_font_size = self.settings.lyrics_font_size()
        self.lyrics_future_color = self.settings.lyrics_future_color()
        self.lyrics_past_color = self.settings.lyrics_past_color()
        self.pianola_color_mode = self.settings.pianola_color_mode()
        self.pianola_single_color = self.settings.pianola_single_color()
        self.pianola_velocity_tinting = self.settings.pianola_velocity_tinting()
        self.pianola_note_label_mode = self.settings.pianola_note_label_mode()
        self.pianola_note_font_family = self.settings.pianola_note_font_family()
        self.pianola_note_font_size = self.settings.pianola_note_font_size()
        self.pianola_octave_designation = self.settings.pianola_octave_designation()
        self._pause_requested = False
        self._current_file: str | None = None
        self.channel_labels: dict[int, str] = {}
        self.lyrics_encoding: str | None = None
        self.player.sequence.set_text_encoding(None)
        self._current_playlist_path: Path | None = None
        self._playlist_modified = False
        self.channels_dialog: ChannelsDialog | None = None
        self.lyrics_dialog: LyricsDialog | None = None
        self.pianola_dialog: PianolaDialog | None = None
        self.playlist_dialog: PlaylistDialog | None = None

        self.playlist = QListWidget()
        self.playlist.itemDoubleClicked.connect(lambda item: self.load_file(self._playlist_item_path(item)))
        self.playlist.currentRowChanged.connect(self._playlist_selection_changed)
        self.title_label = QLabel(self.tr("No file loaded"))
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.setTracking(False)
        self.position.setEnabled(False)
        self.position.sliderReleased.connect(self._seek_to_slider)
        self.time_label = QLabel(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
        self.rhythm_view = RhythmView()
        self.keyboard = PianoKeyboard()
        self.keyboard.notePressed.connect(lambda note, velocity: self._manual_note_on(0, note, velocity, "Keyboard"))
        self.keyboard.noteReleased.connect(lambda note: self._manual_note_off(0, note, "Keyboard"))
        self.event_label = QLabel(self.tr("MIDI output: {name}").format(name=self.output.name))
        self.connection_combo = QComboBox()
        self.connection_combo.setMinimumWidth(260)
        self.pitch_control = self._spinbox(-12, 12, 0, self._set_pitch_shift)
        self.percussion_channel_control = self._spinbox(
            1,
            16,
            self.player.percussion_channel,
            self._set_percussion_channel,
        )
        self.tempo_control = self._spinbox(50, 200, 100, self._set_tempo_percent, "%")
        self.volume_control = self._spinbox(0, 200, 100, self._set_volume_percent, "%")
        self.loop_check = QCheckBox(self.tr("Loop"))
        self.loop_check.toggled.connect(self._toggle_loop)
        self.loop_start = self._spinbox(1, 1, 1, self._update_loop_range)
        self.loop_end = self._spinbox(1, 1, 1, self._update_loop_range)
        self.jump_bar = self._spinbox(1, 1, 1, self._jump_bar_value_changed)
        self._updating_position = False
        self.transport_time_label = QLabel("00:00", self)
        self.transport_time_label.setObjectName("transport_time_label")
        self.transport_summary_label = QLabel("120 BPM", self)
        self.transport_summary_label.setObjectName("transport_summary_label")
        self.transport_volume_label = QLabel("100%", self)
        self.transport_volume_label.setObjectName("transport_volume_label")
        self.transport_pitch_label = QLabel("0", self)
        self.transport_pitch_label.setObjectName("transport_pitch_label")

        self._build_actions()
        self._update_action_state()
        self._build_toolbar()
        self._build_menu_bar()
        self._build_layout()
        self._apply_qt_style(self.qt_style)
        self._apply_color_mode()
        self._apply_icon_theme()
        self._apply_toolbar_button_style(self.toolbar_button_style)
        self._refresh_midi_connections(autoconnect=True)
        if start_files:
            self.open_paths([Path(file_name) for file_name in start_files], remember_folder=False)

    def _build_actions(self) -> None:
        self.open_action = QAction(self.tr("Open"), self)
        self.open_action.setObjectName("open_action")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_files)
        self.open_playlist_action = QAction(self.tr("Open Playlist"), self)
        self.open_playlist_action.setObjectName("open_playlist_action")
        self.open_playlist_action.triggered.connect(self.open_playlist)
        self.open_examples_action = QAction(self.tr("Open Example Playlist"), self)
        self.open_examples_action.setObjectName("open_examples_action")
        self.open_examples_action.triggered.connect(self.open_example_playlist)
        self.playlist_dialog_action = QAction(self.tr("Play List..."), self)
        self.playlist_dialog_action.setObjectName("playlist_dialog_action")
        self.playlist_dialog_action.triggered.connect(self._show_playlist_dialog)
        self.window_main_action = QAction(self.tr("Main Window"), self)
        self.window_main_action.setObjectName("window_main_action")
        self.window_main_action.triggered.connect(self._show_main_window)
        self.window_playlist_action = QAction(self.tr("Play List"), self)
        self.window_playlist_action.setObjectName("window_playlist_action")
        self.window_playlist_action.setCheckable(True)
        self.window_playlist_action.toggled.connect(
            lambda visible: self._set_dialog_visibility("playlist_dialog", self._create_playlist_dialog, visible)
        )
        self.window_channels_action = QAction(self.tr("Channels"), self)
        self.window_channels_action.setObjectName("window_channels_action")
        self.window_channels_action.setCheckable(True)
        self.window_channels_action.toggled.connect(
            lambda visible: self._set_dialog_visibility("channels_dialog", self._create_channels_dialog, visible)
        )
        self.window_pianola_action = QAction(self.tr("Piano Player"), self)
        self.window_pianola_action.setObjectName("window_pianola_action")
        self.window_pianola_action.setCheckable(True)
        self.window_pianola_action.toggled.connect(
            lambda visible: self._set_dialog_visibility("pianola_dialog", self._create_pianola_dialog, visible)
        )
        self.window_lyrics_action = QAction(self.tr("Lyrics"), self)
        self.window_lyrics_action.setObjectName("window_lyrics_action")
        self.window_lyrics_action.setCheckable(True)
        self.window_lyrics_action.toggled.connect(
            lambda visible: self._set_dialog_visibility("lyrics_dialog", self._create_lyrics_dialog, visible)
        )
        self.save_playlist_action = QAction(self.tr("Save Playlist"), self)
        self.save_playlist_action.setObjectName("save_playlist_action")
        self.save_playlist_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_playlist_action.triggered.connect(self.save_playlist)
        self.save_playlist_as_action = QAction(self.tr("Save Playlist As"), self)
        self.save_playlist_as_action.setObjectName("save_playlist_as_action")
        self.save_playlist_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_playlist_as_action.triggered.connect(self.save_playlist_as)
        self.load_song_settings_action = QAction(self.tr("Load"), self)
        self.load_song_settings_action.setObjectName("load_song_settings_action")
        self.load_song_settings_action.triggered.connect(self.load_song_settings)
        self.save_song_settings_action = QAction(self.tr("Save"), self)
        self.save_song_settings_action.setObjectName("save_song_settings_action")
        self.save_song_settings_action.triggered.connect(self.save_song_settings)

        self.exit_action = QAction(self.tr("Exit"), self)
        self.exit_action.setObjectName("exit_action")
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.clear_recent_action = QAction(self.tr("Clear Recent"), self)
        self.clear_recent_action.setObjectName("clear_recent_action")
        self.clear_recent_action.triggered.connect(self._clear_recent_files)
        self.refresh_midi_action = QAction(self.tr("Refresh MIDI Destinations"), self)
        self.refresh_midi_action.setObjectName("refresh_midi_action")
        self.refresh_midi_action.triggered.connect(self._refresh_midi_connections)
        self.connect_midi_action = QAction(self.tr("Connect MIDI Destination"), self)
        self.connect_midi_action.setObjectName("connect_midi_action")
        self.connect_midi_action.triggered.connect(self._connect_selected_midi_output)
        self.disconnect_midi_action = QAction(self.tr("Disconnect MIDI Destinations"), self)
        self.disconnect_midi_action.setObjectName("disconnect_midi_action")
        self.disconnect_midi_action.triggered.connect(self._disconnect_midi_output)
        self.preferences_action = QAction(self.tr("Preferences"), self)
        self.preferences_action.setObjectName("preferences_action")
        self.preferences_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.preferences_action.triggered.connect(self.show_preferences)
        self.remove_selected_action = QAction(self.tr("Remove Selected"), self)
        self.remove_selected_action.setObjectName("remove_selected_action")
        self.remove_selected_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.remove_selected_action.triggered.connect(self._remove_selected_playlist_item)
        self.move_up_action = QAction(self.tr("Move Up"), self)
        self.move_up_action.setObjectName("move_up_action")
        self.move_up_action.setShortcut(QKeySequence("Alt+Up"))
        self.move_up_action.triggered.connect(lambda: self._move_selected_playlist_item(-1))
        self.move_down_action = QAction(self.tr("Move Down"), self)
        self.move_down_action.setObjectName("move_down_action")
        self.move_down_action.setShortcut(QKeySequence("Alt+Down"))
        self.move_down_action.triggered.connect(lambda: self._move_selected_playlist_item(1))
        self.sort_playlist_action = QAction(self.tr("Sort Playlist"), self)
        self.sort_playlist_action.setObjectName("sort_playlist_action")
        self.sort_playlist_action.triggered.connect(self._sort_playlist)
        self.clear_playlist_action = QAction(self.tr("Clear Playlist"), self)
        self.clear_playlist_action.setObjectName("clear_playlist_action")
        self.clear_playlist_action.triggered.connect(self._clear_playlist)
        self.help_contents_action = QAction(self.tr("Help Contents"), self)
        self.help_contents_action.setObjectName("help_contents_action")
        self.help_contents_action.triggered.connect(self._show_help_contents)
        self.user_guide_action = QAction(self.tr("User Guide"), self)
        self.user_guide_action.setObjectName("user_guide_action")
        self.user_guide_action.triggered.connect(self._show_user_guide)
        self.about_action = QAction(self.tr("About"), self)
        self.about_action.setObjectName("about_action")
        self.about_action.triggered.connect(self._show_about_dialog)

        self.previous_action = QAction(self.tr("Previous"), self)
        self.previous_action.setObjectName("previous_action")
        self.previous_action.setShortcut(QKeySequence("Ctrl+Left"))
        self.previous_action.triggered.connect(self.previous_file)
        self.play_action = QAction(self.tr("Play"), self)
        self.play_action.setObjectName("play_action")
        self.play_action.setShortcut(QKeySequence("Space"))
        self.play_action.triggered.connect(self.play)
        self.pause_action = QAction(self.tr("Pause"), self)
        self.pause_action.setObjectName("pause_action")
        self.pause_action.setShortcut(QKeySequence("P"))
        self.pause_action.triggered.connect(self.pause)
        self.stop_action = QAction(self.tr("Stop"), self)
        self.stop_action.setObjectName("stop_action")
        self.stop_action.setShortcut(QKeySequence("Esc"))
        self.stop_action.triggered.connect(self.stop)
        self.next_action = QAction(self.tr("Next"), self)
        self.next_action.setObjectName("next_action")
        self.next_action.setShortcut(QKeySequence("Ctrl+Right"))
        self.next_action.triggered.connect(self.next_file)
        self.previous_bar_action = QAction(self.tr("Bar -"), self)
        self.previous_bar_action.setObjectName("previous_bar_action")
        self.previous_bar_action.setShortcut(QKeySequence("Alt+Left"))
        self.previous_bar_action.triggered.connect(self.previous_bar)
        self.next_bar_action = QAction(self.tr("Bar +"), self)
        self.next_bar_action.setObjectName("next_bar_action")
        self.next_bar_action.setShortcut(QKeySequence("Alt+Right"))
        self.next_bar_action.triggered.connect(self.next_bar)
        self.reset_pitch_action = QAction("0", self)
        self.reset_pitch_action.setObjectName("reset_pitch_action")
        self.reset_pitch_action.triggered.connect(lambda: self.pitch_control.setValue(0))
        self.reset_tempo_action = QAction("100%", self)
        self.reset_tempo_action.setObjectName("reset_tempo_action")
        self.reset_tempo_action.triggered.connect(lambda: self.tempo_control.setValue(100))
        self.reset_volume_action = QAction("100%", self)
        self.reset_volume_action.setObjectName("reset_volume_action")
        self.reset_volume_action.triggered.connect(lambda: self.volume_control.setValue(100))
        self.jump_bar_action = QAction(self.tr("Go"), self)
        self.jump_bar_action.setObjectName("jump_bar_action")
        self.jump_bar_action.setShortcut(QKeySequence("Ctrl+J"))
        self.jump_bar_action.triggered.connect(self.jump_to_bar)
        self.repeat_playlist_action = QAction(self.tr("Repeat Playlist"), self)
        self.repeat_playlist_action.setObjectName("repeat_playlist_action")
        self.repeat_playlist_action.setCheckable(True)
        self.shuffle_playlist_action = QAction(self.tr("Shuffle Playlist"), self)
        self.shuffle_playlist_action.setObjectName("shuffle_playlist_action")
        self.shuffle_playlist_action.setCheckable(True)
        self.auto_play_on_load_action = QAction(self.tr("Auto-Play On Load"), self)
        self.auto_play_on_load_action.setObjectName("auto_play_on_load_action")
        self.auto_play_on_load_action.setCheckable(True)
        self.auto_play_on_load_action.setChecked(self.auto_play_on_load)
        self.auto_play_on_load_action.toggled.connect(self._toggle_auto_play_on_load)
        self.auto_advance_playlist_action = QAction(self.tr("Playlist Auto-Advance"), self)
        self.auto_advance_playlist_action.setObjectName("auto_advance_playlist_action")
        self.auto_advance_playlist_action.setCheckable(True)
        self.auto_advance_playlist_action.setChecked(self.auto_advance_playlist)
        self.auto_advance_playlist_action.toggled.connect(self._toggle_auto_advance_playlist)
        self.customize_toolbar_action = QAction(self.tr("Customize Toolbar"), self)
        self.customize_toolbar_action.setObjectName("customize_toolbar_action")
        self.customize_toolbar_action.triggered.connect(self.show_customize_toolbar_dialog)
        self.toolbar_button_style_group = QActionGroup(self)
        self.toolbar_button_style_group.setExclusive(True)
        self.toolbar_icon_only_action = QAction(self.tr("Icon Only"), self)
        self.toolbar_icon_only_action.setObjectName("toolbar_icon_only_action")
        self.toolbar_icon_only_action.setCheckable(True)
        self.toolbar_icon_only_action.triggered.connect(lambda: self._set_toolbar_button_style("icon_only"))
        self.toolbar_button_style_group.addAction(self.toolbar_icon_only_action)
        self.toolbar_text_only_action = QAction(self.tr("Text Only"), self)
        self.toolbar_text_only_action.setObjectName("toolbar_text_only_action")
        self.toolbar_text_only_action.setCheckable(True)
        self.toolbar_text_only_action.triggered.connect(lambda: self._set_toolbar_button_style("text_only"))
        self.toolbar_button_style_group.addAction(self.toolbar_text_only_action)
        self.toolbar_text_beside_action = QAction(self.tr("Text Beside Icon"), self)
        self.toolbar_text_beside_action.setObjectName("toolbar_text_beside_action")
        self.toolbar_text_beside_action.setCheckable(True)
        self.toolbar_text_beside_action.triggered.connect(lambda: self._set_toolbar_button_style("text_beside"))
        self.toolbar_button_style_group.addAction(self.toolbar_text_beside_action)
        self.toolbar_text_under_action = QAction(self.tr("Text Under Icon"), self)
        self.toolbar_text_under_action.setObjectName("toolbar_text_under_action")
        self.toolbar_text_under_action.setCheckable(True)
        self.toolbar_text_under_action.triggered.connect(lambda: self._set_toolbar_button_style("text_under"))
        self.toolbar_button_style_group.addAction(self.toolbar_text_under_action)
        self.toolbar_follow_style_action = QAction(self.tr("Follow Qt Style"), self)
        self.toolbar_follow_style_action.setObjectName("toolbar_follow_style_action")
        self.toolbar_follow_style_action.setCheckable(True)
        self.toolbar_follow_style_action.triggered.connect(lambda: self._set_toolbar_button_style("follow_style"))
        self.toolbar_button_style_group.addAction(self.toolbar_follow_style_action)

    def _icon_for(self, theme_name: str, internal_name: str) -> QIcon:
        internal = bundled_icon(internal_name)
        if self.use_internal_icon_theme and not internal.isNull():
            return internal
        return QIcon.fromTheme(theme_name, internal)

    def _apply_icon_theme(self) -> None:
        for action_name, (theme_name, internal_name) in ACTION_ICONS.items():
            action = getattr(self, action_name, None)
            if isinstance(action, QAction):
                action.setIcon(self._icon_for(theme_name, internal_name))

    def _apply_toolbar_button_style(self, style_name: str) -> None:
        style = TOOLBAR_BUTTON_STYLES.get(style_name, Qt.ToolButtonStyle.ToolButtonFollowStyle)
        self.toolbar_button_style = style_name if style_name in TOOLBAR_BUTTON_STYLES else "follow_style"
        if hasattr(self, "playback_toolbar"):
            self.playback_toolbar.setToolButtonStyle(style)
        action_map = {
            "icon_only": self.toolbar_icon_only_action,
            "text_only": self.toolbar_text_only_action,
            "text_beside": self.toolbar_text_beside_action,
            "text_under": self.toolbar_text_under_action,
            "follow_style": self.toolbar_follow_style_action,
        }
        target = action_map.get(self.toolbar_button_style, self.toolbar_follow_style_action)
        for action in action_map.values():
            with QSignalBlocker(action):
                action.setChecked(action is target)

    def _set_toolbar_button_style(self, style_name: str) -> None:
        self.settings.set_toolbar_button_style(style_name)
        self._apply_toolbar_button_style(style_name)

    def _toolbar_action_map(self) -> dict[str, QAction]:
        return {
            "open_action": self.open_action,
            "previous_action": self.previous_action,
            "play_action": self.play_action,
            "pause_action": self.pause_action,
            "stop_action": self.stop_action,
            "next_action": self.next_action,
            "previous_bar_action": self.previous_bar_action,
            "next_bar_action": self.next_bar_action,
            "jump_bar_action": self.jump_bar_action,
            "repeat_playlist_action": self.repeat_playlist_action,
            "shuffle_playlist_action": self.shuffle_playlist_action,
            "preferences_action": self.preferences_action,
            "refresh_midi_action": self.refresh_midi_action,
        }

    def _toolbar_action_choices(self) -> list[tuple[str, str]]:
        action_map = self._toolbar_action_map()
        return [(action_id, action.text()) for action_id, action in action_map.items()]

    def _normalized_toolbar_action_ids(self, action_ids: list[str]) -> list[str]:
        valid_ids = set(self._toolbar_action_map())
        normalized = [action_id for action_id in action_ids if action_id in valid_ids]
        return normalized or list(DEFAULT_TOOLBAR_ACTION_ORDER)

    def _rebuild_toolbar(self) -> None:
        action_map = self._toolbar_action_map()
        self.toolbar_action_ids = self._normalized_toolbar_action_ids(self.toolbar_action_ids)
        self.playback_toolbar.clear()
        for action_id in self.toolbar_action_ids:
            action = action_map.get(action_id)
            if action is not None:
                self.playback_toolbar.addAction(action)

    def _apply_toolbar_actions(self, action_ids: list[str]) -> None:
        self.toolbar_action_ids = self._normalized_toolbar_action_ids(action_ids)
        self.settings.set_toolbar_actions(self.toolbar_action_ids)
        self._rebuild_toolbar()

    def _create_toolbar_customization_dialog(self) -> ToolbarCustomizationDialog:
        return ToolbarCustomizationDialog(self, self._toolbar_action_choices(), self.toolbar_action_ids)

    def show_customize_toolbar_dialog(self) -> None:
        dialog = self._create_toolbar_customization_dialog()
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return
        self._apply_toolbar_actions(dialog.selected_action_ids())

    def _update_action_state(self) -> None:
        has_file = self.player.sequence.midi is not None
        current_row = self.playlist.currentRow()
        self.play_action.setEnabled(has_file)
        self.pause_action.setEnabled(has_file)
        self.previous_bar_action.setEnabled(has_file)
        self.next_bar_action.setEnabled(has_file)
        self.previous_action.setEnabled(current_row > 0)
        self.next_action.setEnabled(current_row >= 0 and current_row < self.playlist.count() - 1)
        self.remove_selected_action.setEnabled(current_row >= 0)
        self.move_up_action.setEnabled(current_row > 0)
        self.move_down_action.setEnabled(current_row >= 0 and current_row < self.playlist.count() - 1)
        self.sort_playlist_action.setEnabled(self.playlist.count() > 1)
        self.clear_playlist_action.setEnabled(self.playlist.count() > 0)
        self.save_playlist_action.setEnabled(self.playlist.count() > 0)
        self.save_playlist_as_action.setEnabled(self.playlist.count() > 0)
        self.load_song_settings_action.setEnabled(has_file)
        self.save_song_settings_action.setEnabled(has_file)

    def _update_window_title(self) -> None:
        midi = self.player.sequence.midi
        playlist_name = None if self._current_playlist_path is None else self._current_playlist_path.name
        if playlist_name is not None and self._playlist_modified:
            playlist_name = f"*{playlist_name}"
        if midi is None:
            if playlist_name is None:
                self.setWindowTitle(self.tr(APP_TITLE))
            else:
                self.setWindowTitle(self.tr("{playlist} - {app}").format(playlist=playlist_name, app=self.tr(APP_TITLE)))
            return
        title = midi.title or self.tr("Untitled")
        current_row = self.playlist.currentRow()
        song_title = title
        if self.playlist.count() > 1 and current_row >= 0:
            song_title = self.tr("{song} [{index}/{count}]").format(
                song=title,
                index=current_row + 1,
                count=self.playlist.count(),
            )
        if playlist_name is None:
            self.setWindowTitle(self.tr("{song} - {app}").format(song=song_title, app=self.tr(APP_TITLE)))
            return
        self.setWindowTitle(
            self.tr("{song} - {playlist} - {app}").format(
                song=song_title,
                playlist=playlist_name,
                app=self.tr(APP_TITLE),
            )
        )

    def _playlist_dialog_title(self) -> str:
        if self._current_playlist_path is None:
            return self.tr("Manage Playlists")
        marker = " (*)" if self._playlist_modified else ""
        return self.tr("Manage Playlists: {name}{marker}").format(
            name=self._current_playlist_path.name,
            marker=marker,
        )

    def _build_toolbar(self) -> None:
        self.playback_toolbar = QToolBar(self.tr("Playback"), self)
        self.playback_toolbar.setObjectName("playback_toolbar")
        self.addToolBar(self.playback_toolbar)
        self._rebuild_toolbar()

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("File"))
        file_menu.setObjectName("file_menu")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_playlist_action)
        file_menu.addAction(self.open_examples_action)
        file_menu.addAction(self.playlist_dialog_action)
        self.recent_files_menu = file_menu.addMenu(self.tr("Open Recent"))
        self.recent_files_menu.setObjectName("recent_files_menu")
        self._refresh_recent_files_menu()
        file_menu.addSeparator()
        song_settings_menu = file_menu.addMenu(self.tr("Song Settings"))
        song_settings_menu.setObjectName("song_settings_menu")
        song_settings_menu.addAction(self.load_song_settings_action)
        song_settings_menu.addAction(self.save_song_settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_playlist_action)
        file_menu.addAction(self.save_playlist_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.move_up_action)
        file_menu.addAction(self.move_down_action)
        file_menu.addAction(self.sort_playlist_action)
        file_menu.addSeparator()
        file_menu.addAction(self.remove_selected_action)
        file_menu.addAction(self.clear_playlist_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        playback_menu = self.menuBar().addMenu(self.tr("Playback"))
        playback_menu.setObjectName("playback_menu")
        for action in (
            self.previous_action,
            self.play_action,
            self.pause_action,
            self.stop_action,
            self.next_action,
        ):
            playback_menu.addAction(action)
        playback_menu.addSeparator()
        playback_menu.addAction(self.previous_bar_action)
        playback_menu.addAction(self.next_bar_action)
        playback_menu.addAction(self.jump_bar_action)
        playback_menu.addSeparator()
        playback_menu.addAction(self.repeat_playlist_action)
        playback_menu.addAction(self.shuffle_playlist_action)
        playback_menu.addSeparator()
        playback_menu.addAction(self.auto_play_on_load_action)
        playback_menu.addAction(self.auto_advance_playlist_action)

        view_menu = self.menuBar().addMenu(self.tr("View"))
        view_menu.setObjectName("view_menu")
        toolbar_action = self.playback_toolbar.toggleViewAction()
        toolbar_action.setText(self.tr("Toolbar"))
        toolbar_action.setObjectName("toggle_toolbar_action")
        view_menu.addAction(toolbar_action)
        view_menu.addAction(self.customize_toolbar_action)
        self.statusbar_action = QAction(self.tr("Status bar"), self)
        self.statusbar_action.setObjectName("toggle_statusbar_action")
        self.statusbar_action.setCheckable(True)
        self.statusbar_action.setChecked(True)
        self.statusbar_action.toggled.connect(self.statusBar().setVisible)
        view_menu.addAction(self.statusbar_action)
        self.keyboard_action = QAction(self.tr("Keyboard"), self)
        self.keyboard_action.setObjectName("toggle_keyboard_action")
        self.keyboard_action.setCheckable(True)
        self.keyboard_action.setChecked(True)
        self.keyboard_action.toggled.connect(self.keyboard.setVisible)
        toolbar_buttons_menu = view_menu.addMenu(self.tr("Toolbar Buttons"))
        toolbar_buttons_menu.setObjectName("toolbar_buttons_menu")
        toolbar_buttons_menu.addAction(self.toolbar_icon_only_action)
        toolbar_buttons_menu.addAction(self.toolbar_text_only_action)
        toolbar_buttons_menu.addAction(self.toolbar_text_beside_action)
        toolbar_buttons_menu.addAction(self.toolbar_text_under_action)
        toolbar_buttons_menu.addAction(self.toolbar_follow_style_action)
        self.channels_action = QAction(self.tr("Channels"), self)
        self.channels_action.setObjectName("channels_action")
        self.channels_action.triggered.connect(self._show_channels_dialog)
        view_menu.addAction(self.channels_action)
        self.pianola_action = QAction(self.tr("Piano Player"), self)
        self.pianola_action.setObjectName("pianola_action")
        self.pianola_action.triggered.connect(self._show_pianola_dialog)
        view_menu.addAction(self.pianola_action)
        self.lyrics_action = QAction(self.tr("Lyrics"), self)
        self.lyrics_action.setObjectName("lyrics_action")
        self.lyrics_action.triggered.connect(self._show_lyrics_dialog)
        view_menu.addAction(self.lyrics_action)
        view_menu.addAction(self.keyboard_action)
        self.rhythm_action = QAction(self.tr("Rhythm"), self)
        self.rhythm_action.setObjectName("toggle_rhythm_action")
        self.rhythm_action.setCheckable(True)
        self.rhythm_action.setChecked(True)
        self.rhythm_action.toggled.connect(self.rhythm_view.setVisible)
        view_menu.addAction(self.rhythm_action)

        self.window_menu = self.menuBar().addMenu(self.tr("Window"))
        self.window_menu.setObjectName("window_menu")
        self.window_menu.aboutToShow.connect(self._refresh_window_menu_state)
        self.window_menu.addAction(self.window_main_action)
        self.window_menu.addSeparator()
        self.window_menu.addAction(self.window_playlist_action)
        self.window_menu.addAction(self.window_channels_action)
        self.window_menu.addAction(self.window_pianola_action)
        self.window_menu.addAction(self.window_lyrics_action)

        tools_menu = self.menuBar().addMenu(self.tr("Tools"))
        tools_menu.setObjectName("tools_menu")
        tools_menu.addAction(self.preferences_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.refresh_midi_action)
        tools_menu.addAction(self.connect_midi_action)
        tools_menu.addAction(self.disconnect_midi_action)

        help_menu = self.menuBar().addMenu(self.tr("Help"))
        help_menu.setObjectName("help_menu")
        help_menu.addAction(self.help_contents_action)
        help_menu.addAction(self.user_guide_action)
        help_menu.addAction(self.about_action)

    def _refresh_recent_files_menu(self) -> None:
        self.recent_files_menu.clear()
        recent_files = [path for path in self.settings.recent_files() if self._is_supported_file(path)]
        if not recent_files:
            placeholder = self.recent_files_menu.addAction(self.tr("No recent files"))
            placeholder.setEnabled(False)
        else:
            for path in recent_files:
                self._create_recent_file_action(path)
        self.recent_files_menu.addSeparator()
        self.clear_recent_action.setEnabled(bool(recent_files))
        self.recent_files_menu.addAction(self.clear_recent_action)

    def _clear_recent_files(self) -> None:
        self.settings.clear_recent_files()
        self._refresh_recent_files_menu()

    def _show_main_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def _dialog_is_visible(self, dialog: QDialog | None) -> bool:
        return dialog is not None and dialog.isVisible()

    def _refresh_window_menu_state(self) -> None:
        action_map = (
            (self.window_playlist_action, self.playlist_dialog),
            (self.window_channels_action, self.channels_dialog),
            (self.window_pianola_action, self.pianola_dialog),
            (self.window_lyrics_action, self.lyrics_dialog),
        )
        for action, dialog in action_map:
            with QSignalBlocker(action):
                action.setChecked(self._dialog_is_visible(dialog))

    def _set_dialog_visibility(self, attribute_name: str, factory: object, visible: bool) -> None:
        dialog = getattr(self, attribute_name)
        if visible:
            if dialog is None:
                dialog = factory()
                setattr(self, attribute_name, dialog)
                if attribute_name == "channels_dialog":
                    self._refresh_channels_dialog()
                elif attribute_name == "pianola_dialog":
                    dialog.set_display_preferences(
                        self.pianola_color_mode,
                        self.pianola_single_color,
                        self.pianola_velocity_tinting,
                        self.pianola_note_label_mode,
                        self.pianola_note_font_family,
                        self.pianola_note_font_size,
                        self.pianola_octave_designation,
                    )
                    dialog.trackVisibilityChanged.connect(self._pianola_track_visibility_changed)
                    dialog.allTracksVisibilityChanged.connect(self._pianola_all_tracks_visibility_changed)
                    dialog.rangeModeChanged.connect(self._pianola_range_mode_changed)
                    dialog.noteLabelModeChanged.connect(self._pianola_note_label_mode_changed)
                    dialog.colorModeChanged.connect(self._pianola_color_mode_changed)
                    dialog.octaveDesignationChanged.connect(self._pianola_octave_designation_changed)
                    dialog.manualNoteOn.connect(
                        lambda channel, note, velocity: self._manual_note_on(channel, note, velocity, "Piano Player")
                    )
                    dialog.manualNoteOff.connect(
                        lambda channel, note: self._manual_note_off(channel, note, "Piano Player")
                    )
                    self._refresh_pianola_dialog()
                elif attribute_name == "lyrics_dialog":
                    dialog.set_display_preferences(
                        self.lyrics_font_family,
                        self.lyrics_font_size,
                        self.lyrics_future_color,
                        self.lyrics_past_color,
                    )
                    dialog.set_selected_encoding(self.lyrics_encoding)
                    dialog.textSaved.connect(self._lyrics_text_saved)
                    dialog.textPrinted.connect(self._lyrics_text_printed)
                    self._refresh_lyrics_dialog()
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        elif dialog is not None:
            dialog.hide()
        self._refresh_window_menu_state()

    def _refresh_playlist_dialog(self) -> None:
        if self.playlist_dialog is not None:
            self.playlist_dialog.refresh_from_window()

    def _sync_playlist_ui(self) -> None:
        self._update_action_state()
        self._update_window_title()
        self._refresh_playlist_dialog()

    def _mark_playlist_modified(self) -> None:
        if self._current_playlist_path is None:
            return
        self._playlist_modified = True
        self._update_window_title()

    def _playlist_selection_changed(self, row: int) -> None:
        self._sync_playlist_ui()
        if row < 0 or self.player.sequence.midi is None or self.playlist.count() <= 1:
            return
        self._update_window_title()

    def _reset_loaded_file_state(self, status_message: str) -> None:
        self._current_file = None
        self.channel_labels = {}
        self._set_lyrics_encoding(None)
        self.position.setEnabled(False)
        self.title_label.setText(self.tr("No file loaded"))
        self.time_label.setText(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
        self.event_label.setText(self.tr("No file loaded"))
        self.rhythm_view.clear()
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.set_channels([])
        if self.pianola_dialog is not None:
            self.pianola_dialog.set_tracks([])
        if self.lyrics_dialog is not None:
            self.lyrics_dialog.set_text_events([])
        self._update_midi_output_label()
        self._update_action_state()
        self._update_window_title()
        self.statusBar().showMessage(status_message, 5000)

    def _toggle_auto_play_on_load(self, enabled: bool) -> None:
        self.auto_play_on_load = enabled
        self.settings.set_auto_play_on_load(enabled)

    def _toggle_auto_advance_playlist(self, enabled: bool) -> None:
        self.auto_advance_playlist = enabled
        self.settings.set_playlist_auto_advance(enabled)

    def _create_playlist_dialog(self) -> PlaylistDialog:
        return PlaylistDialog(self)

    def _show_playlist_dialog(self) -> None:
        self._set_dialog_visibility("playlist_dialog", self._create_playlist_dialog, True)

    def _playlist_dialog_folder(self) -> Path:
        saved_playlist = self.settings.playlist_path()
        if saved_playlist is not None:
            return saved_playlist.parent
        return self.settings.last_folder(Path.home())

    def _remove_selected_playlist_item(self) -> None:
        row = self.playlist.currentRow()
        if row < 0:
            return
        item = self.playlist.takeItem(row)
        if item is None:
            return
        removed_file = self._playlist_item_path(item)
        del item
        if self.playlist.count() == 0:
            self.player.clear()
            self._mark_playlist_modified()
            self._reset_loaded_file_state(self.tr("Playlist cleared"))
            return
        self.playlist.setCurrentRow(min(row, self.playlist.count() - 1))
        if removed_file == self._current_file:
            self._mark_playlist_modified()
            current_item = self.playlist.currentItem()
            if current_item is not None:
                self.load_file(self._playlist_item_path(current_item))
            return
        self._mark_playlist_modified()
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Removed {name} from playlist").format(name=Path(removed_file).name), 5000)

    def _move_selected_playlist_item(self, delta: int) -> None:
        row = self.playlist.currentRow()
        target_row = row + delta
        if row < 0 or target_row < 0 or target_row >= self.playlist.count():
            return
        item = self.playlist.takeItem(row)
        if item is None:
            return
        self.playlist.insertItem(target_row, item)
        self.playlist.setCurrentRow(target_row)
        self._mark_playlist_modified()
        self._sync_playlist_ui()
        self.statusBar().showMessage(
            self.tr("Moved {name} in playlist").format(name=Path(self._playlist_item_path(item)).name),
            5000,
        )

    def _sort_playlist(self) -> None:
        if self.playlist.count() < 2:
            return
        selected_path = None
        current_item = self.playlist.currentItem()
        if current_item is not None:
            selected_path = self._playlist_item_path(current_item)
        paths = sorted(self._playlist_paths(), key=lambda path: self._playlist_display_text(path).casefold())
        self.playlist.clear()
        for path in paths:
            self.playlist.addItem(self._create_playlist_item(path))
        if selected_path is not None:
            self._select_playlist_file(selected_path)
        self._mark_playlist_modified()
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Playlist sorted"), 5000)

    def _randomize_playlist(self) -> None:
        if self.playlist.count() < 2:
            return
        selected_path = None
        current_item = self.playlist.currentItem()
        if current_item is not None:
            selected_path = self._playlist_item_path(current_item)
        paths = self._playlist_paths()
        random.shuffle(paths)
        self.playlist.clear()
        for path in paths:
            self.playlist.addItem(self._create_playlist_item(path))
        if selected_path is not None:
            self._select_playlist_file(selected_path)
        self._mark_playlist_modified()
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Playlist randomized"), 5000)

    def _clear_playlist(self) -> None:
        if self.playlist.count() == 0:
            return
        self.playlist.clear()
        self.player.clear()
        self._mark_playlist_modified()
        self._reset_loaded_file_state(self.tr("Playlist cleared"))

    def open_playlist(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Playlist"),
            str(self._playlist_dialog_folder()),
            self.tr("Playlists (*.lst);;All files (*)"),
        )
        if file_name:
            self.load_playlist_file(file_name)

    def _example_playlist_path(self) -> Path:
        return EXAMPLES_DIR / "examples.lst"

    def open_example_playlist(self) -> None:
        playlist_path = self._example_playlist_path()
        if not playlist_path.exists():
            message = self.tr("Example playlist not found: {name}").format(name=playlist_path.name)
            self.statusBar().showMessage(message, 10000)
            QMessageBox.warning(self, self.tr("Open Example Playlist"), message)
            return
        self.load_playlist_file(playlist_path)

    def save_playlist(self) -> None:
        if self._current_playlist_path is not None:
            self.save_playlist_file(self._current_playlist_path)
            return
        self.save_playlist_as()

    def save_playlist_as(self) -> None:
        default_name = self._current_playlist_path.name if self._current_playlist_path is not None else "playlist.lst"
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Playlist"),
            str(self._playlist_dialog_folder() / default_name),
            self.tr("Playlists (*.lst);;All files (*)"),
        )
        if file_name:
            self.save_playlist_file(file_name)

    def load_playlist_file(self, file_name: str | Path) -> list[Path]:
        playlist_path = Path(file_name)
        lines = playlist_path.read_text(encoding="utf-8").splitlines()
        files: list[Path] = []
        for line in lines:
            entry = line.strip()
            if not entry:
                continue
            path = Path(entry)
            if not path.is_absolute():
                path = (playlist_path.parent / path).resolve()
            if self._is_supported_file(path):
                files.append(path)
        self.playlist.clear()
        for path in files:
            self.add_file(str(path), mark_modified=False)
        self._current_playlist_path = playlist_path
        self._playlist_modified = False
        self.settings.set_playlist_path(playlist_path)
        if files:
            self.settings.set_last_folder(files[0].parent)
            self.load_file(str(files[0]))
        else:
            self.player.clear()
            self._reset_loaded_file_state(self.tr("Loaded empty playlist"))
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Loaded playlist {name}").format(name=playlist_path.name), 5000)
        return files

    def save_playlist_file(self, file_name: str | Path) -> Path:
        playlist_path = Path(file_name)
        entries: list[str] = []
        for item_path in self._playlist_paths():
            try:
                entry = os.path.relpath(item_path, playlist_path.parent)
            except ValueError:
                entry = str(item_path)
            entries.append(entry)
        text = "\n".join(entries)
        if text:
            text += "\n"
        playlist_path.write_text(text, encoding="utf-8")
        self._current_playlist_path = playlist_path
        self._playlist_modified = False
        self.settings.set_playlist_path(playlist_path)
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Saved playlist {name}").format(name=playlist_path.name), 5000)
        return playlist_path

    def _playlist_paths(self) -> list[Path]:
        return [Path(self._playlist_item_path(self.playlist.item(row))) for row in range(self.playlist.count())]

    def _song_display_text(self, path: Path) -> str:
        title = ""
        try:
            midi = read_smf(path)
            title = midi.title.strip()
        except (OSError, MidiFileError):
            title = ""
        if title and title != path.name:
            return self.tr("{title} - {name}").format(title=title, name=path.name)
        if title:
            return title
        return path.name

    def _song_summary_title(self, path: Path, title: str) -> str:
        title = title.strip()
        if title and title != path.name:
            return self.tr("{title} - {name}").format(title=title, name=path.name)
        return title or path.name

    def _playlist_display_text(self, path: Path) -> str:
        return self._song_display_text(path)

    def _create_playlist_item(self, path: str | Path) -> QListWidgetItem:
        path = Path(path)
        item = QListWidgetItem(self._playlist_display_text(path))
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setToolTip(str(path))
        return item

    def _playlist_item_path(self, item: QListWidgetItem | None) -> str:
        if item is None:
            return ""
        stored = item.data(Qt.ItemDataRole.UserRole)
        return str(stored or "")

    def _create_recent_file_action(self, path: Path) -> QAction:
        action = self.recent_files_menu.addAction(self._song_display_text(path))
        action.setData(str(path))
        action.setToolTip(str(path))
        action.triggered.connect(lambda checked=False, file_name=str(path): self.load_file(file_name))
        return action

    def _localized_doc_path(self, file_name: str) -> Path:
        locale_name = QLocale.system().name()
        language = locale_name.split("_", 1)[0].casefold()
        candidates = [locale_name.casefold(), language, "en"]
        for candidate in candidates:
            path = HELP_DOCS_DIR / candidate / file_name
            if path.exists():
                return path
        return HELP_DOCS_DIR / "en" / file_name

    def _help_doc_path(self) -> Path:
        return self._localized_doc_path("index.md")

    def _user_guide_path(self) -> Path:
        return self._localized_doc_path("pyqt6-user-guide.md")

    def _about_html(self) -> str:
        return self.tr(
            """
            <h2>{app}</h2>
            <p>Python/PyQt6 port of the Drumstick multiplatform MIDI file player.</p>
            <p><strong>Copyright dmidiplayer</strong></p>
            <p>
              Copyright © 2026
              <a href="mailto:plcl@users.sf.net" title="plcl@users.sf.net">
                Pedro Lopez-Cabanillas
              </a>
              (original C++ version)
            </p>
            <p>
              Copyright © 2026
              <a href="mailto:linuxfrontier@proton.me" title="linuxfrontier@proton.me">
                Washington Indacochea Delgado
              </a>
              (Python/PyQt6 port)
            </p>
            <p>
              This program is free software: you may redistribute it and/or modify it
              under the terms of the GNU General Public License as published by the
              Free Software Foundation, either version 3 of the License, or (at your
              option) any later version.
            </p>
            <p>
              This program is distributed in the hope that it will be useful but
              WITHOUT ANY WARRANTY; without even the implied warranty of
              MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
              Public License for more details.
            </p>
            <p>
              You should have received a copy of the GNU General Public License along
              with this program. If not, see
              <a href="https://www.gnu.org/licenses/">https://www.gnu.org/licenses/</a>.
            </p>
            <h3>Technologies used in this port</h3>
            <ul>
              <li>Python 3</li>
              <li>PyQt6 Qt Widgets</li>
              <li><code>drumstick_py</code> for MIDI file parsing and widgets</li>
              <li><code>ctypes</code> bindings to ALSA Sequencer through <code>libasound</code></li>
              <li>QSettings for persistent application preferences</li>
              <li>Standard MIDI File support for <code>.mid</code> and <code>.kar</code></li>
            </ul>
            """
        ).format(app=self.tr(APP_TITLE)).strip()

    def _show_about_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("About"))
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._about_html())
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.resize(480, 320)
        dialog.exec()

    def _show_help_contents(self) -> None:
        self._show_markdown_help(self._help_doc_path(), self.tr("Help Contents"))

    def _show_user_guide(self) -> None:
        self._show_markdown_help(self._user_guide_path(), self.tr("User Guide"))

    def _show_markdown_help(self, path: Path, window_title: str) -> None:
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.statusBar().showMessage(self.tr("Unable to load help: {error}").format(error=exc), 10000)
            QMessageBox.warning(self, self.tr("Help"), str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(window_title)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(markdown)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.resize(760, 560)
        self.statusBar().showMessage(self.tr("Loaded help from {name}").format(name=path.name), 5000)
        dialog.exec()

    def _create_channels_dialog(self) -> ChannelsDialog:
        return ChannelsDialog(self)

    def _ensure_channels_dialog(self) -> ChannelsDialog:
        if self.channels_dialog is None:
            self.channels_dialog = self._create_channels_dialog()
            self._refresh_channels_dialog()
        return self.channels_dialog

    def _show_channels_dialog(self) -> None:
        self._set_dialog_visibility("channels_dialog", self._create_channels_dialog, True)

    def _refresh_channels_dialog(self) -> None:
        if self.channels_dialog is None:
            return
        initial_programs = self.player.sequence.initial_programs()
        channel_programs = {
            channel: (
                self.player.channel_program(channel)
                if self.player.channel_program(channel) is not None
                else initial_programs.get(channel, 0)
            )
            for channel in self.player.sequence.used_channels()
        }
        self.channels_dialog.set_channels(
            self.player.sequence.used_channels(),
            muted_channels=self.player.muted_channels(),
            solo_channels=self.player.solo_channels(),
            channel_programs=channel_programs,
            locked_channels=self.player.locked_channels(),
            channel_volumes={channel: self.player.channel_volume_percent(channel) for channel in self.player.sequence.used_channels()},
            channel_labels=self.channel_labels,
            label_changed=self._set_channel_label,
            mute_changed=self._set_channel_muted,
            solo_changed=self._set_channel_solo,
            program_changed=self._set_channel_program,
            lock_changed=self._set_channel_locked,
            volume_changed=self._set_channel_volume,
        )

    def _create_lyrics_dialog(self) -> LyricsDialog:
        return LyricsDialog(self)

    def _create_pianola_dialog(self) -> PianolaDialog:
        return PianolaDialog(self)

    def _ensure_pianola_dialog(self) -> PianolaDialog:
        if self.pianola_dialog is None:
            self.pianola_dialog = self._create_pianola_dialog()
            self.pianola_dialog.set_display_preferences(
                self.pianola_color_mode,
                self.pianola_single_color,
                self.pianola_velocity_tinting,
                self.pianola_note_label_mode,
                self.pianola_note_font_family,
                self.pianola_note_font_size,
                self.pianola_octave_designation,
            )
            self.pianola_dialog.trackVisibilityChanged.connect(self._pianola_track_visibility_changed)
            self.pianola_dialog.allTracksVisibilityChanged.connect(self._pianola_all_tracks_visibility_changed)
            self.pianola_dialog.rangeModeChanged.connect(self._pianola_range_mode_changed)
            self.pianola_dialog.noteLabelModeChanged.connect(self._pianola_note_label_mode_changed)
            self.pianola_dialog.colorModeChanged.connect(self._pianola_color_mode_changed)
            self.pianola_dialog.octaveDesignationChanged.connect(self._pianola_octave_designation_changed)
            self.pianola_dialog.manualNoteOn.connect(
                lambda channel, note, velocity: self._manual_note_on(channel, note, velocity, "Piano Player")
            )
            self.pianola_dialog.manualNoteOff.connect(
                lambda channel, note: self._manual_note_off(channel, note, "Piano Player")
            )
            self._refresh_pianola_dialog()
        return self.pianola_dialog

    def _show_pianola_dialog(self) -> None:
        self._set_dialog_visibility("pianola_dialog", self._create_pianola_dialog, True)

    def _refresh_pianola_dialog(self) -> None:
        if self.pianola_dialog is None:
            return
        self.pianola_dialog.set_tracks(self.player.sequence.midi_track_infos())

    def _pianola_track_visibility_changed(self, track_number: int, visible: bool) -> None:
        self.statusBar().showMessage(
            self.tr("Track {number} {state} in Piano Player").format(
                number=track_number + 1,
                state=self.tr("shown") if visible else self.tr("hidden"),
            ),
            3000,
        )

    def _pianola_all_tracks_visibility_changed(self, visible: bool) -> None:
        self.statusBar().showMessage(
            self.tr("Piano Player tracks {state}").format(
                state=self.tr("shown") if visible else self.tr("hidden"),
            ),
            3000,
        )

    def _pianola_range_mode_changed(self, mode: str) -> None:
        mode_label = self.tr("Used octaves") if mode == "octaves" else self.tr("Exact")
        self.statusBar().showMessage(
            self.tr("Piano Player range: {mode}").format(mode=mode_label),
            3000,
        )

    def _pianola_note_label_mode_changed(self, mode: str) -> None:
        labels = {
            "never": self.tr("Never"),
            "minimal": self.tr("Minimal"),
            "active": self.tr("When active"),
            "always": self.tr("Always"),
        }
        self.statusBar().showMessage(
            self.tr("Piano Player labels: {mode}").format(mode=labels.get(mode, mode)),
            3000,
        )

    def _pianola_color_mode_changed(self, mode: str) -> None:
        labels = {
            "blue": self.tr("Blue"),
            "channel": self.tr("By channel"),
        }
        self.statusBar().showMessage(
            self.tr("Piano Player colors: {mode}").format(mode=labels.get(mode, mode)),
            3000,
        )

    def _pianola_octave_designation_changed(self, mode: str) -> None:
        labels = {
            "scientific": self.tr("Scientific"),
            "yamaha": self.tr("Yamaha"),
        }
        self.statusBar().showMessage(
            self.tr("Piano Player octaves: {mode}").format(mode=labels.get(mode, mode)),
            3000,
        )

    def _manual_note_on(self, channel: int, note: int, velocity: int, source: str) -> None:
        try:
            self.output.send_event(
                MidiEvent(
                    tick=self.position.value(),
                    kind="note_on",
                    channel=max(0, min(15, channel)),
                    data=bytes([max(0, min(127, note)), max(1, min(127, velocity))]),
                )
            )
        except MidiOutputError as exc:
            self._output_error(str(exc))
            return
        if self.channels_dialog is not None:
            self.channels_dialog.set_channel_level(channel, velocity)
        self.event_label.setText(
            self.tr("{source} note_on channel={channel} data={data}").format(
                source=source,
                channel=channel,
                data=bytes([note, velocity]).hex(" "),
            )
        )

    def _manual_note_off(self, channel: int, note: int, source: str) -> None:
        try:
            self.output.send_event(
                MidiEvent(
                    tick=self.position.value(),
                    kind="note_off",
                    channel=max(0, min(15, channel)),
                    data=bytes([max(0, min(127, note)), 0]),
                )
            )
        except MidiOutputError as exc:
            self._output_error(str(exc))
            return
        if self.channels_dialog is not None:
            self.channels_dialog.set_channel_level(channel, 0)
        self.event_label.setText(
            self.tr("{source} note_off channel={channel} data={data}").format(
                source=source,
                channel=channel,
                data=bytes([note, 0]).hex(" "),
            )
        )

    def _ensure_lyrics_dialog(self) -> LyricsDialog:
        if self.lyrics_dialog is None:
            self.lyrics_dialog = self._create_lyrics_dialog()
            self.lyrics_dialog.set_display_preferences(
                self.lyrics_font_family,
                self.lyrics_font_size,
                self.lyrics_future_color,
                self.lyrics_past_color,
            )
            self.lyrics_dialog.set_selected_encoding(self.lyrics_encoding)
            self.lyrics_dialog.encoding_combo.currentIndexChanged.connect(
                self._lyrics_encoding_selection_changed
            )
            self.lyrics_dialog.textSaved.connect(self._lyrics_text_saved)
            self.lyrics_dialog.textPrinted.connect(self._lyrics_text_printed)
            self._refresh_lyrics_dialog()
        return self.lyrics_dialog

    def _show_lyrics_dialog(self) -> None:
        self._set_dialog_visibility("lyrics_dialog", self._create_lyrics_dialog, True)

    def _refresh_lyrics_dialog(self) -> None:
        if self.lyrics_dialog is None:
            return
        self.lyrics_dialog.set_selected_encoding(self.lyrics_encoding)
        self.lyrics_dialog.set_text_events(self.player.sequence.text_events())
        self.lyrics_dialog.set_current_tick(self.position.value())

    def _lyrics_text_saved(self, file_name: str, encoding: str) -> None:
        self.statusBar().showMessage(
            self.tr("Saved lyrics to {name} ({encoding})").format(
                name=Path(file_name).name,
                encoding=encoding,
            ),
            5000,
        )

    def _lyrics_text_printed(self) -> None:
        self.statusBar().showMessage(self.tr("Printed lyrics"), 5000)

    def _set_channel_muted(self, channel: int, muted: bool) -> None:
        self.player.set_channel_muted(channel, muted)
        self.statusBar().showMessage(
            self.tr("Channel {number} {state}").format(
                number=channel + 1,
                state=self.tr("muted") if muted else self.tr("unmuted"),
            ),
            3000,
        )

    def _set_channel_solo(self, channel: int, solo: bool) -> None:
        self.player.set_channel_solo(channel, solo)
        self.statusBar().showMessage(
            self.tr("Channel {number} {state}").format(
                number=channel + 1,
                state=self.tr("solo") if solo else self.tr("normal"),
            ),
            3000,
        )

    def _set_channel_program(self, channel: int, value: int) -> None:
        self.player.set_channel_program(channel, value)
        self.statusBar().showMessage(
            self.tr("Channel {number} program {value}").format(number=channel + 1, value=value),
            3000,
        )

    def _set_channel_locked(self, channel: int, locked: bool) -> None:
        self.player.set_channel_locked(channel, locked)
        self.statusBar().showMessage(
            self.tr("Channel {number} {state}").format(
                number=channel + 1,
                state=self.tr("locked") if locked else self.tr("unlocked"),
            ),
            3000,
        )

    def _set_channel_volume(self, channel: int, value: int) -> None:
        self.player.set_channel_volume_percent(channel, value)
        self.statusBar().showMessage(
            self.tr("Channel {number} volume {value}%").format(number=channel + 1, value=value),
            3000,
        )
        self.channels_dialog.clear_levels()

    def _set_channel_label(self, channel: int, label: str) -> None:
        text = label.strip() or self._default_channel_label(channel)
        self.channel_labels[channel] = text
        self.statusBar().showMessage(
            self.tr("Channel {number} label updated").format(number=channel + 1),
            3000,
        )

    def _default_channel_label(self, channel: int) -> str:
        labels = self.player.sequence.default_channel_labels()
        if channel in labels:
            return labels[channel]
        return self.tr("Channel {number}").format(number=channel + 1)

    def _reset_channel_labels(self) -> None:
        self.channel_labels = {
            channel: self._default_channel_label(channel) for channel in self.player.sequence.used_channels()
        }

    def _song_settings_dir(self) -> Path:
        return Path.home() / ".dmidiplayer"

    def _song_settings_path(self, file_name: str | None = None) -> Path | None:
        target = file_name or self._current_file
        if not target:
            return None
        return self._song_settings_dir() / f"{Path(target).name}.cfg"

    def _current_lyrics_encoding(self) -> str | None:
        if self.lyrics_dialog is not None:
            self._set_lyrics_encoding(self.lyrics_dialog.selected_encoding())
        return self.lyrics_encoding

    def _set_lyrics_encoding(self, encoding: str | None) -> None:
        self.lyrics_encoding = encoding
        self.player.sequence.set_text_encoding(encoding)

    def _lyrics_encoding_selection_changed(self) -> None:
        if self.lyrics_dialog is None:
            return
        self._set_lyrics_encoding(self.lyrics_dialog.selected_encoding())

    def _current_song_settings(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        current_file = self._current_file or ""
        encoding = self._current_lyrics_encoding() or "auto"
        config["song"] = {
            "file": current_file,
            "encoding": encoding,
            "transpose": str(self.player.pitch_shift),
            "tempo": str(self.player.tempo_percent),
            "volume": str(self.player.volume_percent),
        }
        for channel in self.player.sequence.used_channels():
            section = f"channel{channel + 1}"
            program = self.player.channel_program(channel)
            config[section] = {
                "label": self.channel_labels.get(channel, self._default_channel_label(channel)),
                "volume": str(self.player.channel_volume_percent(channel)),
                "program": str(0 if program is None else program),
                "solo": str(channel in self.player.solo_channels()).lower(),
                "mute": str(channel in self.player.muted_channels()).lower(),
                "lock": str(channel in self.player.locked_channels()).lower(),
            }
        return config

    def save_song_settings(self) -> None:
        path = self._song_settings_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        config = self._current_song_settings()
        with path.open("w", encoding="utf-8") as handle:
            config.write(handle)
        self.statusBar().showMessage(self.tr("Saved song settings to {name}").format(name=path.name), 5000)

    def load_song_settings(self) -> None:
        path = self._song_settings_path()
        if path is None or not path.exists():
            if path is not None:
                self.statusBar().showMessage(self.tr("Song settings not found: {name}").format(name=path.name), 5000)
            return
        config = configparser.ConfigParser()
        config.read(path, encoding="utf-8")
        song = config["song"] if config.has_section("song") else {}
        encoding = song.get("encoding", "auto")
        self._set_lyrics_encoding(None if encoding == "auto" else encoding)
        self.pitch_control.setValue(int(song.get("transpose", self.player.pitch_shift)))
        self.tempo_control.setValue(int(song.get("tempo", self.player.tempo_percent)))
        self.volume_control.setValue(int(song.get("volume", self.player.volume_percent)))
        self._reset_channel_labels()
        for channel in self.player.sequence.used_channels():
            section = f"channel{channel + 1}"
            if not config.has_section(section):
                self.player.set_channel_muted(channel, False)
                self.player.set_channel_solo(channel, False)
                self.player.set_channel_locked(channel, False)
                self.player.set_channel_volume_percent(channel, 100)
                continue
            channel_data = config[section]
            self.channel_labels[channel] = channel_data.get("label", self._default_channel_label(channel))
            self.player.set_channel_volume_percent(channel, channel_data.getint("volume", fallback=100))
            self.player.set_channel_program(channel, channel_data.getint("program", fallback=0))
            self.player.set_channel_solo(channel, channel_data.getboolean("solo", fallback=False))
            self.player.set_channel_muted(channel, channel_data.getboolean("mute", fallback=False))
            self.player.set_channel_locked(channel, channel_data.getboolean("lock", fallback=False))
        self._refresh_channels_dialog()
        self._refresh_lyrics_dialog()
        self.statusBar().showMessage(self.tr("Loaded song settings from {name}").format(name=path.name), 5000)

    def _create_preferences_dialog(self) -> PreferencesDialog:
        return PreferencesDialog(self, self.settings)

    def _apply_color_mode(self) -> None:
        QApplication.setPalette(dark_palette() if self.force_dark_mode else QApplication.style().standardPalette())

    def _apply_qt_style(self, style_name: str) -> None:
        target = self._system_qt_style if style_name == "system" else style_name
        if not target:
            return
        applied = QApplication.setStyle(target)
        if applied is not None:
            self.qt_style = style_name if style_name in {"system", *available_qt_styles()} else "system"
            self._apply_color_mode()

    def _apply_preferences(
        self,
        percussion_channel: int,
        solo_volume_reduction: int,
        auto_play_on_load: bool,
        playlist_auto_advance: bool,
        auto_song_settings: bool,
        force_dark_mode: bool,
        use_internal_icon_theme: bool,
        qt_style: str,
        midi_reset_before_playback: bool,
        lyrics_font_family: str,
        lyrics_font_size: int,
        lyrics_future_color: str,
        lyrics_past_color: str,
        pianola_color_mode: str,
        pianola_single_color: str,
        pianola_velocity_tinting: bool,
        pianola_note_label_mode: str,
        pianola_note_font_family: str,
        pianola_note_font_size: int,
        pianola_octave_designation: str,
    ) -> None:
        self.percussion_channel_control.setValue(percussion_channel)
        self.solo_volume_reduction = solo_volume_reduction
        self.settings.set_solo_volume_reduction(solo_volume_reduction)
        self.player.set_solo_volume_reduction(solo_volume_reduction)
        self.auto_play_on_load_action.setChecked(auto_play_on_load)
        self.auto_advance_playlist_action.setChecked(playlist_auto_advance)
        self.auto_song_settings = auto_song_settings
        self.settings.set_auto_song_settings(auto_song_settings)
        self.force_dark_mode = force_dark_mode
        self.settings.set_force_dark_mode(force_dark_mode)
        self.use_internal_icon_theme = use_internal_icon_theme
        self.settings.set_use_internal_icon_theme(use_internal_icon_theme)
        self.settings.set_qt_style(qt_style)
        self._apply_qt_style(qt_style)
        self._apply_icon_theme()
        self.player.set_send_reset_before_playback(midi_reset_before_playback)
        self.settings.set_midi_reset_before_playback(midi_reset_before_playback)
        self.lyrics_font_family = lyrics_font_family
        self.lyrics_font_size = lyrics_font_size
        self.lyrics_future_color = lyrics_future_color
        self.lyrics_past_color = lyrics_past_color
        self.settings.set_lyrics_font_family(lyrics_font_family)
        self.settings.set_lyrics_font_size(lyrics_font_size)
        self.settings.set_lyrics_future_color(lyrics_future_color)
        self.settings.set_lyrics_past_color(lyrics_past_color)
        if self.lyrics_dialog is not None:
            self.lyrics_dialog.set_display_preferences(
                self.lyrics_font_family,
                self.lyrics_font_size,
                self.lyrics_future_color,
                self.lyrics_past_color,
            )
        self.pianola_color_mode = pianola_color_mode
        self.pianola_single_color = pianola_single_color
        self.pianola_velocity_tinting = pianola_velocity_tinting
        self.pianola_note_label_mode = pianola_note_label_mode
        self.pianola_note_font_family = pianola_note_font_family
        self.pianola_note_font_size = pianola_note_font_size
        self.pianola_octave_designation = pianola_octave_designation
        self.settings.set_pianola_color_mode(pianola_color_mode)
        self.settings.set_pianola_single_color(pianola_single_color)
        self.settings.set_pianola_velocity_tinting(pianola_velocity_tinting)
        self.settings.set_pianola_note_label_mode(pianola_note_label_mode)
        self.settings.set_pianola_note_font_family(pianola_note_font_family)
        self.settings.set_pianola_note_font_size(pianola_note_font_size)
        self.settings.set_pianola_octave_designation(pianola_octave_designation)
        if self.pianola_dialog is not None:
            self.pianola_dialog.set_display_preferences(
                self.pianola_color_mode,
                self.pianola_single_color,
                self.pianola_velocity_tinting,
                self.pianola_note_label_mode,
                self.pianola_note_font_family,
                self.pianola_note_font_size,
                self.pianola_octave_designation,
            )
        self.statusBar().showMessage(self.tr("Preferences updated"), 5000)

    def show_preferences(self) -> None:
        dialog = self._create_preferences_dialog()
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return
        self._apply_preferences(*dialog.preferences())

    def play(self) -> None:
        self._pause_requested = False
        self.player.play()

    def pause(self) -> None:
        self._pause_requested = True
        self.player.pause()

    def stop(self) -> None:
        self._pause_requested = False
        self.player.stop()

    def _playback_started(self) -> None:
        self.statusBar().showMessage(self.tr("Playing"))

    def _playback_stopped(self) -> None:
        message = self.tr("Paused") if self._pause_requested else self.tr("Stopped")
        self.statusBar().showMessage(message)
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()
        if self.pianola_dialog is not None:
            self.pianola_dialog.clear()
        if not self._pause_requested and self.auto_song_settings and self._current_file is not None:
            self.save_song_settings()
        self._pause_requested = False

    def _restore_window_geometry(self) -> None:
        geometry = self.settings.window_geometry()
        if geometry is None:
            return
        x, y, width, height = geometry
        self.resize(width, height)
        self.move(x, y)

    def _save_window_geometry(self) -> None:
        geometry = self.frameGeometry()
        self.settings.set_window_geometry(geometry.x(), geometry.y(), self.width(), self.height())

    def _build_layout(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(QLabel(self.tr("List")))
        left.addWidget(self.playlist)
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(self._build_transport_summary())
        right.addWidget(self.title_label)
        right.addWidget(self.position)
        right.addWidget(self.time_label)
        right.addWidget(self._build_playback_settings())
        right.addWidget(self.rhythm_view)
        right.addWidget(self._build_midi_destination_row())
        right.addWidget(self.keyboard)
        right.addWidget(self.event_label)
        root.addLayout(left, 1)
        root.addLayout(right, 3)
        self.setCentralWidget(central)

    def _build_transport_summary(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("transport_summary_panel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet(
            "#transport_summary_panel { background: #111111; color: white; border: 1px solid #2b2b2b; }"
            "#transport_time_label { font-size: 34px; color: white; }"
            "#transport_summary_panel QLabel { color: white; }"
        )
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(18)
        self.transport_time_label.setMinimumWidth(160)
        layout.addWidget(self.transport_time_label, 0, Qt.AlignmentFlag.AlignVCenter)
        details = QFormLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setHorizontalSpacing(16)
        details.setVerticalSpacing(6)
        details.addRow(self.tr("Tempo:"), self.transport_summary_label)
        details.addRow(self.tr("Volume:"), self.transport_volume_label)
        details.addRow(self.tr("Pitch:"), self.transport_pitch_label)
        layout.addLayout(details, 1)
        return panel

    def _build_playback_settings(self) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(4)

        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(QLabel(self.tr("Pitch:")))
        controls_layout.addWidget(self.pitch_control)
        controls_layout.addWidget(self._action_button(self.reset_pitch_action))
        controls_layout.addWidget(QLabel(self.tr("Drums:")))
        controls_layout.addWidget(self.percussion_channel_control)
        controls_layout.addWidget(QLabel(self.tr("Tempo:")))
        controls_layout.addWidget(self.tempo_control)
        controls_layout.addWidget(self._action_button(self.reset_tempo_action))
        controls_layout.addWidget(QLabel(self.tr("Volume:")))
        controls_layout.addWidget(self.volume_control)
        controls_layout.addWidget(self._action_button(self.reset_volume_action))
        controls_layout.addWidget(QLabel(self.tr("Bar:")))
        controls_layout.addWidget(self._action_button(self.previous_bar_action))
        controls_layout.addWidget(self._action_button(self.next_bar_action))
        controls_layout.addStretch(1)

        loop_row = QWidget()
        loop_layout = QHBoxLayout(loop_row)
        loop_layout.setContentsMargins(0, 0, 0, 0)
        loop_layout.addWidget(QLabel(self.tr("Jump bar:")))
        loop_layout.addWidget(self.jump_bar)
        loop_layout.addWidget(self._action_button(self.jump_bar_action))
        loop_layout.addWidget(self.loop_check)
        loop_layout.addWidget(QLabel(self.tr("Start bar:")))
        loop_layout.addWidget(self.loop_start)
        loop_layout.addWidget(QLabel(self.tr("End bar:")))
        loop_layout.addWidget(self.loop_end)
        loop_layout.addStretch(1)

        panel_layout.addWidget(controls_row)
        panel_layout.addWidget(loop_row)
        return panel

    def _build_midi_destination_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(self.tr("MIDI destination:")))
        layout.addWidget(self.connection_combo, 1)
        layout.addWidget(self._action_button(self.refresh_midi_action))
        layout.addWidget(self._action_button(self.connect_midi_action))
        layout.addWidget(self._action_button(self.disconnect_midi_action))
        return row

    def _spinbox(self, minimum: int, maximum: int, value: int, slot: object, suffix: str = "") -> QSpinBox:
        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        spinbox.setValue(value)
        if suffix:
            spinbox.setSuffix(suffix)
        spinbox.valueChanged.connect(slot)
        return spinbox

    def _button(self, text: str, slot: object) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    def _action_button(self, action: QAction) -> QToolButton:
        button = QToolButton()
        button.setDefaultAction(action)
        return button

    def _create_midi_output(self) -> object:
        try:
            return self.manager.create_output("alsa")
        except MidiOutputError as exc:
            info = self.manager.alsa_audio_info()
            suffix = (
                self.tr(" Cards detected by python3-alsaaudio: {count}.").format(count=len(info.cards))
                if info.available
                else ""
            )
            self.statusBar().showMessage(
                self.tr("ALSA is not available, using dummy output: {error}.{suffix}").format(
                    error=exc,
                    suffix=suffix,
                ),
                10000,
            )
            return self.manager.create_output("dummy")

    def _refresh_midi_connections(self, autoconnect: bool = False) -> None:
        self.connection_combo.clear()
        if not hasattr(self.output, "connections"):
            self.connection_combo.addItem("Dummy output")
            self.connection_combo.setEnabled(False)
            self._update_midi_output_label()
            return
        try:
            connections = self.output.connections()
        except MidiOutputError as exc:
            self.connection_combo.addItem(self.tr("No ALSA destinations"))
            self.connection_combo.setEnabled(False)
            self.statusBar().showMessage(str(exc), 10000)
            self._update_midi_output_label()
            return
        self.connection_combo.setEnabled(bool(connections))
        if not connections:
            self.connection_combo.addItem(self.tr("No ALSA destinations"))
            self.statusBar().showMessage(
                self.tr("No ALSA MIDI destinations were found. Open QSynth and press Refresh."),
                10000,
            )
            self._update_midi_output_label()
            return
        for connection in connections:
            self.connection_combo.addItem(connection.name, connection)
        if autoconnect:
            self._autoconnect_preferred_midi_output(connections)

    def _autoconnect_preferred_midi_output(self, connections: list[object]) -> None:
        saved_destination = self.settings.midi_destination()
        if saved_destination:
            preferred = next(
                (connection for connection in connections if connection.matches(saved_destination)),
                None,
            )
            if preferred is not None:
                index = connections.index(preferred)
                self.connection_combo.setCurrentIndex(index)
                self._connect_midi_output(preferred, remember=False)
                return
        preferred = next(
            (
                connection
                for connection in connections
                if any(token in connection.name.casefold() for token in ("qsynth", "fluidsynth", "fluid"))
            ),
            None,
        )
        if preferred is None:
            return
        index = connections.index(preferred)
        self.connection_combo.setCurrentIndex(index)
        self._connect_midi_output(preferred)

    def _connect_selected_midi_output(self) -> None:
        connection = self.connection_combo.currentData()
        if connection is None:
            self.statusBar().showMessage(self.tr("No ALSA MIDI destination selected"), 5000)
            return
        self._connect_midi_output(connection)

    def _connect_midi_output(self, connection: object, remember: bool = True) -> None:
        if not hasattr(self.output, "connect_to"):
            self.statusBar().showMessage(self.tr("The dummy output does not support ALSA connections"), 5000)
            return
        try:
            self.output.connect_to(connection)
        except MidiOutputError as exc:
            QMessageBox.warning(self, self.tr("MIDI connection"), str(exc))
            return
        if remember:
            self.settings.set_midi_destination(connection.name)
        self.statusBar().showMessage(self.tr("Connected to {name}").format(name=connection.name), 10000)
        self._update_midi_output_label()

    def _disconnect_midi_output(self) -> None:
        if not hasattr(self.output, "disconnect_all"):
            self.statusBar().showMessage(self.tr("The dummy output has no ALSA connections"), 5000)
            return
        try:
            self.output.disconnect_all()
        except MidiOutputError as exc:
            QMessageBox.warning(self, self.tr("MIDI connection"), str(exc))
            return
        self.statusBar().showMessage(self.tr("Disconnected MIDI destinations"), 5000)
        self._update_midi_output_label()

    def _update_midi_output_label(self) -> None:
        if not hasattr(self.output, "connected_connections"):
            self.event_label.setText(self.tr("MIDI output: {name}").format(name=self.output.name))
            return
        connections = self.output.connected_connections()
        if not connections:
            self.event_label.setText(self.tr("MIDI output: {name}").format(name=self.output.name))
            return
        self.event_label.setText(
            self.tr("MIDI output: {output} -> {destination}").format(
                output=self.output.name,
                destination=", ".join(connection.name for connection in connections),
            )
        )

    def open_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Open Files"),
            str(self.settings.last_folder(Path.home())),
            self.tr("Songs and playlists (*.mid *.midi *.kar *.rmi *.wrk *.lst);;Songs (*.mid *.midi *.kar *.rmi *.wrk);;Playlists (*.lst);;All files (*)"),
        )
        self.open_paths([Path(file_name) for file_name in files], remember_folder=True)

    def open_paths(self, paths: list[Path], remember_folder: bool = False) -> list[Path]:
        openable_paths = [path for path in paths if self._is_openable_path(path)]
        if not openable_paths:
            return []
        if remember_folder:
            self.settings.set_last_folder(openable_paths[0].parent)

        playlist_paths = [path for path in openable_paths if self._is_playlist_file(path)]
        midi_paths = [path for path in openable_paths if self._is_openable_song_file(path)]
        opened: list[Path] = []

        if playlist_paths:
            self.load_playlist_file(playlist_paths[0])
            opened.append(playlist_paths[0])

        for path in midi_paths:
            self.add_file(str(path))
            opened.append(path)

        if midi_paths and self.player.sequence.midi is None:
            self.load_file(str(midi_paths[0]))
        elif not playlist_paths and midi_paths:
            self.load_file(str(midi_paths[0]))

        return opened

    def add_file(self, file_name: str, mark_modified: bool = True) -> bool:
        path = Path(file_name)
        if not self._is_openable_song_file(path):
            return False
        for row in range(self.playlist.count()):
            if self._playlist_item_path(self.playlist.item(row)) == str(path):
                self.playlist.setCurrentRow(row)
                self._sync_playlist_ui()
                return False
        self.playlist.addItem(self._create_playlist_item(path))
        if mark_modified:
            self._mark_playlist_modified()
        self._sync_playlist_ui()
        return True

    def _is_supported_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.casefold() in MIDI_FILE_SUFFIXES

    def _is_openable_song_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.casefold() in OPENABLE_SONG_FILE_SUFFIXES

    def _is_playlist_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.casefold() in PLAYLIST_FILE_SUFFIXES

    def _is_openable_path(self, path: Path) -> bool:
        return self._is_openable_song_file(path) or self._is_playlist_file(path)

    def load_file(self, file_name: str, autoplay: bool | None = None) -> None:
        self.statusBar().showMessage(self.tr("Loading {name}").format(name=Path(file_name).name))
        try:
            self.player.load_file(file_name)
        except (OSError, MidiFileError) as exc:
            self.statusBar().showMessage(self.tr("Error loading file: {error}").format(error=exc), 10000)
            QMessageBox.critical(self, self.tr("Error"), str(exc))
            return
        midi = self.player.sequence.midi
        if midi is None:
            return
        duration = midi.length_microseconds / 1_000_000
        path = Path(file_name)
        song_summary = self._song_summary_title(path, midi.title)
        self.title_label.setText(
            self.tr("{title} - format {format}, {tracks} track(s), {ticks} ticks, {seconds:.1f} s").format(
                title=song_summary,
                format=midi.format,
                tracks=len(midi.tracks),
                ticks=midi.length_ticks,
                seconds=duration,
            )
        )
        self.event_label.setText(self.tr("File loaded"))
        self.position.setEnabled(midi.length_ticks > 0)
        self._reset_loop_controls()
        self._select_playlist_file(file_name)
        self._update_time_label(0, midi.length_ticks)
        self.keyboard.clear()
        self._refresh_channels_dialog()
        self._refresh_pianola_dialog()
        self._refresh_lyrics_dialog()
        self.settings.add_recent_file(file_name)
        self._refresh_recent_files_menu()
        self._current_file = file_name
        self._set_lyrics_encoding(None)
        self._reset_channel_labels()
        if self.auto_song_settings:
            self.load_song_settings()
        self._refresh_channels_dialog()
        self._refresh_lyrics_dialog()
        self._sync_playlist_ui()
        self.statusBar().showMessage(self.tr("Ready: {name}").format(name=song_summary))
        should_autoplay = self.auto_play_on_load if autoplay is None else autoplay
        if should_autoplay:
            self.play()

    def previous_file(self) -> None:
        row = self.playlist.currentRow()
        if row < 0:
            row = 0
        self._load_playlist_row(max(0, row - 1))

    def next_file(self) -> None:
        row = self._next_playlist_row()
        if row is None:
            return
        self._load_playlist_row(row)

    def _next_playlist_row(self) -> int | None:
        count = self.playlist.count()
        if count == 0:
            return None
        row = self.playlist.currentRow()
        if row < 0:
            row = 0
        if self.shuffle_playlist_action.isChecked():
            if count == 1:
                return row
            candidates = [candidate for candidate in range(count) if candidate != row]
            return random.choice(candidates)
        next_row = row + 1
        if next_row < count:
            return next_row
        if self.repeat_playlist_action.isChecked():
            return 0
        return None

    def _load_playlist_row(self, row: int, autoplay: bool = False) -> bool:
        if row < 0 or row >= self.playlist.count():
            return False
        item = self.playlist.item(row)
        self.playlist.setCurrentRow(row)
        self.load_file(self._playlist_item_path(item), autoplay=autoplay)
        return True

    def _select_playlist_file(self, file_name: str) -> None:
        for row in range(self.playlist.count()):
            if self._playlist_item_path(self.playlist.item(row)) == file_name:
                self.playlist.setCurrentRow(row)
                self._sync_playlist_ui()
                return

    def _update_position(self, tick: int, maximum: int) -> None:
        self._updating_position = True
        self.position.setMaximum(maximum)
        self.position.setValue(min(tick, maximum))
        self._updating_position = False
        self._update_time_label(tick, maximum)
        if self.lyrics_dialog is not None:
            self.lyrics_dialog.set_current_tick(tick)

    def _seek_to_slider(self) -> None:
        if self._updating_position:
            return
        self.player.seek(self.position.value())
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()
        if self.pianola_dialog is not None:
            self.pianola_dialog.clear()

    def previous_bar(self) -> None:
        self._seek_to_bar_delta(-1)

    def next_bar(self) -> None:
        self._seek_to_bar_delta(1)

    def _seek_to_bar_delta(self, delta: int) -> None:
        sequence = self.player.sequence
        if sequence.midi is None:
            return
        current_bar = sequence.bar_number_at_tick(self.position.value())
        target_bar = max(1, min(sequence.bar_count, current_bar + delta))
        self._seek_to_bar(target_bar)

    def jump_to_bar(self) -> None:
        self._seek_to_bar(self.jump_bar.value())

    def _seek_to_bar(self, bar_number: int) -> None:
        sequence = self.player.sequence
        if sequence.midi is None:
            return
        target_bar = max(1, min(sequence.bar_count, bar_number))
        if target_bar != self.jump_bar.value():
            with QSignalBlocker(self.jump_bar):
                self.jump_bar.setValue(target_bar)
        self.player.seek(sequence.tick_for_bar(target_bar))
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()
        if self.pianola_dialog is not None:
            self.pianola_dialog.clear()

    def _jump_bar_value_changed(self, value: int) -> None:
        if self.player.sequence.midi is None:
            return
        self.statusBar().showMessage(self.tr("Ready to jump to bar {bar}").format(bar=value), 2000)

    def _reset_loop_controls(self) -> None:
        if self.loop_check is None or self.loop_start is None or self.loop_end is None or self.jump_bar is None:
            return
        bar_count = max(1, self.player.sequence.bar_count)
        with (
            QSignalBlocker(self.loop_check),
            QSignalBlocker(self.loop_start),
            QSignalBlocker(self.loop_end),
            QSignalBlocker(self.jump_bar),
        ):
            self.loop_check.setChecked(False)
            self.jump_bar.setRange(1, bar_count)
            self.jump_bar.setValue(1)
            self.loop_start.setRange(1, bar_count)
            self.loop_end.setRange(1, bar_count)
            self.loop_start.setValue(1)
            self.loop_end.setValue(bar_count)
        self.player.set_loop_range(0, self.player.sequence.length_ticks)
        self.player.set_loop_enabled(False)

    def _toggle_loop(self, enabled: bool) -> None:
        self._update_loop_range()
        self.player.set_loop_enabled(enabled)

    def _update_loop_range(self) -> None:
        if self.loop_start is None or self.loop_end is None:
            return
        if self.player.sequence.midi is None:
            return
        start_bar = self.loop_start.value()
        end_bar = max(start_bar, self.loop_end.value())
        if end_bar != self.loop_end.value():
            with QSignalBlocker(self.loop_end):
                self.loop_end.setValue(end_bar)
        start_tick = self.player.sequence.tick_for_bar(start_bar)
        end_tick = self.player.sequence.tick_for_bar(end_bar + 1)
        self.player.set_loop_range(start_tick, end_tick)

    def _set_tempo_percent(self, value: int) -> None:
        self.player.set_tempo_percent(value)
        self.transport_summary_label.setText(self.tr("{bpm:.0f} BPM").format(bpm=120 * value / 100))
        self._update_time_label(self.position.value(), self.position.maximum())

    def _set_pitch_shift(self, value: int) -> None:
        self.player.set_pitch_shift(value)
        self.transport_pitch_label.setText(str(value))

    def _set_volume_percent(self, value: int) -> None:
        self.player.set_volume_percent(value)
        self.transport_volume_label.setText(f"{value}%")

    def _set_percussion_channel(self, value: int) -> None:
        self.player.set_percussion_channel(value)
        self.settings.set_percussion_channel(self.player.percussion_channel)

    def _update_time_label(self, tick: int, maximum: int) -> None:
        midi = self.player.sequence.midi
        if midi is None:
            self.time_label.setText(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
            self.transport_time_label.setText("00:00")
            self.transport_summary_label.setText(self.tr("{bpm:.0f} BPM").format(bpm=120 * self.player.tempo_percent / 100))
            self.transport_volume_label.setText(f"{self.player.volume_percent}%")
            self.transport_pitch_label.setText(str(self.player.pitch_shift))
            return
        current_us = self.player.sequence.tick_to_microseconds(tick)
        total_us = self.player.sequence.tick_to_microseconds(maximum)
        bpm = self.player.sequence.bpm_at_tick(tick) * self.player.tempo_percent / 100
        bar = self.player.sequence.bar_number_at_tick(tick)
        bar_count = self.player.sequence.bar_count
        numerator, denominator = self.player.sequence.time_signature_at_tick(tick)
        bar_start_tick = self.player.sequence.tick_for_bar(bar)
        ticks_per_beat = max(1, (self.player.sequence.division * 4) // denominator)
        beat = ((max(tick, bar_start_tick) - bar_start_tick) // ticks_per_beat) + 1
        self.rhythm_view.update_state(numerator, denominator, bar, beat, bpm)
        self.time_label.setText(
            self.tr("{current} / {total} - {bpm:.0f} BPM - Bar {bar}/{bar_count}").format(
                current=self._format_time(current_us),
                total=self._format_time(total_us),
                bpm=bpm,
                bar=bar,
                bar_count=bar_count,
            )
        )
        self.transport_time_label.setText(self._format_time(current_us))
        self.transport_summary_label.setText(self.tr("{bpm:.2f} BPM").format(bpm=bpm))
        self.transport_volume_label.setText(f"{self.player.volume_percent}%")
        self.transport_pitch_label.setText(str(self.player.pitch_shift))

    def _format_time(self, microseconds: int) -> str:
        seconds = max(0, microseconds // 1_000_000)
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _event_played(self, event: object) -> None:
        kind = getattr(event, "kind", "event")
        channel = getattr(event, "channel", None)
        data = getattr(event, "data", b"")
        self.event_label.setText(
            self.tr("{kind} channel={channel} data={data}").format(
                kind=kind,
                channel=channel if channel is not None else "-",
                data=data.hex(" "),
            )
        )
        if kind == "note_on" and len(data) >= 2 and data[1] > 0:
            self.keyboard.note_on(data[0], data[1])
            if channel is not None and self.channels_dialog is not None:
                self.channels_dialog.set_channel_level(channel, data[1])
            if channel is not None and self.pianola_dialog is not None:
                self.pianola_dialog.note_on(channel, data[0], data[1])
        elif kind in ("note_off", "note_on") and data:
            self.keyboard.note_off(data[0])
            if channel is not None and self.channels_dialog is not None:
                self.channels_dialog.set_channel_level(channel, 0)
            if channel is not None and self.pianola_dialog is not None:
                self.pianola_dialog.note_off(channel, data[0])

    def _finished(self) -> None:
        next_row = self._next_playlist_row() if self.auto_advance_playlist else None
        if next_row is not None and self._load_playlist_row(next_row, autoplay=True):
            return
        self.event_label.setText(self.tr("End of sequence"))
        self.statusBar().showMessage(self.tr("End of sequence"))
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()
        if self.pianola_dialog is not None:
            self.pianola_dialog.clear()
        if self.auto_song_settings and self._current_file is not None:
            self.save_song_settings()
        self._update_action_state()

    def _output_error(self, message: str) -> None:
        self.event_label.setText(self.tr("MIDI output error: {message}").format(message=message))
        self.statusBar().showMessage(message, 10000)
        QMessageBox.warning(self, self.tr("MIDI output"), message)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_window_geometry()
        self.stop()
        if hasattr(self.output, "close"):
            self.output.close()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(self._is_openable_path(Path(url.toLocalFile())) for url in event.mimeData().urls() if url.isLocalFile()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if self.open_paths(files, remember_folder=True):
            event.acceptProposedAction()
        else:
            event.ignore()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dmidiplayer PyQt6 port")
    parser.add_argument("files", nargs="*", help="SMF/KAR files or .lst playlists")
    parser.add_argument(
        "--language",
        default="en",
        help="UI language code, for example en, es, es_EC, or system",
    )
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1] + args.files)
    app.setOrganizationName("dmidiplayer")
    app.setOrganizationDomain("dmidiplayer.local")
    app.setApplicationName("dmidiplayer-py")
    install_translator(app, args.language)
    window = MainWindow(args.files)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

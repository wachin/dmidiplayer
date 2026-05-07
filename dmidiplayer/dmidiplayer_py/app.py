from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

from PyQt6.QtCore import QLocale, QSignalBlocker, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
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
)

from drumstick_py import BackendManager, MidiFileError, MidiOutputError, PianoKeyboard
from .i18n import install_translator
from .player import SequencePlayer
from .settings import AppSettings


MIDI_FILE_SUFFIXES = {".kar", ".mid", ".midi"}
PLAYLIST_FILE_SUFFIXES = {".lst"}
APP_TITLE = "dmidiplayer PyQt6"
HELP_DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


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

        self.general_midi_reset_before_playback = QCheckBox(self.tr("Send GM reset before playback"), general_tab)
        self.general_midi_reset_before_playback.setObjectName("general_midi_reset_before_playback")
        general_form.addRow("", self.general_midi_reset_before_playback)
        self.tabs.addTab(general_tab, self.tr("General"))

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
        self.general_midi_reset_before_playback.setChecked(self._settings.midi_reset_before_playback())

    def restore_defaults(self) -> None:
        self.general_percussion_channel.setValue(AppSettings.DEFAULT_PERCUSSION_CHANNEL)
        self.general_solo_volume_reduction.setValue(AppSettings.DEFAULT_SOLO_VOLUME_REDUCTION)
        self.general_auto_play_on_load.setChecked(AppSettings.DEFAULT_AUTO_PLAY_ON_LOAD)
        self.general_playlist_auto_advance.setChecked(AppSettings.DEFAULT_PLAYLIST_AUTO_ADVANCE)
        self.general_midi_reset_before_playback.setChecked(AppSettings.DEFAULT_MIDI_RESET_BEFORE_PLAYBACK)

    def preferences(self) -> tuple[int, int, bool, bool, bool]:
        return (
            self.general_percussion_channel.value(),
            self.general_solo_volume_reduction.value(),
            self.general_auto_play_on_load.isChecked(),
            self.general_playlist_auto_advance.isChecked(),
            self.general_midi_reset_before_playback.isChecked(),
        )


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
        self.setWindowTitle(self.tr("Channels"))
        self.channel_rows: dict[int, int] = {}
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5, self)
        self.table.setObjectName("channels_table")
        self.table.setHorizontalHeaderLabels(
            [self.tr("Channel"), self.tr("Label"), self.tr("Mute"), self.tr("Solo"), self.tr("Level")]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.resize(420, 320)

    def set_channels(
        self,
        channels: list[int],
        muted_channels: set[int] | None = None,
        solo_channels: set[int] | None = None,
        mute_changed: object | None = None,
        solo_changed: object | None = None,
    ) -> None:
        muted_channels = muted_channels or set()
        solo_channels = solo_channels or set()
        self.table.setRowCount(0)
        self.channel_rows.clear()
        for row, channel in enumerate(channels):
            self.table.insertRow(row)
            channel_item = QTableWidgetItem(str(channel + 1))
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, channel_item)
            self.table.setItem(row, 1, QTableWidgetItem(self.tr("Channel {number}").format(number=channel + 1)))
            mute_checkbox = QCheckBox(self.table)
            mute_checkbox.setChecked(channel in muted_channels)
            if mute_changed is not None:
                mute_checkbox.toggled.connect(lambda checked, ch=channel: mute_changed(ch, checked))
            self.table.setCellWidget(row, 2, mute_checkbox)
            solo_checkbox = QCheckBox(self.table)
            solo_checkbox.setChecked(channel in solo_channels)
            if solo_changed is not None:
                solo_checkbox.toggled.connect(lambda checked, ch=channel: solo_changed(ch, checked))
            self.table.setCellWidget(row, 3, solo_checkbox)
            level = QProgressBar(self.table)
            level.setRange(0, 127)
            level.setValue(0)
            level.setFormat("%v")
            self.table.setCellWidget(row, 4, level)
            self.channel_rows[channel] = row

    def clear_levels(self) -> None:
        for row in self.channel_rows.values():
            level = self.table.cellWidget(row, 2)
            if isinstance(level, QProgressBar):
                level.setValue(0)

    def set_channel_level(self, channel: int, value: int) -> None:
        row = self.channel_rows.get(channel)
        if row is None:
            return
        level = self.table.cellWidget(row, 4)
        if isinstance(level, QProgressBar):
            level.setValue(max(0, min(127, value)))


class MainWindow(QMainWindow):
    def __init__(self, start_files: list[str]) -> None:
        super().__init__()
        self.setWindowTitle(self.tr(APP_TITLE))
        self.resize(900, 520)
        self.setAcceptDrops(True)
        self.settings = AppSettings()
        self._restore_window_geometry()
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
        self.solo_volume_reduction = self.settings.solo_volume_reduction()
        self._pause_requested = False
        self._current_file: str | None = None
        self._current_playlist_path: Path | None = None
        self._playlist_modified = False
        self.channels_dialog: ChannelsDialog | None = None

        self.playlist = QListWidget()
        self.playlist.itemDoubleClicked.connect(lambda item: self.load_file(item.text()))
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
        self.event_label = QLabel(self.tr("MIDI output: {name}").format(name=self.output.name))
        self.connection_combo = QComboBox()
        self.connection_combo.setMinimumWidth(260)
        self.pitch_control = self._spinbox(-12, 12, 0, self.player.set_pitch_shift)
        self.percussion_channel_control = self._spinbox(
            1,
            16,
            self.player.percussion_channel,
            self._set_percussion_channel,
        )
        self.tempo_control = self._spinbox(50, 200, 100, self._set_tempo_percent, "%")
        self.volume_control = self._spinbox(0, 200, 100, self.player.set_volume_percent, "%")
        self.loop_check = QCheckBox(self.tr("Loop"))
        self.loop_check.toggled.connect(self._toggle_loop)
        self.loop_start = self._spinbox(1, 1, 1, self._update_loop_range)
        self.loop_end = self._spinbox(1, 1, 1, self._update_loop_range)
        self.jump_bar = self._spinbox(1, 1, 1, self._jump_bar_value_changed)
        self._updating_position = False

        self._build_actions()
        self._update_action_state()
        self._build_toolbar()
        self._build_menu_bar()
        self._build_layout()
        self._refresh_midi_connections(autoconnect=True)
        if start_files:
            self.open_paths([Path(file_name) for file_name in start_files], remember_folder=False)

    def _build_actions(self) -> None:
        self.open_action = QAction(QIcon.fromTheme("document-open"), self.tr("Open"), self)
        self.open_action.setObjectName("open_action")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_files)
        self.open_playlist_action = QAction(self.tr("Open Playlist"), self)
        self.open_playlist_action.setObjectName("open_playlist_action")
        self.open_playlist_action.triggered.connect(self.open_playlist)
        self.save_playlist_action = QAction(self.tr("Save Playlist"), self)
        self.save_playlist_action.setObjectName("save_playlist_action")
        self.save_playlist_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_playlist_action.triggered.connect(self.save_playlist)
        self.save_playlist_as_action = QAction(self.tr("Save Playlist As"), self)
        self.save_playlist_as_action.setObjectName("save_playlist_as_action")
        self.save_playlist_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_playlist_as_action.triggered.connect(self.save_playlist_as)

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

    def _build_toolbar(self) -> None:
        self.playback_toolbar = QToolBar(self.tr("Playback"), self)
        self.playback_toolbar.setObjectName("playback_toolbar")
        self.addToolBar(self.playback_toolbar)
        self.playback_toolbar.addAction(self.open_action)
        self.playback_toolbar.addSeparator()
        for action in (
            self.previous_action,
            self.play_action,
            self.pause_action,
            self.stop_action,
            self.next_action,
        ):
            self.playback_toolbar.addAction(action)

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("File"))
        file_menu.setObjectName("file_menu")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_playlist_action)
        self.recent_files_menu = file_menu.addMenu(self.tr("Open Recent"))
        self.recent_files_menu.setObjectName("recent_files_menu")
        self._refresh_recent_files_menu()
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
        self.channels_action = QAction(self.tr("Channels"), self)
        self.channels_action.setObjectName("channels_action")
        self.channels_action.triggered.connect(self._show_channels_dialog)
        view_menu.addAction(self.channels_action)
        view_menu.addAction(self.keyboard_action)
        self.rhythm_action = QAction(self.tr("Rhythm"), self)
        self.rhythm_action.setObjectName("toggle_rhythm_action")
        self.rhythm_action.setCheckable(True)
        self.rhythm_action.setChecked(True)
        self.rhythm_action.toggled.connect(self.rhythm_view.setVisible)
        view_menu.addAction(self.rhythm_action)

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
                action = self.recent_files_menu.addAction(str(path))
                action.triggered.connect(lambda checked=False, file_name=str(path): self.load_file(file_name))
        self.recent_files_menu.addSeparator()
        self.clear_recent_action.setEnabled(bool(recent_files))
        self.recent_files_menu.addAction(self.clear_recent_action)

    def _clear_recent_files(self) -> None:
        self.settings.clear_recent_files()
        self._refresh_recent_files_menu()

    def _mark_playlist_modified(self) -> None:
        if self._current_playlist_path is None:
            return
        self._playlist_modified = True
        self._update_window_title()

    def _playlist_selection_changed(self, row: int) -> None:
        self._update_action_state()
        if row < 0 or self.player.sequence.midi is None or self.playlist.count() <= 1:
            return
        self._update_window_title()

    def _reset_loaded_file_state(self, status_message: str) -> None:
        self._current_file = None
        self.position.setEnabled(False)
        self.title_label.setText(self.tr("No file loaded"))
        self.time_label.setText(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
        self.event_label.setText(self.tr("No file loaded"))
        self.rhythm_view.clear()
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.set_channels([])
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
        removed_file = item.text()
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
                self.load_file(current_item.text())
            return
        self._mark_playlist_modified()
        self._update_action_state()
        self._update_window_title()
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
        self._update_action_state()
        self._update_window_title()
        self.statusBar().showMessage(
            self.tr("Moved {name} in playlist").format(name=Path(item.text()).name),
            5000,
        )

    def _sort_playlist(self) -> None:
        if self.playlist.count() < 2:
            return
        selected_path = None
        current_item = self.playlist.currentItem()
        if current_item is not None:
            selected_path = current_item.text()
        paths = sorted((self.playlist.item(row).text() for row in range(self.playlist.count())), key=str.casefold)
        self.playlist.clear()
        for path in paths:
            self.playlist.addItem(path)
        if selected_path is not None:
            self._select_playlist_file(selected_path)
        self._mark_playlist_modified()
        self._update_action_state()
        self._update_window_title()
        self.statusBar().showMessage(self.tr("Playlist sorted"), 5000)

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
        self._update_window_title()
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
        self._update_window_title()
        self.statusBar().showMessage(self.tr("Saved playlist {name}").format(name=playlist_path.name), 5000)
        return playlist_path

    def _playlist_paths(self) -> list[Path]:
        return [Path(self.playlist.item(row).text()) for row in range(self.playlist.count())]

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
            <p>Copyright © 2006-2024 Pedro Lopez-Cabanillas.</p>
            <p>Distributed under the GNU General Public License version 3 or later.</p>
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
        dialog = self._ensure_channels_dialog()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _refresh_channels_dialog(self) -> None:
        if self.channels_dialog is None:
            return
        self.channels_dialog.set_channels(
            self.player.sequence.used_channels(),
            muted_channels=self.player.muted_channels(),
            solo_channels=self.player.solo_channels(),
            mute_changed=self._set_channel_muted,
            solo_changed=self._set_channel_solo,
        )

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
        self.channels_dialog.clear_levels()

    def _create_preferences_dialog(self) -> PreferencesDialog:
        return PreferencesDialog(self, self.settings)

    def _apply_preferences(
        self,
        percussion_channel: int,
        solo_volume_reduction: int,
        auto_play_on_load: bool,
        playlist_auto_advance: bool,
        midi_reset_before_playback: bool,
    ) -> None:
        self.percussion_channel_control.setValue(percussion_channel)
        self.solo_volume_reduction = solo_volume_reduction
        self.settings.set_solo_volume_reduction(solo_volume_reduction)
        self.player.set_solo_volume_reduction(solo_volume_reduction)
        self.auto_play_on_load_action.setChecked(auto_play_on_load)
        self.auto_advance_playlist_action.setChecked(playlist_auto_advance)
        self.player.set_send_reset_before_playback(midi_reset_before_playback)
        self.settings.set_midi_reset_before_playback(midi_reset_before_playback)
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
        left = QVBoxLayout()
        left.addWidget(QLabel(self.tr("List")))
        left.addWidget(self.playlist)
        right = QVBoxLayout()
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
            self.tr("MIDI and playlists (*.mid *.midi *.kar *.lst);;MIDI (*.mid *.midi *.kar);;Playlists (*.lst);;All files (*)"),
        )
        self.open_paths([Path(file_name) for file_name in files], remember_folder=True)

    def open_paths(self, paths: list[Path], remember_folder: bool = False) -> list[Path]:
        openable_paths = [path for path in paths if self._is_openable_path(path)]
        if not openable_paths:
            return []
        if remember_folder:
            self.settings.set_last_folder(openable_paths[0].parent)

        playlist_paths = [path for path in openable_paths if self._is_playlist_file(path)]
        midi_paths = [path for path in openable_paths if self._is_supported_file(path)]
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
        if not self._is_supported_file(path):
            return False
        for row in range(self.playlist.count()):
            if self.playlist.item(row).text() == str(path):
                self.playlist.setCurrentRow(row)
                self._update_action_state()
                return False
        self.playlist.addItem(str(path))
        if mark_modified:
            self._mark_playlist_modified()
        self._update_action_state()
        return True

    def _is_supported_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.casefold() in MIDI_FILE_SUFFIXES

    def _is_playlist_file(self, path: Path) -> bool:
        return path.exists() and path.is_file() and path.suffix.casefold() in PLAYLIST_FILE_SUFFIXES

    def _is_openable_path(self, path: Path) -> bool:
        return self._is_supported_file(path) or self._is_playlist_file(path)

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
        self.title_label.setText(
            self.tr("{title} - format {format}, {tracks} track(s), {ticks} ticks, {seconds:.1f} s").format(
                title=midi.title,
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
        self.settings.add_recent_file(file_name)
        self._refresh_recent_files_menu()
        self._current_file = file_name
        self._update_action_state()
        self._update_window_title()
        self.statusBar().showMessage(self.tr("Ready: {name}").format(name=midi.title))
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
        self.load_file(item.text(), autoplay=autoplay)
        return True

    def _select_playlist_file(self, file_name: str) -> None:
        for row in range(self.playlist.count()):
            if self.playlist.item(row).text() == file_name:
                self.playlist.setCurrentRow(row)
                self._update_action_state()
                self._update_window_title()
                return

    def _update_position(self, tick: int, maximum: int) -> None:
        self._updating_position = True
        self.position.setMaximum(maximum)
        self.position.setValue(min(tick, maximum))
        self._updating_position = False
        self._update_time_label(tick, maximum)

    def _seek_to_slider(self) -> None:
        if self._updating_position:
            return
        self.player.seek(self.position.value())
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()

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
        self._update_time_label(self.position.value(), self.position.maximum())

    def _set_percussion_channel(self, value: int) -> None:
        self.player.set_percussion_channel(value)
        self.settings.set_percussion_channel(self.player.percussion_channel)

    def _update_time_label(self, tick: int, maximum: int) -> None:
        midi = self.player.sequence.midi
        if midi is None:
            self.time_label.setText(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
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
            self.keyboard.note_on(data[0])
            if channel is not None and self.channels_dialog is not None:
                self.channels_dialog.set_channel_level(channel, data[1])
        elif kind in ("note_off", "note_on") and data:
            self.keyboard.note_off(data[0])
            if channel is not None and self.channels_dialog is not None:
                self.channels_dialog.set_channel_level(channel, 0)

    def _finished(self) -> None:
        next_row = self._next_playlist_row() if self.auto_advance_playlist else None
        if next_row is not None and self._load_playlist_row(next_row, autoplay=True):
            return
        self.event_label.setText(self.tr("End of sequence"))
        self.statusBar().showMessage(self.tr("End of sequence"))
        self.keyboard.clear()
        if self.channels_dialog is not None:
            self.channels_dialog.clear_levels()
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

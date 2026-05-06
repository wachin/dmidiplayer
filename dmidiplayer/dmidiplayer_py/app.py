from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from drumstick_py import BackendManager, MidiFileError, MidiOutputError, PianoKeyboard
from .i18n import install_translator
from .player import SequencePlayer
from .settings import AppSettings


class MainWindow(QMainWindow):
    def __init__(self, start_files: list[str]) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("dmidiplayer PyQt6"))
        self.resize(900, 520)
        self.settings = AppSettings()
        self.manager = BackendManager(self)
        self.output = self._create_midi_output()
        self.player = SequencePlayer(self.output, self)
        self.player.positionChanged.connect(self._update_position)
        self.player.eventPlayed.connect(self._event_played)
        self.player.outputError.connect(self._output_error)
        self.player.finished.connect(self._finished)
        self.auto_advance_playlist = True

        self.playlist = QListWidget()
        self.playlist.itemDoubleClicked.connect(lambda item: self.load_file(item.text()))
        self.title_label = QLabel(self.tr("No file loaded"))
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.setTracking(False)
        self.position.setEnabled(False)
        self.position.sliderReleased.connect(self._seek_to_slider)
        self.time_label = QLabel(self.tr("00:00 / 00:00 - 120 BPM - Bar 1/1"))
        self.keyboard = PianoKeyboard()
        self.event_label = QLabel(self.tr("MIDI output: {name}").format(name=self.output.name))
        self.connection_combo = QComboBox()
        self.connection_combo.setMinimumWidth(260)
        self.pitch_control = self._spinbox(-12, 12, 0, self.player.set_pitch_shift)
        self.tempo_control = self._spinbox(50, 200, 100, self._set_tempo_percent, "%")
        self.volume_control = self._spinbox(0, 200, 100, self.player.set_volume_percent, "%")
        self.loop_check = QCheckBox(self.tr("Loop"))
        self.loop_check.toggled.connect(self._toggle_loop)
        self.loop_start = self._spinbox(1, 1, 1, self._update_loop_range)
        self.loop_end = self._spinbox(1, 1, 1, self._update_loop_range)
        self.jump_bar = self._spinbox(1, 1, 1, self._jump_bar_value_changed)
        self._updating_position = False

        self._build_toolbar()
        self._build_layout()
        self._refresh_midi_connections(autoconnect=True)
        for file_name in start_files:
            self.add_file(file_name)
        if start_files:
            self.load_file(start_files[0])

    def _build_toolbar(self) -> None:
        toolbar = QToolBar(self.tr("Playback"), self)
        self.addToolBar(toolbar)
        open_action = QAction(QIcon.fromTheme("document-open"), self.tr("Open"), self)
        open_action.triggered.connect(self.open_files)
        toolbar.addAction(open_action)
        toolbar.addSeparator()
        for text, slot in (
            (self.tr("Previous"), self.previous_file),
            (self.tr("Play"), self.player.play),
            (self.tr("Pause"), self.player.pause),
            (self.tr("Stop"), self.player.stop),
            (self.tr("Next"), self.next_file),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            toolbar.addWidget(button)

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
        controls_layout.addWidget(self._button("0", lambda: self.pitch_control.setValue(0)))
        controls_layout.addWidget(QLabel(self.tr("Tempo:")))
        controls_layout.addWidget(self.tempo_control)
        controls_layout.addWidget(self._button("100%", lambda: self.tempo_control.setValue(100)))
        controls_layout.addWidget(QLabel(self.tr("Volume:")))
        controls_layout.addWidget(self.volume_control)
        controls_layout.addWidget(self._button("100%", lambda: self.volume_control.setValue(100)))
        controls_layout.addWidget(QLabel(self.tr("Bar:")))
        controls_layout.addWidget(self._button(self.tr("Bar -"), self.previous_bar))
        controls_layout.addWidget(self._button(self.tr("Bar +"), self.next_bar))
        controls_layout.addStretch(1)

        loop_row = QWidget()
        loop_layout = QHBoxLayout(loop_row)
        loop_layout.setContentsMargins(0, 0, 0, 0)
        loop_layout.addWidget(QLabel(self.tr("Jump bar:")))
        loop_layout.addWidget(self.jump_bar)
        loop_layout.addWidget(self._button(self.tr("Go"), self.jump_to_bar))
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
        layout.addWidget(self._button(self.tr("Refresh"), self._refresh_midi_connections))
        layout.addWidget(self._button(self.tr("Connect"), self._connect_selected_midi_output))
        layout.addWidget(self._button(self.tr("Disconnect"), self._disconnect_midi_output))
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
            self.tr("Open MIDI"),
            str(self.settings.last_folder(Path.home())),
            self.tr("MIDI (*.mid *.midi *.kar);;All files (*)"),
        )
        if files:
            self.settings.set_last_folder(Path(files[0]).parent)
        for file_name in files:
            self.add_file(file_name)
        if files:
            self.load_file(files[0])

    def add_file(self, file_name: str) -> None:
        path = Path(file_name)
        if path.exists():
            self.playlist.addItem(str(path))

    def load_file(self, file_name: str) -> None:
        try:
            self.player.load_file(file_name)
        except (OSError, MidiFileError) as exc:
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

    def previous_file(self) -> None:
        row = self.playlist.currentRow()
        if row < 0:
            row = 0
        self._load_playlist_row(max(0, row - 1))

    def next_file(self) -> None:
        row = self.playlist.currentRow()
        if row < 0:
            row = 0
        self._load_playlist_row(min(self.playlist.count() - 1, row + 1))

    def _load_playlist_row(self, row: int, autoplay: bool = False) -> bool:
        if row < 0 or row >= self.playlist.count():
            return False
        item = self.playlist.item(row)
        self.playlist.setCurrentRow(row)
        self.load_file(item.text())
        if autoplay:
            self.player.play()
        return True

    def _select_playlist_file(self, file_name: str) -> None:
        for row in range(self.playlist.count()):
            if self.playlist.item(row).text() == file_name:
                self.playlist.setCurrentRow(row)
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
        elif kind in ("note_off", "note_on") and data:
            self.keyboard.note_off(data[0])

    def _finished(self) -> None:
        if self.auto_advance_playlist and self._load_playlist_row(self.playlist.currentRow() + 1, autoplay=True):
            return
        self.event_label.setText(self.tr("End of sequence"))
        self.keyboard.clear()

    def _output_error(self, message: str) -> None:
        self.event_label.setText(self.tr("MIDI output error: {message}").format(message=message))
        self.statusBar().showMessage(message, 10000)
        QMessageBox.warning(self, self.tr("MIDI output"), message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dmidiplayer PyQt6 port")
    parser.add_argument("files", nargs="*", help="SMF/KAR files")
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

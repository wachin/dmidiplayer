from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from drumstick_py import MidiConnection
from dmidiplayer_py.app import MainWindow
from tests.test_sequence_player import OutputStub, chunk, varlen, write_simple_midi


class FakeBackendManager:
    def __init__(self, parent: object | None = None) -> None:
        self.output = OutputStub()
        self.output.name = "Dummy output"

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> OutputStub:
        return self.output


class FakeSettings:
    midi_destination_value = ""

    def __init__(self) -> None:
        self.folder: Path | None = None
        self.saved_midi_destination = ""

    def last_folder(self, fallback: Path) -> Path:
        return self.folder or fallback

    def set_last_folder(self, folder: str | Path) -> None:
        self.folder = Path(folder)

    def midi_destination(self) -> str:
        return self.midi_destination_value

    def set_midi_destination(self, destination: str) -> None:
        self.saved_midi_destination = destination
        type(self).midi_destination_value = destination


class FakeAlsaOutput(OutputStub):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Fake ALSA"
        self.close_count = 0
        self.connected: list[MidiConnection] = []
        self.available_connections = [
            MidiConnection(driver="alsa", name="128:0 QSynth: MIDI", client=128, port=0),
            MidiConnection(driver="alsa", name="129:0 Hardware Synth: MIDI", client=129, port=0),
        ]

    def connections(self) -> list[MidiConnection]:
        return self.available_connections

    def connect_to(self, connection: MidiConnection) -> None:
        if connection not in self.connected:
            self.connected.append(connection)

    def connected_connections(self) -> list[MidiConnection]:
        return list(self.connected)

    def disconnect_all(self) -> None:
        self.connected.clear()

    def close(self) -> None:
        self.close_count += 1


class FakeAlsaBackendManager:
    output = FakeAlsaOutput()

    def __init__(self, parent: object | None = None) -> None:
        type(self).output = FakeAlsaOutput()

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> FakeAlsaOutput:
        return self.output


def write_two_bar_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x58\x04\x04\x02\x18\x08",
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(1920),
            bytes([0x80, 60, 0]),
            varlen(1920),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


class AppPlaylistTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_next_and_previous_select_playlist_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.add_file(str(first))
                window.add_file(str(second))
                window.load_file(str(first))

                window.next_file()
                self.assertEqual(window.playlist.currentRow(), 1)

                window.previous_file()
                self.assertEqual(window.playlist.currentRow(), 0)

    def test_time_label_updates_from_loaded_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "simple.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                self.assertEqual(window.time_label.text(), "00:00 / 00:00 - 120 BPM - Bar 1/1")
                window._update_position(480, 480)
                self.assertEqual(window.time_label.text(), "00:00 / 00:00 - 120 BPM - Bar 1/1")

    def test_loop_controls_use_bar_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "two-bars.mid")
            write_two_bar_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                self.assertEqual(window.loop_start.minimum(), 1)
                self.assertEqual(window.loop_start.maximum(), 2)
                self.assertEqual(window.loop_end.value(), 2)
                self.assertEqual(window.jump_bar.maximum(), 2)

                window.loop_start.setValue(2)
                window.loop_end.setValue(2)

                self.assertEqual(window.player._loop_start_tick, 1920)
                self.assertEqual(window.player._loop_end_tick, 3840)

    def test_bar_navigation_seeks_to_neighboring_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "two-bars.mid")
            write_two_bar_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                window.next_bar()
                self.assertEqual(window.player._position, 1920)

                window.previous_bar()
                self.assertEqual(window.player._position, 0)

    def test_jump_to_bar_seeks_to_requested_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "two-bars.mid")
            write_two_bar_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                window.jump_bar.setValue(2)
                window.jump_to_bar()

                self.assertEqual(window.player._position, 1920)

    def test_open_paths_adds_supported_files_and_loads_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.kar")
            ignored = Path(tmpdir, "notes.txt")
            write_simple_midi(first)
            write_simple_midi(second)
            ignored.write_text("not midi")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                opened = window.open_paths([ignored, first, second], remember_folder=True)

                self.assertEqual(opened, [first, second])
                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertIn("first", window.title_label.text())
                self.assertEqual(window.settings.folder, first.parent)

    def test_open_paths_ignores_unsupported_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ignored = Path(tmpdir, "notes.txt")
            ignored.write_text("not midi")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])

                self.assertEqual(window.open_paths([ignored], remember_folder=True), [])
                self.assertEqual(window.playlist.count(), 0)
                self.assertIsNone(window.settings.folder)

    def test_saved_midi_destination_is_reconnected_on_startup(self) -> None:
        FakeSettings.midi_destination_value = "129:0"
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertEqual(window.output.connected_connections()[0].name, "129:0 Hardware Synth: MIDI")
            self.assertEqual(window.connection_combo.currentText(), "129:0 Hardware Synth: MIDI")
            self.assertEqual(FakeSettings.midi_destination_value, "129:0")

    def test_manual_midi_connection_is_saved(self) -> None:
        FakeSettings.midi_destination_value = ""
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            window.connection_combo.setCurrentIndex(1)
            window._connect_selected_midi_output()

            self.assertEqual(window.output.connected_connections()[-1].name, "129:0 Hardware Synth: MIDI")
            self.assertEqual(FakeSettings.midi_destination_value, "129:0 Hardware Synth: MIDI")

    def test_close_stops_player_and_closes_output(self) -> None:
        FakeSettings.midi_destination_value = ""
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            window.close()

            self.assertEqual(window.output.all_notes_off_count, 1)
            self.assertEqual(window.output.close_count, 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QSlider
from PyQt6.QtCore import Qt

from drumstick_py import MidiConnection, MidiEvent
from dmidiplayer_py.app import MainWindow, PreferencesDialog
from tests.test_sequence_player import OutputStub, chunk, varlen, write_simple_midi


class FakeBackendManager:
    def __init__(self, parent: object | None = None) -> None:
        self.output = OutputStub()
        self.output.name = "Dummy output"

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> OutputStub:
        return self.output


class FakeSettings:
    DEFAULT_PERCUSSION_CHANNEL = 10
    DEFAULT_AUTO_PLAY_ON_LOAD = False
    DEFAULT_PLAYLIST_AUTO_ADVANCE = True
    DEFAULT_SOLO_VOLUME_REDUCTION = 50
    DEFAULT_MIDI_RESET_BEFORE_PLAYBACK = False
    midi_destination_value = ""
    percussion_channel_value = 10
    auto_play_on_load_value = False
    playlist_auto_advance_value = True
    solo_volume_reduction_value = 50
    midi_reset_before_playback_value = False
    playlist_path_value: Path | None = None
    window_geometry_value: tuple[int, int, int, int] | None = None

    def __init__(self) -> None:
        self.folder: Path | None = None
        self.saved_midi_destination = ""
        self.recent: list[Path] = []
        self.saved_window_geometry: tuple[int, int, int, int] | None = None

    def last_folder(self, fallback: Path) -> Path:
        return self.folder or fallback

    def set_last_folder(self, folder: str | Path) -> None:
        self.folder = Path(folder)

    def midi_destination(self) -> str:
        return self.midi_destination_value

    def set_midi_destination(self, destination: str) -> None:
        self.saved_midi_destination = destination
        type(self).midi_destination_value = destination

    def recent_files(self) -> list[Path]:
        return list(self.recent)

    def add_recent_file(self, file_name: str | Path) -> None:
        path = Path(file_name)
        self.recent = [item for item in self.recent if item != path]
        self.recent.insert(0, path)

    def clear_recent_files(self) -> None:
        self.recent.clear()

    def window_geometry(self) -> tuple[int, int, int, int] | None:
        return type(self).window_geometry_value

    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.saved_window_geometry = (x, y, width, height)
        type(self).window_geometry_value = self.saved_window_geometry

    def percussion_channel(self) -> int:
        return type(self).percussion_channel_value

    def set_percussion_channel(self, channel: int) -> None:
        type(self).percussion_channel_value = channel

    def auto_play_on_load(self) -> bool:
        return type(self).auto_play_on_load_value

    def set_auto_play_on_load(self, enabled: bool) -> None:
        type(self).auto_play_on_load_value = enabled

    def playlist_auto_advance(self) -> bool:
        return type(self).playlist_auto_advance_value

    def set_playlist_auto_advance(self, enabled: bool) -> None:
        type(self).playlist_auto_advance_value = enabled

    def solo_volume_reduction(self) -> int:
        return type(self).solo_volume_reduction_value

    def set_solo_volume_reduction(self, value: int) -> None:
        type(self).solo_volume_reduction_value = value

    def midi_reset_before_playback(self) -> bool:
        return type(self).midi_reset_before_playback_value

    def set_midi_reset_before_playback(self, enabled: bool) -> None:
        type(self).midi_reset_before_playback_value = enabled

    def playlist_path(self) -> Path | None:
        return type(self).playlist_path_value

    def set_playlist_path(self, playlist_path: str | Path) -> None:
        type(self).playlist_path_value = Path(playlist_path) if playlist_path else None


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


def write_multichannel_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            varlen(0),
            bytes([0xC0, 10]),
            varlen(0),
            bytes([0xC1, 20]),
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(0),
            bytes([0x91, 64, 80]),
            varlen(480),
            bytes([0x80, 60, 0]),
            varlen(0),
            bytes([0x81, 64, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_text_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x01\x05Hello",
            varlen(0),
            b"\xff\x05\x06Sing!\n",
            varlen(0),
            b"\xff\x06\x05Verse",
            varlen(0),
            b"\xff\x07\x03Cue",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_multitrack_text_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0").replace(b"\x00\x01", b"\x00\x02", 1)
    track_one = b"".join(
        [
            varlen(0),
            b"\xff\x01\x05Intro",
            varlen(0),
            b"\xff\x06\x05Start",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    track_two = b"".join(
        [
            varlen(0),
            b"\xff\x05\x05Line1",
            varlen(120),
            b"\xff\x05\x05Line2",
            varlen(120),
            b"\xff\x07\x04Solo",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track_one) + chunk(b"MTrk", track_two))


def write_cp1252_text_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x01\x0aPrecio \x8010",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_timed_lyrics_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x05\x05Line1",
            varlen(120),
            b"\xff\x05\x05Line2",
            varlen(120),
            b"\xff\x05\x05Line3",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_many_track_midi(path: Path, total_tracks: int, midi_track_indexes: list[int]) -> None:
    header = chunk(b"MThd", struct.pack(">HHH", 1, total_tracks, 480))
    tracks: list[bytes] = []
    for track_index in range(total_tracks):
        track_name = f"Part {track_index + 1}".encode("ascii")
        if track_index in midi_track_indexes:
            channel = track_index % 16
            payload = b"".join(
                [
                    varlen(0),
                    b"\xff\x03" + varlen(len(track_name)) + track_name,
                    varlen(0),
                    bytes([0x90 | channel, 60 + (track_index % 12), 100]),
                    varlen(120),
                    bytes([0x80 | channel, 60 + (track_index % 12), 0]),
                    varlen(0),
                    b"\xff\x2f\x00",
                ]
            )
        else:
            payload = b"".join([varlen(0), b"\xff\x03" + varlen(len(track_name)) + track_name, varlen(0), b"\xff\x2f\x00"])
        tracks.append(chunk(b"MTrk", payload))
    path.write_bytes(header + b"".join(tracks))


def write_track_range_midi(path: Path) -> None:
    header = chunk(b"MThd", struct.pack(">HHH", 1, 2, 480))
    track_one = b"".join(
        [
            varlen(0),
            b"\xff\x03\x06Piano1",
            varlen(0),
            bytes([0x90, 48, 100]),
            varlen(120),
            bytes([0x80, 48, 0]),
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(120),
            bytes([0x80, 60, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    track_two = b"".join(
        [
            varlen(0),
            b"\xff\x03\x06Piano2",
            varlen(0),
            bytes([0x91, 72, 100]),
            varlen(120),
            bytes([0x81, 72, 0]),
            varlen(0),
            bytes([0x91, 84, 100]),
            varlen(120),
            bytes([0x81, 84, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track_one) + chunk(b"MTrk", track_two))


class AppPlaylistTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        FakeSettings.midi_destination_value = ""
        FakeSettings.percussion_channel_value = 10
        FakeSettings.auto_play_on_load_value = False
        FakeSettings.playlist_auto_advance_value = True
        FakeSettings.solo_volume_reduction_value = 50
        FakeSettings.midi_reset_before_playback_value = False
        FakeSettings.playlist_path_value = None
        FakeSettings.window_geometry_value = None

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

    def test_rhythm_view_updates_with_bar_and_beat(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "simple.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                self.assertEqual(window.rhythm_view.summary_label.text(), "Rhythm: 4/4 - Bar 1 Beat 1 - 120 BPM")
                self.assertEqual(window.rhythm_view.beat_labels[0].text(), "1:X")
                self.assertEqual(window.rhythm_view.beat_labels[1].text(), "2:-")

                window._update_position(480, 480)

                self.assertEqual(window.rhythm_view.summary_label.text(), "Rhythm: 4/4 - Bar 1 Beat 2 - 120 BPM")
                self.assertEqual(window.rhythm_view.beat_labels[0].text(), "1:-")
                self.assertEqual(window.rhythm_view.beat_labels[1].text(), "2:X")

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

    def test_open_paths_does_not_duplicate_existing_playlist_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])
                opened = window.open_paths([first, second], remember_folder=True)

                self.assertEqual(opened, [first, second])
                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.playlist.item(0).text(), str(first))
                self.assertEqual(window.playlist.item(1).text(), str(second))
                self.assertEqual(window.playlist.currentRow(), 0)

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

    def test_open_paths_loads_playlist_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            playlist_path = Path(tmpdir, "setlist.lst")
            write_simple_midi(first)
            write_simple_midi(second)
            playlist_path.write_text(f"{first}\n{second}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                opened = window.open_paths([playlist_path], remember_folder=True)

                self.assertEqual(opened, [playlist_path])
                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.windowTitle(), "first.mid [1/2] - setlist.lst - dmidiplayer PyQt6")
                self.assertEqual(window.settings.folder, playlist_path.parent)

    def test_open_paths_loads_playlist_then_appends_explicit_midi_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            third = Path(tmpdir, "third.mid")
            playlist_path = Path(tmpdir, "setlist.lst")
            write_simple_midi(first)
            write_simple_midi(second)
            write_simple_midi(third)
            playlist_path.write_text(f"{first}\n{second}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                opened = window.open_paths([playlist_path, third], remember_folder=True)

                self.assertEqual(opened, [playlist_path, third])
                self.assertEqual(window.playlist.count(), 3)
                self.assertEqual(window.playlist.item(2).text(), str(third))
                self.assertEqual(window.windowTitle(), "first.mid [1/3] - *setlist.lst - dmidiplayer PyQt6")

    def test_startup_argument_can_be_playlist_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            playlist_path = Path(tmpdir, "setlist.lst")
            write_simple_midi(first)
            write_simple_midi(second)
            playlist_path.write_text(f"{first}\n{second}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(playlist_path)])

                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.windowTitle(), "first.mid [1/2] - setlist.lst - dmidiplayer PyQt6")

    def test_add_file_reuses_existing_playlist_row_instead_of_duplicating(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])

                added = window.add_file(str(first))

                self.assertFalse(added)
                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.playlist.currentRow(), 0)

    def test_menu_bar_contains_primary_menus_and_actions(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            menus = [action.text() for action in window.menuBar().actions()]

            self.assertEqual(menus, ["File", "Playback", "View", "Tools", "Help"])
            self.assertIsNotNone(window.findChild(type(window.open_action), "open_action"))
            self.assertIsNotNone(window.findChild(type(window.open_playlist_action), "open_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.save_playlist_action), "save_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.save_playlist_as_action), "save_playlist_as_action"))
            self.assertIsNotNone(window.findChild(type(window.play_action), "play_action"))
            self.assertIsNotNone(window.findChild(type(window.statusbar_action), "toggle_statusbar_action"))
            self.assertIsNotNone(window.findChild(type(window.channels_action), "channels_action"))
            self.assertIsNotNone(window.findChild(type(window.pianola_action), "pianola_action"))
            self.assertIsNotNone(window.findChild(type(window.lyrics_action), "lyrics_action"))
            self.assertIsNotNone(window.findChild(type(window.keyboard_action), "toggle_keyboard_action"))
            self.assertIsNotNone(window.findChild(type(window.rhythm_action), "toggle_rhythm_action"))
            self.assertIsNotNone(window.findChild(type(window.next_bar_action), "next_bar_action"))
            self.assertIsNotNone(window.findChild(type(window.jump_bar_action), "jump_bar_action"))
            self.assertIsNotNone(window.findChild(type(window.reset_pitch_action), "reset_pitch_action"))
            self.assertIsNotNone(window.findChild(type(window.reset_tempo_action), "reset_tempo_action"))
            self.assertIsNotNone(window.findChild(type(window.reset_volume_action), "reset_volume_action"))
            self.assertIsNotNone(window.findChild(type(window.repeat_playlist_action), "repeat_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.shuffle_playlist_action), "shuffle_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.auto_play_on_load_action), "auto_play_on_load_action"))
            self.assertIsNotNone(
                window.findChild(type(window.auto_advance_playlist_action), "auto_advance_playlist_action")
            )
            self.assertIsNotNone(window.findChild(type(window.preferences_action), "preferences_action"))
            self.assertIsNotNone(window.findChild(type(window.refresh_midi_action), "refresh_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.connect_midi_action), "connect_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.disconnect_midi_action), "disconnect_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.move_up_action), "move_up_action"))
            self.assertIsNotNone(window.findChild(type(window.move_down_action), "move_down_action"))
            self.assertIsNotNone(window.findChild(type(window.sort_playlist_action), "sort_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.remove_selected_action), "remove_selected_action"))
            self.assertIsNotNone(window.findChild(type(window.clear_playlist_action), "clear_playlist_action"))
            self.assertIsNotNone(window.findChild(type(window.help_contents_action), "help_contents_action"))
            self.assertIsNotNone(window.findChild(type(window.user_guide_action), "user_guide_action"))
            self.assertIsNotNone(window.findChild(type(window.about_action), "about_action"))

    def test_successful_load_adds_recent_file_menu_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "recent.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_file(str(path))

                self.assertEqual(window.settings.recent_files(), [path])
                self.assertEqual(window.recent_files_menu.actions()[0].text(), str(path))
                self.assertTrue(window.clear_recent_action.isEnabled())

    def test_clear_recent_files_action_updates_menu(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "recent.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_file(str(path))
                window.clear_recent_action.trigger()

                self.assertEqual(window.settings.recent_files(), [])
                self.assertEqual(window.recent_files_menu.actions()[0].text(), "No recent files")
                self.assertFalse(window.clear_recent_action.isEnabled())

    def test_recent_file_action_loads_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "recent.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.settings.add_recent_file(path)
                window._refresh_recent_files_menu()
                window.recent_files_menu.actions()[0].trigger()

                self.assertIn("recent", window.title_label.text())

    def test_view_menu_toggles_status_bar(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window.statusbar_action.setChecked(False)
            self.assertTrue(window.statusBar().isHidden())
            window.statusbar_action.setChecked(True)
            self.assertFalse(window.statusBar().isHidden())

    def test_view_menu_toggles_keyboard(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window.keyboard_action.setChecked(False)
            self.assertTrue(window.keyboard.isHidden())
            window.keyboard_action.setChecked(True)
            self.assertFalse(window.keyboard.isHidden())

    def test_channels_action_opens_dialog(self) -> None:
        shown: list[str] = []

        def fake_show(dialog: object) -> None:
            shown.append(getattr(dialog, "windowTitle")())

        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            patch("dmidiplayer_py.app.ChannelsDialog.show", fake_show),
            patch("dmidiplayer_py.app.ChannelsDialog.raise_", lambda dialog: None),
            patch("dmidiplayer_py.app.ChannelsDialog.activateWindow", lambda dialog: None),
        ):
            window = MainWindow([])
            window.channels_action.trigger()

            self.assertEqual(shown, ["Channels"])

    def test_lyrics_action_opens_dialog(self) -> None:
        shown: list[str] = []

        def fake_show(dialog: object) -> None:
            shown.append(getattr(dialog, "windowTitle")())

        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            patch("dmidiplayer_py.app.LyricsDialog.show", fake_show),
            patch("dmidiplayer_py.app.LyricsDialog.raise_", lambda dialog: None),
            patch("dmidiplayer_py.app.LyricsDialog.activateWindow", lambda dialog: None),
        ):
            window = MainWindow([])
            window.lyrics_action.trigger()

            self.assertEqual(shown, ["Lyrics"])

    def test_pianola_action_opens_dialog(self) -> None:
        shown: list[str] = []

        def fake_show(dialog: object) -> None:
            shown.append(getattr(dialog, "windowTitle")())

        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            patch("dmidiplayer_py.app.PianolaDialog.show", fake_show),
            patch("dmidiplayer_py.app.PianolaDialog.raise_", lambda dialog: None),
            patch("dmidiplayer_py.app.PianolaDialog.activateWindow", lambda dialog: None),
        ):
            window = MainWindow([])
            window.pianola_action.trigger()

            self.assertEqual(shown, ["Piano Player"])

    def test_view_menu_toggles_rhythm_panel(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window.rhythm_action.setChecked(False)
            self.assertTrue(window.rhythm_view.isHidden())
            window.rhythm_action.setChecked(True)
            self.assertFalse(window.rhythm_view.isHidden())

    def test_channels_dialog_lists_used_channels_with_editable_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()

                self.assertEqual(dialog.table.rowCount(), 2)
                self.assertEqual(dialog.table.item(0, 0).text(), "1")
                self.assertEqual(dialog.table.item(1, 0).text(), "2")
                self.assertEqual(dialog.table.item(0, 1).text(), "Channel 1")
                self.assertTrue(bool(dialog.table.item(0, 1).flags() & Qt.ItemFlag.ItemIsEditable))
                self.assertIsInstance(dialog.table.cellWidget(0, 2), QCheckBox)
                self.assertIsInstance(dialog.table.cellWidget(0, 3), QCheckBox)
                self.assertIsInstance(dialog.table.cellWidget(0, 4), QComboBox)
                self.assertIsInstance(dialog.table.cellWidget(0, 5), QCheckBox)
                self.assertIsInstance(dialog.table.cellWidget(0, 6), QSlider)
                self.assertEqual(dialog.table.cellWidget(0, 4).currentIndex(), 10)
                self.assertEqual(dialog.table.cellWidget(1, 4).currentIndex(), 20)
                self.assertIn("Music Box", dialog.table.cellWidget(0, 4).currentText())

    def test_pianola_dialog_shows_only_tracks_with_midi(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "tracks.mid")
            write_many_track_midi(path, total_tracks=4, midi_track_indexes=[1, 3])

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_pianola_dialog()
                tab = dialog.tabs.widget(0)
                labels = [label.text() for label in tab.findChildren(QLabel) if label.objectName().startswith("pianola_track_label_")]
                details = [label.text() for label in tab.findChildren(QLabel) if label.objectName().startswith("pianola_track_detail_")]

                self.assertEqual(dialog.tabs.count(), 1)
                self.assertEqual(labels, ["Track 2 - Part 2", "Track 4 - Part 4"])
                self.assertEqual(details, ["Channels: 2", "Channels: 4"])

    def test_pianola_dialog_splits_tracks_into_tabs_of_eight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "many-tracks.mid")
            write_many_track_midi(path, total_tracks=17, midi_track_indexes=list(range(17)))

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_pianola_dialog()

                self.assertEqual(dialog.tabs.count(), 3)
                self.assertEqual(dialog.tabs.tabText(0), "Tracks 1-8")
                self.assertEqual(dialog.tabs.tabText(1), "Tracks 9-16")
                self.assertEqual(dialog.tabs.tabText(2), "Tracks 17-17")
                self.assertEqual(dialog.tabs.currentIndex(), 0)

    def test_pianola_dialog_tracks_follow_played_channel_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "tracks.mid")
            write_many_track_midi(path, total_tracks=3, midi_track_indexes=[0, 1])

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_pianola_dialog()
                keyboard = dialog.findChild(type(window.keyboard), "pianola_track_keyboard_1")

                window._event_played(MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100])))
                self.assertIn(60, keyboard._active)

                window._event_played(MidiEvent(tick=120, kind="note_off", channel=0, data=bytes([60, 0])))
                self.assertNotIn(60, keyboard._active)

    def test_pianola_dialog_keyboards_follow_used_note_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "ranges.mid")
            write_track_range_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_pianola_dialog()
                keyboard_one = dialog.findChild(type(window.keyboard), "pianola_track_keyboard_1")
                keyboard_two = dialog.findChild(type(window.keyboard), "pianola_track_keyboard_2")

                self.assertEqual((keyboard_one._min_note, keyboard_one._max_note), (48, 60))
                self.assertEqual((keyboard_two._min_note, keyboard_two._max_note), (72, 84))

    def test_channels_dialog_level_updates_from_played_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()

                window._event_played(type("Evt", (), {"kind": "note_on", "channel": 1, "data": bytes([64, 80])})())
                level = dialog.table.cellWidget(1, 7)
                self.assertEqual(level.value(), 80)

                window._event_played(type("Evt", (), {"kind": "note_off", "channel": 1, "data": bytes([64, 0])})())
                self.assertEqual(level.value(), 0)

    def test_channels_dialog_mute_checkbox_updates_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()
                mute_checkbox = dialog.table.cellWidget(0, 2)

                mute_checkbox.setChecked(True)

                self.assertIn(0, window.player.muted_channels())
                self.assertEqual(window.statusBar().currentMessage(), "Channel 1 muted")

    def test_channels_dialog_solo_checkbox_updates_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()
                solo_checkbox = dialog.table.cellWidget(1, 3)

                solo_checkbox.setChecked(True)

                self.assertIn(1, window.player.solo_channels())
                self.assertEqual(window.statusBar().currentMessage(), "Channel 2 solo")

    def test_channels_dialog_program_spinbox_updates_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()
                program_combo = dialog.table.cellWidget(0, 4)

                program_combo.setCurrentIndex(33)

                self.assertEqual(window.player.channel_program(0), 33)
                self.assertEqual(window.statusBar().currentMessage(), "Channel 1 program 33")

    def test_channels_dialog_lock_checkbox_updates_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()
                lock_checkbox = dialog.table.cellWidget(0, 5)

                lock_checkbox.setChecked(True)

                self.assertIn(0, window.player.locked_channels())
                self.assertEqual(window.statusBar().currentMessage(), "Channel 1 locked")

    def test_channels_dialog_volume_slider_updates_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multi.mid")
            write_multichannel_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_channels_dialog()
                volume_slider = dialog.table.cellWidget(0, 6)

                volume_slider.setValue(60)

                self.assertEqual(window.player.channel_volume_percent(0), 60)
                self.assertEqual(window.statusBar().currentMessage(), "Channel 1 volume 60%")

    def test_lyrics_dialog_shows_text_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                text = dialog.browser.toPlainText()

                self.assertIn("Text: Hello", text)
                self.assertIn("Lyric: Sing!", text)
                self.assertIn("Marker: Verse", text)
                self.assertIn("Cue Point: Cue", text)

    def test_lyrics_dialog_filter_selects_event_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                dialog.filter_combo.setCurrentIndex(1)
                self.assertEqual(dialog.browser.toPlainText().strip(), "Lyric: Sing!")

                dialog.filter_combo.setCurrentIndex(3)
                self.assertEqual(dialog.browser.toPlainText().strip(), "Marker: Verse")

    def test_lyrics_dialog_track_filter_defaults_to_most_text_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multitrack-text.mid")
            write_multitrack_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                self.assertEqual(dialog.track_combo.currentText(), "Track 2")
                text = dialog.browser.toPlainText()
                self.assertIn("Lyric: Line1", text)
                self.assertIn("Lyric: Line2", text)
                self.assertIn("Cue Point: Solo", text)
                self.assertNotIn("Intro", text)

    def test_lyrics_dialog_prefers_track_with_lyrics_over_plain_text_track(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multitrack-text.mid")
            write_multitrack_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                self.assertEqual(dialog.track_combo.currentText(), "Track 2")
                self.assertIn("Lyric: Line1", dialog.browser.toPlainText())
                self.assertNotIn("Text: Intro", dialog.browser.toPlainText())

    def test_lyrics_dialog_track_filter_can_show_all_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multitrack-text.mid")
            write_multitrack_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                dialog.track_combo.setCurrentIndex(0)
                text = dialog.browser.toPlainText()

                self.assertIn("Track 1 - Text: Intro", text)
                self.assertIn("Track 1 - Marker: Start", text)
                self.assertIn("Track 2 - Lyric: Line1", text)

    def test_lyrics_dialog_track_filter_can_select_individual_track(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "multitrack-text.mid")
            write_multitrack_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                dialog.track_combo.setCurrentIndex(1)
                self.assertEqual(dialog.browser.toPlainText().strip(), "Text: Intro\nMarker: Start")

    def test_lyrics_dialog_copy_button_uses_filtered_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.filter_combo.setCurrentIndex(1)

                dialog.copy_button.click()

                self.assertEqual(QApplication.clipboard().text().strip(), "Lyric: Sing!")

    def test_lyrics_dialog_font_button_updates_browser_font(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)
            chosen_font = QFont("Sans Serif", 15)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.QFontDialog.getFont", return_value=(chosen_font, True)),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                dialog.font_button.click()

                self.assertEqual(dialog.browser.font().family(), chosen_font.family())
                self.assertEqual(dialog.browser.font().pointSize(), chosen_font.pointSize())

    def test_lyrics_dialog_save_button_writes_filtered_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            save_path = Path(tmpdir, "lyrics.txt")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.QFileDialog.getSaveFileName", return_value=(str(save_path), "")),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.filter_combo.setCurrentIndex(1)

                dialog.save_button.click()

                self.assertEqual(save_path.read_text(encoding="utf-8").strip(), "Lyric: Sing!")
                self.assertEqual(window.statusBar().currentMessage(), "Saved lyrics to lyrics.txt (utf-8)")

    def test_lyrics_dialog_save_button_uses_selected_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            save_path = Path(tmpdir, "lyrics-latin1.txt")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.QFileDialog.getSaveFileName", return_value=(str(save_path), "")),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.encoding_combo.setCurrentIndex(dialog.encoding_combo.findData("latin-1"))
                dialog.browser.setPlainText("Lyric: Canción")

                dialog.save_button.click()

                self.assertEqual(save_path.read_text(encoding="latin-1"), "Lyric: Canción")
                self.assertEqual(window.statusBar().currentMessage(), "Saved lyrics to lyrics-latin1.txt (latin-1)")

    def test_lyrics_dialog_fullscreen_button_toggles_window_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.show()

                dialog.fullscreen_button.click()

                self.assertTrue(dialog.isFullScreen())
                self.assertEqual(dialog.fullscreen_button.text(), "Window")

                dialog.fullscreen_button.click()

                self.assertFalse(dialog.isFullScreen())
                self.assertEqual(dialog.fullscreen_button.text(), "Fullscreen")

    def test_lyrics_dialog_escape_exits_fullscreen(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.show()
                dialog.fullscreen_button.setChecked(True)

                dialog.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))

                self.assertFalse(dialog.isFullScreen())
                self.assertFalse(dialog.fullscreen_button.isChecked())

    def test_lyrics_dialog_auto_detects_cp1252_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "cp1252.mid")
            write_cp1252_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                self.assertEqual(dialog.encoding_combo.currentData(), None)
                self.assertIn("Text: Precio €10", dialog.browser.toPlainText())

    def test_lyrics_dialog_manual_encoding_override_redecodes_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "cp1252.mid")
            write_cp1252_text_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()

                dialog.encoding_combo.setCurrentIndex(dialog.encoding_combo.findData("latin-1"))

                self.assertEqual(dialog.browser.toPlainText().strip(), "Text: Precio \x8010")

    def test_lyrics_dialog_highlights_past_current_and_future_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "timed-lyrics.mid")
            write_timed_lyrics_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.filter_combo.setCurrentIndex(dialog.filter_combo.findData("lyrics"))

                self.assertEqual(dialog._event_state(0, dialog._visible_events), "current")
                self.assertEqual(dialog._event_state(1, dialog._visible_events), "future")

                window._update_position(120, 240)
                self.assertEqual(dialog._event_state(0, dialog._visible_events), "past")
                self.assertEqual(dialog._event_state(1, dialog._visible_events), "current")
                self.assertEqual(dialog._event_state(2, dialog._visible_events), "future")

                window._update_position(240, 240)
                self.assertEqual(dialog._event_state(2, dialog._visible_events), "current")

    def test_lyrics_dialog_print_button_prints_filtered_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)
            printed: list[str] = []

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.QPrintDialog.exec", return_value=int(QDialog.DialogCode.Accepted)),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog.filter_combo.setCurrentIndex(1)
                dialog._print_document = lambda printer: printed.append(dialog.current_text())

                dialog.print_button.click()

                self.assertEqual(printed, ["Lyric: Sing!\n"])
                self.assertEqual(window.statusBar().currentMessage(), "Printed lyrics")

    def test_lyrics_dialog_print_button_respects_cancelled_dialog(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "text.mid")
            write_text_midi(path)
            printed: list[str] = []

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.QPrintDialog.exec", return_value=int(QDialog.DialogCode.Rejected)),
            ):
                window = MainWindow([str(path)])
                dialog = window._ensure_lyrics_dialog()
                dialog._print_document = lambda printer: printed.append(dialog.current_text())

                dialog.print_button.click()

                self.assertEqual(printed, [])
                self.assertNotEqual(window.statusBar().currentMessage(), "Printed lyrics")

    def test_playback_actions_have_keyboard_shortcuts(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertEqual(window.open_action.shortcut().toString(), "Ctrl+O")
            self.assertEqual(window.play_action.shortcut().toString(), "Space")
            self.assertEqual(window.pause_action.shortcut().toString(), "P")
            self.assertEqual(window.stop_action.shortcut().toString(), "Esc")
            self.assertEqual(window.previous_action.shortcut().toString(), "Ctrl+Left")
            self.assertEqual(window.next_action.shortcut().toString(), "Ctrl+Right")
            self.assertEqual(window.previous_bar_action.shortcut().toString(), "Alt+Left")
            self.assertEqual(window.next_bar_action.shortcut().toString(), "Alt+Right")
            self.assertEqual(window.jump_bar_action.shortcut().toString(), "Ctrl+J")
            self.assertEqual(window.move_up_action.shortcut().toString(), "Alt+Up")
            self.assertEqual(window.move_down_action.shortcut().toString(), "Alt+Down")

    def test_shared_actions_drive_reset_controls_and_jump(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "two-bars.mid")
            write_two_bar_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])
                window.pitch_control.setValue(5)
                window.tempo_control.setValue(150)
                window.volume_control.setValue(80)
                window.jump_bar.setValue(2)

                window.reset_pitch_action.trigger()
                window.reset_tempo_action.trigger()
                window.reset_volume_action.trigger()
                window.jump_bar_action.trigger()

                self.assertEqual(window.pitch_control.value(), 0)
                self.assertEqual(window.tempo_control.value(), 100)
                self.assertEqual(window.volume_control.value(), 100)
                self.assertEqual(window.player._position, 1920)

    def test_bar_navigation_actions_seek_to_neighboring_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "two-bars.mid")
            write_two_bar_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                window.next_bar_action.trigger()
                self.assertEqual(window.player._position, 1920)

                window.previous_bar_action.trigger()
                self.assertEqual(window.player._position, 0)

    def test_stop_menu_action_turns_off_notes(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window.stop_action.trigger()

            self.assertEqual(window.output.all_notes_off_count, 1)

    def test_status_bar_reports_load_and_playback_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "simple.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_file(str(path))

                self.assertEqual(window.statusBar().currentMessage(), "Ready: simple.mid")

                window.player.started.emit()
                self.assertEqual(window.statusBar().currentMessage(), "Playing")

                window.pause_action.trigger()
                self.assertEqual(window.statusBar().currentMessage(), "Paused")

                window.stop_action.trigger()
                self.assertEqual(window.statusBar().currentMessage(), "Stopped")

                window.player.finished.emit()
                self.assertEqual(window.statusBar().currentMessage(), "End of sequence")

    def test_playback_actions_are_disabled_until_file_load(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertFalse(window.play_action.isEnabled())
            self.assertFalse(window.pause_action.isEnabled())
            self.assertFalse(window.previous_action.isEnabled())
            self.assertFalse(window.next_action.isEnabled())
            self.assertFalse(window.previous_bar_action.isEnabled())
            self.assertFalse(window.next_bar_action.isEnabled())
            self.assertTrue(window.stop_action.isEnabled())

    def test_playback_actions_update_after_file_load_and_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])

                self.assertTrue(window.play_action.isEnabled())
                self.assertTrue(window.pause_action.isEnabled())
                self.assertFalse(window.previous_action.isEnabled())
                self.assertTrue(window.next_action.isEnabled())
                self.assertTrue(window.previous_bar_action.isEnabled())
                self.assertTrue(window.next_bar_action.isEnabled())

                window.next_file()

                self.assertTrue(window.previous_action.isEnabled())
                self.assertFalse(window.next_action.isEnabled())
                self.assertTrue(window.move_up_action.isEnabled())
                self.assertFalse(window.move_down_action.isEnabled())

    def test_playlist_reorder_actions_are_disabled_until_selection_allows_them(self) -> None:
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
                self.assertFalse(window.move_up_action.isEnabled())
                self.assertFalse(window.move_down_action.isEnabled())
                self.assertFalse(window.sort_playlist_action.isEnabled())

                window.open_paths([first, second], remember_folder=True)
                self.assertFalse(window.move_up_action.isEnabled())
                self.assertTrue(window.move_down_action.isEnabled())
                self.assertTrue(window.sort_playlist_action.isEnabled())

                window.next_file()
                self.assertTrue(window.move_up_action.isEnabled())
                self.assertFalse(window.move_down_action.isEnabled())

    def test_move_selected_playlist_item_updates_order_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            third = Path(tmpdir, "third.mid")
            write_simple_midi(first)
            write_simple_midi(second)
            write_simple_midi(third)
            playlist_path = Path(tmpdir, "setlist.lst")
            playlist_path.write_text(f"{first}\n{second}\n{third}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_playlist_file(playlist_path)
                window.next_file()

                window.move_up_action.trigger()

                self.assertEqual(window.playlist.item(0).text(), str(second))
                self.assertEqual(window.playlist.item(1).text(), str(first))
                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.windowTitle(), "second.mid [1/3] - *setlist.lst - dmidiplayer PyQt6")

    def test_sort_playlist_action_orders_rows_alphabetically_and_keeps_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            zulu = Path(tmpdir, "zulu.mid")
            bravo = Path(tmpdir, "bravo.mid")
            alpha = Path(tmpdir, "alpha.mid")
            write_simple_midi(zulu)
            write_simple_midi(bravo)
            write_simple_midi(alpha)
            playlist_path = Path(tmpdir, "setlist.lst")
            playlist_path.write_text(f"{zulu}\n{bravo}\n{alpha}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_playlist_file(playlist_path)
                window.load_file(str(bravo))

                window.sort_playlist_action.trigger()

                self.assertEqual(
                    [window.playlist.item(row).text() for row in range(window.playlist.count())],
                    [str(alpha), str(bravo), str(zulu)],
                )
                self.assertEqual(window.playlist.currentRow(), 1)
                self.assertEqual(window.windowTitle(), "bravo.mid [2/3] - *setlist.lst - dmidiplayer PyQt6")
                self.assertEqual(window.statusBar().currentMessage(), "Playlist sorted")

    def test_playlist_remove_selected_action_loads_neighbor_when_current_song_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])

                window.remove_selected_action.trigger()

                self.assertEqual(window.playlist.count(), 1)
                self.assertEqual(window.playlist.currentItem().text(), str(second))
                self.assertEqual(window.windowTitle(), "second.mid - dmidiplayer PyQt6")

    def test_playlist_clear_action_resets_loaded_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "solo.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                window.clear_playlist_action.trigger()

                self.assertEqual(window.playlist.count(), 0)
                self.assertEqual(window.windowTitle(), "dmidiplayer PyQt6")
                self.assertEqual(window.title_label.text(), "No file loaded")
                self.assertFalse(window.position.isEnabled())
                self.assertFalse(window.play_action.isEnabled())
                self.assertFalse(window.clear_playlist_action.isEnabled())
                self.assertEqual(window.statusBar().currentMessage(), "Playlist cleared")

    def test_window_title_tracks_current_song_and_playlist_position(self) -> None:
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

                self.assertEqual(window.windowTitle(), "dmidiplayer PyQt6")

                window.open_paths([first, second], remember_folder=True)
                self.assertEqual(window.windowTitle(), "first.mid [1/2] - dmidiplayer PyQt6")

                window.next_file()
                self.assertEqual(window.windowTitle(), "second.mid [2/2] - dmidiplayer PyQt6")

    def test_window_title_uses_song_name_without_playlist_context_for_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "solo.mid")
            write_simple_midi(path)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(path)])

                self.assertEqual(window.windowTitle(), "solo.mid - dmidiplayer PyQt6")

    def test_save_playlist_file_uses_relative_entries_when_possible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            songs = Path(tmpdir, "songs")
            songs.mkdir()
            first = songs / "first.mid"
            second = songs / "second.mid"
            playlist_path = Path(tmpdir, "setlist.lst")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])
                window.save_playlist_file(playlist_path)

                self.assertEqual(playlist_path.read_text(encoding="utf-8"), "songs/first.mid\nsongs/second.mid\n")
                self.assertEqual(FakeSettings.playlist_path_value, playlist_path)

    def test_load_playlist_file_resolves_relative_entries_and_remembers_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            songs = Path(tmpdir, "songs")
            songs.mkdir()
            first = songs / "first.mid"
            second = songs / "second.mid"
            write_simple_midi(first)
            write_simple_midi(second)
            playlist_path = Path(tmpdir, "setlist.lst")
            playlist_path.write_text("songs/first.mid\nsongs/second.mid\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                loaded = window.load_playlist_file(playlist_path)

                self.assertEqual(loaded, [first, second])
                self.assertEqual(window.playlist.count(), 2)
                self.assertEqual(window.windowTitle(), "first.mid [1/2] - setlist.lst - dmidiplayer PyQt6")
                self.assertEqual(FakeSettings.playlist_path_value, playlist_path)

    def test_saved_playlist_title_shows_unsaved_marker_after_modification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            third = Path(tmpdir, "third.mid")
            write_simple_midi(first)
            write_simple_midi(second)
            write_simple_midi(third)
            playlist_path = Path(tmpdir, "setlist.lst")
            playlist_path.write_text(f"{first}\n{second}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_playlist_file(playlist_path)
                window.add_file(str(third))

                self.assertEqual(window.windowTitle(), "first.mid [1/3] - *setlist.lst - dmidiplayer PyQt6")

    def test_load_playlist_file_keeps_absolute_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)
            playlist_path = Path(tmpdir, "absolute.lst")
            playlist_path.write_text(f"{first}\n{second}\n", encoding="utf-8")

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                loaded = window.load_playlist_file(playlist_path)

                self.assertEqual(loaded, [first, second])
                self.assertEqual(window.playlist.item(0).text(), str(first))
                self.assertEqual(window.playlist.item(1).text(), str(second))

    def test_auto_play_on_load_preference_starts_playback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "auto.mid")
            write_simple_midi(path)
            FakeSettings.auto_play_on_load_value = True

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([])
                window.load_file(str(path))

                self.assertTrue(window.player._playing)
                self.assertEqual(window.statusBar().currentMessage(), "Playing")

    def test_playback_preference_actions_persist_in_settings(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window.auto_play_on_load_action.setChecked(True)
            window.auto_advance_playlist_action.setChecked(False)

            self.assertTrue(FakeSettings.auto_play_on_load_value)
            self.assertFalse(FakeSettings.playlist_auto_advance_value)
            self.assertTrue(window.auto_play_on_load)
            self.assertFalse(window.auto_advance_playlist)

    def test_preferences_dialog_loads_current_settings_and_restores_defaults(self) -> None:
        FakeSettings.percussion_channel_value = 3
        FakeSettings.solo_volume_reduction_value = 35
        FakeSettings.auto_play_on_load_value = True
        FakeSettings.playlist_auto_advance_value = False
        FakeSettings.midi_reset_before_playback_value = True
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            dialog = window._create_preferences_dialog()

            self.assertIsInstance(dialog, PreferencesDialog)
            self.assertEqual(dialog.tabs.tabText(0), "General")
            self.assertEqual(dialog.general_percussion_channel.value(), 3)
            self.assertEqual(dialog.general_solo_volume_reduction.value(), 35)
            self.assertTrue(dialog.general_auto_play_on_load.isChecked())
            self.assertFalse(dialog.general_playlist_auto_advance.isChecked())
            self.assertTrue(dialog.general_midi_reset_before_playback.isChecked())

            dialog.restore_defaults()

            self.assertEqual(dialog.general_percussion_channel.value(), 10)
            self.assertEqual(dialog.general_solo_volume_reduction.value(), 50)
            self.assertFalse(dialog.general_auto_play_on_load.isChecked())
            self.assertTrue(dialog.general_playlist_auto_advance.isChecked())
            self.assertFalse(dialog.general_midi_reset_before_playback.isChecked())

    def test_preferences_dialog_applies_values_to_window_and_settings(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            window._apply_preferences(12, 40, True, False, True)

            self.assertEqual(window.player.percussion_channel, 12)
            self.assertEqual(window.percussion_channel_control.value(), 12)
            self.assertEqual(window.solo_volume_reduction, 40)
            self.assertTrue(window.auto_play_on_load)
            self.assertFalse(window.auto_advance_playlist)
            self.assertTrue(window.player.send_reset_before_playback)
            self.assertEqual(FakeSettings.percussion_channel_value, 12)
            self.assertEqual(FakeSettings.solo_volume_reduction_value, 40)
            self.assertTrue(FakeSettings.auto_play_on_load_value)
            self.assertFalse(FakeSettings.playlist_auto_advance_value)
            self.assertTrue(FakeSettings.midi_reset_before_playback_value)
            self.assertEqual(window.statusBar().currentMessage(), "Preferences updated")

    def test_repeat_playlist_restarts_from_first_song_at_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])
                window.next_file()
                window.repeat_playlist_action.setChecked(True)

                window.player.finished.emit()

                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.windowTitle(), "first.mid [1/2] - dmidiplayer PyQt6")

    def test_playlist_auto_advance_preference_can_disable_end_of_song_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])
                window.auto_advance_playlist_action.setChecked(False)

                window.player.finished.emit()

                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.statusBar().currentMessage(), "End of sequence")

    def test_end_of_sequence_message_remains_when_repeat_playlist_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            write_simple_midi(first)
            write_simple_midi(second)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([str(first), str(second)])
                window.next_file()
                window.repeat_playlist_action.setChecked(False)

                window.player.finished.emit()

                self.assertEqual(window.playlist.currentRow(), 1)
                self.assertEqual(window.statusBar().currentMessage(), "End of sequence")

    def test_shuffle_playlist_changes_manual_next_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            third = Path(tmpdir, "third.mid")
            write_simple_midi(first)
            write_simple_midi(second)
            write_simple_midi(third)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.random.choice", return_value=2),
            ):
                window = MainWindow([str(first), str(second), str(third)])
                window.shuffle_playlist_action.setChecked(True)

                window.next_file()

                self.assertEqual(window.playlist.currentRow(), 2)
                self.assertEqual(window.windowTitle(), "third.mid [3/3] - dmidiplayer PyQt6")

    def test_shuffle_playlist_changes_auto_advance_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            third = Path(tmpdir, "third.mid")
            write_simple_midi(first)
            write_simple_midi(second)
            write_simple_midi(third)

            with (
                patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
                patch("dmidiplayer_py.app.random.choice", return_value=0),
            ):
                window = MainWindow([str(first), str(second), str(third)])
                window.next_file()
                window.shuffle_playlist_action.setChecked(True)

                window.player.finished.emit()

                self.assertEqual(window.playlist.currentRow(), 0)
                self.assertEqual(window.windowTitle(), "first.mid [1/3] - dmidiplayer PyQt6")

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

    def test_tools_menu_midi_actions_drive_connection_flow(self) -> None:
        FakeSettings.midi_destination_value = ""
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertEqual(window.connection_combo.count(), 2)

            window.refresh_midi_action.trigger()
            self.assertEqual(window.connection_combo.count(), 2)

            window.connection_combo.setCurrentIndex(1)
            window.connect_midi_action.trigger()
            self.assertEqual(window.output.connected_connections()[-1].name, "129:0 Hardware Synth: MIDI")

            window.disconnect_midi_action.trigger()
            self.assertEqual(window.output.connected_connections(), [])

    def test_help_doc_path_falls_back_to_existing_local_file(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            path = window._help_doc_path()

            self.assertTrue(path.exists())
            self.assertEqual(path.name, "index.md")

    def test_user_guide_path_falls_back_to_existing_local_file(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            path = window._user_guide_path()

            self.assertTrue(path.exists())
            self.assertEqual(path.name, "pyqt6-user-guide.md")

    def test_about_and_help_actions_open_dialogs(self) -> None:
        dialogs: list[str] = []

        def fake_exec(dialog: object) -> int:
            dialogs.append(getattr(dialog, "windowTitle")())
            return 0

        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            patch("PyQt6.QtWidgets.QDialog.exec", fake_exec),
        ):
            window = MainWindow([])
            window.about_action.trigger()
            window.help_contents_action.trigger()
            window.user_guide_action.trigger()

            self.assertEqual(dialogs, ["About", "Help Contents", "User Guide"])
            about_html = window._about_html()
            self.assertIn("Python/PyQt6 port", about_html)
            self.assertIn("Pedro Lopez-Cabanillas", about_html)
            self.assertIn("Washington Indacochea Delgado", about_html)
            self.assertIn("mailto:plcl@users.sf.net", about_html)
            self.assertIn("mailto:linuxfrontier@proton.me", about_html)
            self.assertIn('title="plcl@users.sf.net"', about_html)
            self.assertIn('title="linuxfrontier@proton.me"', about_html)
            self.assertIn("Technologies used in this port", about_html)
            self.assertIn("PyQt6 Qt Widgets", about_html)

    def test_preferences_action_opens_dialog(self) -> None:
        dialogs: list[str] = []

        def fake_exec(dialog: object) -> int:
            dialogs.append(getattr(dialog, "windowTitle")())
            return int(QDialog.DialogCode.Accepted)

        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            patch("dmidiplayer_py.app.PreferencesDialog.exec", fake_exec),
        ):
            window = MainWindow([])
            window.preferences_action.trigger()

            self.assertEqual(dialogs, ["Preferences"])

    def test_close_stops_player_and_closes_output(self) -> None:
        FakeSettings.midi_destination_value = ""
        FakeSettings.window_geometry_value = None
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            window.close()

            self.assertEqual(window.output.all_notes_off_count, 1)
            self.assertEqual(window.output.close_count, 1)

    def test_window_geometry_is_restored_from_settings(self) -> None:
        FakeSettings.window_geometry_value = (40, 50, 640, 360)
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertEqual(window.width(), 640)
            self.assertEqual(window.height(), 360)

    def test_window_geometry_is_saved_on_close(self) -> None:
        FakeSettings.window_geometry_value = None
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeAlsaBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            window.resize(700, 420)
            window.close()

            self.assertIsNotNone(window.settings.saved_window_geometry)
            self.assertEqual(window.settings.saved_window_geometry[2:], (700, 420))

    def test_percussion_channel_setting_initializes_and_persists_control(self) -> None:
        FakeSettings.percussion_channel_value = 2
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertEqual(window.player.percussion_channel, 2)
            self.assertEqual(window.percussion_channel_control.value(), 2)

            window.percussion_channel_control.setValue(11)

            self.assertEqual(window.player.percussion_channel, 11)
            self.assertEqual(FakeSettings.percussion_channel_value, 11)

    def test_midi_reset_preference_initializes_player(self) -> None:
        FakeSettings.midi_reset_before_playback_value = True
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])

            self.assertTrue(window.player.send_reset_before_playback)


if __name__ == "__main__":
    unittest.main()

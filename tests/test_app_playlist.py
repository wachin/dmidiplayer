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
    percussion_channel_value = 10
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

    def setUp(self) -> None:
        FakeSettings.midi_destination_value = ""
        FakeSettings.percussion_channel_value = 10
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

    def test_menu_bar_contains_primary_menus_and_actions(self) -> None:
        with (
            patch("dmidiplayer_py.app.BackendManager", FakeBackendManager),
            patch("dmidiplayer_py.app.AppSettings", FakeSettings),
        ):
            window = MainWindow([])
            menus = [action.text() for action in window.menuBar().actions()]

            self.assertEqual(menus, ["File", "Playback", "View", "Tools", "Help"])
            self.assertIsNotNone(window.findChild(type(window.open_action), "open_action"))
            self.assertIsNotNone(window.findChild(type(window.play_action), "play_action"))
            self.assertIsNotNone(window.findChild(type(window.statusbar_action), "toggle_statusbar_action"))
            self.assertIsNotNone(window.findChild(type(window.keyboard_action), "toggle_keyboard_action"))
            self.assertIsNotNone(window.findChild(type(window.next_bar_action), "next_bar_action"))
            self.assertIsNotNone(window.findChild(type(window.refresh_midi_action), "refresh_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.connect_midi_action), "connect_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.disconnect_midi_action), "disconnect_midi_action"))
            self.assertIsNotNone(window.findChild(type(window.help_contents_action), "help_contents_action"))
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

            self.assertEqual(dialogs, ["About", "Help Contents"])
            self.assertIn("Python/PyQt6 port", window._about_html())

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


if __name__ == "__main__":
    unittest.main()

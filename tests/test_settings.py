from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dmidiplayer_py.settings import AppSettings


class AppSettingsTest(unittest.TestCase):
    def test_last_folder_is_saved_in_app_data_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            folder = Path(tmpdir, "music")
            fallback = Path(tmpdir)
            folder.mkdir()

            settings = AppSettings(base_dir)
            settings.set_last_folder(folder)
            restored = AppSettings(base_dir)

            self.assertEqual(restored.last_folder(fallback), folder)
            self.assertTrue((base_dir / "settings.ini").exists())

    def test_missing_last_folder_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            fallback = Path(tmpdir)

            settings = AppSettings(base_dir)

            self.assertEqual(settings.last_folder(fallback), fallback)

    def test_recent_files_are_saved_most_recent_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            first = Path(tmpdir, "first.mid")
            second = Path(tmpdir, "second.mid")
            first.write_text("")
            second.write_text("")

            settings = AppSettings(base_dir)
            settings.add_recent_file(first)
            settings.add_recent_file(second)
            settings.add_recent_file(first)
            restored = AppSettings(base_dir)

            self.assertEqual(restored.recent_files(), [first, second])

    def test_recent_files_keep_last_ten_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            files = []
            for index in range(12):
                path = Path(tmpdir, f"song-{index}.mid")
                path.write_text("")
                files.append(path)

            settings = AppSettings(base_dir)
            for path in files:
                settings.add_recent_file(path)
            restored = AppSettings(base_dir)

            self.assertEqual(restored.recent_files(), list(reversed(files[-10:])))

    def test_clear_recent_files_removes_saved_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            path = Path(tmpdir, "song.mid")
            path.write_text("")

            settings = AppSettings(base_dir)
            settings.add_recent_file(path)
            settings.clear_recent_files()
            restored = AppSettings(base_dir)

            self.assertEqual(restored.recent_files(), [])

    def test_window_geometry_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")

            settings = AppSettings(base_dir)
            settings.set_window_geometry(10, 20, 900, 520)
            restored = AppSettings(base_dir)

            self.assertEqual(restored.window_geometry(), (10, 20, 900, 520))

    def test_invalid_window_geometry_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")

            settings = AppSettings(base_dir)
            settings.set_window_geometry(10, 20, 0, 520)
            restored = AppSettings(base_dir)

            self.assertIsNone(restored.window_geometry())

    def test_percussion_channel_defaults_to_general_midi_channel_10(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = AppSettings(Path(tmpdir, "appdata"))

            self.assertEqual(settings.percussion_channel(), 10)

    def test_percussion_channel_is_saved_and_clamped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")

            settings = AppSettings(base_dir)
            settings.set_percussion_channel(2)
            self.assertEqual(AppSettings(base_dir).percussion_channel(), 2)

            settings.set_percussion_channel(30)
            self.assertEqual(AppSettings(base_dir).percussion_channel(), 16)

            settings.set_percussion_channel(0)
            self.assertEqual(AppSettings(base_dir).percussion_channel(), 1)

    def test_playlist_path_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            playlist = Path(tmpdir, "setlist.lst")
            playlist.write_text("")

            settings = AppSettings(base_dir)
            settings.set_playlist_path(playlist)

            self.assertEqual(AppSettings(base_dir).playlist_path(), playlist)

    def test_empty_playlist_path_clears_saved_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")
            playlist = Path(tmpdir, "setlist.lst")
            playlist.write_text("")

            settings = AppSettings(base_dir)
            settings.set_playlist_path(playlist)
            settings.set_playlist_path("")

            self.assertIsNone(AppSettings(base_dir).playlist_path())

    def test_midi_destination_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")

            settings = AppSettings(base_dir)
            settings.set_midi_destination("128:0 QSynth: MIDI")
            restored = AppSettings(base_dir)

            self.assertEqual(restored.midi_destination(), "128:0 QSynth: MIDI")

    def test_empty_midi_destination_clears_saved_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir, "appdata")

            settings = AppSettings(base_dir)
            settings.set_midi_destination("128:0 QSynth: MIDI")
            settings.set_midi_destination("")
            restored = AppSettings(base_dir)

            self.assertEqual(restored.midi_destination(), "")

    def test_unwritable_app_data_falls_back_to_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            blocking_file = Path(tmpdir, "not-a-directory")
            blocking_file.write_text("")

            settings = AppSettings(blocking_file)

            self.assertNotEqual(settings.base_dir, blocking_file)
            self.assertTrue(settings.path.exists() or settings.base_dir.exists())


if __name__ == "__main__":
    unittest.main()

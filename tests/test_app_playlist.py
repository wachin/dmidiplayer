from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.app import MainWindow
from tests.test_sequence_player import OutputStub, write_simple_midi


class FakeBackendManager:
    def __init__(self, parent: object | None = None) -> None:
        self.output = OutputStub()
        self.output.name = "Dummy output"

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> OutputStub:
        return self.output


class FakeSettings:
    def __init__(self) -> None:
        self.folder: Path | None = None

    def last_folder(self, fallback: Path) -> Path:
        return self.folder or fallback

    def set_last_folder(self, folder: str | Path) -> None:
        self.folder = Path(folder)


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


if __name__ == "__main__":
    unittest.main()

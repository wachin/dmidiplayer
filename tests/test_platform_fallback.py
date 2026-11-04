from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from drumstick_py import MidiOutputError, PianoKeyboard
from drumstick_py.rt import AlsaAudioInfo
from dmidiplayer_py.app import MainWindow
from tests.test_app_playlist import FakeSettings, write_multichannel_midi
from tests.test_channel_selector_and_pianola import reset_fake_settings
from tests.test_sequence_player import OutputStub


class UnavailableAlsaBackend:
    """Simulates Windows/macOS or a Linux host without ALSA sequencer."""

    def __init__(self, parent: object | None = None) -> None:
        self.dummy = OutputStub()
        self.dummy.name = "Dummy output"

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> OutputStub:
        if driver == "alsa":
            raise MidiOutputError("No se pudo cargar libasound.so.2")
        return self.dummy

    def alsa_audio_info(self) -> AlsaAudioInfo:
        return AlsaAudioInfo(available=False, cards=[], pcms=[])

    def connections(self, driver: str = "dummy") -> list[object]:
        return []


class PlatformFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_window_starts_with_dummy_output_when_alsa_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "song.mid")
            write_multichannel_midi(path)
            reset_fake_settings()
            with (
                patch("dmidiplayer_py.app.BackendManager", UnavailableAlsaBackend),
                patch("dmidiplayer_py.app.AppSettings", FakeSettings),
            ):
                window = MainWindow([], output_driver="alsa")
                self.addCleanup(window.close)
                self.assertEqual(window._output_driver, "dummy")
                self.assertEqual(window.output.name, "Dummy output")
                self.assertIn("ALSA is not available", window.statusBar().currentMessage())
                # The rest of the application remains usable.
                window.open_paths([path])
                self.assertEqual(window.playlist.count(), 1)
                self.assertIsNone(window.findChild(PianoKeyboard))
                window.player.play()
                self.assertTrue(window.player.is_playing)
                window.stop()


if __name__ == "__main__":
    unittest.main()

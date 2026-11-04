from __future__ import annotations

import time
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.player import SequencePlayer
from drumstick_py import BackendManager, MidiEvent
from drumstick_py.sonivox import SonivoxOutput, sonivox_available


@unittest.skipUnless(sonivox_available(), "libsonivox3/libpulse-simple are not available")
class SonivoxBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_sends_gm_events_and_closes(self) -> None:
        output = SonivoxOutput()
        try:
            output.send_event(MidiEvent(tick=0, kind="program_change", channel=9, data=bytes([0])))
            output.send_event(MidiEvent(tick=0, kind="note_on", channel=9, data=bytes([36, 100])))
            output.send_event(MidiEvent(tick=1, kind="note_off", channel=9, data=bytes([36, 0])))
            output.all_notes_off()
        finally:
            output.close()

    def test_real_file_playback(self) -> None:
        song = Path(__file__).resolve().parents[1] / "MIDI-Karaoke" / "Amor_amor_amor-Annette_Moreno.mid"
        if not song.is_file():
            self.skipTest("test MIDI file is missing")
        output = SonivoxOutput()
        try:
            player = SequencePlayer(output)
            player.load_file(str(song))
            player.play()
            deadline = time.perf_counter() + 1.5
            while time.perf_counter() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
            player.stop()
        finally:
            output.close()

    def test_backend_manager_lists_sonivox(self) -> None:
        manager = BackendManager()
        self.assertIn("sonivox", manager.output_drivers())
        connections = manager.connections("sonivox")
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].name, "SonivoxEAS")

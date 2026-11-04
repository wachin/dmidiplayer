from __future__ import annotations

import time
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.player import SequencePlayer
from drumstick_py import BackendManager, MidiEvent
from drumstick_py.fluidsynth import (
    FluidSynthOutput,
    default_soundfont_path,
    fluidsynth_available,
)
from tests.test_sequence_player import write_simple_midi


@unittest.skipUnless(fluidsynth_available(), "libfluidsynth is not available")
class FluidSynthBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_output(self) -> FluidSynthOutput:
        soundfont = default_soundfont_path()
        if soundfont is None:
            self.skipTest("no General MIDI SoundFont installed")
        return FluidSynthOutput(start_audio=False, soundfont=soundfont)

    def test_drum_channel_uses_the_drum_bank(self) -> None:
        output = self.make_output()
        try:
            self.assertEqual(output.channel_preset_bank(9), 128)
            output.send_event(MidiEvent(tick=0, kind="program_change", channel=9, data=bytes([0])))
            # A stray Bank Select 0/0 must not turn percussion melodic.
            output.send_event(MidiEvent(tick=0, kind="control_change", channel=9, data=bytes([0, 0])))
            output.send_event(MidiEvent(tick=0, kind="control_change", channel=9, data=bytes([32, 0])))
            output.send_event(MidiEvent(tick=0, kind="program_change", channel=9, data=bytes([0])))
            self.assertEqual(output.channel_preset_bank(9), 128)
            output.send_event(MidiEvent(tick=0, kind="note_on", channel=9, data=bytes([36, 100])))
            output.send_event(MidiEvent(tick=1, kind="note_off", channel=9, data=bytes([36, 0])))
            output.all_notes_off()
        finally:
            output.close()

    def test_percussion_channel_can_move(self) -> None:
        output = self.make_output()
        try:
            output.set_percussion_channel(10)
            self.assertEqual(output.channel_preset_bank(10), 128)
            output.set_percussion_channel(9)
            self.assertEqual(output.channel_preset_bank(9), 128)
        finally:
            output.close()

    def test_xg_reset_cannot_turn_drums_melodic(self) -> None:
        output = self.make_output()
        try:
            output.send_event(
                MidiEvent(tick=0, kind="sysex", data=bytes.fromhex("f0 43 10 4c 00 00 7e 00 f7"))
            )
            output.send_event(MidiEvent(tick=0, kind="control_change", channel=9, data=bytes([0, 0])))
            output.send_event(MidiEvent(tick=0, kind="control_change", channel=9, data=bytes([32, 0])))
            output.send_event(MidiEvent(tick=0, kind="program_change", channel=9, data=bytes([0])))
            self.assertEqual(output.channel_preset_bank(9), 128)
        finally:
            output.close()

    def test_real_file_keeps_the_drum_preset(self) -> None:
        output = self.make_output()
        try:
            player = SequencePlayer(output)
            song = Path(__file__).resolve().parents[1] / "MIDI-Karaoke" / "Amor_amor_amor-Annette_Moreno.mid"
            if not song.is_file():
                self.skipTest("test MIDI file is missing")
            player.load_file(str(song))
            player.play()
            deadline = time.perf_counter() + 1.5
            while time.perf_counter() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
            player.stop()
            self.assertEqual(output.channel_preset_bank(9), 128)
            self.assertIn("trumpet", output.channel_preset_name(0).casefold())
        finally:
            output.close()

    def test_new_song_resets_stale_channel_state(self) -> None:
        output = self.make_output()
        try:
            # Simulate the state a previous XG/GS file can leave behind:
            # channel 10 switched to a melodic bank and preset.
            lib = output._lib.lib
            synth = output._synth
            lib.fluid_synth_set_channel_type(synth, 9, 0)
            lib.fluid_synth_bank_select(synth, 9, 0)
            lib.fluid_synth_program_change(synth, 9, 0)
            self.assertEqual(output.channel_preset_bank(9), 0)

            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir, "clean.mid")
                write_simple_midi(path)
                player = SequencePlayer(output)
                player.load_file(str(path))
                player.play()
                player.stop()

            self.assertEqual(output.channel_preset_bank(9), 128)
        finally:
            output.close()

    def test_backend_manager_lists_fluidsynth(self) -> None:
        manager = BackendManager()
        self.assertIn("fluidsynth", manager.output_drivers())
        connections = manager.connections("fluidsynth")
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].name, "FluidSynth")

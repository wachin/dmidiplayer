from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from drumstick_py import MidiEvent
from dmidiplayer_py.player import SequencePlayer


def varlen(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= (value & 0x7F) | 0x80
        value >>= 7
    out = bytearray()
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            return bytes(out)


def chunk(name: bytes, payload: bytes) -> bytes:
    return name + struct.pack(">I", len(payload)) + payload


def write_simple_midi(path: Path) -> None:
    header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
    track = b"".join(
        [
            varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(480),
            bytes([0x80, 60, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


class OutputStub:
    def __init__(self) -> None:
        self.all_notes_off_count = 0
        self.events: list[object] = []

    def send_event(self, event: object) -> None:
        self.events.append(event)

    def all_notes_off(self) -> None:
        self.all_notes_off_count += 1


class SequencePlayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_seek_updates_position_and_next_event(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "simple.mid")
            write_simple_midi(path)
            player.load_file(str(path))

        player.seek(240)

        self.assertEqual(player._position, 240)
        self.assertEqual(player._position_us, 250_000)
        self.assertEqual(player._index, 2)
        self.assertGreaterEqual(output.all_notes_off_count, 1)

    def test_pause_turns_off_current_notes(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)
        player._playing = True

        player.pause()

        self.assertFalse(player._playing)
        self.assertEqual(output.all_notes_off_count, 1)

    def test_pitch_shift_transposes_note_events(self) -> None:
        player = SequencePlayer(OutputStub())
        player.set_pitch_shift(2)

        event = MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100]))
        shifted = player._playable_event(event)

        self.assertIsNotNone(shifted)
        self.assertEqual(shifted.data, bytes([62, 100]))

    def test_pitch_shift_change_turns_off_current_notes(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)

        player.set_pitch_shift(-2)

        self.assertEqual(output.all_notes_off_count, 1)

    def test_pitch_shift_same_value_does_not_repeat_all_notes_off(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)

        player.set_pitch_shift(-2)
        player.set_pitch_shift(-2)

        self.assertEqual(output.all_notes_off_count, 1)

    def test_pitch_shift_skips_percussion_channel(self) -> None:
        player = SequencePlayer(OutputStub())
        player.set_pitch_shift(2)

        event = MidiEvent(tick=0, kind="note_on", channel=9, data=bytes([60, 100]))
        shifted = player._playable_event(event)

        self.assertIs(shifted, event)

    def test_pitch_shift_drops_notes_outside_midi_range(self) -> None:
        player = SequencePlayer(OutputStub())
        player.set_pitch_shift(12)

        event = MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([120, 100]))

        self.assertIsNone(player._playable_event(event))

    def test_tempo_and_pitch_controls_are_clamped(self) -> None:
        player = SequencePlayer(OutputStub())

        player.set_tempo_percent(250)
        player.set_pitch_shift(-20)

        self.assertEqual(player.tempo_percent, 200)
        self.assertEqual(player.pitch_shift, -12)

    def test_volume_control_change_is_scaled(self) -> None:
        player = SequencePlayer(OutputStub())
        player.set_volume_percent(150)

        event = MidiEvent(tick=0, kind="control_change", channel=0, data=bytes([7, 80]))
        scaled = player._playable_event(event)

        self.assertEqual(player.volume_percent, 150)
        self.assertEqual(scaled.data, bytes([7, 120]))

    def test_volume_control_change_is_clamped_to_midi_range(self) -> None:
        player = SequencePlayer(OutputStub())
        player.set_volume_percent(200)

        event = MidiEvent(tick=0, kind="control_change", channel=0, data=bytes([7, 100]))
        scaled = player._playable_event(event)

        self.assertEqual(scaled.data, bytes([7, 127]))

    def test_set_volume_sends_cc7_to_all_channels(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)

        player.set_volume_percent(80)

        self.assertEqual(len(output.events), 16)
        self.assertEqual(output.events[0].data, bytes([7, 80]))

    def test_loop_rewinds_to_start_tick_when_end_is_reached(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "simple.mid")
            write_simple_midi(path)
            player.load_file(str(path))

        player.set_loop_range(0, 240)
        player.set_loop_enabled(True)
        player._playing = True
        player._position_us = 300_000
        player._base_position_us = 300_000

        player._tick()

        self.assertTrue(player.loop_enabled)
        self.assertEqual(player._position, 0)
        self.assertEqual(player._index, 0)
        self.assertGreaterEqual(output.all_notes_off_count, 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from drumstick_py import MidiFileError, read_smf


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


def read_track(track: bytes):
    data = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480)) + chunk(b"MTrk", track)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir, "system.mid")
        path.write_bytes(data)
        return read_smf(path)


class SystemMessageTest(unittest.TestCase):
    def test_system_common_data_is_consumed(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(0),
                bytes([0xF1, 0x00]),  # MIDI time code quarter frame, 1 data byte
                varlen(0),
                bytes([0x91, 64, 80]),  # explicit status after system common
                varlen(0),
                bytes([0x40, 0x50]),  # running status on channel 1
                varlen(0),
                bytes([0x81, 64, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_track(track)
        notes = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual(
            [(event.kind, event.channel, event.data) for event in notes],
            [
                ("note_on", 0, bytes([60, 100])),
                ("note_on", 1, bytes([64, 80])),
                ("note_on", 1, bytes([64, 80])),
                ("note_off", 1, bytes([64, 0])),
            ],
        )

    def test_song_position_pointer_uses_two_data_bytes(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0xF2, 0x01, 0x02]),
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(0),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_track(track)
        notes = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0].data, bytes([60, 100]))

    def test_realtime_bytes_are_ignored(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(0),
                bytes([0xF8]),  # timing clock
                varlen(0),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_track(track)
        notes = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual([event.kind for event in notes], ["note_on", "note_off"])

    def test_truncated_system_message_raises(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0xF1]),  # missing data byte
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        with self.assertRaises(MidiFileError):
            read_track(track)


if __name__ == "__main__":
    unittest.main()

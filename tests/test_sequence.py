from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dmidiplayer_py.sequence import Sequence, supported_text_encodings


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
    return name + len(payload).to_bytes(4, "big") + payload


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


def write_program_only_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x01\x00\x02\x01\xe0")
    track_one = b"".join(
        [
            varlen(0),
            bytes([0xC0, 40]),
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
            bytes([0x99, 35, 100]),
            varlen(120),
            bytes([0x89, 35, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track_one) + chunk(b"MTrk", track_two))


def write_bank_select_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            bytes([0xB0, 0, 16]),
            varlen(0),
            bytes([0xB0, 32, 3]),
            varlen(0),
            bytes([0xC0, 40]),
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(120),
            bytes([0x80, 60, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_cp1252_named_midi(path: Path) -> None:
    header = chunk(b"MThd", b"\x00\x00\x00\x01\x01\xe0")
    track = b"".join(
        [
            varlen(0),
            b"\xff\x03\x07Piano \x80",
            varlen(0),
            b"\xff\x04\x05Caf\xe9s",
            varlen(0),
            bytes([0x90, 60, 100]),
            varlen(120),
            bytes([0x80, 60, 0]),
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


class SequenceTest(unittest.TestCase):
    def test_supported_text_encodings_include_common_and_extra_entries(self) -> None:
        encodings = supported_text_encodings()
        data = dict(encodings)

        self.assertEqual(encodings[0], ("UTF-8", "utf-8"))
        self.assertEqual(encodings[1], ("Latin-1", "latin-1"))
        self.assertEqual(encodings[2], ("CP1252", "cp1252"))
        self.assertEqual(data["CP437"], "cp437")
        self.assertEqual(data["UTF-16"], "utf-16")

    def test_text_events_use_sequence_encoding_when_no_override_is_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "cp1252.mid")
            write_cp1252_text_midi(path)
            sequence = Sequence()
            sequence.load_file(path)

            self.assertEqual(sequence.text_events()[0].text, "Precio €10")

            sequence.set_text_encoding("latin-1")

            self.assertEqual(sequence.text_events()[0].text, "Precio \x8010")

    def test_text_events_still_allow_manual_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "cp1252.mid")
            write_cp1252_text_midi(path)
            sequence = Sequence()
            sequence.load_file(path)
            sequence.set_text_encoding("latin-1")

            event = sequence.text_events()[0]

            self.assertEqual(event.text, "Precio \x8010")
            self.assertEqual(event.decoded_text("cp1252"), "Precio €10")

    def test_default_channel_labels_fall_back_to_instrument_and_percussion_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "programs.mid")
            write_program_only_midi(path)
            sequence = Sequence()
            sequence.load_file(path)

            self.assertEqual(
                sequence.default_channel_labels(),
                {
                    0: "Violin",
                    9: "Percussion 36",
                },
            )

    def test_initial_banks_reads_msb_and_lsb_bank_select(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "banks.mid")
            write_bank_select_midi(path)
            sequence = Sequence()
            sequence.load_file(path)

            self.assertEqual(sequence.initial_banks(), {0: 2051})

    def test_midi_track_infos_use_selected_encoding_for_track_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "named-cp1252.mid")
            write_cp1252_named_midi(path)
            sequence = Sequence()
            sequence.load_file(path)

            infos = sequence.midi_track_infos()
            self.assertEqual(infos[0]["track_name"], "Piano €")
            self.assertEqual(infos[0]["instrument_name"], "Cafés")

            sequence.set_text_encoding("latin-1")
            infos = sequence.midi_track_infos()
            self.assertEqual(infos[0]["track_name"], "Piano \x80")
            self.assertEqual(infos[0]["instrument_name"], "Cafés")


if __name__ == "__main__":
    unittest.main()

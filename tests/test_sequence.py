from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dmidiplayer_py.sequence import Sequence


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


class SequenceTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

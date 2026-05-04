from __future__ import annotations

import ctypes
import unittest

from drumstick_py.rt import (
    AlsaSequencerOutput,
    MidiConnection,
    MidiOutputError,
    SND_SEQ_EVENT_LENGTH_MASK,
    SND_SEQ_EVENT_LENGTH_VARIABLE,
    SND_SEQ_EVENT_SYSEX,
    _SndSeqEvent,
)


class AlsaEventTest(unittest.TestCase):
    def test_sysex_event_is_marked_as_variable_length(self) -> None:
        class OutputStub:
            _port = 0

            def _base_event(self, event_type: int):
                return AlsaSequencerOutput._base_event(self, event_type)

        output = OutputStub()

        event = AlsaSequencerOutput._make_sysex_event(output, bytes.fromhex("41 10 42 12 40 00 7f 00 41 f7"))

        self.assertEqual(event.type, SND_SEQ_EVENT_SYSEX)
        self.assertEqual(event.flags & SND_SEQ_EVENT_LENGTH_MASK, SND_SEQ_EVENT_LENGTH_VARIABLE)
        self.assertEqual(event.data.ext.len, 11)
        self.assertTrue(event._payload.raw.startswith(b"\xf0\x41"))
        self.assertTrue(event._payload.raw.endswith(b"\xf7\x00"))

    def test_snd_seq_event_layout_matches_expected_size(self) -> None:
        self.assertEqual(_SndSeqEvent.type.offset, 0)
        self.assertEqual(_SndSeqEvent.queue.offset, 3)
        self.assertEqual(_SndSeqEvent.time.offset, 4)
        self.assertEqual(_SndSeqEvent.source.offset, 12)
        self.assertEqual(_SndSeqEvent.dest.offset, 14)
        self.assertEqual(_SndSeqEvent.data.offset, 16)
        self.assertEqual(ctypes.sizeof(_SndSeqEvent), 28)

    def test_connect_and_disconnect_track_active_connections(self) -> None:
        class FakeLib:
            def __init__(self) -> None:
                self.connected: list[tuple[int, int, int]] = []
                self.disconnected: list[tuple[int, int, int]] = []

            def snd_seq_connect_to(self, seq, source_port: int, client: int, port: int) -> int:
                self.connected.append((source_port, client, port))
                return 0

            def snd_seq_disconnect_to(self, seq, source_port: int, client: int, port: int) -> int:
                self.disconnected.append((source_port, client, port))
                return 0

        class FakeAlsa:
            def __init__(self) -> None:
                self.lib = FakeLib()

            def error(self, code: int) -> str:
                return f"error {code}"

        class OutputStub:
            _alsa = FakeAlsa()
            _seq = object()
            _port = 7
            _connected: dict[tuple[int, int], MidiConnection] = {}

            def connections(self) -> list[MidiConnection]:
                return [MidiConnection(driver="alsa", name="128:0 QSynth: MIDI", client=128, port=0)]

            def connected_connections(self) -> list[MidiConnection]:
                return AlsaSequencerOutput.connected_connections(self)

        output = OutputStub()
        connection = output.connections()[0]

        AlsaSequencerOutput.connect_to(output, connection)
        AlsaSequencerOutput.connect_to(output, connection)
        self.assertEqual(output._alsa.lib.connected, [(7, 128, 0)])
        self.assertEqual([item.name for item in output.connected_connections()], ["128:0 QSynth: MIDI"])

        AlsaSequencerOutput.disconnect_from(output, "qsynth")
        self.assertEqual(output._alsa.lib.disconnected, [(7, 128, 0)])
        self.assertEqual(output.connected_connections(), [])

    def test_disconnect_unknown_connection_by_name_reports_error(self) -> None:
        class OutputStub:
            _connected: dict[tuple[int, int], MidiConnection] = {}

            def connected_connections(self) -> list[MidiConnection]:
                return AlsaSequencerOutput.connected_connections(self)

        with self.assertRaisesRegex(MidiOutputError, "No hay una conexion ALSA activa"):
            AlsaSequencerOutput.disconnect_from(OutputStub(), "qsynth")


if __name__ == "__main__":
    unittest.main()

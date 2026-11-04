from __future__ import annotations

import unittest

from drumstick_py import MidiEvent
from drumstick_py.rt import (
    AlsaSequencerOutput,
    SND_SEQ_EVENT_CHANPRESS,
    SND_SEQ_EVENT_CONTROLLER,
    SND_SEQ_EVENT_KEYPRESS,
    SND_SEQ_EVENT_LENGTH_MASK,
    SND_SEQ_EVENT_LENGTH_VARIABLE,
    SND_SEQ_EVENT_NOTEON,
    SND_SEQ_EVENT_NOTEOFF,
    SND_SEQ_EVENT_PGMCHANGE,
    SND_SEQ_EVENT_PITCHBEND,
    SND_SEQ_EVENT_SYSEX,
    SND_SEQ_QUEUE_DIRECT,
)


class EncodingOutput(AlsaSequencerOutput):
    """Encoder-only instance: no ALSA sequencer is opened."""

    def __init__(self) -> None:
        self._port = 3


class MidiOutputEncodingTest(unittest.TestCase):
    def encode(self, event: MidiEvent):
        return AlsaSequencerOutput._event_to_alsa(EncodingOutput(), event)

    def test_note_on_and_note_off(self) -> None:
        note_on = self.encode(MidiEvent(tick=0, kind="note_on", channel=5, data=bytes([60, 100])))
        note_off = self.encode(MidiEvent(tick=0, kind="note_off", channel=5, data=bytes([60, 40])))
        self.assertEqual(note_on.type, SND_SEQ_EVENT_NOTEON)
        self.assertEqual(note_on.data.note.channel, 5)
        self.assertEqual(note_on.data.note.note, 60)
        self.assertEqual(note_on.data.note.velocity, 100)
        self.assertEqual(note_off.type, SND_SEQ_EVENT_NOTEOFF)
        self.assertEqual(note_off.data.note.channel, 5)

    def test_note_on_with_zero_velocity_is_note_off(self) -> None:
        event = self.encode(MidiEvent(tick=0, kind="note_on", channel=2, data=bytes([64, 0])))
        self.assertEqual(event.type, SND_SEQ_EVENT_NOTEOFF)
        self.assertEqual(event.data.note.channel, 2)
        self.assertEqual(event.data.note.note, 64)

    def test_all_sixteen_channels_are_encoded_independently(self) -> None:
        for channel in range(16):
            event = self.encode(
                MidiEvent(tick=0, kind="note_on", channel=channel, data=bytes([48 + channel, 90]))
            )
            self.assertEqual(event.data.note.channel, channel)
            self.assertEqual(event.data.note.note, 48 + channel)

    def test_program_change_and_bank_select(self) -> None:
        program = self.encode(MidiEvent(tick=0, kind="program_change", channel=3, data=bytes([81])))
        bank_msb = self.encode(
            MidiEvent(tick=0, kind="control_change", channel=3, data=bytes([0, 1]))
        )
        bank_lsb = self.encode(
            MidiEvent(tick=0, kind="control_change", channel=3, data=bytes([32, 2]))
        )
        self.assertEqual(program.type, SND_SEQ_EVENT_PGMCHANGE)
        self.assertEqual(program.data.control.channel, 3)
        self.assertEqual(program.data.control.value, 81)
        self.assertEqual(bank_msb.type, SND_SEQ_EVENT_CONTROLLER)
        self.assertEqual((bank_msb.data.control.param, bank_msb.data.control.value), (0, 1))
        self.assertEqual((bank_lsb.data.control.param, bank_lsb.data.control.value), (32, 2))

    def test_key_pressure_channel_pressure_and_pitch_bend(self) -> None:
        key = self.encode(MidiEvent(tick=0, kind="key_pressure", channel=0, data=bytes([60, 77])))
        pressure = self.encode(
            MidiEvent(tick=0, kind="channel_pressure", channel=0, data=bytes([55]))
        )
        bend = self.encode(MidiEvent(tick=0, kind="pitch_bend", channel=0, data=bytes([0, 96])))
        self.assertEqual(key.type, SND_SEQ_EVENT_KEYPRESS)
        self.assertEqual(key.data.note.note, 60)
        self.assertEqual(pressure.type, SND_SEQ_EVENT_CHANPRESS)
        self.assertEqual(pressure.data.control.value, 55)
        self.assertEqual(bend.type, SND_SEQ_EVENT_PITCHBEND)
        self.assertEqual(bend.data.control.value, 4096)

    def test_sysex_is_variable_length_with_framing(self) -> None:
        event = self.encode(
            MidiEvent(tick=0, kind="sysex", data=bytes.fromhex("41 10 42 12 40 00 7f 00 41 f7"))
        )
        self.assertEqual(event.type, SND_SEQ_EVENT_SYSEX)
        self.assertEqual(event.flags & SND_SEQ_EVENT_LENGTH_MASK, SND_SEQ_EVENT_LENGTH_VARIABLE)
        self.assertEqual(event.data.ext.len, 11)
        self.assertTrue(event._payload.raw.startswith(b"\xf0\x41"))
        self.assertTrue(event._payload.raw.endswith(b"\xf7\x00"))

    def test_events_use_direct_delivery_and_subscriber_destination(self) -> None:
        event = self.encode(MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100])))
        self.assertEqual(event.queue, SND_SEQ_QUEUE_DIRECT)
        self.assertEqual(event.dest.client, 254)
        self.assertEqual(event.dest.port, 253)
        self.assertEqual(event.source.port, 3)

    def test_same_tick_events_keep_their_dispatch_order(self) -> None:
        # The scheduler dispatches events in sequence order; the ALSA encoder
        # must not reorder them.
        from dmidiplayer_py.player import SequencePlayer

        class Output:
            def __init__(self) -> None:
                self.events: list[object] = []

            def send_event(self, event: object) -> None:
                self.events.append(event)

            def all_notes_off(self) -> None:
                pass

        output = Output()
        player = SequencePlayer(output)
        player._events = [
            MidiEvent(tick=0, kind="control_change", channel=0, data=bytes([0, 1])),
            MidiEvent(tick=0, kind="program_change", channel=0, data=bytes([40])),
            MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100])),
        ]
        player._event_times_us = [0, 0, 0]
        player._elapsed_microseconds = lambda: 1
        player._tick()
        self.assertEqual(
            [(event.kind, event.data) for event in output.events],
            [
                ("control_change", bytes([0, 1])),
                ("program_change", bytes([40])),
                ("note_on", bytes([60, 100])),
            ],
        )


from PyQt6.QtWidgets import QApplication


class MidiOutputEncodingWithQtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])


if __name__ == "__main__":
    unittest.main()


class ExpressiveEventDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_player_dispatches_pitch_bend_pressures_and_sysex(self) -> None:
        from dmidiplayer_py.player import SequencePlayer

        class Output:
            def __init__(self) -> None:
                self.events: list[object] = []

            def send_event(self, event: object) -> None:
                self.events.append(event)

            def all_notes_off(self) -> None:
                pass

        output = Output()
        player = SequencePlayer(output)
        player._events = [
            MidiEvent(tick=0, kind="pitch_bend", channel=2, data=bytes([0x00, 0x60])),
            MidiEvent(tick=0, kind="channel_pressure", channel=2, data=bytes([70])),
            MidiEvent(tick=0, kind="key_pressure", channel=2, data=bytes([64, 33])),
            MidiEvent(tick=0, kind="sysex", data=bytes.fromhex("7e 7f 09 01 f7")),
        ]
        player._event_times_us = [0, 0, 0, 0]
        player._elapsed_microseconds = lambda: 1
        player._tick()

        self.assertEqual(
            [(event.kind, event.channel, event.data) for event in output.events],
            [
                ("pitch_bend", 2, bytes([0x00, 0x60])),
                ("channel_pressure", 2, bytes([70])),
                ("key_pressure", 2, bytes([64, 33])),
                ("sysex", None, bytes.fromhex("7e 7f 09 01 f7")),
            ],
        )

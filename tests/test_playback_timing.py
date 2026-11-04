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
from tests.test_sequence_player import OutputStub, chunk, varlen


def write_tempo_map_midi(path: Path) -> None:
    """Format 0 file with an initial tempo != 500000 and a mid-song change.

    At division 480:
      0..960   600000 us/qn  -> 1.200 s
      960..1920 300000 us/qn -> 0.600 s
    Total duration: 1.800 s (1_800_000 us).
    """
    header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
    track = b"".join(
        [
            varlen(0),
            b"\xff\x51\x03" + (600_000).to_bytes(3, "big"),
            varlen(0),
            b"\xc0\x28",  # program 40 on channel 0
            varlen(0),
            b"\x90\x3c\x64",  # note on 60
            varlen(480),
            b"\x80\x3c\x00",  # note off at 480
            varlen(480),
            b"\xff\x51\x03" + (300_000).to_bytes(3, "big"),  # tempo at 960
            varlen(0),
            b"\x90\x3e\x64",  # note on 62 at 960
            varlen(480),
            b"\x80\x3e\x00",  # note off at 1440
            varlen(480),
            b"\xff\x2f\x00",  # end at 1920
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


def write_note_at_zero_midi(path: Path) -> None:
    header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
    track = b"".join(
        [
            varlen(0),
            b"\x90\x3c\x64",
            varlen(480),
            b"\x80\x3c\x00",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


class TempoMapTest(unittest.TestCase):
    def test_microseconds_to_tick_is_inverse_of_tick_to_microseconds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "tempo.mid")
            write_tempo_map_midi(path)
            from drumstick_py import read_smf

            midi = read_smf(path)

        for tick in (0, 1, 120, 240, 480, 720, 959, 960, 1440, 1919, 1920):
            microseconds = midi.tick_to_microseconds(tick)
            self.assertLessEqual(abs(midi.microseconds_to_tick(microseconds) - tick), 1)
        self.assertEqual(midi.length_microseconds, 1_800_000)
        self.assertEqual(midi.microseconds_to_tick(1_800_000), 1920)
        self.assertEqual(midi.microseconds_to_tick(1_200_000), 960)


class PlaybackPositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_player(self) -> tuple[SequencePlayer, OutputStub, tempfile.TemporaryDirectory]:
        output = OutputStub()
        player = SequencePlayer(output)
        tmpdir = tempfile.TemporaryDirectory()
        path = Path(tmpdir.name, "tempo.mid")
        write_tempo_map_midi(path)
        player.load_file(str(path))
        return player, output, tmpdir

    def test_seek_reports_position_from_tempo_map(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            positions: list[tuple[int, int]] = []
            player.positionChanged.connect(lambda tick, maximum: positions.append((tick, maximum)))
            player.seek(960)
            self.assertEqual(player._position, 960)
            self.assertEqual(player._position_us, 1_200_000)
            self.assertEqual(player._index, 4)
            self.assertEqual(positions[-1], (960, 1920))
            self.assertFalse(player._playing)
            self.assertFalse(player._timer.isActive())

    def test_seek_while_paused_remains_paused(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            player._paused = True
            player.seek(480)
            self.assertFalse(player._playing)
            self.assertTrue(player.is_paused)
            self.assertFalse(player._timer.isActive())
            self.assertEqual(player._position, 480)

    def test_seek_while_playing_restarts_scheduler_at_new_tick(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            player.play()
            self.assertTrue(player._playing)
            player.seek(960)
            self.assertTrue(player._playing)
            self.assertGreaterEqual(player._position, 960)
            self.assertTrue(player._timer.isActive())
            player.stop()

    def test_end_of_song_sets_exact_position_and_stops_timer(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            finished: list[int] = []
            positions: list[tuple[int, int]] = []
            player.finished.connect(lambda: finished.append(1))
            player.positionChanged.connect(lambda tick, maximum: positions.append((tick, maximum)))
            player._playing = True
            player._timer.start()
            player._elapsed_microseconds = lambda: player.sequence.length_microseconds

            player._tick()

            self.assertFalse(player._playing)
            self.assertFalse(player._timer.isActive())
            self.assertEqual(player._position, player.sequence.length_ticks)
            self.assertEqual(player._position_us, player.sequence.length_microseconds)
            self.assertEqual(finished, [1])
            self.assertEqual(positions[-1], (1920, 1920))

            # A second scheduler pass must not emit finished again.
            player._tick()
            self.assertEqual(finished, [1])

    def test_end_of_song_releases_active_notes(self) -> None:
        player, output, tmpdir = self.make_player()
        with tmpdir:
            player._track_active_note_event(
                MidiEvent(tick=0, kind="note_on", channel=2, data=bytes([60, 100]))
            )
            player._playing = True
            player._elapsed_microseconds = lambda: player.sequence.length_microseconds

            player._tick()

            self.assertEqual(player._active_notes, {})
            note_offs = [
                event
                for event in output.events
                if getattr(event, "kind", "") == "note_off" and getattr(event, "channel", None) == 2
            ]
            self.assertTrue(note_offs)
            self.assertGreaterEqual(output.all_notes_off_count, 1)

    def test_pause_then_seek_does_not_leave_finished_armed(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            player.play()
            player.pause()
            player.seek(player.sequence.length_ticks)
            self.assertFalse(player.is_playing)
            self.assertFalse(player._timer.isActive())

    def test_loop_does_not_finish_song(self) -> None:
        player, _output, tmpdir = self.make_player()
        with tmpdir:
            finished: list[int] = []
            player.finished.connect(lambda: finished.append(1))
            player.set_loop_range(0, 480)
            player.set_loop_enabled(True)
            player._playing = True
            player._position_us = 800_000
            player._base_position_us = 800_000
            player._tick()
            self.assertEqual(finished, [])
            self.assertEqual(player._position, 0)
            self.assertTrue(player._playing)

    def test_command_channel_setup_is_resent_at_start(self) -> None:
        player, output, tmpdir = self.make_player()
        with tmpdir:
            output.events.clear()
            player.play()
            player.stop()

            program_events = [
                event for event in output.events if getattr(event, "kind", "") == "program_change"
            ]
            controllers = {
                (event.channel, event.data[0], event.data[1])
                for event in output.events
                if getattr(event, "kind", "") == "control_change"
            }
            self.assertTrue(program_events)
            # The reset sends program 0 to every channel; the score program
            # change (40) must still be delivered afterwards.
            self.assertIn((0, 40), {(event.channel, event.data[0]) for event in program_events})
            self.assertIn((0, 0), {(event.channel, event.data[0]) for event in program_events})
            self.assertIn((0, 121, 0), controllers)  # reset all controllers
            self.assertIn((0, 123, 0), controllers)  # all notes off
            self.assertIn((0, 7, 100), controllers)  # channel volume

    def test_only_one_reset_sysex_message_is_sent(self) -> None:
        player, output, tmpdir = self.make_player()
        with tmpdir:
            player.set_send_reset_before_playback(True)
            output.events.clear()
            player.play()
            player.stop()
            sysex = [event for event in output.events if getattr(event, "kind", "") == "sysex"]
            self.assertEqual(len(sysex), 1)
            self.assertEqual(sysex[0].data, bytes.fromhex("7e 7f 09 01 f7"))

    def test_first_tick_events_are_dispatched_synchronously(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "zero.mid")
            write_note_at_zero_midi(path)
            player.load_file(str(path))
            output.events.clear()
            player.play()
            self.assertTrue(
                any(
                    getattr(event, "kind", "") == "note_on" and getattr(event, "tick", -1) == 0
                    for event in output.events
                )
            )
            self.assertEqual(player._position, 0)
            self.assertTrue(player.is_playing)
            player.stop()

    def test_overlapping_notes_require_all_offs_before_release(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)
        player._track_active_note_event(
            MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100]))
        )
        player._track_active_note_event(
            MidiEvent(tick=10, kind="note_on", channel=0, data=bytes([60, 90]))
        )
        player._track_active_note_event(
            MidiEvent(tick=20, kind="note_off", channel=0, data=bytes([60, 0]))
        )
        self.assertIn(60, player._active_notes[0])
        player._track_active_note_event(
            MidiEvent(tick=30, kind="note_off", channel=0, data=bytes([60, 0]))
        )
        self.assertNotIn(0, player._active_notes)

        player._track_active_note_event(
            MidiEvent(tick=40, kind="note_on", channel=0, data=bytes([60, 100]))
        )
        player._track_active_note_event(
            MidiEvent(tick=50, kind="note_on", channel=0, data=bytes([60, 100]))
        )
        player._silence_active_notes()
        self.assertEqual(player._active_notes, {})
        note_offs = [
            event
            for event in output.events
            if getattr(event, "kind", "") == "note_off" and getattr(event, "channel", None) == 0
        ]
        self.assertEqual(len(note_offs), 2)

    def test_seek_restores_bank_and_program_state(self) -> None:
        header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
        track = b"".join(
            [
                varlen(0),
                b"\xff\x51\x03" + (500_000).to_bytes(3, "big"),
                varlen(0),
                b"\xb0\x00\x01",  # bank MSB 1
                varlen(0),
                b"\xb0\x20\x02",  # bank LSB 2
                varlen(0),
                b"\xc0\x07",  # program 7
                varlen(0),
                b"\x90\x3c\x64",
                varlen(480),
                b"\x80\x3c\x00",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        data = header + chunk(b"MTrk", track)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "bank.mid")
            path.write_bytes(data)
            output = OutputStub()
            player = SequencePlayer(output)
            player.load_file(str(path))
            output.events.clear()
            player.seek(480)
            setup = [
                (event.kind, event.channel, event.data)
                for event in output.events
                if getattr(event, "channel", None) is not None
            ]
            self.assertIn(("control_change", 0, bytes([0, 1])), setup)
            self.assertIn(("control_change", 0, bytes([32, 2])), setup)
            self.assertIn(("program_change", 0, bytes([7])), setup)


if __name__ == "__main__":
    unittest.main()


class UnmuteResyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_unmute_resends_current_program_and_volume(self) -> None:
        from tests.test_sequence_player import OutputStub

        output = OutputStub()
        player = SequencePlayer(output)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "tempo.mid")
            write_tempo_map_midi(path)
            player.load_file(str(path))

        player.set_channel_muted(0, True)
        player._track_source_event(MidiEvent(tick=0, kind="program_change", channel=0, data=bytes([40])))
        player._track_source_event(
            MidiEvent(tick=0, kind="control_change", channel=0, data=bytes([7, 80]))
        )
        output.events.clear()
        player.set_channel_muted(0, False)

        programs = [
            event.data[0]
            for event in output.events
            if getattr(event, "kind", "") == "program_change" and getattr(event, "channel", None) == 0
        ]
        volumes = [
            event.data[1]
            for event in output.events
            if getattr(event, "kind", "") == "control_change"
            and getattr(event, "channel", None) == 0
            and event.data[0] == 7
        ]
        self.assertIn(40, programs)
        self.assertIn(80, volumes)


class ClockScalingAndProgramLockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_tempo_percent_scales_the_authoritative_clock(self) -> None:
        class FakeClock:
            def isValid(self) -> bool:
                return True

            def nsecsElapsed(self) -> int:
                return 100_000_000  # 100 ms

        output = OutputStub()
        player = SequencePlayer(output)
        player._clock = FakeClock()
        player._base_position_us = 0
        player._position_us = 0
        player._tempo_percent = 50
        self.assertEqual(player._elapsed_microseconds(), 50_000)
        player._tempo_percent = 200
        self.assertEqual(player._elapsed_microseconds(), 200_000)

    def test_locked_channel_keeps_the_user_selected_patch_at_start(self) -> None:
        player = SequencePlayer(OutputStub())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "tempo.mid")
            write_tempo_map_midi(path)
            player.load_file(str(path))
        player.set_channel_program(0, 40)
        player.set_channel_locked(0, True)
        self.assertEqual(player._locked_programs[0], 40)
        event = MidiEvent(tick=0, kind="program_change", channel=0, data=bytes([10]))
        patched = player._playable_event(event)
        self.assertIsNotNone(patched)
        self.assertEqual(patched.data, bytes([40]))


def write_drum_channel_midi(path: Path) -> None:
    header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
    track = b"".join(
        [
            varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            varlen(0),
            b"\xc9\x00",  # program 0 on MIDI channel 10
            varlen(0),
            b"\x99\x24\x64",  # note 36 on channel 10
            varlen(480),
            b"\x89\x24\x00",
            varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    path.write_bytes(header + chunk(b"MTrk", track))


class DrumBankPreservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_reset_at_start_does_not_force_bank_select_on_drums(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "drums.mid")
            write_drum_channel_midi(path)
            player.load_file(str(path))
            output.events.clear()
            player.play()
            player.stop()

        drum_bank_events = [
            event
            for event in output.events
            if getattr(event, "kind", "") == "control_change"
            and getattr(event, "channel", None) == 9
            and len(event.data) >= 1
            and event.data[0] in (0, 32)
        ]
        self.assertEqual(drum_bank_events, [])
        drum_programs = [
            event.data[0]
            for event in output.events
            if getattr(event, "kind", "") == "program_change"
            and getattr(event, "channel", None) == 9
        ]
        self.assertIn(0, drum_programs)

    def test_seek_does_not_force_bank_select_on_drums(self) -> None:
        output = OutputStub()
        player = SequencePlayer(output)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "drums.mid")
            write_drum_channel_midi(path)
            player.load_file(str(path))
        output.events.clear()
        player.seek(480)
        drum_bank_events = [
            event
            for event in output.events
            if getattr(event, "kind", "") == "control_change"
            and getattr(event, "channel", None) == 9
            and len(event.data) >= 1
            and event.data[0] in (0, 32)
        ]
        self.assertEqual(drum_bank_events, [])

    def test_explicit_score_bank_is_still_restored(self) -> None:
        header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
        track = b"".join(
            [
                varlen(0),
                b"\xff\x51\x03\x07\xa1\x20",
                varlen(0),
                b"\xb9\x00\x7f",  # bank MSB 127 on channel 10
                varlen(0),
                b"\xb9\x20\x00",  # bank LSB 0
                varlen(0),
                b"\xc9\x00",
                varlen(0),
                b"\x99\x24\x64",
                varlen(480),
                b"\x89\x24\x00",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "banked_drums.mid")
            path.write_bytes(header + chunk(b"MTrk", track))
            output = OutputStub()
            player = SequencePlayer(output)
            player.load_file(str(path))
        output.events.clear()
        player.seek(480)
        drum_bank_events = [
            (event.data[0], event.data[1])
            for event in output.events
            if getattr(event, "kind", "") == "control_change"
            and getattr(event, "channel", None) == 9
            and event.data[0] in (0, 32)
        ]
        self.assertEqual(drum_bank_events, [(0, 127), (32, 0)])

from __future__ import annotations

import unittest
from collections import defaultdict
from pathlib import Path

from drumstick_py import read_smf
from dmidiplayer_py.sequence import Sequence

REPO = Path(__file__).resolve().parents[1]
COLLECTION = REPO / "MIDI-Karaoke"

FILES = {
    "Amor_amor_amor-Annette_Moreno.mid": {"format": 1, "division": 120, "channels": 14, "tracks": 18},
    "Bendito_Jesus-Danilo_Montero.mid": {"format": 1, "division": 480, "channels": 16, "tracks": 13},
    "El_me_levantara-Inspiracion.mid": {"format": 1, "division": 480, "channels": 4, "tracks": 6},
    "En_Tu_Luz-Grupo_Luz_y_Salvacion.mid": {"format": 0, "division": 1920, "channels": 11, "tracks": 1},
    "Our_God-Chris_Tomlin.mid": {"format": 1, "division": 960, "channels": 9, "tracks": 13},
    "Te_Doy_Gloria-Grupo_Luz_Y_Salvacion.mid": {"format": 0, "division": 1920, "channels": 10, "tracks": 1},
}


class MidiCollectionTest(unittest.TestCase):
    def test_collection_is_present(self) -> None:
        missing = [name for name in FILES if not (COLLECTION / name).exists()]
        self.assertEqual(missing, [], f"missing MIDI-Karaoke files: {missing}")

    def test_channel_and_format_analysis(self) -> None:
        for name, expected in FILES.items():
            with self.subTest(file=name):
                path = COLLECTION / name
                if not path.exists():
                    self.skipTest(f"{name} not available")
                midi = read_smf(path)
                self.assertEqual(midi.format, expected["format"])
                self.assertEqual(midi.division, expected["division"])
                self.assertEqual(len(midi.tracks), expected["tracks"])
                sequence = Sequence()
                sequence.load_file(path)
                infos = sequence.channel_infos(9)
                self.assertEqual(len(infos), expected["channels"])
                channels = [int(info["channel"]) for info in infos]
                self.assertEqual(channels, sorted(set(channels)))
                self.assertTrue(all(0 <= channel < 16 for channel in channels))
                self.assertGreater(midi.length_ticks, 0)
                self.assertGreater(midi.length_microseconds, 0)
                self.assertTrue(midi.tempo_changes)

    def test_no_stuck_notes_and_valid_program_changes(self) -> None:
        for name in FILES:
            with self.subTest(file=name):
                path = COLLECTION / name
                if not path.exists():
                    self.skipTest(f"{name} not available")
                midi = read_smf(path)
                active: dict[tuple[int, int], int] = defaultdict(int)
                for event in midi.events:
                    if event.channel is None or not event.data:
                        continue
                    self.assertGreaterEqual(event.channel, 0)
                    self.assertLess(event.channel, 16)
                    if event.kind == "program_change":
                        self.assertGreaterEqual(event.data[0], 0)
                        self.assertLess(event.data[0], 128)
                    if event.kind == "note_on" and len(event.data) >= 2 and event.data[1] > 0:
                        active[(event.channel, event.data[0])] += 1
                    elif event.kind == "note_off" or (
                        event.kind == "note_on" and len(event.data) >= 2 and event.data[1] == 0
                    ):
                        key = (event.channel, event.data[0])
                        if active[key] > 0:
                            active[key] -= 1
                        # A stray note-off (Our God has one) is tolerated.
                self.assertEqual(
                    {key: count for key, count in active.items() if count > 0},
                    {},
                    f"{name} leaves unclosed notes",
                )

    def test_tempo_map_is_invertible(self) -> None:
        for name in FILES:
            with self.subTest(file=name):
                path = COLLECTION / name
                if not path.exists():
                    self.skipTest(f"{name} not available")
                midi = read_smf(path)
                length = midi.length_ticks
                for tick in (0, length // 4, length // 2, (3 * length) // 4, length):
                    microseconds = midi.tick_to_microseconds(tick)
                    self.assertLessEqual(abs(midi.microseconds_to_tick(microseconds) - tick), 1)
                self.assertEqual(midi.microseconds_to_tick(midi.length_microseconds), length)

    def test_percussion_channel_has_a_drums_entry(self) -> None:
        for name in FILES:
            with self.subTest(file=name):
                path = COLLECTION / name
                if not path.exists():
                    self.skipTest(f"{name} not available")
                sequence = Sequence()
                sequence.load_file(path)
                infos = sequence.channel_infos(9)
                by_channel = {int(info["channel"]): info for info in infos}
                self.assertIn(9, by_channel)
                self.assertTrue(by_channel[9]["percussion"])
                self.assertIn("Drums", str(by_channel[9]["label"]))

    def test_multiple_tracks_sharing_a_channel_are_merged(self) -> None:
        path = COLLECTION / "Our_God-Chris_Tomlin.mid"
        if not path.exists():
            self.skipTest("Our_God-Chris_Tomlin.mid not available")
        midi = read_smf(path)
        channel_zero_tracks = sum(
            1
            for track in midi.tracks
            if any(event.channel == 0 for event in track.events)
        )
        self.assertGreaterEqual(channel_zero_tracks, 2)
        sequence = Sequence()
        sequence.load_file(path)
        infos = sequence.channel_infos(9)
        channel_zero = [info for info in infos if int(info["channel"]) == 0]
        self.assertEqual(len(channel_zero), 1)
        self.assertGreaterEqual(len(channel_zero[0]["part_names"]), 2)

    def test_channels_without_notes_still_exist_in_bendito(self) -> None:
        path = COLLECTION / "Bendito_Jesus-Danilo_Montero.mid"
        if not path.exists():
            self.skipTest("Bendito_Jesus-Danilo_Montero.mid not available")
        sequence = Sequence()
        sequence.load_file(path)
        infos = sequence.channel_infos(9)
        self.assertEqual(len(infos), 16)
        no_note_channels = [info for info in infos if int(info["note_count"]) == 0]
        self.assertTrue(no_note_channels)
        # They must not be dropped: C++ channelUsed() also marks a channel
        # used by program/controller events.
        self.assertEqual(len(infos), 16)

    def test_sysex_events_are_preserved(self) -> None:
        for name in (
            "En_Tu_Luz-Grupo_Luz_y_Salvacion.mid",
            "Te_Doy_Gloria-Grupo_Luz_Y_Salvacion.mid",
        ):
            path = COLLECTION / name
            if not path.exists():
                self.skipTest(f"{name} not available")
            midi = read_smf(path)
            self.assertTrue(any(event.kind == "sysex" for event in midi.events), name)


if __name__ == "__main__":
    unittest.main()

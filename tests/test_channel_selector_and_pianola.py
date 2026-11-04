from __future__ import annotations

import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from drumstick_py import MidiEvent
from dmidiplayer_py.app import MainWindow, PianolaDialog, PianoKeyboard
from dmidiplayer_py.sequence import Sequence
from tests.test_app_playlist import FakeBackendManager, FakeSettings
from tests.test_sequence_player import chunk, varlen


def reset_fake_settings() -> None:
    FakeSettings.midi_destination_value = ""
    FakeSettings.percussion_channel_value = 10
    FakeSettings.auto_play_on_load_value = False
    FakeSettings.playlist_auto_advance_value = False
    FakeSettings.auto_song_settings_value = False
    FakeSettings.qt_style_value = "system"
    FakeSettings.force_dark_mode_value = False
    FakeSettings.use_internal_icon_theme_value = False
    FakeSettings.toolbar_button_style_value = "follow_style"
    FakeSettings.toolbar_actions_value = list(FakeSettings.DEFAULT_TOOLBAR_ACTIONS)
    FakeSettings.solo_volume_reduction_value = 50
    FakeSettings.midi_reset_before_playback_value = False
    FakeSettings.lyrics_font_family_value = "Sans Serif"
    FakeSettings.lyrics_font_size_value = 10
    FakeSettings.lyrics_future_color_value = "#2563eb"
    FakeSettings.lyrics_past_color_value = "#6b7280"
    FakeSettings.pianola_color_mode_value = "blue"
    FakeSettings.pianola_single_color_value = "#1d4ed8"
    FakeSettings.pianola_velocity_tinting_value = True
    FakeSettings.pianola_note_label_mode_value = "never"
    FakeSettings.pianola_note_font_family_value = "Sans Serif"
    FakeSettings.pianola_note_font_size_value = 8
    FakeSettings.pianola_octave_designation_value = "scientific"
    FakeSettings.playlist_path_value = None
    FakeSettings.window_geometry_value = None
    FakeSettings.dialog_geometry_values = {}
    _reset_fake_alsa()


def _reset_fake_alsa() -> None:
    FakeBackendManager.last_driver = None
    FakeBackendManager.last_connection = None


def track_chunk(*events: bytes) -> bytes:
    return chunk(b"MTrk", b"".join(events))


def name_event(name: str) -> bytes:
    encoded = name.encode("ascii")
    return varlen(0) + b"\xff\x03" + varlen(len(encoded)) + encoded


def program_event(channel: int, program: int) -> bytes:
    return varlen(0) + bytes([0xC0 | channel, program])


def note_event(channel: int, note: int, velocity: int, duration: int = 240) -> bytes:
    return (
        varlen(0)
        + bytes([0x90 | channel, note, velocity])
        + varlen(duration)
        + bytes([0x80 | channel, note, 0])
    )


def end_event() -> bytes:
    return varlen(0) + b"\xff\x2f\x00"


def write_channel_file(path: Path) -> None:
    """Three used channels; two tracks share channel 0; one unused track."""
    tracks = [
        track_chunk(varlen(0), b"\xff\x51\x03\x07\xa1\x20", end_event()),
        track_chunk(name_event("Guitar"), program_event(0, 0), note_event(0, 60, 100), note_event(0, 64, 90), end_event()),
        track_chunk(name_event("Guitar Double"), note_event(0, 67, 80), end_event()),
        track_chunk(name_event("Bass"), program_event(1, 32), note_event(1, 40, 110), end_event()),
        track_chunk(name_event("Drums"), note_event(9, 36, 120), end_event()),
        track_chunk(name_event("Lyrics only"), varlen(0), b"\xff\x01\x05Hello", end_event()),
    ]
    header = chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), 480))
    path.write_bytes(header + b"".join(tracks))


def write_note_range_file(path: Path) -> None:
    """Channel 0 has notes 48..84; channel 1 only a program change."""
    tracks = [
        track_chunk(varlen(0), b"\xff\x51\x03\x07\xa1\x20", end_event()),
        track_chunk(name_event("Piano"), note_event(0, 48, 100), note_event(0, 84, 100), end_event()),
        track_chunk(name_event("Silent part"), program_event(1, 40), end_event()),
    ]
    header = chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), 480))
    path.write_bytes(header + b"".join(tracks))


class ChannelInfoTest(unittest.TestCase):
    def test_channel_infos_merges_tracks_sharing_a_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            sequence = Sequence()
            sequence.load_file(path)
            infos = sequence.channel_infos(9)

        self.assertEqual([int(info["channel"]) for info in infos], [0, 1, 9])
        guitar = infos[0]
        self.assertEqual(guitar["part_names"], ["Guitar", "Guitar Double"])
        self.assertEqual(guitar["note_count"], 3)
        self.assertIn("1: Acoustic Grand Piano", str(guitar["label"]))
        bass = infos[1]
        self.assertIn("Acoustic Bass", str(bass["label"]))
        drums = infos[2]
        self.assertTrue(drums["percussion"])
        self.assertIn("10: Drums", str(drums["label"]))

    def test_program_at_tick_follows_program_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "programs.mid")
            write_channel_file(path)
            sequence = Sequence()
            sequence.load_file(path)

            self.assertEqual(sequence.instrument_at_tick(0, 0)[2], "Acoustic Grand Piano")
            self.assertEqual(sequence.instrument_at_tick(1, 0)[2], "Acoustic Bass")
            self.assertEqual(sequence.instrument_at_tick(9, 0)[2], "Drums")


class ChannelAnalyzerMixin:
    def make_window(self, path: Path) -> MainWindow:
        reset_fake_settings()
        patcher_manager = patch("dmidiplayer_py.app.BackendManager", FakeBackendManager)
        patcher_settings = patch("dmidiplayer_py.app.AppSettings", FakeSettings)
        self.addCleanup(patcher_manager.stop)
        self.addCleanup(patcher_settings.stop)
        patcher_manager.start()
        patcher_settings.start()
        window = MainWindow([str(path)])
        self.addCleanup(window.close)
        return window


class PianolaChannelTest(ChannelAnalyzerMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_dialog(self, count: int) -> PianolaDialog:
        dialog = PianolaDialog()
        self.addCleanup(dialog.close)
        dialog.set_channels(
            [
                {
                    "channel": channel,
                    "title": f"Part {channel + 1}",
                    "part_name": f"Part {channel + 1}",
                    "instrument_name": "Acoustic Grand Piano",
                    "program": 0,
                    "bank": 0,
                    "percussion": channel == 9,
                    "min_note": 48,
                    "max_note": 84,
                    "note_count": 1,
                    "program_changes": [(0, 0)],
                    "label": f"{channel + 1}: Acoustic Grand Piano",
                }
                for channel in range(count)
            ]
        )
        return dialog

    def test_tab_distribution(self) -> None:
        expected = {
            4: ([4], "Channels 1-4"),
            7: ([7], "Channels 1-7"),
            9: ([8, 1], "Channels 1-8"),
            14: ([8, 6], "Channels 1-8"),
            16: ([8, 8], "Channels 1-8"),
        }
        for count, (distribution, first_tab) in expected.items():
            dialog = self.make_dialog(count)
            sizes = []
            for index in range(dialog.tabs.count()):
                sizes.append(len(dialog.tabs.widget(index).findChildren(PianoKeyboard)))
            self.assertEqual(sizes, distribution, f"{count} channels")
            self.assertEqual(dialog.tabs.tabText(0), first_tab)
            dialog.close()

    def test_seventeen_synthetic_parts_use_three_tabs(self) -> None:
        dialog = self.make_dialog(17)
        sizes = [
            len(dialog.tabs.widget(index).findChildren(PianoKeyboard))
            for index in range(dialog.tabs.count())
        ]
        self.assertEqual(sizes, [8, 8, 1])
        self.assertEqual(dialog.tabs.tabText(2), "Channel 17")

    def test_tracks_sharing_a_channel_create_one_keyboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "shared.mid")
            write_channel_file(path)
            window = self.make_window(path)
            dialog = window._ensure_pianola_dialog()
            keyboards = dialog.findChildren(PianoKeyboard)
            self.assertEqual(len(keyboards), 3)

    def test_notes_are_routed_to_the_matching_channel_keyboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            window = self.make_window(path)
            dialog = window._ensure_pianola_dialog()
            keyboard_one = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_1")
            keyboard_two = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_2")
            keyboard_ten = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_10")

            window._event_played(MidiEvent(tick=0, kind="note_on", channel=0, data=bytes([60, 100])))
            window._event_played(MidiEvent(tick=0, kind="note_on", channel=1, data=bytes([40, 90])))
            window._event_played(MidiEvent(tick=0, kind="note_on", channel=9, data=bytes([36, 120])))

            self.assertEqual(keyboard_one._active, {60})
            self.assertEqual(keyboard_two._active, {40})
            self.assertEqual(keyboard_ten._active, {36})

    def test_song_range_ignores_channels_without_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "range.mid")
            write_note_range_file(path)
            window = self.make_window(path)
            dialog = window._ensure_pianola_dialog()
            keyboard_one = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_1")
            keyboard_two = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_2")

            # Only channel 0 contributes notes (48..84).  Channel 1 contains
            # only a program change and must not widen the range to 21..108.
            self.assertEqual((keyboard_one._min_note, keyboard_one._max_note), (48, 96))
            self.assertEqual((keyboard_two._min_note, keyboard_two._max_note), (48, 96))

    def test_show_active_notes_preserves_overlap_counts(self) -> None:
        dialog = self.make_dialog(2)
        dialog.show_active_notes({0: {60}}, lambda channel, note: 90, lambda channel, note: 2)
        keyboard = dialog.findChild(PianoKeyboard, "pianola_channel_keyboard_1")
        self.assertEqual(keyboard._active_counts[60], 2)
        self.assertIn(60, keyboard._active)
        keyboard.note_off(60)
        self.assertIn(60, keyboard._active)
        keyboard.note_off(60)
        self.assertNotIn(60, keyboard._active)

    def test_program_change_updates_channel_heading_or_tooltip(self) -> None:
        from PyQt6.QtWidgets import QLabel

        dialog = self.make_dialog(2)
        dialog.set_channel_instrument(0, "Violin")
        heading = dialog.findChild(QLabel, "pianola_channel_label_1")
        self.assertIn("Violin", heading.toolTip())


if __name__ == "__main__":
    unittest.main()

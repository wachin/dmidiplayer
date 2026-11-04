from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.app import PianolaDialog, PianoKeyboard
from dmidiplayer_py.sequence import Sequence
from tests.test_channel_selector_and_pianola import write_channel_file

REPO = Path(__file__).resolve().parents[1]
AMOR = REPO / "MIDI-Karaoke" / "Amor_amor_amor-Annette_Moreno.mid"
BENDITO = REPO / "MIDI-Karaoke" / "Bendito_Jesus-Danilo_Montero.mid"
OUR_GOD = REPO / "MIDI-Karaoke" / "Our_God-Chris_Tomlin.mid"


class PianolaResponsiveLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_dialog(self, midi_path: Path) -> PianolaDialog:
        sequence = Sequence()
        sequence.load_file(midi_path)
        dialog = PianolaDialog()
        self.addCleanup(dialog.close)
        dialog.set_channels(sequence.channel_infos(9))
        dialog.show()
        self.app.processEvents()
        return dialog

    def assert_no_keyboard_clipped(self, dialog: PianolaDialog) -> None:
        for tab_index in range(dialog.tabs.count()):
            dialog.tabs.setCurrentIndex(tab_index)
            self.app.processEvents()
            page = dialog.tabs.widget(tab_index)
            keyboards = page.findChildren(PianoKeyboard)
            self.assertTrue(keyboards, f"tab {tab_index} has no keyboards")
            for keyboard in keyboards:
                self.assertTrue(keyboard.isVisible(), f"{keyboard.objectName()} is hidden")
                self.assertGreaterEqual(keyboard.height(), keyboard.minimumHeight())
                bottom_in_page = keyboard.mapTo(page, QPoint(0, keyboard.height())).y()
                self.assertLessEqual(
                    bottom_in_page,
                    page.height() + 1,
                    f"{keyboard.objectName()} is clipped by the tab page",
                )
                rects = keyboard.white_key_rects()
                self.assertTrue(rects)
                self.assertEqual(max(y + height for _x, y, _w, height in rects.values()), keyboard.height())

    @unittest.skipUnless(AMOR.exists(), "MIDI-Karaoke collection not available")
    def test_amor_fourteen_channels_fit_at_both_resolutions(self) -> None:
        dialog = self.make_dialog(AMOR)
        self.assertEqual(dialog.tabs.count(), 2)
        sizes = [
            len(dialog.tabs.widget(index).findChildren(PianoKeyboard))
            for index in range(dialog.tabs.count())
        ]
        self.assertEqual(sizes, [8, 6])

        dialog.resize(1360, 730)
        self.app.processEvents()
        self.assert_no_keyboard_clipped(dialog)
        small_heights = [
            keyboard.height()
            for keyboard in dialog.tabs.widget(0).findChildren(PianoKeyboard)
        ]

        dialog.resize(1920, 1040)
        self.app.processEvents()
        self.assert_no_keyboard_clipped(dialog)
        large_heights = [
            keyboard.height()
            for keyboard in dialog.tabs.widget(0).findChildren(PianoKeyboard)
        ]
        self.assertGreater(min(large_heights), min(small_heights))
        self.assertGreaterEqual(min(large_heights), 80)

    @unittest.skipUnless(OUR_GOD.exists(), "MIDI-Karaoke collection not available")
    def test_single_keyboard_tab_keeps_the_row_height(self) -> None:
        dialog = self.make_dialog(OUR_GOD)
        self.assertEqual(dialog.tabs.count(), 2)
        self.assertEqual(len(dialog.tabs.widget(0).findChildren(PianoKeyboard)), 8)
        self.assertEqual(len(dialog.tabs.widget(1).findChildren(PianoKeyboard)), 1)

        for width, height in ((1360, 730), (1920, 1040)):
            dialog.resize(width, height)
            self.app.processEvents()
            self.assert_no_keyboard_clipped(dialog)
            first_tab_heights = [
                keyboard.height()
                for keyboard in dialog.tabs.widget(0).findChildren(PianoKeyboard)
            ]
            single = dialog.tabs.widget(1).findChildren(PianoKeyboard)[0]
            self.assertLessEqual(
                abs(single.height() - min(first_tab_heights)),
                12,
                "a single-channel tab must not stretch its keyboard over the page",
            )
            page = dialog.tabs.widget(1)
            self.assertLess(single.height(), page.height() // 2)

    @unittest.skipUnless(BENDITO.exists(), "MIDI-Karaoke collection not available")
    def test_bendito_sixteen_channels_fit_at_both_resolutions(self) -> None:
        dialog = self.make_dialog(BENDITO)
        self.assertEqual(dialog.tabs.count(), 2)
        sizes = [
            len(dialog.tabs.widget(index).findChildren(PianoKeyboard))
            for index in range(dialog.tabs.count())
        ]
        self.assertEqual(sizes, [8, 8])

        dialog.resize(1360, 730)
        self.app.processEvents()
        self.assert_no_keyboard_clipped(dialog)

        dialog.resize(1920, 1040)
        self.app.processEvents()
        self.assert_no_keyboard_clipped(dialog)

    def test_first_open_sizes_to_the_available_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)

            class FakeScreen:
                def __init__(self, width: int, height: int) -> None:
                    self._rect = QRect(0, 0, width, height)

                def availableGeometry(self) -> QRect:
                    return self._rect

            dialog._geometry_adopted = False
            dialog.screen = lambda: FakeScreen(1360, 728)
            dialog.fit_to_screen()
            self.assertLessEqual(dialog.width(), 1360)
            self.assertLessEqual(dialog.height(), 728)
            self.assertGreaterEqual(dialog.height(), dialog.minimumSizeHint().height())

    def test_dialog_minimum_height_fits_a_768_pixel_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)
            # Leave room for the window title bar and the desktop panel.
            self.assertLessEqual(dialog.minimumSizeHint().height(), 700)

    def test_hiding_a_channel_expands_the_remaining_keyboards(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)
            dialog.resize(1360, 730)
            self.app.processEvents()
            page = dialog.tabs.widget(0)
            keyboards = page.findChildren(PianoKeyboard)
            before = [keyboard.height() for keyboard in keyboards]

            dialog._set_channel_visible(0, False, emit_signal=False)
            self.app.processEvents()
            after = [keyboard.height() for keyboard in keyboards[1:]]
            self.assertGreater(min(after), min(before))

            dialog._set_channel_visible(0, True, emit_signal=False)
            self.app.processEvents()


    def test_dynamic_resize_reflows_without_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)
            for width, height in ((1360, 730), (1920, 1040), (1100, 650), (1360, 730)):
                dialog.resize(width, height)
                self.app.processEvents()
                self.assert_no_keyboard_clipped(dialog)

    def test_tab_switch_recalculates_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)
            dialog.resize(1360, 730)
            dialog.tabs.setCurrentIndex(0)
            self.app.processEvents()
            self.assert_no_keyboard_clipped(dialog)

    def test_fullscreen_keeps_keyboards_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "channels.mid")
            write_channel_file(path)
            dialog = self.make_dialog(path)
            dialog.showFullScreen()
            self.app.processEvents()
            self.assert_no_keyboard_clipped(dialog)
            dialog.set_fullscreen_enabled(False)
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()

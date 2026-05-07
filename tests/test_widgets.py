from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from drumstick_py import PianoKeyboard


class PianoKeyboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_visible_note_lists_follow_selected_range(self) -> None:
        keyboard = PianoKeyboard()
        keyboard.set_note_range(48, 60)

        self.assertEqual(keyboard.visible_white_notes(), [48, 50, 52, 53, 55, 57, 59, 60])
        self.assertEqual(keyboard.visible_black_notes(), [49, 51, 54, 56, 58])

    def test_note_range_is_clamped_to_midi_limits(self) -> None:
        keyboard = PianoKeyboard()
        keyboard.set_note_range(-10, 200)

        self.assertEqual(keyboard.visible_white_notes()[0], 0)
        self.assertEqual(keyboard.visible_black_notes()[-1], 126)


if __name__ == "__main__":
    unittest.main()

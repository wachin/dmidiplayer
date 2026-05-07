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

    def test_note_on_stores_velocity_and_note_off_clears_it(self) -> None:
        keyboard = PianoKeyboard()

        keyboard.note_on(60, 45)

        self.assertIn(60, keyboard._active)
        self.assertEqual(keyboard._active_velocities[60], 45)

        keyboard.note_off(60)

        self.assertNotIn(60, keyboard._active)
        self.assertNotIn(60, keyboard._active_velocities)

    def test_active_note_color_changes_with_velocity(self) -> None:
        keyboard = PianoKeyboard()

        keyboard.note_on(60, 20)
        soft = keyboard.active_note_color(60)

        keyboard.note_on(61, 120)
        loud = keyboard.active_note_color(61)

        self.assertNotEqual(soft.name(), loud.name())


if __name__ == "__main__":
    unittest.main()

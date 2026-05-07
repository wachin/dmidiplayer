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

    def test_visible_note_labels_follow_selected_mode(self) -> None:
        keyboard = PianoKeyboard()
        keyboard.set_note_range(48, 60)

        keyboard.set_note_label_mode("never")
        self.assertEqual(keyboard.visible_note_labels(), {})

        keyboard.set_note_label_mode("minimal")
        self.assertEqual(keyboard.visible_note_labels(), {48: "C3", 60: "C4"})

        keyboard.note_on(49, 70)
        keyboard.note_on(60, 100)
        keyboard.set_note_label_mode("active")
        self.assertEqual(keyboard.visible_note_labels(), {49: "C#3", 60: "C4"})

        keyboard.set_note_label_mode("always")
        self.assertEqual(keyboard.visible_note_labels()[48], "C3")
        self.assertEqual(keyboard.visible_note_labels()[58], "A#3")

    def test_active_colors_can_be_overridden(self) -> None:
        keyboard = PianoKeyboard()
        keyboard.set_active_colors(
            white_low="#fef3c7",
            white_high="#d97706",
            black_low="#92400e",
            black_high="#fcd34d",
        )
        keyboard.note_on(60, 127)
        keyboard.note_on(61, 127)

        self.assertEqual(keyboard.active_note_color(60).name(), "#d97706")
        self.assertEqual(keyboard.active_note_color(61, black_key=True).name(), "#fcd34d")


if __name__ == "__main__":
    unittest.main()

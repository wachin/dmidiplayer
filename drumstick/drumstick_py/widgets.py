"""Reusable PyQt6 widgets for the Drumstick Python port."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget


class PianoKeyboard(QWidget):
    BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active: set[int] = set()
        self._min_note = 21
        self._max_note = 108
        self.setMinimumHeight(72)

    def note_on(self, note: int) -> None:
        self._active.add(note)
        self.update()

    def note_off(self, note: int) -> None:
        self._active.discard(note)
        self.update()

    def clear(self) -> None:
        self._active.clear()
        self.update()

    def set_note_range(self, min_note: int, max_note: int) -> None:
        self._min_note = max(0, min(127, min_note))
        self._max_note = max(self._min_note, min(127, max_note))
        self.update()

    def visible_white_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 not in self.BLACK_KEY_CLASSES]

    def visible_black_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 in self.BLACK_KEY_CLASSES]

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        white_notes = self.visible_white_notes()
        if not white_notes:
            white_notes = [n for n in range(21, 109) if n % 12 not in (1, 3, 6, 8, 10)]
        key_width = max(1, self.width() / len(white_notes))
        white_active = QColor("#2f80ed")
        black_idle = QColor("#111827")
        black_active = QColor("#60a5fa")
        painter.setPen(Qt.GlobalColor.black)
        white_positions: dict[int, tuple[int, int]] = {}
        for index, note in enumerate(white_notes):
            rect_x = round(index * key_width)
            rect_w = round((index + 1) * key_width) - rect_x
            white_positions[note] = (rect_x, rect_w)
            painter.fillRect(rect_x, 0, rect_w, self.height(), white_active if note in self._active else Qt.GlobalColor.white)
            painter.drawRect(rect_x, 0, rect_w, self.height() - 1)
        black_height = max(12, round(self.height() * 0.62))
        black_width = max(4, round(key_width * 0.62))
        for note in self.visible_black_notes():
            previous_white = note - 1
            while previous_white >= self._min_note and previous_white % 12 in self.BLACK_KEY_CLASSES:
                previous_white -= 1
            if previous_white not in white_positions:
                continue
            base_x, base_w = white_positions[previous_white]
            rect_x = round(base_x + base_w - (black_width / 2))
            painter.fillRect(
                rect_x,
                0,
                black_width,
                black_height,
                black_active if note in self._active else black_idle,
            )
            painter.drawRect(rect_x, 0, black_width, black_height)

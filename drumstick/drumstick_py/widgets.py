"""Reusable PyQt6 widgets for the Drumstick Python port."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget


class PianoKeyboard(QWidget):
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

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        white_notes = [n for n in range(self._min_note, self._max_note + 1) if n % 12 not in (1, 3, 6, 8, 10)]
        if not white_notes:
            white_notes = [n for n in range(21, 109) if n % 12 not in (1, 3, 6, 8, 10)]
        key_width = max(1, self.width() / len(white_notes))
        active = QColor("#2f80ed")
        painter.setPen(Qt.GlobalColor.black)
        for index, note in enumerate(white_notes):
            rect_x = round(index * key_width)
            rect_w = round((index + 1) * key_width) - rect_x
            painter.fillRect(rect_x, 0, rect_w, self.height(), active if note in self._active else Qt.GlobalColor.white)
            painter.drawRect(rect_x, 0, rect_w, self.height() - 1)

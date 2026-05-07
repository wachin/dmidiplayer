"""Reusable PyQt6 widgets for the Drumstick Python port."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget


class PianoKeyboard(QWidget):
    BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}
    NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active: set[int] = set()
        self._active_velocities: dict[int, int] = {}
        self._min_note = 21
        self._max_note = 108
        self._note_label_mode = "never"
        self.setMinimumHeight(72)

    def note_on(self, note: int, velocity: int = 127) -> None:
        self._active.add(note)
        self._active_velocities[note] = max(1, min(127, velocity))
        self.update()

    def note_off(self, note: int) -> None:
        self._active.discard(note)
        self._active_velocities.pop(note, None)
        self.update()

    def clear(self) -> None:
        self._active.clear()
        self._active_velocities.clear()
        self.update()

    def set_note_range(self, min_note: int, max_note: int) -> None:
        self._min_note = max(0, min(127, min_note))
        self._max_note = max(self._min_note, min(127, max_note))
        self.update()

    def set_note_label_mode(self, mode: str) -> None:
        if mode not in {"never", "minimal", "active", "always"}:
            mode = "never"
        self._note_label_mode = mode
        self.update()

    def visible_white_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 not in self.BLACK_KEY_CLASSES]

    def visible_black_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 in self.BLACK_KEY_CLASSES]

    def note_label(self, note: int) -> str:
        name = self.NOTE_NAMES[note % 12]
        octave = (note // 12) - 1
        return f"{name}{octave}"

    def visible_note_labels(self) -> dict[int, str]:
        notes = self.visible_white_notes() + self.visible_black_notes()
        if self._note_label_mode == "never":
            return {}
        if self._note_label_mode == "minimal":
            notes = [note for note in notes if note % 12 == 0]
        elif self._note_label_mode == "active":
            notes = [note for note in notes if note in self._active]
        return {note: self.note_label(note) for note in sorted(notes)}

    def active_note_color(self, note: int, black_key: bool = False) -> QColor:
        velocity = self._active_velocities.get(note, 127)
        if black_key:
            low = QColor("#1d4ed8")
            high = QColor("#93c5fd")
        else:
            low = QColor("#bfdbfe")
            high = QColor("#1d4ed8")
        return self._interpolate_color(low, high, velocity / 127.0)

    def _interpolate_color(self, low: QColor, high: QColor, ratio: float) -> QColor:
        ratio = max(0.0, min(1.0, ratio))
        return QColor(
            round(low.red() + (high.red() - low.red()) * ratio),
            round(low.green() + (high.green() - low.green()) * ratio),
            round(low.blue() + (high.blue() - low.blue()) * ratio),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        white_notes = self.visible_white_notes()
        labels = self.visible_note_labels()
        if not white_notes:
            white_notes = [n for n in range(21, 109) if n % 12 not in (1, 3, 6, 8, 10)]
        key_width = max(1, self.width() / len(white_notes))
        black_idle = QColor("#111827")
        painter.setPen(Qt.GlobalColor.black)
        white_positions: dict[int, tuple[int, int]] = {}
        for index, note in enumerate(white_notes):
            rect_x = round(index * key_width)
            rect_w = round((index + 1) * key_width) - rect_x
            white_positions[note] = (rect_x, rect_w)
            painter.fillRect(
                rect_x,
                0,
                rect_w,
                self.height(),
                self.active_note_color(note) if note in self._active else Qt.GlobalColor.white,
            )
            painter.drawRect(rect_x, 0, rect_w, self.height() - 1)
            if note in labels:
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(rect_x, self.height() - 18, rect_w, 16, int(Qt.AlignmentFlag.AlignCenter), labels[note])
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
                self.active_note_color(note, black_key=True) if note in self._active else black_idle,
            )
            painter.drawRect(rect_x, 0, black_width, black_height)
            if note in labels:
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(rect_x, black_height - 16, black_width, 14, int(Qt.AlignmentFlag.AlignCenter), labels[note])

"""Reusable PyQt6 widgets for the Drumstick Python port."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget


class PianoKeyboard(QWidget):
    notePressed = pyqtSignal(int, int)
    noteReleased = pyqtSignal(int)
    BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}
    NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    KEYBOARD_NOTE_STEPS = {
        int(Qt.Key.Key_Z): 0,
        int(Qt.Key.Key_S): 1,
        int(Qt.Key.Key_X): 2,
        int(Qt.Key.Key_D): 3,
        int(Qt.Key.Key_C): 4,
        int(Qt.Key.Key_V): 5,
        int(Qt.Key.Key_G): 6,
        int(Qt.Key.Key_B): 7,
        int(Qt.Key.Key_H): 8,
        int(Qt.Key.Key_N): 9,
        int(Qt.Key.Key_J): 10,
        int(Qt.Key.Key_M): 11,
        int(Qt.Key.Key_Comma): 12,
        int(Qt.Key.Key_L): 13,
        int(Qt.Key.Key_Period): 14,
        int(Qt.Key.Key_Semicolon): 15,
        int(Qt.Key.Key_Slash): 16,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active: set[int] = set()
        self._active_velocities: dict[int, int] = {}
        self._min_note = 21
        self._max_note = 108
        self._note_label_mode = "never"
        self._octave_offset = -1
        self._note_label_font = QFont("Sans Serif", 8)
        self._velocity_tinting_enabled = True
        self._white_low_color = QColor("#bfdbfe")
        self._white_high_color = QColor("#1d4ed8")
        self._black_low_color = QColor("#1d4ed8")
        self._black_high_color = QColor("#93c5fd")
        self._black_idle_color = QColor("#111827")
        self._mouse_note: int | None = None
        self._pressed_keys: dict[int, int] = {}
        self.setMinimumHeight(72)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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

    def set_octave_offset(self, offset: int) -> None:
        self._octave_offset = offset
        self.update()

    def set_note_label_font(self, font: QFont) -> None:
        self._note_label_font = QFont(font)
        self.update()

    def set_velocity_tinting_enabled(self, enabled: bool) -> None:
        self._velocity_tinting_enabled = bool(enabled)
        self.update()

    def set_active_colors(
        self,
        *,
        white_low: QColor | str,
        white_high: QColor | str,
        black_low: QColor | str,
        black_high: QColor | str,
        black_idle: QColor | str | None = None,
    ) -> None:
        self._white_low_color = QColor(white_low)
        self._white_high_color = QColor(white_high)
        self._black_low_color = QColor(black_low)
        self._black_high_color = QColor(black_high)
        if black_idle is not None:
            self._black_idle_color = QColor(black_idle)
        self.update()

    def visible_white_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 not in self.BLACK_KEY_CLASSES]

    def visible_black_notes(self) -> list[int]:
        return [note for note in range(self._min_note, self._max_note + 1) if note % 12 in self.BLACK_KEY_CLASSES]

    def note_label(self, note: int) -> str:
        name = self.NOTE_NAMES[note % 12]
        octave = (note // 12) + self._octave_offset
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
        velocity = self._active_velocities.get(note, 127) if self._velocity_tinting_enabled else 127
        if black_key:
            low = self._black_low_color
            high = self._black_high_color
        else:
            low = self._white_low_color
            high = self._white_high_color
        return self._interpolate_color(low, high, velocity / 127.0)

    def _interpolate_color(self, low: QColor, high: QColor, ratio: float) -> QColor:
        ratio = max(0.0, min(1.0, ratio))
        return QColor(
            round(low.red() + (high.red() - low.red()) * ratio),
            round(low.green() + (high.green() - low.green()) * ratio),
            round(low.blue() + (high.blue() - low.blue()) * ratio),
        )

    def keyboard_base_note(self) -> int:
        for note in self.visible_white_notes():
            if note % 12 == 0:
                return note
        return self._min_note

    def mapped_key_note(self, key: int) -> int | None:
        step = self.KEYBOARD_NOTE_STEPS.get(int(key))
        if step is None:
            return None
        note = self.keyboard_base_note() + step
        if note < self._min_note or note > self._max_note:
            return None
        return note

    def note_at_position(self, position: QPointF) -> int | None:
        black_rects = self.black_key_rects()
        for note, (rect_x, rect_y, rect_w, rect_h) in black_rects.items():
            if rect_x <= position.x() <= rect_x + rect_w and rect_y <= position.y() <= rect_y + rect_h:
                return note
        white_rects = self.white_key_rects()
        for note, (rect_x, rect_y, rect_w, rect_h) in white_rects.items():
            if rect_x <= position.x() <= rect_x + rect_w and rect_y <= position.y() <= rect_y + rect_h:
                return note
        return None

    def white_key_rects(self) -> dict[int, tuple[int, int, int, int]]:
        white_notes = self.visible_white_notes()
        if not white_notes:
            white_notes = [n for n in range(21, 109) if n % 12 not in self.BLACK_KEY_CLASSES]
        key_width = max(1, self.width() / len(white_notes))
        rects: dict[int, tuple[int, int, int, int]] = {}
        for index, note in enumerate(white_notes):
            rect_x = round(index * key_width)
            rect_w = round((index + 1) * key_width) - rect_x
            rects[note] = (rect_x, 0, rect_w, self.height())
        return rects

    def black_key_rects(self) -> dict[int, tuple[int, int, int, int]]:
        white_rects = self.white_key_rects()
        white_notes = sorted(white_rects)
        if not white_notes:
            return {}
        key_width = max(1, self.width() / len(white_notes))
        black_height = max(12, round(self.height() * 0.62))
        black_width = max(4, round(key_width * 0.62))
        rects: dict[int, tuple[int, int, int, int]] = {}
        for note in self.visible_black_notes():
            previous_white = note - 1
            while previous_white >= self._min_note and previous_white % 12 in self.BLACK_KEY_CLASSES:
                previous_white -= 1
            if previous_white not in white_rects:
                continue
            base_x, _base_y, base_w, _base_h = white_rects[previous_white]
            rect_x = round(base_x + base_w - (black_width / 2))
            rects[note] = (rect_x, 0, black_width, black_height)
        return rects

    def _press_note(self, note: int, velocity: int = 100) -> None:
        self.note_on(note, velocity)
        self.notePressed.emit(note, velocity)

    def _release_note(self, note: int) -> None:
        self.note_off(note)
        self.noteReleased.emit(note)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        white_notes = self.visible_white_notes()
        labels = self.visible_note_labels()
        if not white_notes:
            white_notes = [n for n in range(21, 109) if n % 12 not in (1, 3, 6, 8, 10)]
        key_width = max(1, self.width() / len(white_notes))
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
                painter.setFont(self._note_label_font)
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
                self.active_note_color(note, black_key=True) if note in self._active else self._black_idle_color,
            )
            painter.drawRect(rect_x, 0, black_width, black_height)
            if note in labels:
                painter.setFont(self._note_label_font)
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(rect_x, black_height - 16, black_width, 14, int(Qt.AlignmentFlag.AlignCenter), labels[note])

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setFocus()
        note = self.note_at_position(event.position())
        if note is not None:
            self._mouse_note = note
            self._press_note(note)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        note = self.note_at_position(event.position())
        if note == self._mouse_note:
            event.accept()
            return
        if self._mouse_note is not None:
            self._release_note(self._mouse_note)
            self._mouse_note = None
        if note is not None:
            self._mouse_note = note
            self._press_note(note)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._mouse_note is not None:
            self._release_note(self._mouse_note)
            self._mouse_note = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            event.ignore()
            return
        note = self.mapped_key_note(event.key())
        if note is None:
            super().keyPressEvent(event)
            return
        if event.key() not in self._pressed_keys:
            self._pressed_keys[event.key()] = note
            self._press_note(note)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            event.ignore()
            return
        note = self._pressed_keys.pop(event.key(), None)
        if note is None:
            super().keyReleaseEvent(event)
            return
        self._release_note(note)
        event.accept()

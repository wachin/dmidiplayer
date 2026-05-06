"""dmidiplayer sequence model backed by drumstick_py.file."""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from drumstick_py import MidiEvent, MidiFile, read_smf


class Sequence(QObject):
    loaded = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.midi: MidiFile | None = None

    def load_file(self, file_name: str | Path) -> None:
        self.midi = read_smf(file_name)
        self.loaded.emit()

    def clear(self) -> None:
        self.midi = None
        self.loaded.emit()

    @property
    def events(self) -> list[MidiEvent]:
        return [] if self.midi is None else self.midi.events

    @property
    def title(self) -> str:
        return "" if self.midi is None else self.midi.title

    @property
    def length_ticks(self) -> int:
        return 0 if self.midi is None else self.midi.length_ticks

    @property
    def length_microseconds(self) -> int:
        return 0 if self.midi is None else self.midi.length_microseconds

    @property
    def division(self) -> int:
        return 480 if self.midi is None else self.midi.division

    def tick_to_microseconds(self, tick: int) -> int:
        return 0 if self.midi is None else self.midi.tick_to_microseconds(tick)

    def microseconds_to_tick(self, microseconds: int) -> int:
        return 0 if self.midi is None else self.midi.microseconds_to_tick(microseconds)

    def bpm_at_tick(self, tick: int) -> float:
        return 120.0 if self.midi is None else self.midi.bpm_at_tick(tick)

    @property
    def bar_count(self) -> int:
        return 1 if self.midi is None else self.midi.bar_count

    def bar_number_at_tick(self, tick: int) -> int:
        return 1 if self.midi is None else self.midi.bar_number_at_tick(tick)

    def tick_for_bar(self, bar_number: int) -> int:
        return 0 if self.midi is None else self.midi.tick_for_bar(bar_number)

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

    def time_signature_at_tick(self, tick: int) -> tuple[int, int]:
        if self.midi is None:
            return (4, 4)
        numerator = 4
        denominator = 4
        for signature in self.midi.time_signatures:
            if signature.tick > tick:
                break
            numerator = signature.numerator
            denominator = signature.denominator
        return (numerator, denominator)

    def used_channels(self) -> list[int]:
        if self.midi is None:
            return []
        return sorted({event.channel for event in self.midi.events if event.channel is not None})

    def initial_programs(self) -> dict[int, int]:
        programs: dict[int, int] = {}
        if self.midi is None:
            return programs
        for event in self.midi.events:
            if event.channel is None or event.kind != "program_change" or not event.data:
                continue
            programs.setdefault(event.channel, event.data[0])
        return programs

    def text_events(self) -> list[object]:
        if self.midi is None:
            return []
        return list(self.midi.text_events)

    def midi_tracks(self) -> list[tuple[int, set[int]]]:
        if self.midi is None:
            return []
        tracks: list[tuple[int, set[int]]] = []
        for track_number, track in enumerate(self.midi.tracks):
            channels = {event.channel for event in track.events if event.channel is not None}
            if channels:
                tracks.append((track_number, channels))
        return tracks

    def midi_track_infos(self) -> list[dict[str, object]]:
        if self.midi is None:
            return []
        tracks: list[dict[str, object]] = []
        for track_number, track in enumerate(self.midi.tracks):
            channels = {event.channel for event in track.events if event.channel is not None}
            if not channels:
                continue
            notes: list[int] = []
            for event in track.events:
                if event.kind in ("note_on", "note_off", "key_pressure") and event.data:
                    notes.append(event.data[0])
            min_note = min(notes, default=21)
            max_note = max(notes, default=108)
            tracks.append(
                {
                    "track": track_number,
                    "channels": channels,
                    "title": track.name or track.instrument_name,
                    "track_name": track.name,
                    "instrument_name": track.instrument_name,
                    "min_note": min_note,
                    "max_note": max_note,
                }
            )
        return tracks

    def default_channel_labels(self) -> dict[int, str]:
        if self.midi is None:
            return {}
        labels: dict[int, str] = {}
        for info in self.midi_track_infos():
            title = str(info.get("instrument_name") or info.get("track_name") or "").strip()
            if not title:
                continue
            for channel in sorted(set(info["channels"])):
                labels.setdefault(int(channel), title)
        return labels

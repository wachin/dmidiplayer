"""dmidiplayer sequence model backed by drumstick_py.file."""

from __future__ import annotations

import codecs
from encodings.aliases import aliases
from dataclasses import dataclass
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from drumstick_py import MidiEvent, MidiFile, TextEvent, read_smf
from drumstick_py.file import decode_midi_text
from .instrumentset import gm_program_name, percussion_name


def supported_text_encodings() -> list[tuple[str, str]]:
    preferred = [
        ("UTF-8", "utf-8"),
        ("Latin-1", "latin-1"),
        ("CP1252", "cp1252"),
        ("CP437", "cp437"),
        ("CP850", "cp850"),
        ("CP852", "cp852"),
        ("ISO-8859-15", "iso8859-15"),
        ("Mac Roman", "mac-roman"),
        ("KOI8-R", "koi8-r"),
        ("UTF-16", "utf-16"),
        ("UTF-16 LE", "utf-16-le"),
        ("UTF-16 BE", "utf-16-be"),
    ]
    seen = {encoding for _, encoding in preferred}
    entries = list(preferred)
    discovered: set[str] = set()
    for alias in aliases.values():
        try:
            canonical = codecs.lookup(alias).name
        except LookupError:
            continue
        discovered.add(canonical)
    for encoding in sorted(discovered):
        if encoding in seen:
            continue
        entries.append((encoding.upper(), encoding))
    return entries


@dataclass(frozen=True, slots=True)
class SequenceTextEvent:
    source: TextEvent
    default_encoding_getter: object

    @property
    def track(self) -> int:
        return self.source.track

    @property
    def tick(self) -> int:
        return self.source.tick

    @property
    def meta_type(self) -> int:
        return self.source.meta_type

    @property
    def data(self) -> bytes:
        return self.source.data

    @property
    def text(self) -> str:
        return self.decoded_text()

    def decoded_text(self, preferred_encoding: str | None = None) -> str:
        getter = self.default_encoding_getter
        default_encoding = getter() if callable(getter) else None
        return self.source.decoded_text(preferred_encoding or default_encoding)


class Sequence(QObject):
    loaded = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.midi: MidiFile | None = None
        self._text_encoding: str | None = None

    def load_file(self, file_name: str | Path) -> None:
        self.midi = read_smf(file_name)
        self.loaded.emit()

    def clear(self) -> None:
        self.midi = None
        self.loaded.emit()

    def set_text_encoding(self, encoding: str | None) -> None:
        self._text_encoding = encoding

    def text_encoding(self) -> str | None:
        return self._text_encoding

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

    def initial_banks(self) -> dict[int, int]:
        banks: dict[int, int] = {}
        bank_msb: dict[int, int] = {}
        bank_lsb: dict[int, int] = {}
        if self.midi is None:
            return banks
        for event in self.midi.events:
            if event.channel is None or event.kind != "control_change" or len(event.data) < 2:
                continue
            controller = event.data[0]
            value = event.data[1]
            if controller == 0:
                bank_msb[event.channel] = value
                banks[event.channel] = (value * 0x80) + bank_lsb.get(event.channel, 0)
            elif controller == 32:
                bank_lsb[event.channel] = value
                banks[event.channel] = (bank_msb.get(event.channel, 0) * 0x80) + value
        return banks

    def channel_part_names(self) -> dict[int, list[str]]:
        """Return track/part names associated with each used MIDI channel.

        Tracks and instruments are deliberately *not* treated as one-to-one:
        several tracks may share a channel.  The returned lists preserve every
        distinct name for the channel without creating duplicate channels.
        """
        names: dict[int, list[str]] = {}
        if self.midi is None:
            return names
        for track in self.midi.tracks:
            channels = {event.channel for event in track.events if event.channel is not None}
            if not channels:
                continue
            track_name = self._decode_track_text(track.name_data, track.name)
            instrument_name = self._decode_track_text(track.instrument_name_data, track.instrument_name)
            name = track_name or instrument_name
            if not name:
                continue
            for channel in sorted(channels):
                channel_names = names.setdefault(channel, [])
                if name not in channel_names:
                    channel_names.append(name)
        return names

    @staticmethod
    def selector_label(channel: int, instrument: str, part_name: str) -> str:
        label = f"{channel + 1}: {instrument}"
        if part_name:
            folded_instrument = instrument.casefold()
            folded_part = part_name.casefold()
            if folded_part != folded_instrument and folded_part not in folded_instrument and folded_instrument not in folded_part:
                label += f" - {part_name}"
        return label

    def instrument_at_tick(
        self,
        channel: int,
        tick: int,
        percussion_channel: int = 9,
    ) -> tuple[int, int, str, bool]:
        """Return ``(program, bank, instrument name, is percussion)``.

        The program used by the score at ``tick`` is the last program change at
        or before that tick (0 when the file never selects a program).
        """
        if self.midi is None:
            return (0, 0, "", False)
        if channel == percussion_channel:
            return (0, 0, "Drums", True)
        program = 0
        bank_msb = 0
        bank_lsb = 0
        for event in self.midi.events:
            if event.tick > tick:
                break
            if event.channel != channel:
                continue
            if event.kind == "control_change" and len(event.data) >= 2:
                if event.data[0] == 0:
                    bank_msb = event.data[1]
                elif event.data[0] == 32:
                    bank_lsb = event.data[1]
            elif event.kind == "program_change" and event.data:
                program = event.data[0]
        return (program, (bank_msb << 7) | bank_lsb, gm_program_name(program), False)

    def channel_infos(self, percussion_channel: int = 9) -> list[dict[str, object]]:
        """Return one authoritative entry per used MIDI channel.

        This is the data model shared by the Piano Player and the Channels
        dialog.  It merges tracks that share a channel and keeps program
        changes so the UI can follow them during playback.
        """
        if self.midi is None:
            return []
        used = self.used_channels()
        if not used:
            return []
        used_set = set(used)
        part_names = self.channel_part_names()
        first_programs: dict[int, int] = {}
        first_banks: dict[int, int] = {}
        program_changes: dict[int, list[tuple[int, int]]] = {channel: [] for channel in used}
        bank_msb: dict[int, int] = {}
        bank_lsb: dict[int, int] = {}
        notes: dict[int, list[int]] = {channel: [] for channel in used}
        note_counts: dict[int, int] = {channel: 0 for channel in used}
        for event in self.midi.events:
            channel = event.channel
            if channel is None or channel not in used_set:
                continue
            if event.kind == "control_change" and len(event.data) >= 2:
                if event.data[0] == 0:
                    bank_msb[channel] = event.data[1]
                elif event.data[0] == 32:
                    bank_lsb[channel] = event.data[1]
            elif event.kind == "program_change" and event.data:
                program_changes[channel].append((event.tick, event.data[0]))
                if channel not in first_programs:
                    first_programs[channel] = event.data[0]
                    first_banks[channel] = (bank_msb.get(channel, 0) << 7) | bank_lsb.get(channel, 0)
            elif event.kind in ("note_on", "note_off", "key_pressure") and event.data:
                notes[channel].append(event.data[0])
                if event.kind == "key_pressure" or (
                    event.kind == "note_on" and len(event.data) >= 2 and event.data[1] > 0
                ):
                    note_counts[channel] += 1
        labels = self.default_channel_labels(percussion_channel)
        infos: list[dict[str, object]] = []
        for channel in used:
            names = part_names.get(channel, [])
            part_name = names[0] if names else ""
            is_percussion = channel == percussion_channel
            program = first_programs.get(channel, 0)
            bank = first_banks.get(channel, 0)
            instrument = "Drums" if is_percussion else gm_program_name(program)
            note_list = notes.get(channel, [])
            infos.append(
                {
                    "channel": channel,
                    "title": labels.get(channel, ""),
                    "part_name": part_name,
                    "part_names": names,
                    "instrument_name": instrument,
                    "program": program,
                    "bank": bank,
                    "percussion": is_percussion,
                    "min_note": min(note_list, default=21),
                    "max_note": max(note_list, default=108),
                    "note_count": note_counts[channel],
                    "program_changes": program_changes[channel],
                    "label": self.selector_label(channel, instrument, part_name),
                }
            )
        return infos


    def info_metadata(self) -> dict[str, str]:
        if self.midi is None:
            return {}
        if not self.midi.info_data:
            return dict(self.midi.info)
        return {
            key: decode_midi_text(data, self._text_encoding).strip()
            for key, data in self.midi.info_data.items()
            if decode_midi_text(data, self._text_encoding).strip()
        }

    def _decode_track_text(self, data: bytes, fallback: str) -> str:
        if not data:
            return fallback
        return decode_midi_text(data, self._text_encoding).strip()

    def text_events(self) -> list[object]:
        if self.midi is None:
            return []
        return [
            SequenceTextEvent(event, self.text_encoding)
            for event in self.midi.text_events
        ]

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
            track_name = self._decode_track_text(track.name_data, track.name)
            instrument_name = self._decode_track_text(track.instrument_name_data, track.instrument_name)
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
                    "title": track_name or instrument_name,
                    "track_name": track_name,
                    "instrument_name": instrument_name,
                    "min_note": min_note,
                    "max_note": max_note,
                }
            )
        return tracks

    def pianola_channel_infos(self, percussion_channel: int = 9) -> list[dict[str, object]]:
        """Return per-channel info for the Pianola, matching C++ behaviour.

        The C++ Pianola shows one piano keyboard per MIDI channel (0-15),
        only for channels that are actually used in the loaded file.  The
        number of rows therefore comes from channels, not from tracks, and
        multiple tracks sharing a channel are merged into one keyboard
        (``Pianola::m_frame[MIDI_STD_CHANNELS]``).  Tabs are a Python-port
        addition to keep up to eight readable keyboards on screen.
        """
        return self.channel_infos(percussion_channel)

    def default_channel_labels(self, percussion_channel: int = 9) -> dict[int, str]:
        if self.midi is None:
            return {}
        labels: dict[int, str] = {}
        for info in self.midi_track_infos():
            title = str(info.get("instrument_name") or info.get("track_name") or "").strip()
            if not title:
                continue
            for channel in sorted(set(info["channels"])):
                labels.setdefault(int(channel), title)
        programs = self.initial_programs()
        first_notes: dict[int, int] = {}
        for event in self.midi.events:
            if event.channel is None or channel_has_label(labels, event.channel):
                continue
            if event.kind not in ("note_on", "note_off", "key_pressure") or not event.data:
                continue
            first_notes.setdefault(event.channel, event.data[0])
        for channel in self.used_channels():
            if channel_has_label(labels, channel):
                continue
            if channel == percussion_channel and channel in first_notes:
                labels[channel] = percussion_name(first_notes[channel])
                continue
            if channel in programs:
                labels[channel] = gm_program_name(programs[channel])
        return labels


def channel_has_label(labels: dict[int, str], channel: int) -> bool:
    return channel in labels and bool(labels[channel].strip())

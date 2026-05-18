"""Minimal Standard MIDI File reader used by the PyQt6 port.

The original Drumstick file library supports SMF, RIFF MIDI, and Cakewalk WRK.
This module starts with SMF because it unlocks dmidiplayer's main workflow and
keeps the first Python version dependency-free on Debian 12. It also supports
the common RIFF/RMID wrapper used by some MIDI collections.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
import struct

WRK_HEADER = b"CAKEWALK"


class MidiFileError(ValueError):
    """Raised when a MIDI file cannot be parsed."""


@dataclass(frozen=True, slots=True)
class _WrkHeader:
    major_version: int
    minor_version: int
    first_chunk_id: int | None = None
    first_chunk_length: int | None = None
    timebase: int | None = None
    software_version: str | None = None
    track_number: int | None = None
    track_name: str | None = None
    comments: str | None = None
    track_volume_track: int | None = None
    track_volume: int | None = None
    track_bank_track: int | None = None
    track_bank: int | None = None
    track_patch_track: int | None = None
    track_patch: int | None = None
    track_offset_track: int | None = None
    track_offset: int | None = None
    track_repetitions_track: int | None = None
    track_repetitions: int | None = None
    time_format: int | None = None
    time_format_offset: int | None = None
    new_track_offset_track: int | None = None
    new_track_offset: int | None = None
    track_chunk_number: int | None = None
    track_chunk_name: str | None = None
    track_chunk_channel: int | None = None
    track_chunk_patch: int | None = None
    marker_count: int | None = None
    first_marker_time: int | None = None
    first_marker_smpte: int | None = None
    first_marker_name: str | None = None


def decode_midi_text(data: bytes, preferred_encoding: str | None = None) -> str:
    if preferred_encoding is not None:
        return data.decode(preferred_encoding, errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if any(0x80 <= value <= 0x9F for value in data):
        try:
            return data.decode("cp1252")
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1", errors="replace")


@dataclass(slots=True)
class MidiEvent:
    tick: int
    kind: str
    channel: int | None = None
    data: bytes = b""
    meta_type: int | None = None

    @property
    def text(self) -> str:
        return decode_midi_text(self.data)

    @property
    def tempo_us_per_quarter(self) -> int | None:
        if self.kind == "meta" and self.meta_type == 0x51 and len(self.data) == 3:
            return int.from_bytes(self.data, "big")
        return None


@dataclass(frozen=True, slots=True)
class TempoChange:
    tick: int
    microseconds_per_quarter: int


@dataclass(frozen=True, slots=True)
class TimeSignature:
    tick: int
    numerator: int
    denominator: int
    clocks_per_metronome: int
    thirty_seconds_per_quarter: int


@dataclass(frozen=True, slots=True)
class KeySignature:
    tick: int
    sharps_flats: int
    minor: bool


@dataclass(frozen=True, slots=True)
class TextEvent:
    track: int
    tick: int
    meta_type: int
    data: bytes

    @property
    def text(self) -> str:
        return decode_midi_text(self.data)

    def decoded_text(self, preferred_encoding: str | None = None) -> str:
        return decode_midi_text(self.data, preferred_encoding)


@dataclass(slots=True)
class MidiTrack:
    events: list[MidiEvent] = field(default_factory=list)
    name: str = ""
    instrument_name: str = ""


@dataclass(slots=True)
class MidiFile:
    path: Path
    format: int
    division: int
    tracks: list[MidiTrack]
    _events_cache: list[MidiEvent] | None = field(default=None, init=False, repr=False)
    _length_ticks_cache: int | None = field(default=None, init=False, repr=False)
    _tempo_changes_cache: list[TempoChange] | None = field(default=None, init=False, repr=False)
    _time_signatures_cache: list[TimeSignature] | None = field(default=None, init=False, repr=False)
    _key_signatures_cache: list[KeySignature] | None = field(default=None, init=False, repr=False)
    _text_events_cache: list[TextEvent] | None = field(default=None, init=False, repr=False)
    _length_microseconds_cache: int | None = field(default=None, init=False, repr=False)
    _bar_count_cache: int | None = field(default=None, init=False, repr=False)
    _title_cache: str | None = field(default=None, init=False, repr=False)

    @property
    def events(self) -> list[MidiEvent]:
        if self._events_cache is None:
            self._events_cache = sorted((event for track in self.tracks for event in track.events), key=lambda e: e.tick)
        return self._events_cache

    @property
    def length_ticks(self) -> int:
        if self._length_ticks_cache is None:
            self._length_ticks_cache = max((event.tick for event in self.events), default=0)
        return self._length_ticks_cache

    @property
    def tempo_changes(self) -> list[TempoChange]:
        if self._tempo_changes_cache is not None:
            return self._tempo_changes_cache
        changes = [
            TempoChange(event.tick, tempo)
            for event in self.events
            if (tempo := event.tempo_us_per_quarter) is not None
        ]
        if not changes or changes[0].tick > 0:
            changes.insert(0, TempoChange(0, 500_000))
        elif changes[0].tick == 0 and changes[0].microseconds_per_quarter != 500_000:
            changes.insert(0, TempoChange(0, 500_000))
        self._tempo_changes_cache = _dedupe_tempo_changes(changes)
        return self._tempo_changes_cache

    @property
    def time_signatures(self) -> list[TimeSignature]:
        if self._time_signatures_cache is not None:
            return self._time_signatures_cache
        signatures: list[TimeSignature] = []
        for event in self.events:
            if event.kind == "meta" and event.meta_type == 0x58 and len(event.data) >= 4:
                signatures.append(
                    TimeSignature(
                        tick=event.tick,
                        numerator=event.data[0],
                        denominator=2 ** event.data[1],
                        clocks_per_metronome=event.data[2],
                        thirty_seconds_per_quarter=event.data[3],
                    )
                )
        self._time_signatures_cache = signatures
        return self._time_signatures_cache

    @property
    def key_signatures(self) -> list[KeySignature]:
        if self._key_signatures_cache is not None:
            return self._key_signatures_cache
        signatures: list[KeySignature] = []
        for event in self.events:
            if event.kind == "meta" and event.meta_type == 0x59 and len(event.data) >= 2:
                sf = event.data[0]
                if sf >= 128:
                    sf -= 256
                signatures.append(KeySignature(tick=event.tick, sharps_flats=sf, minor=bool(event.data[1])))
        self._key_signatures_cache = signatures
        return self._key_signatures_cache

    @property
    def text_events(self) -> list[TextEvent]:
        if self._text_events_cache is None:
            text_events: list[TextEvent] = []
            for track_number, track in enumerate(self.tracks):
                for event in track.events:
                    if event.kind == "meta" and event.meta_type in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07):
                        text_events.append(TextEvent(track_number, event.tick, event.meta_type, event.data))
            self._text_events_cache = sorted(text_events, key=lambda event: (event.tick, event.track, event.meta_type))
        return self._text_events_cache

    @property
    def length_microseconds(self) -> int:
        if self._length_microseconds_cache is None:
            self._length_microseconds_cache = self.tick_to_microseconds(self.length_ticks)
        return self._length_microseconds_cache

    @property
    def title(self) -> str:
        if self._title_cache is not None:
            return self._title_cache
        for event in self.events:
            if event.kind == "meta" and event.meta_type in (0x03, 0x01) and event.text.strip():
                self._title_cache = event.text.strip()
                return self._title_cache
        self._title_cache = self.path.name
        return self._title_cache

    def tick_to_microseconds(self, tick: int) -> int:
        if tick <= 0:
            return 0
        if self.division & 0x8000:
            return _smpte_tick_to_microseconds(self.division, tick)

        ticks_per_quarter = self.division
        if ticks_per_quarter <= 0:
            raise MidiFileError("Invalid MIDI division")

        elapsed = 0
        previous_tick = 0
        previous_tempo = 500_000
        for change in self.tempo_changes:
            if change.tick <= 0:
                previous_tempo = change.microseconds_per_quarter
                continue
            if change.tick >= tick:
                break
            elapsed += ((change.tick - previous_tick) * previous_tempo) // ticks_per_quarter
            previous_tick = change.tick
            previous_tempo = change.microseconds_per_quarter
        elapsed += ((tick - previous_tick) * previous_tempo) // ticks_per_quarter
        return elapsed

    def event_microseconds(self, event: MidiEvent) -> int:
        return self.tick_to_microseconds(event.tick)

    def microseconds_to_tick(self, microseconds: int) -> int:
        if microseconds <= 0:
            return 0
        if self.division & 0x8000:
            return _smpte_microseconds_to_tick(self.division, microseconds)

        ticks_per_quarter = self.division
        if ticks_per_quarter <= 0:
            raise MidiFileError("Invalid MIDI division")

        elapsed = 0
        previous_tick = 0
        previous_tempo = 500_000
        changes = [change for change in self.tempo_changes if change.tick > 0]
        for change in changes:
            segment_us = ((change.tick - previous_tick) * previous_tempo) // ticks_per_quarter
            if elapsed + segment_us >= microseconds:
                remaining = microseconds - elapsed
                return previous_tick + (remaining * ticks_per_quarter) // previous_tempo
            elapsed += segment_us
            previous_tick = change.tick
            previous_tempo = change.microseconds_per_quarter
        remaining = microseconds - elapsed
        return previous_tick + (remaining * ticks_per_quarter) // previous_tempo

    def tempo_at_tick(self, tick: int) -> int:
        if self.division & 0x8000:
            return 500_000
        changes = self.tempo_changes
        index = bisect_right([change.tick for change in changes], max(0, tick)) - 1
        return changes[max(0, index)].microseconds_per_quarter

    def bpm_at_tick(self, tick: int) -> float:
        tempo = self.tempo_at_tick(tick)
        if tempo <= 0:
            return 120.0
        return 60_000_000 / tempo

    @property
    def bar_count(self) -> int:
        if self._bar_count_cache is None:
            self._bar_count_cache = self._bar_number_for_tick(self.length_ticks, round_up=True)
        return self._bar_count_cache

    def bar_number_at_tick(self, tick: int) -> int:
        return min(self.bar_count, self._bar_number_for_tick(tick, round_up=False))

    def tick_for_bar(self, bar_number: int) -> int:
        target = max(1, bar_number) - 1
        segment_start = 0
        ticks_per_bar = self._ticks_per_bar(self._initial_time_signature())
        for signature in self._time_signature_changes_after_zero():
            segment_bars = max(0, (signature.tick - segment_start) // ticks_per_bar)
            if target < segment_bars:
                return min(self.length_ticks, segment_start + target * ticks_per_bar)
            target -= segment_bars
            segment_start = signature.tick
            ticks_per_bar = self._ticks_per_bar(signature)
        return min(self.length_ticks, segment_start + target * ticks_per_bar)

    def _bar_number_for_tick(self, tick: int, round_up: bool) -> int:
        tick = max(0, tick)
        bar_index = 0
        segment_start = 0
        ticks_per_bar = self._ticks_per_bar(self._initial_time_signature())
        for signature in self._time_signature_changes_after_zero():
            if signature.tick >= tick:
                break
            segment_ticks = max(0, signature.tick - segment_start)
            bar_index += _divide_ticks_by_bar(segment_ticks, ticks_per_bar, round_up=False)
            segment_start = signature.tick
            ticks_per_bar = self._ticks_per_bar(signature)
        segment_ticks = max(0, tick - segment_start)
        bar_index += _divide_ticks_by_bar(segment_ticks, ticks_per_bar, round_up=round_up)
        return max(1, bar_index + 1 if not round_up else bar_index)

    def _time_signature_changes_after_zero(self) -> list[TimeSignature]:
        return [signature for signature in self.time_signatures if signature.tick > 0]

    def _initial_time_signature(self) -> TimeSignature:
        initial = _default_time_signature()
        for signature in self.time_signatures:
            if signature.tick > 0:
                break
            initial = signature
        return initial

    def _ticks_per_bar(self, signature: TimeSignature) -> int:
        if self.division & 0x8000:
            return max(1, self.division & 0xFF)
        ticks = (self.division * signature.numerator * 4) // signature.denominator
        return max(1, ticks)


class _Reader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, size: int) -> bytes:
        if self._pos + size > len(self._data):
            raise MidiFileError("Unexpected end of file")
        out = self._data[self._pos : self._pos + size]
        self._pos += size
        return out

    def read_u16(self) -> int:
        return struct.unpack(">H", self.read(2))[0]

    def read_u16_le(self) -> int:
        return struct.unpack("<H", self.read(2))[0]

    def read_u32(self) -> int:
        return struct.unpack(">I", self.read(4))[0]

    def read_u32_le(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def read_varlen(self) -> int:
        value = 0
        for _ in range(4):
            byte = self.read(1)[0]
            value = (value << 7) | (byte & 0x7F)
            if not byte & 0x80:
                return value
        raise MidiFileError("Invalid variable-length quantity")

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos


def read_smf(file_name: str | Path) -> MidiFile:
    path = Path(file_name)
    return _read_midi_file_bytes(path.read_bytes(), path)


def _read_midi_file_bytes(data: bytes, path: Path) -> MidiFile:
    if _looks_like_wrk(data, path):
        header = _read_wrk_header(data, path)
        details = f"detected version {header.major_version}.{header.minor_version}"
        if header.timebase is not None:
            details += f", timebase {header.timebase}"
        if header.software_version:
            details += f", saved by {header.software_version}"
        if header.track_number is not None and header.track_name:
            details += f", track {header.track_number + 1} '{header.track_name}'"
        if header.comments:
            details += f", comments '{header.comments}'"
        if header.track_volume_track is not None and header.track_volume is not None:
            details += f", track {header.track_volume_track + 1} volume {header.track_volume}"
        if header.track_bank_track is not None and header.track_bank is not None:
            details += f", track {header.track_bank_track + 1} bank {header.track_bank}"
        if header.track_patch_track is not None and header.track_patch is not None:
            details += f", track {header.track_patch_track + 1} patch {header.track_patch}"
        if header.track_offset_track is not None and header.track_offset is not None:
            details += f", track {header.track_offset_track + 1} offset {header.track_offset}"
        if (
            header.track_repetitions_track is not None
            and header.track_repetitions is not None
        ):
            details += (
                f", track {header.track_repetitions_track + 1} repetitions "
                f"{header.track_repetitions}"
            )
        if header.time_format is not None and header.time_format_offset is not None:
            details += (
                f", time format {header.time_format}"
                f" offset {header.time_format_offset}"
            )
        if (
            header.new_track_offset_track is not None
            and header.new_track_offset is not None
        ):
            details += (
                f", track {header.new_track_offset_track + 1} "
                f"new offset {header.new_track_offset}"
            )
        if header.track_chunk_number is not None:
            details += f", track {header.track_chunk_number + 1}"
            if header.track_chunk_name:
                details += f" '{header.track_chunk_name}'"
            if header.track_chunk_channel is not None:
                details += f" channel {header.track_chunk_channel + 1}"
            if header.track_chunk_patch is not None:
                details += f" patch {header.track_chunk_patch}"
        if header.marker_count is not None:
            details += f", markers {header.marker_count}"
            if header.first_marker_time is not None:
                details += f" first at {header.first_marker_time}"
            if header.first_marker_smpte is not None:
                details += f" smpte {header.first_marker_smpte}"
            if header.first_marker_name:
                details += f" '{header.first_marker_name}'"
        raise MidiFileError(
            f"Cakewalk WRK files are not supported yet ({details})"
        )
    if data.startswith(b"RIFF"):
        data = _unwrap_rmid_data(data)
    reader = _Reader(data)
    if reader.read(4) != b"MThd":
        raise MidiFileError("Not a Standard MIDI File")
    header_size = reader.read_u32()
    if header_size < 6:
        raise MidiFileError("Invalid MIDI header")
    midi_format = reader.read_u16()
    track_count = reader.read_u16()
    division = reader.read_u16()
    if header_size > 6:
        reader.read(header_size - 6)

    tracks: list[MidiTrack] = []
    for _ in range(track_count):
        if reader.read(4) != b"MTrk":
            raise MidiFileError("Missing MIDI track chunk")
        track_size = reader.read_u32()
        tracks.append(_read_track(reader.read(track_size)))
    return MidiFile(path=path, format=midi_format, division=division, tracks=tracks)


def _unwrap_rmid_data(data: bytes) -> bytes:
    reader = _Reader(data)
    if reader.read(4) != b"RIFF":
        raise MidiFileError("Not a Standard MIDI File")
    riff_size = reader.read_u32_le()
    if reader.remaining < 4:
        raise MidiFileError("Unexpected end of file")
    form_type = reader.read(4)
    if form_type != b"RMID":
        raise MidiFileError("Unsupported RIFF MIDI form")

    container_limit = min(len(data), riff_size + 8)
    while reader._pos + 8 <= container_limit:
        chunk_id = reader.read(4)
        chunk_size = reader.read_u32_le()
        if reader._pos + chunk_size > container_limit:
            raise MidiFileError("Unexpected end of file")
        chunk_data = reader.read(chunk_size)
        if chunk_size % 2 and reader._pos < container_limit:
            reader.read(1)
        if chunk_id == b"data":
            return chunk_data
    raise MidiFileError("RIFF MIDI data chunk not found")


def _looks_like_wrk(data: bytes, path: Path) -> bool:
    return data.startswith(WRK_HEADER) or path.suffix.casefold() == ".wrk"


def _read_wrk_header(data: bytes, path: Path) -> _WrkHeader:
    if not data.startswith(WRK_HEADER):
        raise MidiFileError("Invalid Cakewalk WRK file format")
    if len(data) < len(WRK_HEADER) + 3:
        raise MidiFileError("Unexpected end of file")
    reader = _Reader(data)
    reader.read(len(WRK_HEADER))
    reader.read(1)  # reserved gap byte
    minor_version = reader.read(1)[0]
    major_version = reader.read(1)[0]
    if reader.remaining <= 0:
        return _WrkHeader(major_version=major_version, minor_version=minor_version)
    first_chunk_id = reader.read(1)[0]
    if first_chunk_id == 0xFF:
        return _WrkHeader(
            major_version=major_version,
            minor_version=minor_version,
            first_chunk_id=first_chunk_id,
            first_chunk_length=0,
        )
    if reader.remaining < 4:
        raise MidiFileError("Corrupted Cakewalk WRK file")
    first_chunk_length = reader.read_u32_le()
    if reader.remaining < first_chunk_length:
        raise MidiFileError("Corrupted Cakewalk WRK file")
    timebase: int | None = None
    software_version: str | None = None
    track_number: int | None = None
    track_name: str | None = None
    comments: str | None = None
    track_volume_track: int | None = None
    track_volume: int | None = None
    track_bank_track: int | None = None
    track_bank: int | None = None
    track_patch_track: int | None = None
    track_patch: int | None = None
    track_offset_track: int | None = None
    track_offset: int | None = None
    track_repetitions_track: int | None = None
    track_repetitions: int | None = None
    time_format: int | None = None
    time_format_offset: int | None = None
    new_track_offset_track: int | None = None
    new_track_offset: int | None = None
    track_chunk_number: int | None = None
    track_chunk_name: str | None = None
    track_chunk_channel: int | None = None
    track_chunk_patch: int | None = None
    marker_count: int | None = None
    first_marker_time: int | None = None
    first_marker_smpte: int | None = None
    first_marker_name: str | None = None
    if first_chunk_id == 10:
        if first_chunk_length < 2:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        timebase = reader.read_u16_le()
    elif first_chunk_id == 74:
        if first_chunk_length < 1:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        text_length = reader.read(1)[0]
        if first_chunk_length - 1 < text_length:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        software_version = reader.read(text_length).decode("latin-1", errors="replace")
    elif first_chunk_id == 24:
        if first_chunk_length < 3:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_number = reader.read_u16_le()
        text_length = reader.read(1)[0]
        if first_chunk_length - 3 < text_length:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_name = reader.read(text_length).decode("latin-1", errors="replace")
    elif first_chunk_id == 8:
        if first_chunk_length < 2:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        text_length = reader.read_u16_le()
        if first_chunk_length - 2 < text_length:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        comments = reader.read(text_length).decode("latin-1", errors="replace")
    elif first_chunk_id == 19:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_volume_track = reader.read_u16_le()
        track_volume = reader.read_u16_le()
    elif first_chunk_id == 30:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_bank_track = reader.read_u16_le()
        track_bank = reader.read_u16_le()
    elif first_chunk_id == 14:
        if first_chunk_length < 3:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_patch_track = reader.read_u16_le()
        track_patch = reader.read(1)[0]
    elif first_chunk_id == 9:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_offset_track = reader.read_u16_le()
        track_offset = struct.unpack("<h", reader.read(2))[0]
    elif first_chunk_id == 12:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_repetitions_track = reader.read_u16_le()
        track_repetitions = reader.read_u16_le()
    elif first_chunk_id == 11:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        time_format = reader.read_u16_le()
        time_format_offset = reader.read_u16_le()
    elif first_chunk_id == 27:
        if first_chunk_length < 6:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        new_track_offset_track = reader.read_u16_le()
        new_track_offset = reader.read_u32_le()
    elif first_chunk_id == 36:
        if first_chunk_length < 9:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        track_chunk_number = reader.read_u16_le()
        name_length = reader.read(1)[0]
        if reader.remaining < name_length + 1:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        primary_name = reader.read(name_length).decode("latin-1", errors="replace")
        alt_name_length = reader.read(1)[0]
        if reader.remaining < alt_name_length + 5:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        alternate_name = reader.read(alt_name_length).decode("latin-1", errors="replace")
        track_chunk_channel = reader.read(1)[0] & 0x0F
        track_chunk_patch = reader.read(1)[0]
        reader.read(3)  # velocity, port, flags
        track_chunk_name = primary_name or alternate_name or None
    elif first_chunk_id == 21:
        if first_chunk_length < 4:
            raise MidiFileError("Corrupted Cakewalk WRK file")
        marker_count = reader.read_u32_le()
        if marker_count > 0:
            if reader.remaining < 11:
                raise MidiFileError("Corrupted Cakewalk WRK file")
            first_marker_smpte = reader.read(1)[0]
            reader.read(1)
            first_marker_time = int.from_bytes(reader.read(3), "little")
            reader.read(5)
            name_length = reader.read(1)[0]
            if reader.remaining < name_length:
                raise MidiFileError("Corrupted Cakewalk WRK file")
            first_marker_name = reader.read(name_length).decode(
                "latin-1", errors="replace"
            )
    return _WrkHeader(
        major_version=major_version,
        minor_version=minor_version,
        first_chunk_id=first_chunk_id,
        first_chunk_length=first_chunk_length,
        timebase=timebase,
        software_version=software_version,
        track_number=track_number,
        track_name=track_name,
        comments=comments,
        track_volume_track=track_volume_track,
        track_volume=track_volume,
        track_bank_track=track_bank_track,
        track_bank=track_bank,
        track_patch_track=track_patch_track,
        track_patch=track_patch,
        track_offset_track=track_offset_track,
        track_offset=track_offset,
        track_repetitions_track=track_repetitions_track,
        track_repetitions=track_repetitions,
        time_format=time_format,
        time_format_offset=time_format_offset,
        new_track_offset_track=new_track_offset_track,
        new_track_offset=new_track_offset,
        track_chunk_number=track_chunk_number,
        track_chunk_name=track_chunk_name,
        track_chunk_channel=track_chunk_channel,
        track_chunk_patch=track_chunk_patch,
        marker_count=marker_count,
        first_marker_time=first_marker_time,
        first_marker_smpte=first_marker_smpte,
        first_marker_name=first_marker_name,
    )


def _read_track(data: bytes) -> MidiTrack:
    reader = _Reader(data)
    tick = 0
    running_status: int | None = None
    events: list[MidiEvent] = []
    track_name = ""
    instrument_name = ""

    while reader.remaining:
        tick += reader.read_varlen()
        status = reader.read(1)[0]
        if status < 0x80:
            if running_status is None:
                raise MidiFileError("Running status used before status byte")
            reader._pos -= 1
            status = running_status
        elif status < 0xF0:
            running_status = status

        if status == 0xFF:
            meta_type = reader.read(1)[0]
            payload = reader.read(reader.read_varlen())
            events.append(MidiEvent(tick=tick, kind="meta", data=payload, meta_type=meta_type))
            text = decode_midi_text(payload).strip()
            if meta_type == 0x03 and text and not track_name:
                track_name = text
            elif meta_type == 0x04 and text and not instrument_name:
                instrument_name = text
            if meta_type == 0x2F:
                break
            continue

        if status in (0xF0, 0xF7):
            events.append(MidiEvent(tick=tick, kind="sysex", data=reader.read(reader.read_varlen())))
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        size = 1 if event_type in (0xC0, 0xD0) else 2
        payload = reader.read(size)
        events.append(MidiEvent(tick=tick, kind=_channel_kind(event_type), channel=channel, data=payload))

    return MidiTrack(events=events, name=track_name, instrument_name=instrument_name)


def _channel_kind(event_type: int) -> str:
    return {
        0x80: "note_off",
        0x90: "note_on",
        0xA0: "key_pressure",
        0xB0: "control_change",
        0xC0: "program_change",
        0xD0: "channel_pressure",
        0xE0: "pitch_bend",
    }.get(event_type, "channel")


def _dedupe_tempo_changes(changes: list[TempoChange]) -> list[TempoChange]:
    ordered = sorted(changes, key=lambda change: change.tick)
    result: list[TempoChange] = []
    for change in ordered:
        if result and result[-1].tick == change.tick:
            result[-1] = change
        else:
            result.append(change)
    return result


def _default_time_signature() -> TimeSignature:
    return TimeSignature(0, 4, 4, 24, 8)


def _divide_ticks_by_bar(ticks: int, ticks_per_bar: int, round_up: bool) -> int:
    if ticks <= 0:
        return 0
    if round_up:
        return (ticks + ticks_per_bar - 1) // ticks_per_bar
    return ticks // ticks_per_bar


def _smpte_tick_to_microseconds(division: int, tick: int) -> int:
    fps_byte = (division >> 8) & 0xFF
    ticks_per_frame = division & 0xFF
    if fps_byte >= 0x80:
        fps_byte -= 0x100
    frames_per_second = -fps_byte
    if frames_per_second == 29:
        frames_per_second = 29.97
    if frames_per_second <= 0 or ticks_per_frame <= 0:
        raise MidiFileError("Invalid SMPTE MIDI division")
    return int((tick * 1_000_000) / (frames_per_second * ticks_per_frame))


def _smpte_microseconds_to_tick(division: int, microseconds: int) -> int:
    fps_byte = (division >> 8) & 0xFF
    ticks_per_frame = division & 0xFF
    if fps_byte >= 0x80:
        fps_byte -= 0x100
    frames_per_second = -fps_byte
    if frames_per_second == 29:
        frames_per_second = 29.97
    if frames_per_second <= 0 or ticks_per_frame <= 0:
        raise MidiFileError("Invalid SMPTE MIDI division")
    return int((microseconds * frames_per_second * ticks_per_frame) / 1_000_000)

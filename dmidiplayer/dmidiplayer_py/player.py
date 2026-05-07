"""Realtime sequence player for the first Python port."""

from __future__ import annotations

from bisect import bisect_left

from PyQt6.QtCore import QElapsedTimer, QObject, Qt, QTimer, pyqtSignal

from drumstick_py import MidiEvent, MidiOutputError
from .sequence import Sequence


class SequencePlayer(QObject):
    started = pyqtSignal()
    stopped = pyqtSignal()
    finished = pyqtSignal()
    positionChanged = pyqtSignal(int, int)
    eventPlayed = pyqtSignal(object)
    outputError = pyqtSignal(str)

    def __init__(self, output: object, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sequence = Sequence(self)
        self.output = output
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._events: list[MidiEvent] = []
        self._event_times_us: list[int] = []
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._playing = False
        self._tempo_percent = 100
        self._pitch_shift = 0
        self._volume_percent = 100
        self._percussion_channel = 9
        self._send_reset_before_playback = False
        self._muted_channels: set[int] = set()
        self._solo_channels: set[int] = set()
        self._solo_volume_reduction = 50
        self._loop_enabled = False
        self._loop_start_tick = 0
        self._loop_end_tick = 0
        self._clock = QElapsedTimer()

    def load_file(self, file_name: str) -> None:
        self.stop()
        self.sequence.load_file(file_name)
        self._events = self.sequence.events
        midi = self.sequence.midi
        self._event_times_us = [] if midi is None else [midi.event_microseconds(event) for event in self._events]
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._loop_start_tick = 0
        self._loop_end_tick = self.sequence.length_ticks
        self.positionChanged.emit(self._position, self.sequence.length_ticks)

    def clear(self) -> None:
        self.stop()
        self.sequence.clear()
        self._events = []
        self._event_times_us = []
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._loop_start_tick = 0
        self._loop_end_tick = 0
        self.positionChanged.emit(0, 0)

    def play(self) -> None:
        if not self._events:
            return
        if self._index >= len(self._events):
            self._index = 0
            self._position = 0
            self._position_us = 0
        if self._send_reset_before_playback:
            try:
                self.output.send_event(MidiEvent(tick=0, kind="sysex", data=bytes.fromhex("7e 7f 09 01 f7")))
            except MidiOutputError as exc:
                self.outputError.emit(str(exc))
                return
        self._base_position_us = self._position_us
        self._clock.start()
        self._timer.start(2)
        self._playing = True
        self.started.emit()
        self._tick()

    def pause(self) -> None:
        self._position_us = self._elapsed_microseconds()
        self._timer.stop()
        self.output.all_notes_off()
        self._playing = False
        self.stopped.emit()

    def stop(self) -> None:
        self._timer.stop()
        self.output.all_notes_off()
        self._playing = False
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self.positionChanged.emit(self._position, self.sequence.length_ticks)
        self.stopped.emit()

    def seek(self, tick: int) -> None:
        if not self._events:
            return
        was_playing = self._playing
        self._timer.stop()
        self.output.all_notes_off()

        self._position = max(0, min(tick, self.sequence.length_ticks))
        self._position_us = self.sequence.tick_to_microseconds(self._position)
        self._base_position_us = self._position_us
        self._index = bisect_left(self._event_times_us, self._position_us)
        self.positionChanged.emit(self._position, self.sequence.length_ticks)

        if was_playing and self._index < len(self._events):
            self._clock.start()
            self._timer.start(2)
            self._playing = True
        else:
            self._playing = False

    @property
    def tempo_percent(self) -> int:
        return self._tempo_percent

    def set_tempo_percent(self, value: int) -> None:
        value = max(50, min(200, value))
        if value == self._tempo_percent:
            return
        if self._playing:
            self._position_us = self._elapsed_microseconds()
            self._base_position_us = self._position_us
            self._clock.start()
        self._tempo_percent = value

    @property
    def pitch_shift(self) -> int:
        return self._pitch_shift

    def set_pitch_shift(self, semitones: int) -> None:
        semitones = max(-12, min(12, semitones))
        if semitones == self._pitch_shift:
            return
        self.output.all_notes_off()
        self._pitch_shift = semitones

    @property
    def percussion_channel(self) -> int:
        return self._percussion_channel + 1

    def set_percussion_channel(self, channel: int) -> None:
        channel_index = max(1, min(16, channel)) - 1
        if channel_index == self._percussion_channel:
            return
        self.output.all_notes_off()
        self._percussion_channel = channel_index

    @property
    def volume_percent(self) -> int:
        return self._volume_percent

    def set_volume_percent(self, value: int) -> None:
        self._volume_percent = max(0, min(200, value))
        self._send_global_volume()

    @property
    def send_reset_before_playback(self) -> bool:
        return self._send_reset_before_playback

    def set_send_reset_before_playback(self, enabled: bool) -> None:
        self._send_reset_before_playback = bool(enabled)

    @property
    def solo_volume_reduction(self) -> int:
        return self._solo_volume_reduction

    def set_solo_volume_reduction(self, value: int) -> None:
        self._solo_volume_reduction = max(0, min(100, value))

    def muted_channels(self) -> set[int]:
        return set(self._muted_channels)

    def solo_channels(self) -> set[int]:
        return set(self._solo_channels)

    def set_channel_muted(self, channel: int, muted: bool) -> None:
        channel = max(0, min(15, channel))
        if muted:
            if channel in self._muted_channels:
                return
            self._muted_channels.add(channel)
        else:
            if channel not in self._muted_channels:
                return
            self._muted_channels.remove(channel)
        self.output.all_notes_off()

    def set_channel_solo(self, channel: int, solo: bool) -> None:
        channel = max(0, min(15, channel))
        if solo:
            if channel in self._solo_channels:
                return
            self._solo_channels.add(channel)
        else:
            if channel not in self._solo_channels:
                return
            self._solo_channels.remove(channel)
        self.output.all_notes_off()

    @property
    def loop_enabled(self) -> bool:
        return self._loop_enabled

    def set_loop_enabled(self, enabled: bool) -> None:
        self._loop_enabled = enabled and self._loop_end_tick > self._loop_start_tick

    def set_loop_range(self, start_tick: int, end_tick: int) -> None:
        length = self.sequence.length_ticks
        start = max(0, min(start_tick, length))
        end = max(0, min(end_tick, length))
        if end <= start:
            end = length
        self._loop_start_tick = start
        self._loop_end_tick = end
        self._loop_enabled = self._loop_enabled and self._loop_end_tick > self._loop_start_tick

    def _tick(self) -> None:
        self._position_us = self._elapsed_microseconds()
        limit_us = self._loop_end_microseconds() if self._loop_enabled else self._position_us
        play_until_us = min(self._position_us, limit_us)
        while self._index < len(self._events) and self._event_times_us[self._index] <= play_until_us:
            event = self._events[self._index]
            output_event = self._playable_event(event)
            try:
                if output_event is not None:
                    self.output.send_event(output_event)
            except MidiOutputError as exc:
                self._timer.stop()
                self.output.all_notes_off()
                self._playing = False
                self.outputError.emit(str(exc))
                self.stopped.emit()
                return
            self.eventPlayed.emit(output_event or event)
            self._position = event.tick
            self._index += 1
        if self._loop_enabled and self._position_us >= limit_us:
            self.seek(self._loop_start_tick)
            return
        self._position = min(
            self.sequence.microseconds_to_tick(self._position_us),
            self.sequence.length_ticks,
        )
        self.positionChanged.emit(self._position, self.sequence.length_ticks)
        if self._index >= len(self._events):
            self._timer.stop()
            self._playing = False
            self._position = self.sequence.length_ticks
            self._position_us = self.sequence.length_microseconds
            self._base_position_us = self._position_us
            self.positionChanged.emit(self._position, self.sequence.length_ticks)
            self.finished.emit()

    def _elapsed_microseconds(self) -> int:
        if not self._clock.isValid():
            return self._position_us
        elapsed = (self._clock.nsecsElapsed() // 1000) * self._tempo_percent // 100
        return self._base_position_us + elapsed

    def _playable_event(self, event: MidiEvent) -> MidiEvent | None:
        event = self._volume_event(event)
        event = self._channel_mix_event(event)
        if event is None:
            return None
        if self._pitch_shift == 0:
            return event
        if event.channel is None or event.channel == self._percussion_channel:
            return event
        if event.kind not in ("note_on", "note_off", "key_pressure") or not event.data:
            return event
        note = event.data[0] + self._pitch_shift
        if note < 0 or note > 127:
            return None
        return MidiEvent(
            tick=event.tick,
            kind=event.kind,
            channel=event.channel,
            data=bytes([note]) + event.data[1:],
            meta_type=event.meta_type,
        )

    def _volume_event(self, event: MidiEvent) -> MidiEvent:
        if self._volume_percent == 100:
            return event
        if event.kind != "control_change" or len(event.data) < 2 or event.data[0] != 7:
            return event
        value = min(127, max(0, event.data[1] * self._volume_percent // 100))
        return MidiEvent(
            tick=event.tick,
            kind=event.kind,
            channel=event.channel,
            data=bytes([event.data[0], value]) + event.data[2:],
            meta_type=event.meta_type,
        )

    def _channel_mix_event(self, event: MidiEvent) -> MidiEvent | None:
        if event.channel is None:
            return event
        if event.channel in self._muted_channels:
            if event.kind in ("note_off", "note_on") and event.data:
                return MidiEvent(
                    tick=event.tick,
                    kind=event.kind,
                    channel=event.channel,
                    data=bytes([event.data[0], 0]) + event.data[2:],
                    meta_type=event.meta_type,
                )
            return None
        if not self._solo_channels or event.channel in self._solo_channels:
            return event
        if self._solo_volume_reduction <= 0:
            if event.kind in ("note_off", "note_on") and event.data:
                return MidiEvent(
                    tick=event.tick,
                    kind=event.kind,
                    channel=event.channel,
                    data=bytes([event.data[0], 0]) + event.data[2:],
                    meta_type=event.meta_type,
                )
            return None
        if event.kind == "note_on" and len(event.data) >= 2 and event.data[1] > 0:
            value = min(127, max(0, event.data[1] * self._solo_volume_reduction // 100))
            return MidiEvent(
                tick=event.tick,
                kind=event.kind,
                channel=event.channel,
                data=bytes([event.data[0], value]) + event.data[2:],
                meta_type=event.meta_type,
            )
        if event.kind == "control_change" and len(event.data) >= 2 and event.data[0] == 7:
            value = min(127, max(0, event.data[1] * self._solo_volume_reduction // 100))
            return MidiEvent(
                tick=event.tick,
                kind=event.kind,
                channel=event.channel,
                data=bytes([event.data[0], value]) + event.data[2:],
                meta_type=event.meta_type,
            )
        return event

    def _send_global_volume(self) -> None:
        value = min(127, 100 * self._volume_percent // 100)
        for channel in range(16):
            try:
                self.output.send_event(
                    MidiEvent(tick=self._position, kind="control_change", channel=channel, data=bytes([7, value]))
                )
            except MidiOutputError as exc:
                self.outputError.emit(str(exc))
                return

    def _loop_end_microseconds(self) -> int:
        return self.sequence.tick_to_microseconds(self._loop_end_tick)

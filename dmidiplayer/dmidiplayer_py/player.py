"""Realtime sequence player for the PyQt6 port.

The scheduler uses a single monotonic clock (:class:`QElapsedTimer`) for both
MIDI event dispatch and the position reported to the user interface.  The
position is never advanced by an independent timer, so the slider, the
keyboards and the outgoing MIDI stream share the same time reference.

The C++ implementation (``dmidiplayer/seqplayer.cpp``) is the behavioural
reference for channel state: at the beginning of a song it resets
controllers, programs and volumes, tracks the last program sent per channel,
and only suppresses score program changes when the channel is locked.
"""

from __future__ import annotations

from bisect import bisect_left
import time

from PyQt6.QtCore import QElapsedTimer, QObject, Qt, QTimer, pyqtSignal

from drumstick_py import MidiEvent, MidiOutputError
from .sequence import Sequence


class SequencePlayer(QObject):
    started = pyqtSignal()
    stopped = pyqtSignal()
    finished = pyqtSignal()
    positionChanged = pyqtSignal(int, int)
    eventPlayed = pyqtSignal(object)
    channelProgramChanged = pyqtSignal(int, int)
    outputError = pyqtSignal(str)

    # Position updates are throttled to about 30 Hz.  Sending a signal for
    # every 2 ms scheduler tick made the GUI do hundreds of relayouts per
    # second and stole time from MIDI dispatch.
    POSITION_UPDATE_INTERVAL_NS = 33_000_000
    TIMER_INTERVAL_MS = 2

    # Controllers restored after a seek.  Bank select is handled separately
    # because it must precede the program change.
    RESTORED_CONTROLLERS = (10, 11, 64, 65, 66, 67, 71, 72, 73, 74, 91, 93)

    def __init__(self, output: object, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.sequence = Sequence(self)
        self.output = output
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(self.TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._events: list[MidiEvent] = []
        self._event_times_us: list[int] = []
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._playing = False
        self._paused = False
        self._tempo_percent = 100
        self._pitch_shift = 0
        self._volume_percent = 100
        self._percussion_channel = 9
        self._send_reset_before_playback = False
        self._muted_channels: set[int] = set()
        self._solo_channels: set[int] = set()
        self._solo_volume_reduction = 50
        self._channel_volume_percents: dict[int, int] = {}
        self._channel_program_overrides: dict[int, int] = {}
        self._locked_channels: set[int] = set()
        # Authoritative state sent to (or read from) the synthesizer.
        self._active_notes: dict[int, set[int]] = {}
        self._active_note_counts: dict[int, dict[int, int]] = {}
        self._active_note_velocities: dict[tuple[int, int], int] = {}
        self._last_programs: dict[int, int] = {}
        self._locked_programs: dict[int, int] = {}
        self._source_programs: dict[int, int] = {}
        self._source_bank_msb: dict[int, int] = {}
        self._source_bank_lsb: dict[int, int] = {}
        self._channel_base_volumes: dict[int, int] = {}
        self._source_controllers: dict[int, dict[int, int]] = {}
        self._source_pitch_bends: dict[int, int] = {}
        self._source_channel_pressures: dict[int, int] = {}
        self._loop_enabled = False
        self._loop_start_tick = 0
        self._loop_end_tick = 0
        self._late_event_count = 0
        self._max_late_event_us = 0
        self._total_late_event_us = 0
        self._finished_emitted = False
        self._last_position_emit_ns = 0
        self._strict_setup = False
        self._clock = QElapsedTimer()

    # ------------------------------------------------------------------
    # Loading and state reset
    # ------------------------------------------------------------------
    def load_file(self, file_name: str) -> None:
        self.stop()
        try:
            self.sequence.load_file(file_name)
        except Exception:
            # Never keep scheduling the previous song after a failed load.
            self.sequence.clear()
            self._events = []
            self._event_times_us = []
            raise
        self._events = self.sequence.events
        midi = self.sequence.midi
        self._event_times_us = [] if midi is None else [midi.event_microseconds(event) for event in self._events]
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._loop_start_tick = 0
        self._loop_end_tick = self.sequence.length_ticks
        self._muted_channels.clear()
        self._solo_channels.clear()
        self._channel_volume_percents.clear()
        self._channel_program_overrides.clear()
        self._locked_channels.clear()
        self._active_notes.clear()
        self._active_note_counts.clear()
        self._active_note_velocities.clear()
        self._finished_emitted = False
        self._reset_channel_state()
        self._reset_scheduler_diagnostics()
        self._emit_position(force=True)

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
        self._muted_channels.clear()
        self._solo_channels.clear()
        self._channel_volume_percents.clear()
        self._channel_program_overrides.clear()
        self._locked_channels.clear()
        self._active_notes.clear()
        self._active_note_counts.clear()
        self._active_note_velocities.clear()
        self._reset_channel_state()
        self._finished_emitted = False
        self._reset_scheduler_diagnostics()
        self._emit_position(force=True)

    def _reset_channel_state(self) -> None:
        self._last_programs = {}
        self._locked_programs = {}
        self._source_programs = dict(self.sequence.initial_programs())
        self._source_bank_msb = {}
        self._source_bank_lsb = {}
        self._channel_base_volumes = {}
        self._source_controllers = {}
        self._source_pitch_bends = {}
        self._source_channel_pressures = {}

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def play(self) -> None:
        if not self._events:
            return
        length_us = self.sequence.length_microseconds
        if self._position_us >= length_us or self._index >= len(self._events):
            self._index = 0
            self._position = 0
            self._position_us = 0
        self._finished_emitted = False
        if self._position_us == 0:
            try:
                self._prepare_playback()
            except MidiOutputError as exc:
                self._abort_playback(str(exc))
                return
        self._base_position_us = self._position_us
        self._clock.start()
        self._playing = True
        self._paused = False
        self._last_position_emit_ns = time.monotonic_ns()
        self._timer.start(self.TIMER_INTERVAL_MS)
        self.started.emit()
        # The first events (tick 0) are dispatched synchronously so that the
        # MIDI stream and the reported position start from the same instant.
        self._tick()

    def pause(self) -> None:
        if not self._playing:
            return
        self._position_us = min(self._elapsed_microseconds(), self.sequence.length_microseconds)
        self._position = self.sequence.microseconds_to_tick(self._position_us)
        self._timer.stop()
        self._playing = False
        self._paused = True
        self._silence_active_notes()
        self._emit_position(force=True)
        self.stopped.emit()

    def stop(self) -> None:
        self._timer.stop()
        self._silence_active_notes()
        self._playing = False
        self._paused = False
        self._index = 0
        self._position = 0
        self._position_us = 0
        self._base_position_us = 0
        self._finished_emitted = False
        self._emit_position(force=True)
        self.stopped.emit()

    def seek(self, tick: int, _from_loop: bool = False) -> None:
        if not self._events:
            return
        was_playing = self._playing
        self._timer.stop()
        self._silence_active_notes()
        self._finished_emitted = False

        self._position = max(0, min(tick, self.sequence.length_ticks))
        self._position_us = self.sequence.tick_to_microseconds(self._position)
        self._base_position_us = self._position_us
        self._index = bisect_left(self._event_times_us, self._position_us)
        # Restore the score's channel state at the new position so that the
        # synthesizer does not keep a program, bank or volume from the old
        # location.  The C++ player only replays the previous event; restoring
        # the tracked state is more reliable and does not send any notes.
        self._restore_channel_state(self._position)
        self._emit_position(force=True)

        if was_playing:
            if self._position_us >= self.sequence.length_microseconds and self._index >= len(self._events):
                self._finish_playback()
                return
            self._clock.start()
            self._playing = True
            self._paused = False
            self._last_position_emit_ns = time.monotonic_ns()
            if not _from_loop:
                # Dispatch events exactly at the seek position immediately for
                # responsive interactive seeking.  A loop restart keeps the
                # index at the loop start and lets the timer do the work.
                self._tick()
            if self._playing:
                self._timer.start(self.TIMER_INTERVAL_MS)
        else:
            self._playing = False

    # ------------------------------------------------------------------
    # Musical and mixer settings
    # ------------------------------------------------------------------
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
        self._silence_active_notes()
        self._pitch_shift = semitones

    @property
    def percussion_channel(self) -> int:
        return self._percussion_channel + 1

    def set_percussion_channel(self, channel: int) -> None:
        channel_index = max(1, min(16, channel)) - 1
        if channel_index != self._percussion_channel:
            self._silence_active_notes()
            self._percussion_channel = channel_index
        # Always inform outputs that can distinguish drum/melodic channels;
        # this also configures a newly selected output.
        setter = getattr(self.output, "set_percussion_channel", None)
        if callable(setter):
            setter(channel_index)

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

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_paused(self) -> bool:
        return self._paused

    def active_notes(self) -> dict[int, set[int]]:
        """Return a copy of the notes currently sounding per channel."""
        return {channel: set(notes) for channel, notes in self._active_notes.items()}

    def active_note_velocity(self, channel: int, note: int) -> int:
        return self._active_note_velocities.get((channel, note), 100)

    def active_note_counts(self) -> dict[int, dict[int, int]]:
        """Return the number of active note-ons per channel and pitch."""
        return {
            channel: dict(counts)
            for channel, counts in self._active_note_counts.items()
        }

    def active_note_count(self, channel: int, note: int) -> int:
        return self._active_note_counts.get(channel, {}).get(note, 0)

    # ------------------------------------------------------------------
    # Per-channel mixer state
    # ------------------------------------------------------------------
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
            self._resync_channel(channel)
        self._silence_active_notes()

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
        self._silence_active_notes()
        for solo_channel in range(16):
            self._send_channel_volume(solo_channel)

    def channel_volume_percent(self, channel: int) -> int:
        channel = max(0, min(15, channel))
        return self._channel_volume_percents.get(channel, 100)

    def set_channel_volume_percent(self, channel: int, value: int) -> None:
        channel = max(0, min(15, channel))
        value = max(0, min(200, value))
        if value == 100:
            if channel not in self._channel_volume_percents:
                return
            del self._channel_volume_percents[channel]
        else:
            if self._channel_volume_percents.get(channel, 100) == value:
                return
            self._channel_volume_percents[channel] = value
        self._send_channel_volume(channel)

    def channel_program(self, channel: int) -> int | None:
        """Manual program requested from the channel view.

        This is *not* a permanent override of score program changes.  The
        score keeps controlling its own program changes unless the channel is
        explicitly locked, matching the C++ ``SequencePlayer`` behaviour.
        """
        channel = max(0, min(15, channel))
        return self._channel_program_overrides.get(channel)

    def last_program(self, channel: int) -> int:
        """The last program actually sent to the synthesizer."""
        channel = max(0, min(15, channel))
        return self._last_programs.get(channel, self._source_programs.get(channel, 0))

    def set_channel_program(self, channel: int, program: int) -> None:
        channel = max(0, min(15, channel))
        program = max(0, min(127, program))
        if self._channel_program_overrides.get(channel) == program:
            return
        self._channel_program_overrides[channel] = program
        if channel in self._locked_channels:
            self._locked_programs[channel] = program
        self._send_program(channel, program)

    def locked_channels(self) -> set[int]:
        return set(self._locked_channels)

    def set_channel_locked(self, channel: int, locked: bool) -> None:
        channel = max(0, min(15, channel))
        if locked:
            if channel in self._locked_channels:
                return
            self._locked_channels.add(channel)
            # Lock the program that is currently in effect (the last one sent,
            # or the score's program if playback has not reached one yet).
            self._locked_programs[channel] = self._channel_program_overrides.get(
                channel,
                self._last_programs.get(channel, self._source_programs.get(channel, 0)),
            )
        else:
            if channel not in self._locked_channels:
                return
            self._locked_channels.remove(channel)
            self._locked_programs.pop(channel, None)

    @property
    def loop_enabled(self) -> bool:
        return self._loop_enabled

    def set_loop_enabled(self, enabled: bool) -> None:
        self._loop_enabled = bool(enabled) and self._loop_end_tick > self._loop_start_tick

    def set_loop_range(self, start_tick: int, end_tick: int) -> None:
        length = self.sequence.length_ticks
        start = max(0, min(start_tick, length))
        end = max(0, min(end_tick, length))
        if end <= start:
            end = length
        self._loop_start_tick = start
        self._loop_end_tick = end
        self._loop_enabled = self._loop_enabled and self._loop_end_tick > self._loop_start_tick

    def scheduler_diagnostics(self) -> dict[str, int]:
        return {
            "late_event_count": self._late_event_count,
            "max_late_event_us": self._max_late_event_us,
            "total_late_event_us": self._total_late_event_us,
        }

    def _reset_scheduler_diagnostics(self) -> None:
        self._late_event_count = 0
        self._max_late_event_us = 0
        self._total_late_event_us = 0

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def _emit_position(self, force: bool = False) -> None:
        now = time.monotonic_ns()
        if not force and now - self._last_position_emit_ns < self.POSITION_UPDATE_INTERVAL_NS:
            return
        self._last_position_emit_ns = now
        self.positionChanged.emit(self._position, self.sequence.length_ticks)

    def _tick(self) -> None:
        if not self._events:
            return
        self._position_us = max(0, self._elapsed_microseconds())
        if self.sequence.midi is not None:
            length_us = self.sequence.length_microseconds
            length_ticks = self.sequence.length_ticks
        else:
            # Support scheduler-only test harnesses that install ``_events``
            # directly without loading a file.
            length_us = self._event_times_us[-1] if self._event_times_us else 0
            length_ticks = self._events[-1].tick if self._events else 0

        if self._loop_enabled:
            limit_us = self._loop_end_microseconds()
        else:
            limit_us = length_us
        play_until_us = min(self._position_us, limit_us)

        while self._index < len(self._events) and self._event_times_us[self._index] <= play_until_us:
            event = self._events[self._index]
            lateness_us = max(0, self._position_us - self._event_times_us[self._index])
            if lateness_us > 0:
                self._late_event_count += 1
                self._max_late_event_us = max(self._max_late_event_us, lateness_us)
                self._total_late_event_us += lateness_us
            self._track_source_event(event)
            output_event = self._playable_event(event)
            if output_event is not None:
                try:
                    self.output.send_event(output_event)
                except MidiOutputError as exc:
                    self._abort_playback(str(exc))
                    return
                self._track_active_note_event(output_event)
                if output_event.kind == "program_change" and output_event.channel is not None and output_event.data:
                    self._last_programs[output_event.channel] = output_event.data[0]
                    self.channelProgramChanged.emit(output_event.channel, output_event.data[0])
                self.eventPlayed.emit(output_event)
            self._position = event.tick
            self._index += 1

        if self._loop_enabled and self._position_us >= limit_us:
            self.seek(self._loop_start_tick, _from_loop=True)
            return

        if self.sequence.midi is not None:
            self._position = min(
                self.sequence.microseconds_to_tick(self._position_us),
                length_ticks,
            )
        self._emit_position()
        if self._position_us >= length_us:
            self._position = length_ticks
            self._position_us = length_us
            self._base_position_us = length_us
            self._emit_position(force=True)
            if self._playing:
                self._finish_playback()

    def _elapsed_microseconds(self) -> int:
        if not self._clock.isValid():
            return self._position_us
        elapsed = (self._clock.nsecsElapsed() // 1000) * self._tempo_percent // 100
        return self._base_position_us + elapsed

    def _finish_playback(self) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self._timer.stop()
        self._playing = False
        self._paused = False
        self._position = self.sequence.length_ticks
        self._position_us = self.sequence.length_microseconds
        self._base_position_us = self._position_us
        self._index = len(self._events)
        self._silence_active_notes()
        self._emit_position(force=True)
        self.finished.emit()

    def _abort_playback(self, message: str) -> None:
        self._timer.stop()
        self._playing = False
        self._paused = False
        self._silence_active_notes()
        self.outputError.emit(message)
        self.stopped.emit()

    # ------------------------------------------------------------------
    # Note state
    # ------------------------------------------------------------------
    def _track_active_note_event(self, event: MidiEvent) -> None:
        if event.channel is None or not event.data:
            return
        note = event.data[0]
        if event.kind == "note_on" and len(event.data) >= 2 and event.data[1] > 0:
            channel_counts = self._active_note_counts.setdefault(event.channel, {})
            channel_counts[note] = channel_counts.get(note, 0) + 1
            self._active_notes.setdefault(event.channel, set()).add(note)
            self._active_note_velocities[(event.channel, note)] = event.data[1]
            return
        if event.kind not in ("note_off", "note_on"):
            return
        channel_counts = self._active_note_counts.get(event.channel)
        if channel_counts is None:
            # Compatibility with callers that populate ``_active_notes``
            # directly (the public tests do this).
            channel_notes = self._active_notes.get(event.channel)
            if channel_notes:
                channel_notes.discard(note)
                if not channel_notes:
                    del self._active_notes[event.channel]
            self._active_note_velocities.pop((event.channel, note), None)
            return
        count = channel_counts.get(note, 0)
        if count <= 1:
            channel_counts.pop(note, None)
            channel_notes = self._active_notes.get(event.channel)
            if channel_notes is not None:
                channel_notes.discard(note)
                if not channel_notes:
                    del self._active_notes[event.channel]
            self._active_note_velocities.pop((event.channel, note), None)
        else:
            channel_counts[note] = count - 1
        if not channel_counts:
            self._active_note_counts.pop(event.channel, None)

    def _silence_active_notes(self) -> None:
        channels = set(self._active_notes) | set(self._active_note_counts)
        for channel in sorted(channels):
            notes = set(self._active_notes.get(channel, set())) | set(
                self._active_note_counts.get(channel, {})
            )
            for note in sorted(notes):
                count = max(1, self._active_note_counts.get(channel, {}).get(note, 1))
                for _ in range(count):
                    try:
                        self.output.send_event(
                            MidiEvent(
                                tick=self._position,
                                kind="note_off",
                                channel=channel,
                                data=bytes([note, 0]),
                            )
                        )
                    except MidiOutputError as exc:
                        self.outputError.emit(str(exc))
                        break
        self._active_notes.clear()
        self._active_note_counts.clear()
        self._active_note_velocities.clear()
        try:
            self.output.all_notes_off()
        except MidiOutputError as exc:
            self.outputError.emit(str(exc))

    # ------------------------------------------------------------------
    # Channel state preparation and restoration
    # ------------------------------------------------------------------
    def _send_setup_event(self, event: MidiEvent, notify: bool = False) -> bool:
        """Send a state event without treating it as a score event."""
        try:
            self.output.send_event(event)
        except MidiOutputError as exc:
            if self._strict_setup:
                raise
            self.outputError.emit(str(exc))
            return False
        if event.kind == "program_change" and event.channel is not None and event.data:
            self._last_programs[event.channel] = event.data[0]
            if notify:
                self.channelProgramChanged.emit(event.channel, event.data[0])
        return True

    def _send_program(self, channel: int, program: int) -> None:
        self._send_setup_event(
            MidiEvent(tick=self._position, kind="program_change", channel=channel, data=bytes([program])),
            notify=True,
        )

    def _prepare_playback(self) -> None:
        """Match ``GUIPlayer::play()`` at position zero.

        A synthesizer may still hold programs, banks, controllers and volume
        from a previous song or another application.  Resetting them before
        the first score events prevents instruments from sounding with the
        wrong patch.  Only one reset SysEx message is sent: the previous port
        sent GM, GS and XG resets in sequence, which left GS/XG-capable synths
        in an inconsistent mode.
        """
        self._strict_setup = True
        try:
            self._prepare_playback_state()
        finally:
            self._strict_setup = False

    def _prepare_playback_state(self) -> None:
        if self._send_reset_before_playback:
            self._send_setup_event(
                MidiEvent(
                    tick=0,
                    kind="sysex",
                    data=bytes.fromhex("7e 7f 09 01 f7"),  # GM Reset
                )
            )
        for channel in range(16):
            self._send_setup_event(
                MidiEvent(tick=0, kind="control_change", channel=channel, data=bytes([123, 0]))
            )
            self._send_setup_event(
                MidiEvent(tick=0, kind="control_change", channel=channel, data=bytes([120, 0]))
            )
            # Reset all controllers (pan, expression, sustain, pitch bend...).
            self._send_setup_event(
                MidiEvent(tick=0, kind="control_change", channel=channel, data=bytes([121, 0]))
            )
        self._source_programs = dict(self.sequence.initial_programs())
        self._source_bank_msb = {}
        self._source_bank_lsb = {}
        self._source_controllers = {}
        self._source_pitch_bends = {}
        self._source_channel_pressures = {}
        self._channel_base_volumes = {}
        self._last_programs = {}
        for channel in range(16):
            program = self._locked_programs.get(channel, 0)
            # Deliberately do not reset Bank Select here.  C++
            # SequencePlayer::resetPrograms() sends only the program, leaving
            # the synth bank untouched.  Forcing bank 0/0 on channel 10 can
            # switch a drum channel to a melodic bank on XG/hardware synths,
            # making the drums sound like another instrument.
            self._send_setup_event(
                MidiEvent(tick=0, kind="program_change", channel=channel, data=bytes([program]))
            )
            self._send_setup_event(
                MidiEvent(
                    tick=0,
                    kind="control_change",
                    channel=channel,
                    data=bytes([7, self._effective_channel_volume(channel)]),
                )
            )
            self._send_setup_event(
                MidiEvent(tick=0, kind="control_change", channel=channel, data=bytes([10, 64]))
            )
            self._send_setup_event(
                MidiEvent(tick=0, kind="control_change", channel=channel, data=bytes([11, 127]))
            )
            self._send_setup_event(
                MidiEvent(tick=0, kind="pitch_bend", channel=channel, data=bytes([0, 64]))
            )

    def _track_source_event(self, event: MidiEvent) -> None:
        if event.channel is None or not event.data:
            return
        channel = event.channel
        if event.kind == "program_change":
            self._source_programs[channel] = event.data[0]
        elif event.kind == "control_change" and len(event.data) >= 2:
            controller = event.data[0]
            value = event.data[1]
            if controller == 0:
                self._source_bank_msb[channel] = value
            elif controller == 32:
                self._source_bank_lsb[channel] = value
            elif controller == 7:
                self._channel_base_volumes[channel] = value
            else:
                self._source_controllers.setdefault(channel, {})[controller] = value
        elif event.kind == "pitch_bend" and len(event.data) >= 2:
            self._source_pitch_bends[channel] = (event.data[1] << 7) | event.data[0]
        elif event.kind == "channel_pressure":
            self._source_channel_pressures[channel] = event.data[0]

    def _resync_channel(self, channel: int) -> None:
        """Restore the current score state after a channel is unmuted.

        Muted channels drop program and controller events.  Without this
        resynchronization the synthesizer would keep the patch that was
        active before the mute, which is a common cause of an instrument
        sounding like another part after mixing channels.
        """
        self._send_known_bank_select(channel, self._position)
        program = self._locked_programs.get(channel, self._last_programs.get(channel, self._source_programs.get(channel, 0)))
        self._send_setup_event(
            MidiEvent(tick=self._position, kind="program_change", channel=channel, data=bytes([program])),
            notify=True,
        )
        self._send_setup_event(
            MidiEvent(
                tick=self._position,
                kind="control_change",
                channel=channel,
                data=bytes([7, self._effective_channel_volume(channel)]),
            )
        )
        for controller in self.RESTORED_CONTROLLERS:
            value = self._source_controllers.get(channel, {}).get(controller)
            if value is None:
                value = 64 if controller == 10 else (127 if controller == 11 else 0)
            self._send_setup_event(
                MidiEvent(
                    tick=self._position,
                    kind="control_change",
                    channel=channel,
                    data=bytes([controller, max(0, min(127, value))]),
                )
            )
        bend = self._source_pitch_bends.get(channel, 8192)
        self._send_setup_event(
            MidiEvent(
                tick=self._position,
                kind="pitch_bend",
                channel=channel,
                data=bytes([bend & 0x7F, (bend >> 7) & 0x7F]),
            )
        )

    def _send_known_bank_select(self, channel: int, tick: int) -> None:
        """Send Bank Select only when the score explicitly selected a bank.

        Sending a default 0/0 bank would override the synthesizer's drum bank
        (GM channel 10) and can turn percussion into a melodic patch.
        """
        if channel not in self._source_bank_msb and channel not in self._source_bank_lsb:
            return
        bank_msb = self._source_bank_msb.get(channel, 0)
        bank_lsb = self._source_bank_lsb.get(channel, 0)
        self._send_setup_event(
            MidiEvent(tick=tick, kind="control_change", channel=channel, data=bytes([0, bank_msb]))
        )
        self._send_setup_event(
            MidiEvent(tick=tick, kind="control_change", channel=channel, data=bytes([32, bank_lsb]))
        )

    def _restore_channel_state(self, tick: int) -> None:
        if self.sequence.midi is None:
            return
        # Rebuild the state from the start of the score.  Do not keep
        # controllers observed after the target position from a previous
        # forward pass.
        self._source_programs = dict(self.sequence.initial_programs())
        self._source_bank_msb = {}
        self._source_bank_lsb = {}
        self._source_controllers = {}
        self._source_pitch_bends = {}
        self._source_channel_pressures = {}
        self._channel_base_volumes = {}
        for event in self._events:
            if event.tick > tick:
                break
            self._track_source_event(event)
        for channel in self.sequence.used_channels():
            self._send_known_bank_select(channel, tick)
            program = self._locked_programs.get(
                channel, self._source_programs.get(channel, 0)
            )
            self._send_setup_event(
                MidiEvent(tick=tick, kind="program_change", channel=channel, data=bytes([program])),
                notify=True,
            )
            self._send_setup_event(
                MidiEvent(
                    tick=tick,
                    kind="control_change",
                    channel=channel,
                    data=bytes([7, self._effective_channel_volume(channel)]),
                )
            )
            for controller in self.RESTORED_CONTROLLERS:
                value = self._source_controllers.get(channel, {}).get(controller)
                if value is None:
                    value = 64 if controller == 10 else (127 if controller == 11 else 0)
                self._send_setup_event(
                    MidiEvent(
                        tick=tick,
                        kind="control_change",
                        channel=channel,
                        data=bytes([controller, max(0, min(127, value))]),
                    )
                )
            bend = self._source_pitch_bends.get(channel, 8192)
            self._send_setup_event(
                MidiEvent(
                    tick=tick,
                    kind="pitch_bend",
                    channel=channel,
                    data=bytes([bend & 0x7F, (bend >> 7) & 0x7F]),
                )
            )
            pressure = self._source_channel_pressures.get(channel, 0)
            self._send_setup_event(
                MidiEvent(
                    tick=tick,
                    kind="channel_pressure",
                    channel=channel,
                    data=bytes([max(0, min(127, pressure))]),
                )
            )

    # ------------------------------------------------------------------
    # Event transformation
    # ------------------------------------------------------------------
    def _playable_event(self, event: MidiEvent) -> MidiEvent | None:
        event = self._channel_mix_event(event)
        if event is None:
            return None
        event = self._channel_program_event(event)
        if event is None:
            return None
        event = self._channel_volume_event(event)
        event = self._volume_event(event)
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

    def _channel_volume_event(self, event: MidiEvent) -> MidiEvent:
        if event.channel is None:
            return event
        channel_percent = self.channel_volume_percent(event.channel)
        if channel_percent == 100:
            return event
        if event.kind != "control_change" or len(event.data) < 2 or event.data[0] != 7:
            return event
        value = min(127, max(0, event.data[1] * channel_percent // 100))
        return MidiEvent(
            tick=event.tick,
            kind=event.kind,
            channel=event.channel,
            data=bytes([event.data[0], value]) + event.data[2:],
            meta_type=event.meta_type,
        )

    def _channel_program_event(self, event: MidiEvent) -> MidiEvent:
        if event.channel is None or event.kind != "program_change":
            return event
        if event.channel in self._locked_channels:
            program = self._locked_programs.get(
                event.channel, self._last_programs.get(event.channel, 0)
            )
            return MidiEvent(
                tick=event.tick,
                kind=event.kind,
                channel=event.channel,
                data=bytes([program]) + event.data[1:],
                meta_type=event.meta_type,
            )
        return event

    def _channel_mix_event(self, event: MidiEvent) -> MidiEvent | None:
        if event.channel is None:
            return event
        if event.channel in self._muted_channels:
            if event.kind in ("note_off", "note_on") and event.data:
                return MidiEvent(
                    tick=event.tick,
                    kind="note_on",
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
                    kind="note_on",
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

    # ------------------------------------------------------------------
    # Volume helpers
    # ------------------------------------------------------------------
    def _send_global_volume(self) -> None:
        for channel in range(16):
            value = self._effective_channel_volume(channel)
            self._send_setup_event(
                MidiEvent(tick=self._position, kind="control_change", channel=channel, data=bytes([7, value]))
            )

    def _send_channel_volume(self, channel: int) -> None:
        self._send_setup_event(
            MidiEvent(
                tick=self._position,
                kind="control_change",
                channel=channel,
                data=bytes([7, self._effective_channel_volume(channel)]),
            )
        )

    def _effective_channel_volume(self, channel: int) -> int:
        base = self._channel_base_volumes.get(channel, 100)
        return min(
            127,
            max(0, base * self.channel_volume_percent(channel) * self._volume_percent // 10_000),
        )

    def _loop_end_microseconds(self) -> int:
        return self.sequence.tick_to_microseconds(self._loop_end_tick)

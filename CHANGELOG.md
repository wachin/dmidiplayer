# Changelog

All notable changes to the dmidiplayer PyQt6 port are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Playback, channel and responsive-UI audit (2026-11-04)

#### Added

- **Internal SonivoxEAS output backend, now the default.**  This mirrors
  Drumstick's Linux `eassynth` backend, which the C++ AppImage uses first.
  The port drives `libsonivox` through ctypes, renders EAS audio in a worker
  thread and writes it to PulseAudio via `libpulse-simple`.  It uses
  Sonivox's embedded General MIDI samples, so the C++ and Python applications
  now use the same synthesis engine and do not depend on QSynth's SoundFont.
  Install `libsonivox3`, or build the source tree added under
  `Linux-SonivoxEas-devel/sonivox` with `./build-sonivox.sh`; without either
  the port falls back to FluidSynth.  The ctypes binding recognizes both the
  3.x (64-bit EAS types) and 4.x (32-bit EAS types) `S_EAS_LIB_CONFIG` layouts.
- **Internal FluidSynth output backend** as the second preference.  It loads
  a GM SoundFont (FluidR3_GM by default, or `DMIDIPLAYER_SOUNDFONT`) and sends
  notes, programs, controllers, pitch bend and SysEx directly to it.
- The configured percussion channel is explicitly kept in FluidSynth's DRUM
  mode and the GM drum bank (128).  Bank Select messages on that channel are
  ignored, so a stray `CC0=0` can no longer turn the drum track into a piano or
  guitar.  Additional GS/XG drum channels are left untouched.
- `Tools -> MIDI Connections` lists `sonivox`, `fluidsynth`, `alsa` and
  `dummy` as available; the selected driver is persisted and restored on the
  next launch.
- The FluidSynth audio driver can be overridden with
  `DMIDIPLAYER_FLUIDSYNTH_AUDIO`; soundfonts with `DMIDIPLAYER_SOUNDFONT` and
  the Sonivox library with `DMIDIPLAYER_SONIVOX_LIB`.

#### Removed

- **The main-window virtual keyboard and its instrument/channel selector were
  removed at the user's request.**  The keyboard did not fit the main interface
  and the user asked for it to be deleted to avoid malfunction.  All keyboard
  visualization remains available in `View -> Piano Player`, which uses the
  same channel-based model and the improved responsive layout.
- The `View -> Keyboard` action and the selector row above the old main
  keyboard were deleted.  The main window no longer creates a `PianoKeyboard`.
- Main-window keyboard/selector tests were removed; a regression test now
  asserts that `MainWindow` contains no `PianoKeyboard` and no selector.
- Per-channel note activity is still tracked for the Channels dialog level
  bars; it is no longer attached to a main-window keyboard.

#### Fixed

- **A tab containing fewer than eight channels no longer stretches its last
  keyboard over the full page.**  Every tab now reserves eight equal vertical
  slots; a single-channel tab keeps the same row height as the eight-row tab
  and leaves empty space below.  Hiding a channel still lets the remaining
  visible rows expand.  Added a regression test using
  `Our_God-Chris_Tomlin.mid` at 1360x768 and 1920x1080.

- **Seeking after a tempo change no longer drifts or jumps to the end.**
  `MidiFile.microseconds_to_tick()` used 500000 us/qn as the initial tempo
  instead of the file's tempo at tick 0.  The forward and inverse tempo maps now
  share one cached segment table, so `tick_to_microseconds()` and
  `microseconds_to_tick()` are consistent across every tempo change.  This was
  the root cause of the slider jumping backwards after a seek and of seeks near
  the end finishing immediately.

- **Playback now ends at the exact sequence end and stops the timer.**
  The scheduler previously ended when all events had been dispatched.  It now
  waits for the authoritative clock to reach `length_microseconds`, sets the
  final tick/microsecond, stops the `QTimer`, releases any active notes and
  emits `finished` exactly once.  Loop playback still rewinds to the loop start
  without entering the end-of-song state.

- **Seeking works while stopped, paused and playing.**  A seek releases active
  notes, invalidates pending events with `bisect_left` on the new tick, and
  restores the score state at the destination: bank select, program, channel
  volume, common controllers (pan, expression, sustain, etc.), pitch bend and
  channel pressure.  Repeated forward/backward seeks are covered by tests.

- **A manual program choice no longer overrides the whole song.**
  Selecting a patch in the Channels dialog sent it immediately, but the player
  also rewrote every later score program change with that patch, even when the
  channel was not locked.  The C++ behaviour is now matched: the manual patch
  updates the last program, score program changes are delivered normally, and
  only a locked channel substitutes the locked program.  A locked channel with
  no manual patch now receives its captured program instead of dropping the
  event.

- **Global and per-channel volume preserve the score's CC7 value.**
  Volume changes now scale the last volume controller sent by the file instead
  of assuming 100.  This prevents a file's quiet/balanced channels from being
  reset to full volume when the user moves the master slider.

- **Only one MIDI reset SysEx message is sent.**  The previous implementation
  sent GM Reset, GS Reset and XG Reset consecutively, which can leave a
  GS/XG-capable synthesizer in an inconsistent mode.  A single GM Reset is sent
  when the preference is enabled.

- **Controller, program and volume state is reset at position zero.**  This
  matches `GUIPlayer::play()` and prevents a new song from starting with a
  patch, bank or volume left over from another file or application.

- **Unmuting a channel resynchronizes its patch and controllers.**  Muted
  channels drop program/controller events; unmuting now sends the current bank,
  program, volume, common controllers and pitch bend so later notes do not sound
  with the wrong instrument.

- **Overlapping notes on the same pitch are tracked by count.**  One note-off
  no longer clears a still sounding voice in the player or in `PianoKeyboard`,
  and panic/silence paths send the required number of note-offs plus
  `all_notes_off`.

- **UI updates no longer starve the MIDI scheduler.**  Position signals are
  emitted at about 30 Hz instead of every 2 ms tick, and the informational event
  label at about 20 Hz.  Note visualization and channel activity still update on
  every note event.

- **Piano Player keyboards are no longer clipped at 1360x768.**  Rows used a
  72-pixel keyboard minimum plus a trailing stretch, requiring about 900 pixels
  for eight rows.  Rows now share all available vertical space, the keyboard
  minimum is 40 pixels, headers are font-metric sized, and a hidden channel
  releases its space to the other rows.  The dialog sizes itself from the
  available screen on first open, restores saved geometry afterwards, and
  clamps restored geometry to the current screen.  At 1920x1080 the keyboards
  grow to use the extra height.

- **Channels containing only a program change no longer widen the tightened
  key range.**  Only channels with actual note events contribute to the
  song-wide lowest/highest note.

- **System Common and real-time bytes in an SMF track are consumed safely**
  instead of being misdecoded as channel events.  Running status remains
  tolerant, matching Drumstick's reader.

- **The drum channel keeps its drum bank.**  The Python reset path was sending
  Bank Select 0/0 to all 16 channels before program 0, unlike C++
  `SequencePlayer::resetPrograms()`, which sends only the program.  On
  FluidSynth in XG mode (and on some hardware), Bank Select 0 switches channel
  10 from drums to a melodic channel, so the drum track plays a piano or guitar.
  The port no longer resets banks; after a seek or unmute it sends Bank Select
  only when the score explicitly selected a bank.  This now matches the C++
  instrument-loading behavior.

- **Identical Qt styles and palettes are no longer re-applied on every window
  creation.**  Repeated `QApplication.setStyle()`/`setPalette()` calls forced a
  full restyle of every live widget, slowed window creation and caused a
  nondeterministic PyQt offscreen crash in long test runs.  Style and palette
  changes are now skipped when the requested value is already active.

#### Added

- `Sequence.channel_infos()`, `Sequence.instrument_at_tick()` and
  `Sequence.channel_part_names()` as the shared channel model for the Piano
  Player and the Channels dialog.
- `PianoKeyboard.sizeHint()` / `minimumSizeHint()`, expanding size policy,
  overlap-aware note state and smaller black-key geometry for compact layouts.
- `PianoDialog.set_channel_instrument()` so program changes update Piano Player
  headings or tooltips.
- `PianoDialog.show_active_notes()` so opening the window during playback shows
  notes that are already sounding.
- Channel program/volume resynchronization after unmute and solo changes.

#### Changed

- The Piano Player tab label now reflects the actual channel numbers of its
  slice; contiguous slices still read "Channels 1-8" / "Channels 9-16".
- Tab grouping is documented as a Python-port UX extension.  The original C++
  Pianola has one frame per channel and no tabs.
- The scheduler uses one `QElapsedTimer` for both MIDI dispatch and the position
  reported to the UI.

#### Tests

- Added `tests/test_playback_timing.py`: tempo-map inversion, seek in stopped /
  paused / playing states, exact end position, timer stop, one `finished`
  signal, loop behaviour, program/volume reset at start, one reset SysEx,
  synchronous tick-zero dispatch, overlapping notes, seek state restoration and
  unmute resynchronization.
- Added `tests/test_channel_selector_and_pianola.py`: the merged per-channel
  model, tracks sharing a channel, percussion labels, manual-note channel
  routing, 4/7/9/14/16/17-part tab distribution, per-channel note routing and
  note-range filtering.
- Added `tests/test_pianola_layout.py`: 1360x768 and 1920x1080 geometry,
  no clipping for every keyboard in every tab, expanding space at larger
  resolutions, hidden-row redistribution and fullscreen.
- Added `tests/test_midi_output_messages.py`: note on/off, velocity-zero
  note-on, all 16 channels, program change, bank select, key/channel pressure,
  pitch bend, SysEx framing and same-tick dispatch order.
- Added `tests/test_midi_collection.py`: analysis of the six supplied
  `MIDI-Karaoke` files, expected channel counts, note pairing, invertible tempo
  maps, percussion entries, shared-channel merging and SysEx preservation.
- Added `tests/test_smf_system_messages.py`: System Common, real-time and
  truncated system-message parsing.
- Added `tests/test_platform_fallback.py`: the window remains usable with dummy
  output when ALSA/libasound is unavailable (Windows/macOS path).
- Full suite: **373 passed, 1 skipped** with a Sonivox library available (system or local build); **370 passed, 4 skipped** without one.

#### Verification limits

- Real QSynth/FluidSynth listening was not possible in the audit environment:
  `/dev/snd/seq` is absent.  Parser events, scheduler timing and the exact ALSA
  message fields are tested, but tonal accuracy and SoundFont behaviour still
  require a manual listening pass with QSynth/FluidR3.
- The Preferences checkbox currently sends GM Reset only; choosing GM/GS/XG
  individually (as in C++) remains pending.

### Earlier channel-based Pianola correction

#### Fixed

- **Pianola shows one keyboard per MIDI channel, not per track.** The C++
  `Pianola` class displays exactly one piano keyboard per MIDI channel (0–15),
  hiding channels that are not used in the loaded file. The Python port
  previously created one keyboard per MIDI track, which could produce more rows
  than the C++ version because multiple tracks can share the same channel.

  For example, the file `Amor_amor_amor-Annette_Moreno_MIDI_Jorge_Gómez.mid`
  has 18 tracks with MIDI data but only 14 unique channels. The old
  implementation displayed 18 pianos (10 + 8 across two tabs); the corrected
  implementation displays 14 pianos (8 + 6 across two tabs), matching the C++
  AppImage.

#### Changed

- `Sequence.pianola_channel_infos()` replaces the track-based data source for
  the Pianola. It returns one dict per used MIDI channel with keys `channel`,
  `title`, `min_note`, and `max_note`.

- `PianolaDialog.set_channels()` replaces `set_tracks()`. The internal data
  structures now map channel numbers to keyboards, checkboxes, and containers
  instead of track numbers.

- `PianolaDialog.note_on()` and `note_off()` now route directly to the
  channel's keyboard in O(1) instead of iterating over all tracks to find
  matching channels.

- Tab labels changed from "Tracks 1–8" to "Channels 1–8".

- Status bar messages changed from "Track N" to "Channel N" when showing/hiding
  individual pianos.

#### Tests

- Updated `test_pianola_dialog_shows_only_channels_with_midi` to expect channel
  labels ("Channel 2 - Part 2") instead of track labels.
- Updated `test_pianola_dialog_splits_channels_into_tabs_of_eight` to expect 2
  tabs of 16 channels instead of 3 tabs of 17 tracks.
- Updated object name references from `pianola_track_*` to `pianola_channel_*`
  across all pianola-related tests.
- Historical result at that time: 17 pianola tests and 87 parser/sequence/settings/i18n tests passed.

#### Technical Details

**Root cause:** The C++ `Pianola` class uses a fixed array of 16 frames
(`m_frame[MIDI_STD_CHANNELS]`), one per MIDI channel. `initSong()` calls
`channelUsed(i)` for each channel to show/hide rows. The Python port
incorrectly used `midi_track_infos()` which returns one entry per MIDI track.

**Key files changed:**
- `dmidiplayer/dmidiplayer_py/sequence.py` — added `pianola_channel_infos()`
- `dmidiplayer/dmidiplayer_py/app.py` — refactored `PianolaDialog` for
  channel-based display
- `tests/test_app_playlist.py` — updated pianola test assertions and object names
- `ROADMAP.md` — updated documentation to reflect channel-based Pianola

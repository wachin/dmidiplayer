# Changelog

All notable changes to the dmidiplayer PyQt6 port are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

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

### Changed

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

### Tests

- Updated `test_pianola_dialog_shows_only_channels_with_midi` to expect channel
  labels ("Channel 2 - Part 2") instead of track labels.
- Updated `test_pianola_dialog_splits_channels_into_tabs_of_eight` to expect 2
  tabs of 16 channels instead of 3 tabs of 17 tracks.
- Updated object name references from `pianola_track_*` to `pianola_channel_*`
  across all pianola-related tests.
- All 17 pianola tests pass.
- All 87 parser/sequence/settings/i18n tests pass.

### Technical Details

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

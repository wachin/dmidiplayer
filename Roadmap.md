# Qt/Python PyQt6 Port Roadmap

Last updated: 2026-05-06.

This file is the handoff document for continuing the migration in a future
session. Before changing code, read especially:

- `Current State At Handoff`
- `Quick Verification`
- `Next Session: Concrete Tasks`
- `Known Limitations`

This repository contains two C++/Qt projects that must coexist during the port:

- `drumstick`: the MIDI library stack for Qt. In Python it lives as
  `drumstick_py` inside the same directory.
- `dmidiplayer`: the player application that depends on Drumstick. In Python it
  lives as `dmidiplayer_py` inside the same directory.

The conversion should be done in layers. Port `drumstick_py` first, then connect
`dmidiplayer_py` to that Python API. Keep the original C++ code as reference
until every module reaches functional parity and has tests.

## Full Drumstick Ecosystem

![Drumstick ecosystem](drumstick-ecosystem.webp)

The `drumstick-ecosystem.webp` image shows how the Drumstick family fits
together. Green blocks are Drumstick libraries or utilities; pink blocks are
external applications or external dependencies. For this port, the important
point is that `dmidiplayer_py` must not be treated as an isolated program: it
should depend on a Python equivalent of the original C++ Drumstick ecosystem.

Reference C++ libraries and expected Python equivalents:

- `Drumstick::ALSA`: Linux-only ALSA Sequencer layer. In Python this is being
  replaced inside `drumstick_py.rt` using `ctypes` over `libasound.so.2`.
- `Drumstick::File`: file I/O for `.mid`, `.kar`, `.rmi`, and `.wrk`. In Python
  this is replaced by `drumstick_py.file`.
- `Drumstick::RT`: realtime MIDI I/O with ALSA, FluidSynth, and other backends.
  In Python this should become a reusable input/output API for `dmidiplayer_py`,
  `vpiano_py`, and future utilities.
- `Drumstick::Widgets`: Qt MIDI widgets, especially virtual piano/keyboard
  widgets. In Python this is replaced by `drumstick_py.widgets`.

Besides `dmidiplayer_py`, the final goal includes complete PyQt6 ports of the
three graphical Drumstick utilities listed in `drumstick/readme.md`:

- `drumgrid`: "Drumstick Drum Grid", a graphical drum pattern editor/player.
  It mainly depends on the ALSA layer.
- `guiplayer`: "Drumstick ALSA MIDI Player", a graphical MIDI/WRK player based
  on Drumstick::ALSA and Drumstick::File. It is a direct reference for player
  behavior and comparison testing.
- `vpiano`: "Drumstick Virtual Piano", a graphical virtual piano based on
  Drumstick::RT and Drumstick::Widgets. It should validate realtime I/O and
  reusable widgets.

These three applications must have their own Python launcher scripts, complete
PyQt6 UIs, basic tests, and usage documentation. The repository should end up
providing a coherent family:

- `dmidiplayer-py`
- `drumstick-drumgrid-py`
- `drumstick-guiplayer-py`
- `drumstick-vpiano-py`

## Final Functional Parity Goal

The goal of this port is for `dmidiplayer_py`, using `drumstick_py`, to become a
complete and pleasant real-world MIDI player: open songs, sound good with MIDI
hardware or software synths, show useful musical information, help singers and
instrumentalists rehearse, and keep a practical UI for playlists, repertoire,
and karaoke.

This section summarizes the final expected features from the dmidiplayer and
Drumstick documentation. It is the target list for the whole migration.

### File Formats And Parsing

- [x] Open `.mid`, `.midi`, and `.kar` as Standard MIDI Files.
- [ ] Open Cakewalk `.wrk` files.
- [ ] Port RIFF MIDI.
- [x] Preserve channel MIDI events, meta events, lyrics, text, markers, cue points,
  tempo changes, time signatures, key signatures, and SysEx.
- [ ] Detect or allow choosing text/lyrics encoding.
- [x] Report file errors without closing the application.
- [x] Keep enough metadata for lyrics, channel views, player piano, duration, bars,
  and position lookup.

### MIDI Output And Synthesizers

- [x] Send MIDI to hardware ports through ALSA sequencer destinations.
- [x] Send MIDI to software synths through Drumstick backends:
  - [x] ALSA sequencer on Linux;
  - [ ] FluidSynth;
  - [ ] other backends available or reasonable in the Python version.
- [x] List MIDI destinations and connect/disconnect from the UI.
- [x] Support dummy output for automated tests.
- [ ] Send GM/GS/XG reset SysEx before playback when configured.
- [x] Run `all_notes_off` when stopping, pausing, changing files, closing, seeking,
  or changing loop.
- [x] MIDI output failures must be recoverable UI errors, not process aborts.

### Playback Controls

- [x] Play, pause/resume, and stop.
- [x] Fast forward and rewind by bar.
- [x] Jump to a specific bar number.
- [x] Move the position with a slider.
- [x] Auto-play after loading a file when the preference is enabled.
- [x] Show current state in the status bar: playing, stopped, paused, loading,
  error, etc.
- [x] Auto-advance to the next playlist item when the preference is enabled.

### Tempo, Transpose, And Volume

- [x] Transpose song tonality between -12 and +12 semitones.
- [x] Do not transpose the configured percussion channel, GM channel 10 by default.
- [x] Control global volume from 0% to 200%, sending MIDI CC7 while respecting the
  MIDI 0-127 range.
- [x] Reset global volume.
- [x] Scale tempo from 50% to 200%.
- [x] Reset tempo.
- [x] Show effective tempo in BPM, starting at 120 BPM when the file has no tempo.
- [x] Update visible BPM during playback when the file has tempo changes.
- [x] Apply pitch/tempo/volume to the scheduler and outgoing events, not just the UI.

### Jump, Loop, And Musical Positioning

- [x] Calculate bars from tempo and time-signature maps.
- [x] Jump to a bar number from 1 to the last bar of the song.
- [x] Define a loop between two bars.
- [x] Enable/disable loop during playback.
- [x] Keep the position slider synchronized with ticks, real time, and bars.
- [x] Allow arbitrary seek without leaving stuck notes.

### Per-Song Settings

- [ ] Save and load per-song settings in `$HOME/.dmidiplayer`.
- [ ] Use the song name plus `.cfg` suffix.
- [ ] Allow automatic load/save depending on preferences.
- [ ] Allow manual load/save from the menu.
- [ ] Save:
  - [ ] text/lyrics encoding;
  - [ ] MIDI file path;
  - [ ] transpose;
  - [ ] tempo variation;
  - [ ] global volume variation.
- [ ] Save per channel:
  - [ ] volume variation;
  - [ ] editable label;
  - [ ] MIDI patch/program;
  - [ ] solo state;
  - [ ] mute state;
  - [ ] lock state.

### Channel View

- [x] Show up to 16 rows, one per used MIDI channel.
- [x] Show channel number and editable label.
- [x] Mute per channel.
- [x] Solo per channel, reducing other channels according to preference.
- [x] Activity/level indicator per channel.
- [x] Volume slider per channel.
- [ ] Patch lock to prevent program changes sent by the file.
- [ ] Patch/program selector using General MIDI names.
- [x] Synchronize channel changes with realtime playback.

### Player Piano / Pianola

- [ ] Show up to 16 rows, one per used channel.
- [ ] Each row should have channel number/label and keyboard.
- [x] Highlight keys according to MIDI notes being played in the minimal keyboard.
- [ ] Allow customizable colors per channel/state.
- [ ] Allow velocity tinting.
- [ ] Show note names according to preference:
  - [ ] never;
  - [ ] minimal;
  - [ ] when active;
  - [ ] always.
- [ ] Support configurable octave designation.
- [ ] Allow manual note playing with computer keyboard and mouse where appropriate.
- [ ] Window menu:
  - [ ] fullscreen;
  - [ ] show all channels;
  - [ ] hide all channels;
  - [ ] adjust key range to actually used octaves;
  - [ ] show/hide individual channels.

### Lyrics And Karaoke

- [ ] Show MIDI/KAR meta text.
- [ ] Filter by track:
  - [ ] all tracks;
  - [ ] individual track.
- [ ] Automatically select the track with the most text data.
- [ ] Filter by text type:
  - [ ] lyrics;
  - [ ] text;
  - [ ] marker;
  - [ ] cue point;
  - [ ] other relevant types;
  - [ ] all.
- [ ] Detect encoding automatically and allow manual override.
- [ ] Highlight past/future lyrics with configurable colors.
- [ ] Copy lyrics to clipboard.
- [ ] Save lyrics to a file with selected encoding.
- [ ] Print lyrics.
- [ ] Change lyrics font.
- [ ] Fullscreen lyrics view.

### Rhythm View

- [x] Port the embedded Rhythm view in the main window.
- [x] Allow showing/hiding it from the View menu.
- [x] Synchronize it with playback, tempo, and bars.

### Playlists And Repertoire

- [ ] Manage playlists from `File -> Play List...`.
- [ ] Create, modify, sort, open, and save playlists.
  - [x] Open and save `.lst` playlists.
  - [x] Add and remove playlist entries.
  - [x] Reorder playlist entries up and down.
  - [x] Sort playlist entries alphabetically.
  - [x] Open `.lst` playlists from shared file-opening paths, including startup arguments.
- [x] Show the playlist file name in the window title.
- [x] Navigate manually with Next and Previous.
- [x] Create a temporary playlist when opening multiple command-line files.
- [x] Create a temporary playlist when dragging/dropping files into the window.
- [x] Remember the last opened or saved playlist.
- [x] Do not save playlists automatically unless explicitly requested.
- [x] Use plain text playlist files, one file per line.
- [x] Support absolute paths and paths relative to the `.lst` file.
- [x] Allow starting with an empty playlist.
- [ ] Include an initial playlist with examples.

### File Opening And Recent Files

- [x] Open files from menu/toolbar.
- [x] Recent files menu, remembering up to ten entries.
- [x] Open files passed on the command line.
- [x] Open `.lst` playlists passed on the command line.
- [ ] Integrate with file managers through "Open With...".
- [x] Support drag and drop into the main window.

### Preferences

- [x] Preferences dialog with Restore Defaults button.
- [ ] General tab:
  - [x] percussion channel, default 10, persisted in settings;
  - [x] solo volume reduction percentage, default 50%;
  - [x] auto-play on load;
  - [x] playlist auto-advance;
  - [ ] auto-load/save song settings;
  - [ ] sticky window borders, if kept for Windows;
  - [ ] force dark mode where applicable;
  - [ ] use internal icon theme;
  - [ ] Qt Widgets style;
  - [x] MIDI reset SysEx before playback.
- [ ] Lyrics tab:
  - [ ] font;
  - [ ] future text color;
  - [ ] past text color.
- [ ] Player Piano tab:
  - [ ] highlight palettes;
  - [ ] single highlight color;
  - [ ] velocity tinting;
  - [ ] note-name font;
  - [ ] note-name display mode;
  - [ ] octave designation.
- [x] Persist basic application preferences with `QSettings`.

### Toolbar Customization

- [x] Allow moving the toolbar through the default Qt toolbar.
- [x] Allow toolbar at top, bottom, or floating when Qt supports it.
- [ ] Customization dialog with:
  - [ ] available actions;
  - [ ] selected actions;
  - [ ] add/remove;
  - [ ] move up/down.
- [ ] Button styles:
  - [ ] icon only;
  - [ ] text only;
  - [ ] text beside icon;
  - [ ] text under icon;
  - [ ] follow Qt style.

### Main UI And Views

- [ ] Port File menu, View menu, tools, status bar, and main dialogs.
- [ ] Independent views:
  - [x] Channels;
  - [ ] Lyrics;
  - [ ] Piano Player.
- [ ] Embedded views that can be shown/hidden:
  - [x] toolbar;
  - [x] status bar;
  - [x] Rhythm.
- [ ] Keep existing icons and internal theme where needed.
- [ ] Port Help and About window.
- [ ] Port translations, especially English and Spanish.

### Documentation, Help, And Distribution

- [x] Document installation and usage in README.
- [x] Keep testing notes for MX Linux 23, RT kernel, QjackCtl, QSynth, and
  `FluidR3.sf2`.
- [x] Port local help from existing markdown/html files.
  - [x] Add a dedicated PyQt6 user guide for the current interface.
- [ ] Prepare local packaging once the port is stable:
  - [x] launcher scripts;
  - [ ] `.desktop` file;
  - [ ] resources;
  - [ ] icons;
  - [ ] translations;
  - [ ] possible `pyproject.toml`.

### Success Criteria

- [x] dmidiplayer Python plays real files with initial realtime MIDI output.
- [ ] The main experience matches or improves the C++ version for opening, playing,
  pausing, stopping, navigating, changing tempo/pitch/volume, and using
  playlists.
- [ ] Channel, lyrics, player piano, and rhythm views are synchronized with playback.
- [ ] Preferences and song settings survive across sessions.
- [x] Automated tests cover parser, scheduler, dummy output, basic ALSA conversion,
  and critical UI flows.
- [x] The application never leaves stuck notes after stop, seek, close, or MIDI
  output failure.
- [ ] `drumgrid`, `guiplayer`, and `vpiano` also exist as complete PyQt6
  applications and reuse `drumstick_py` instead of duplicating MIDI logic.

## Current State At Handoff

A runnable Python base exists and stays inside each project directory without
removing or replacing the original C++ code.

- `drumstick/drumstick_py/`
  - [x] `file.py`: initial dependency-free SMF reader with tempo map, real duration,
    time signatures, key signatures, text metadata, bar calculations, and basic
    metadata.
  - [x] `rt.py`: `BackendManager`, dummy output, diagnostics with
    `python3-alsaaudio`, initial ALSA sequencer output through `libasound`, ALSA
    destination listing, and port connection.
  - [x] `widgets.py`: initial PyQt6 `PianoKeyboard`.
- `dmidiplayer/dmidiplayer_py/`
  - [x] `app.py`: initial PyQt6 window with list, controls, position slider,
    keyboard, ALSA destination selector, compact toolbar, two-row musical
    controls, time/BPM/bar display, previous/next bar navigation, direct bar
    jump, and bar-based loop controls.
  - [x] `i18n.py`: Qt `.qm` translation loading with English as source language.
  - [x] `settings.py`: persistent configuration through
    `QStandardPaths.AppConfigLocation` and `QSettings`.
  - [x] `sequence.py`: model that loads SMF through `drumstick_py`.
  - [x] `player.py`: `QTimer` player with real-time clock based on the tempo map.
  - [x] `__main__.py`: `python3 -m dmidiplayer_py` entry point.
- [x] `dmidiplayer/dmidiplayer-py`: local launcher that configures `PYTHONPATH`.
- [x] Tests:
  - [x] `tests/test_smf_parser.py`
  - [x] `tests/test_alsa_event.py`
  - [x] `tests/test_sequence_player.py`
  - [x] `tests/test_i18n.py`
  - [x] `tests/test_settings.py`
  - [x] `tests/test_app_playlist.py`
- [x] Parser coverage added after the initial handoff:
  - [x] format 1 multi-track event merging;
  - [x] running status events and malformed running-status error reporting;
  - [x] SysEx `0xF0` and `0xF7` events;
  - [x] time signature, key signature, lyrics, and marker metadata.
- [x] ALSA connection handling added after the initial handoff:
  - [x] active output connections are tracked by `AlsaSequencerOutput`;
  - [x] the UI can disconnect active ALSA destinations;
  - [x] `snd_seq_event_t` layout is covered by a small ctypes test.
- [x] `README.md`: testing notes for MX Linux 23, RT kernel, QjackCtl, QSynth, and
  `FluidR3.sf2`.
- [x] `drumstick-ecosystem.webp`: diagram used in this Roadmap to document the full
  Drumstick ecosystem target.

Functional state:

- [x] `./dmidiplayer/dmidiplayer-py --help` works.
- [x] The PyQt6 window starts.
- [x] `.mid`, `.midi`, and `.kar` files can be loaded when they are SMF-compatible
  with the current parser.
- [x] The parser computes tempo map, bars, time signatures, key signatures, text,
  and real duration.
- [x] The player emits events to the configured output using real timing derived
  from the tempo map.
- [x] The position slider supports basic seek by tick. Seeking sends `all_notes_off`
  and continues from the new position if playback was active.
- [x] The UI shows current/total time, effective BPM, and current/total bar. BPM
  respects MIDI tempo changes and the selected tempo percentage.
- [x] The UI has initial `Bar -` and `Bar +` actions for previous/next bar seek.
- [x] The UI has a `Jump bar` control with `Go` to seek directly to a specific bar.
- [x] The list works as a temporary playlist:
  - [x] multiple files can be loaded from the command line or file dialog;
  - [x] `Previous` and `Next` navigate the list;
  - [x] playback auto-advances to the next song at the end.
- [x] Initial pitch and tempo controls live in the main panel:
  - [x] transpose from -12 to +12 semitones;
  - [x] GM percussion channel 10 is not transposed;
  - [x] tempo from 50% to 200%, applied to scheduler timing.
- [x] Initial global volume control:
  - [x] scales MIDI CC7 from 0% to 200%;
  - [x] sends CC7 to all 16 channels when changed;
  - [x] clamps to MIDI range 0-127.
- [x] Basic bar-based loop:
  - [x] `Loop`, `Start bar`, and `End bar` controls in the main panel;
  - [x] the UI converts bar numbers to MIDI ticks with `tick_for_bar()`;
  - [x] reaching the loop end rewinds to the start and sends `all_notes_off`;
  - [ ] full loop dialog and richer loop behavior are still missing.
- [x] UI source strings are in English and can load Qt Linguist compiled
  translations from `dmidiplayer/dmidiplayer_py/translations`.
- [x] Configuration is stored under `.config` on Linux and AppData/equivalent on
  Windows through Qt. The last folder visited by the Open MIDI dialog is
  remembered.
- [x] The app tries ALSA sequencer first.
- [x] If ALSA sequencer fails, the app falls back to dummy output and still opens
  the UI.
- [x] `python3-alsaaudio` is used only for card/PCM diagnostics. It does not expose
  ALSA sequencer MIDI.
- [x] ALSA MIDI output is implemented with `ctypes` over `libasound.so.2`.
- [x] ALSA SysEx events are marked as variable length, avoiding `Invalid argument`
  with files such as `examples/test.mid`.
- [x] The UI lists ALSA destinations and can connect directly to QSynth, FluidSynth,
  or another compatible MIDI port. If QSynth/FluidSynth is detected at startup,
  it tries to auto-connect.

Current execution:

```bash
./dmidiplayer/dmidiplayer-py file.mid
```

Real ALSA MIDI output has an initial implementation. If ALSA sequencer is not
available, the app automatically falls back to dummy output so parser, UI, and
timing can still be validated.

ALSA sequencer requires `/dev/snd/seq`. On Debian it is usually enabled by the
`snd-seq` kernel module. Check with:

```bash
aconnect -lo
```

If `aconnect -lo` fails with `open /dev/snd/seq failed`, load the module:

```bash
sudo modprobe snd-seq
```

After launching `dmidiplayer-py`, the ALSA port can be connected from the app's
`MIDI destination` selector. `aconnect` remains useful for manual diagnostics.

## Quick Verification

From the repository root:

```bash
./dmidiplayer/dmidiplayer-py --help
PYTHONPATH=drumstick:dmidiplayer python3 -m compileall drumstick/drumstick_py dmidiplayer/dmidiplayer_py tests
PYTHONPATH=drumstick:dmidiplayer python3 -m unittest tests.test_smf_parser tests.test_alsa_event tests.test_sequence_player tests.test_i18n tests.test_settings tests.test_app_playlist
QT_QPA_PLATFORM=offscreen timeout 2s ./dmidiplayer/dmidiplayer-py
```

Notes:

- The offscreen command should end by `timeout` because the app remains open;
  that is normal.
- If `/dev/snd/seq` does not exist in the environment, ALSA will print a warning
  and the app will use dummy output. That is not an import failure.
- After `compileall`, generated `__pycache__` directories can be removed if
  desired.

Manual ALSA test:

```bash
aconnect -lo
./dmidiplayer/dmidiplayer-py file.mid
aconnect -lo
```

In another terminal, connect the `dmidiplayer PyQt6` port to FluidSynth,
hardware MIDI, QSynth, or another ALSA synthesizer.

## Known Limitations

- [ ] The initial SMF parser computes tempo, real duration, and bars for PPQ SMF,
  but still needs more edge-case tests and comparison with Drumstick C++.
- [ ] The scheduler already supports real timing, basic seek, loop, and tempo scale.
  The UI loop works by bars and converts to ticks before calling the scheduler.
  The scheduler still depends on `QTimer` and has no advanced latency
  compensation yet.
- [ ] Initial transpose affects note events, but still needs integration with song
  settings, locked channels, and final UI.
- [ ] Per-channel volume and restoring original song/channel volume through song
  settings are still missing.
- [ ] ALSA output lists/connects destinations from the UI, but backend-querying
  active connection display is still missing.
- [ ] The current PyQt6 UI is a minimal hand-written window, not a full conversion
  of `guiplayer.ui`.
- [ ] Full channels, playlist dialog, lyrics, full pianola, preferences, and help are
  not yet ported.
- [ ] Temporary playlist navigation and auto-advance exist, but full playlist dialog,
  `.lst` open/save, repeat, and shuffle are still missing.
- [ ] RIFF MIDI and Cakewalk WRK are not ported yet.
- [ ] `uchardet` is not connected to the Python parser yet.
- [ ] Automated tests exist but coverage still needs to grow.
- [ ] The initial Spanish translation exists as `.ts`, but is not translated or
  compiled to `.qm` yet.

## Next Session: Concrete Tasks

Recommended priority:

1. [ ] Extend `drumstick_py.file` tests further:
   - [x] parser error cases around truncated chunks and invalid variable-length
     quantities;
   - [x] SMPTE division timing;
   - [x] tempo and time-signature maps with mid-song changes;
   - [ ] RIFF MIDI fixtures once `rmid.cpp` is ported;
   - [ ] Cakewalk WRK fixtures once `qwrk.cpp` is ported.
2. [ ] Improve `drumstick_py.rt`:
   - [ ] query active ALSA subscriptions from the backend instead of only tracking
     connections made during this process;
   - [ ] connect by a more flexible name search from preferences;
   - [ ] expose ALSA errors without excessive stderr noise;
   - [x] add reconnect-to-last-destination preferences once settings are expanded.
3. [ ] Start real UI conversion:
   - [ ] decide between `pyuic6` and `PyQt6.uic.loadUi`;
   - [ ] load `guiplayer.ui`;
   - [ ] connect basic actions to the Python `SequencePlayer`.
4. [ ] Translate `dmidiplayer_py_es.ts` in Qt Linguist and compile `.qm`.
5. [ ] Port the full loop dialog when the C++ UI starts being loaded.
6. [ ] Start the connections dialog or playlist dialog from the original C++ UI.

## Expanded Pending Task Backlog

This backlog is intentionally granular so future sessions can take larger,
clearer bites instead of rediscovering the next small step.

### Parser And File Formats

- [ ] Compare parser timing and metadata against C++ Drumstick for
  `examples/test.mid`.
- [ ] Compare parser timing and metadata against C++ Drumstick for
  `examples/mozart_diesirae.mid`.
- [ ] Add a karaoke `.kar` fixture with lyric meta events split across tracks.
- [ ] Preserve original track numbers for meta text and channel events.
- [ ] Preserve track names and instrument names as structured metadata.
- [ ] Parse RIFF MIDI container headers and delegate embedded SMF data to
  `read_smf()`.
- [ ] Add invalid RIFF MIDI tests for missing `RMID` and missing `data` chunks.
- [ ] Study `qwrk.cpp` and define the minimum WRK event model needed by
  dmidiplayer.
- [ ] Add WRK parser skeleton with explicit unsupported-feature errors.
- [ ] Add encoding detection tests with Latin-1 karaoke text.
- [ ] Add user-selectable lyrics/text encoding to the sequence model.

### Playback Engine

- [ ] Track active notes per channel in `SequencePlayer`.
- [ ] Send note-off for active notes before seek instead of relying only on
  controller all-notes-off.
- [ ] Reset pitch, tempo, and volume when loading a new file if song settings
  are not active.
- [x] Add preference-backed percussion channel instead of hardcoding channel 10.
- [ ] Add per-channel mute filtering in `_playable_event()`.
- [ ] Add per-channel solo filtering with configurable reduction.
- [ ] Add per-channel volume scaling before global volume scaling.
- [ ] Suppress program changes on locked channels.
- [ ] Add GM/GS/XG reset SysEx actions before playback.
- [ ] Add latency/late-event counters for scheduler diagnostics.

### Main Window UX

- [x] Build a real menu bar: File, Playback, View, Tools, Help.
- [x] Add File -> Open, Open Recent, Clear Recent, Exit.
  - [x] Add File -> Open.
  - [x] Add File -> Exit.
  - [x] Add File -> Open Recent submenu.
  - [x] Add File -> Clear Recent.
- [x] Add Playback -> Play, Pause, Stop, Previous, Next.
- [ ] Add View toggles for toolbar, status bar, keyboard, future rhythm view.
  - [x] Add toolbar visibility toggle.
  - [x] Add status bar visibility toggle.
  - [x] Add keyboard visibility toggle.
  - [ ] Add rhythm view visibility toggle.
- [x] Add Tools menu actions for MIDI connections and future preferences.
- [x] Add Help menu actions for About and local help.
- [x] Promote toolbar buttons to shared `QAction` instances everywhere.
- [x] Add enabled/disabled menu state when no file is loaded.
- [x] Add status bar state messages for loading, playing, paused, stopped, and
  errors.
- [x] Keep the window title synchronized with the current song and playlist.
- [x] Prevent duplicate playlist rows for the same file unless explicitly
  requested.
- [x] Add remove-selected and clear-playlist actions.
- [x] Add repeat playlist and shuffle toggles.
  - [x] Add repeat playlist toggle.
  - [x] Add shuffle toggle.
- [x] Save and restore main window size and position.
- [x] Add keyboard shortcuts for open, play/pause, stop, next/previous, and
  seek by bar.

### Playlist Files

- [ ] Create a playlist model separate from `QListWidget`.
- [x] Open `.lst` playlist files with relative path resolution.
- [x] Save `.lst` playlist files using paths relative to the playlist location
  when possible.
- [x] Add Save Playlist and Save Playlist As actions.
- [x] Remember the last playlist path in settings.
- [x] Show unsaved playlist state in the window title.
- [x] Add tests for absolute and relative playlist entries.

### Dialogs And Original UI

- [ ] Decide `pyuic6` generated classes versus `PyQt6.uic.loadUi` for each
  original `.ui` file.
- [ ] Load `guiplayer.ui` in a scratch module and document blockers.
- [ ] Port `connections.ui` as a standalone dialog.
- [ ] Port `loopdialog.ui` and connect it to current loop state.
- [ ] Port `playlist.ui` with open/save controls.
- [ ] Port `prefsdialog.ui` with settings read/write only, before wiring every
  behavior.
- [ ] Port `playerabout.ui` and wire Help -> About.
- [ ] Port `toolbareditdialog.ui` after menu/action names stabilize.

### Tests And Tooling

- [ ] Add import/offscreen startup tests for the main window without ALSA.
- [ ] Add UI tests for toolbar play/pause/stop state transitions.
- [ ] Add drag/drop event tests using real `QDropEvent` when practical.
- [ ] Add tests for recent files and playlist persistence.
  - [x] Add recent files persistence tests.
  - [ ] Add playlist persistence tests.
- [ ] Add tests for per-channel mute/solo/volume once channel controls exist.
- [ ] Add tests that close the app while playback is active.
- [ ] Add README instructions for running only fast tests versus manual ALSA
  tests.

Do not repeat:

- [x] Do not look for `python3-alsaaudio` bindings for MIDI sequencer. This was
  already checked; it only exposes PCM/mixer.
- [x] Do not delete the original C++ code; it remains the reference.
- [x] Do not move Python packages outside their current directories.
- [x] Do not introduce `pip` dependencies unless there is a strong reason.

## Debian 12 Dependencies

Already installed by the user:

- `python3-pyqt6`
- `uchardet`
- `pandoc`
- `python3-alsaaudio`

Recommended packages for real sound testing:

- `alsa-utils`: provides `aconnect`; `/usr/bin/aconnect` exists in the checked
  environment.
- `fluidsynth`: software synth for MIDI output.
- `fluid-soundfont-gm`: common Debian General MIDI soundfont.

Packages the user mentioned as available if needed:

- `python3-audioread`
- `python3-pydub`
- `python-soundfile-doc`
- `python3-pyao`
- `python3-pymad`
- `python-mutagen-doc`
- `python3-soundfile`
- `python3-mediafile`
- `python3-ecasound`
- `python3-jack-client`
- `python3-aubio`

Evaluation:

- `python3-jack-client` may be useful later if JACK support is ported.
- `python3-soundfile`, `python3-pydub`, and `python3-audioread` would only be
  useful for audio rendering/export, not realtime MIDI.
- `python3-aubio` is for audio analysis and is not a priority.
- `python3-pymad`, `python3-mediafile`, `python-mutagen-doc`, `python3-pyao`,
  and `python3-ecasound` are not needed for the current dmidiplayer path.

Recommended later dependencies:

- `python3-pyqt6.qtmultimedia`, if Qt Multimedia is used for audio.
- `python3-alsaaudio`, already installed, kept for PCM/mixer diagnostics.
- `fluidsynth` and, if available in repositories, Python FluidSynth bindings;
  otherwise use `ctypes` over `libfluidsynth`.
- `python3-pytest` for unit tests.
- `python3-pytestqt` for PyQt6 widget tests.
- `pyqt6-dev-tools` for `pylupdate6`.
- `qt6-tools-dev-tools`, `qttools5-dev-tools`, and `qtchooser` for Qt Linguist,
  `lupdate`, and `lrelease` depending on the local environment.
- `linguist-qt6`, available on MX Linux for editing `.ts` translations.

Do not introduce `pip` packages unless unavoidable. Prefer Debian 12 packages.

## [x] Phase 1: Python Base And Structure Compatibility

Status: started and usable as a skeleton.

- [x] Keep the original C++ code.
- [x] Use parallel Python packages:
  - [x] `drumstick/drumstick_py`
  - [x] `dmidiplayer/dmidiplayer_py`
- [x] Keep class names close to the originals where helpful:
  - [x] `BackendManager`
  - [x] `Sequence`
  - [x] `SequencePlayer`
  - [x] `PianoKeyboard`
- [x] Create local launcher scripts without global installation at first.
- [x] Confirm `python3 -m compileall` passes for both packages.
- [x] Confirm `./dmidiplayer/dmidiplayer-py --help` works.

## [ ] Phase 2: Drumstick File

Status: started. Basic SMF reader exists in `drumstick_py/file.py`.

Goal: replace `library/file` in Python.

Tasks:

- [ ] Complete SMF reader:
  - [x] tempo `0x51`;
  - [x] time signature `0x58`;
  - [x] key signature `0x59`;
  - [x] text, lyrics, markers, cue points;
  - [x] full SysEx;
  - [x] running status basic support;
  - [x] running status edge-case tests;
  - [x] real duration in microseconds with tempo changes;
  - [x] bar count and bar/tick conversion.
- [ ] Add SMF writer if any utility requires it.
- [ ] Port RIFF MIDI from `rmid.cpp`.
- [ ] Port Cakewalk WRK from `qwrk.cpp`.
- [ ] Integrate encoding detection:
  - [ ] use `uchardet` through external command or `ctypes` binding;
  - [ ] map encodings to Python codecs;
  - [ ] preserve karaoke lyrics behavior.
- [x] Define Python exceptions equivalent to C++ load errors.
- [ ] Create small MIDI fixtures for tests:
  - [x] format 0;
  - [x] format 1 multi-track;
  - [ ] karaoke `.kar`;
  - [x] file with SysEx;
  - [x] file with tempo changes.

Exit criteria:

- [x] `drumstick_py.file.read_smf()` returns events sortable by tick.
- [ ] Duration and metadata match C++ dmidiplayer for test files.
- [x] File errors are reported without closing the application.

## [ ] Phase 3: Drumstick RT

Status: started. Dummy output and initial ALSA sequencer output exist in
`drumstick_py/rt.py`.

Goal: replace `library/rt` and the backends needed for Debian 12.

Linux/Debian priority:

- [x] ALSA sequencer output.
- [ ] ALSA sequencer input, if needed for utilities such as vpiano.
- [ ] FluidSynth output.
- [x] Dummy output for tests.

Tasks:

- [ ] Design stable Python interface:
  - [ ] `MIDIOutput.open()`
  - [x] `MIDIOutput.close()`
  - [x] `MIDIOutput.send_event()`
  - [x] `MIDIOutput.all_notes_off()`
  - [x] `BackendManager.output_drivers()`
  - [x] `BackendManager.connections()`
- [x] `python3-alsaaudio` covers PCM/mixer but not ALSA sequencer MIDI. Use it for
  diagnostics and keep MIDI on `ctypes` over `libasound.so`.
- [x] Port MIDI event conversion to raw messages.
- [x] Implement port listing and connection by name.
- [ ] Implement GM/GS/XG reset if dmidiplayer needs it.
- [x] Keep dummy backend for automated tests.

Exit criteria:

- [x] dmidiplayer Python can send notes to a visible ALSA port.
- [ ] dmidiplayer Python can use FluidSynth if available.
- [x] `all_notes_off` works on stop, pause, close, and file change.

## [ ] Phase 4: Drumstick Widgets

Status: only minimal `PianoKeyboard` exists.

Goal: replace `library/widgets`.

Tasks:

- [ ] Complete `PianoKeyboard`:
  - [ ] black keys;
  - [ ] configurable range;
  - [ ] colors by channel/state;
  - [ ] mouse/keyboard events needed by vpiano.
- [ ] Port configuration dialogs:
  - [ ] FluidSynth;
  - [ ] Network;
  - [ ] Sonivox only if support is kept;
  - [ ] MacSynth is not a Debian priority.
- [ ] Port `SettingsFactory`.
- [ ] Reuse existing `.ui` files with `pyuic6` or load through `PyQt6.uic`, choosing
  whichever is more maintainable.

Exit criteria:

- [x] Widgets can be imported without depending on dmidiplayer.
- [ ] Dialogs save/restore configuration through `QSettings`.

## [ ] Phase 5: dmidiplayer Core

Status: started with minimal `Sequence` and `SequencePlayer`.

Goal: port the C++ dmidiplayer logic.

Original C++ files to cover:

- [ ] `events.*`
  - [x] create initial Python dataclasses/classes for MIDI, tempo, beat, and text events.
- [ ] `sequence.*`
  - [x] use `drumstick_py.file`;
  - [x] calculate real times with the tempo map;
  - [x] preserve text, lyrics, markers, bars, and key signatures;
  - [ ] port codec lookup and metadata.
- [ ] `seqplayer.*`
  - [ ] replace simple timer with precise scheduler;
  - [ ] respect tempo, pitch shift, volume, mute, lock, and programs;
  - [x] implement loop by bars/ticks;
  - [x] emit initial PyQt signals equivalent to C++.
- [ ] `settings.*`
  - [ ] port application constants;
  - [x] use `QSettings`;
  - [ ] portable mode `--portable` and `--file`.
- [ ] `instrumentset.*`
  - [ ] load instrument and bank names.
- [x] `recentfileshelper.*`
  - [x] save and populate recent files menu.

Exit criteria:

- [x] Open, play, pause, stop, and seek work with real MIDI output.
- [ ] Channels respect mute, volume, program, and lock.
- [ ] Loop behavior matches C++.

## [ ] Phase 6: dmidiplayer PyQt6 UI

Status: started with a minimal hand-written window. The full original UI is not
ported yet.

Goal: port all windows and dialogs.

`.ui` files to convert or load:

- [ ] `guiplayer.ui`
- [ ] `connections.ui`
- [ ] `loopdialog.ui`
- [ ] `playerabout.ui`
- [ ] `playlist.ui`
- [ ] `prefsdialog.ui`
- [ ] `toolbareditdialog.ui`

C++ widgets/views to port:

- [ ] `channels.*`
- [ ] `connections.*`
- [ ] `framelesswindow.*`
- [ ] `helpwindow.*`
- [ ] `lyrics.*`
- [ ] `pianola.*`
- [ ] `playlist.*`
- [ ] `prefsdialog.*`
- [ ] `rhythmview.*`
- [ ] `toolbareditdialog.*`
- [ ] `vumeter.*`

Tasks:

- [ ] Convert `.qrc` to Python resources or resolve icons from local paths.
- [ ] Reuse existing icons in `dmidiplayer/icons`.
- [ ] Port menus, toolbars, and actions.
- [x] Implement drag and drop.
- [ ] Implement connections dialog using `BackendManager`.
- [ ] Implement full preferences.
- [ ] Implement playlist with repeat and shuffle.
- [ ] Implement synchronized lyrics/karaoke.
- [ ] Implement pianola and rhythm view.
- [ ] Implement help using markdown converted with `pandoc` where appropriate.

Exit criteria:

- [ ] Python UI allows the same main flows as C++.
- [x] No main buttons remain connected to placeholders in the minimal UI.
- [x] The app closes without leaving stuck notes.

## [ ] Phase 7: Translations And Documentation

Tasks:

- [ ] Review existing `.ts` files.
- [x] Decide whether to keep Qt Linguist (`.qm`) translations with PyQt6.
- [x] Port dynamic language loading.
- [ ] Regenerate help/manpages with `pandoc`.
- [x] Document Python execution in `README.md`.
- [x] Keep notes about differences from C++ during migration.

Exit criteria:

- [ ] English and Spanish work in the Python UI.
- [x] Help opens from the application.

## [ ] Phase 8: Drumstick Utilities

Goal: port utilities under `drumstick/utils` to Python/PyQt6, keeping CLI tools
as diagnostics and fully converting graphical utilities.

Mandatory graphical priority:

- [ ] `utils/drumgrid` -> `drumstick-drumgrid-py`.
  - [ ] Complete PyQt6 UI for creating and playing drum patterns.
  - [ ] Reuse `drumstick_py.rt` for ALSA/realtime output.
  - [ ] Match the C++ "Drumstick Drum Grid" behavior.
- [ ] `utils/guiplayer` -> `drumstick-guiplayer-py`.
  - [ ] Complete PyQt6 UI for playing SMF/WRK with ALSA output.
  - [ ] Reuse `drumstick_py.file` and `drumstick_py.rt`.
  - [ ] Use it as a reference application for comparison with dmidiplayer.
- [ ] `utils/vpiano` -> `drumstick-vpiano-py`.
  - [ ] Complete PyQt6 virtual piano UI.
  - [ ] Reuse and expand `drumstick_py.widgets.PianoKeyboard` with mouse/keyboard
    interaction.
  - [ ] Reuse `drumstick_py.rt` for realtime MIDI input/output.

These three utilities are not optional; they are part of the final Python
Drumstick ecosystem goal.

CLI and diagnostic priority:

- [ ] `utils/playsmf`
- [ ] `utils/dumpsmf`
- [ ] `utils/dumpmid`
- [ ] `utils/dumprmi`
- [ ] `utils/dumpwrk`
- [ ] `utils/sysinfo`
- [ ] `utils/metronome`

Each utility should have its own package or module under `drumstick_py/utils`.

Exit criteria:

- [ ] Each graphical utility starts from the source tree with a local script.
- [ ] Each graphical utility can use dummy output for tests and ALSA for manual
  testing.
- [ ] `drumgrid`, `guiplayer`, and `vpiano` have import/offscreen startup tests.
- [ ] README explains how to run every Python utility.

## [ ] Phase 9: Tests

Status: started. Current tests cover parser basics, ALSA event conversion,
sequence player behavior, i18n fallback, settings persistence, playlist UI,
time/BPM display, bar navigation, direct bar jump, and bar-based loop controls.

Minimum tests to keep expanding:

- [ ] Parser SMF:
  - [x] invalid header;
  - [x] meta event;
  - [x] running status;
  - [x] SysEx;
  - [x] tempo;
  - [x] format 0 and 1;
  - [x] bar mapping with time-signature changes.
- [ ] Scheduler:
  - [x] event order;
  - [x] variable tempo;
  - [x] loop;
  - [x] stop/all notes off.
- [ ] UI:
  - [x] opens main window;
  - [x] loads file;
  - [ ] changes play/pause/stop state;
  - [ ] connections dialog lists backends.

Expected commands:

```bash
PYTHONPATH=drumstick:dmidiplayer python3 -m compileall drumstick/drumstick_py dmidiplayer/dmidiplayer_py tests
PYTHONPATH=drumstick:dmidiplayer python3 -m dmidiplayer_py --help
PYTHONPATH=drumstick:dmidiplayer python3 -m unittest tests.test_smf_parser tests.test_alsa_event tests.test_sequence_player tests.test_i18n tests.test_settings tests.test_app_playlist
```

## [ ] Phase 10: Local Packaging

Tasks:

- [ ] Create `pyproject.toml` if installing as a package becomes useful.
- [ ] Create scripts:
  - [x] `dmidiplayer-py`
  - [ ] `drumstick-*` utilities.
- [ ] Evaluate `/usr/local` installation only at the end.
- [ ] Create `.desktop` file for the Python version.
- [ ] Ensure resources, icons, and translations are found both from source tree and
  installation.

## Recommended Work Order

1. [ ] Expand automated tests for parser and scheduler.
2. [ ] Complete `drumstick_py.rt` with ALSA active connection listing and
   disconnect/reconnect.
3. [ ] Port `settings`, `sequence`, and `events` to C++ parity.
4. [ ] Convert/load `.ui` files and connect real actions.
5. [ ] Port channels, lyrics, playlist, loop dialog, pianola, and rhythm.
6. [ ] Port preferences, connections, help, and translations.
7. [ ] Port graphical Drumstick utilities:
   - [ ] `drumstick-guiplayer-py`
   - [ ] `drumstick-vpiano-py`
   - [ ] `drumstick-drumgrid-py`
8. [ ] Port remaining Drumstick CLI utilities.
9. [ ] Prepare packaging and installation.

## Python Files Created So Far

- [x] `drumstick/drumstick_py/__init__.py`
- [x] `drumstick/drumstick_py/file.py`
- [x] `drumstick/drumstick_py/rt.py`
- [x] `drumstick/drumstick_py/widgets.py`
- [x] `dmidiplayer/dmidiplayer_py/__init__.py`
- [x] `dmidiplayer/dmidiplayer_py/__main__.py`
- [x] `dmidiplayer/dmidiplayer_py/app.py`
- [x] `dmidiplayer/dmidiplayer_py/i18n.py`
- [x] `dmidiplayer/dmidiplayer_py/player.py`
- [x] `dmidiplayer/dmidiplayer_py/sequence.py`
- [x] `dmidiplayer/dmidiplayer_py/settings.py`
- [x] `dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.ts`
- [x] `dmidiplayer/dmidiplayer-py`
- [x] `tests/test_smf_parser.py`
- [x] `tests/test_alsa_event.py`
- [x] `tests/test_sequence_player.py`
- [x] `tests/test_i18n.py`
- [x] `tests/test_settings.py`
- [x] `tests/test_app_playlist.py`

## Notes From Previous Investigation

- `python3-alsaaudio` exists but is not useful for ALSA sequencer MIDI. It only
  exposes PCM/mixer/card diagnostics.
- `drumstick_py.rt` uses `libasound.so.2` through `ctypes` for sequencer output.
- ALSA event conversion currently supports channel voice events and variable
  length SysEx payloads.
- Output port is created as a writable source port so other ALSA clients can
  subscribe.
- Destination listing uses `snd_seq_query_next_client` and
  `snd_seq_query_next_port`.
- The UI can auto-connect to destinations whose names look like QSynth,
  FluidSynth, or Fluid.
- If ALSA fails, the app shows a status bar message and uses dummy output.
- `dmidiplayer_py.settings` uses Qt AppConfigLocation, so Linux paths normally
  look like `~/.config/dmidiplayer/dmidiplayer-py/settings.ini` and Windows uses
  AppData/equivalent.
- The current toolbar is minimal: open, previous, play, pause, stop, next.
- Tone/tempo/volume/bar navigation/direct bar jump/loop/MIDI destination
  controls live in compact rows inside the main panel to avoid overloading the
  toolbar or making the window unnecessarily wide.

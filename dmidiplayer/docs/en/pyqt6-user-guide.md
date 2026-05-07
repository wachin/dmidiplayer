# dmidiplayer PyQt6 User Guide

This guide explains the current PyQt6 interface in plain language. It is meant
to help you understand what each visible control does in the Python port as it
exists today.

## Main Window

The main window is split into two areas:

- `List`: the playlist. It shows the MIDI files queued for playback.
- Playback area: song information, position slider, playback controls, rhythm
  panel, MIDI destination row, keyboard view, and status text.

If no file is loaded yet, the window starts in an empty state and waits for you
to open a MIDI file or playlist.

## File Menu

- `Open`: open one or more MIDI files or a `.lst` playlist file.
- `Open Playlist`: open a plain-text playlist file directly.
- `Open Recent`: reopen a recently loaded MIDI file.
- `Save Playlist`: save the current playlist to the current `.lst` file.
- `Save Playlist As`: save the current playlist to a new `.lst` file.
- `Move Up`: move the selected playlist row one step earlier.
- `Move Down`: move the selected playlist row one step later.
- `Sort Playlist`: sort the playlist alphabetically by file name.
- `Remove Selected`: remove the selected row from the playlist.
- `Clear Playlist`: remove every row from the playlist and unload the current
  song.
- `Exit`: close the application.

## Playback Menu

- `Previous`: load the previous playlist entry.
- `Play`: start playback from the current position.
- `Pause`: pause playback and keep the current position.
- `Stop`: stop playback and return to the beginning.
- `Next`: load the next playlist entry.
- `Bar -`: jump to the beginning of the previous bar.
- `Bar +`: jump to the beginning of the next bar.
- `Go`: jump to the bar number shown in the `Jump bar` control.
- `Repeat Playlist`: when playback reaches the last song, continue from the
  first one.
- `Shuffle Playlist`: choose the next playlist song randomly instead of in
  order.
- `Auto-Play On Load`: start playback automatically after loading a file.
- `Playlist Auto-Advance`: automatically continue to the next playlist item
  when a song finishes.

## View Menu

- `Channels`: open the channel activity window.
- `Lyrics`: open the text and lyrics window for the current song.
- `Toolbar`: show or hide the main toolbar.
- `Status bar`: show or hide the status bar at the bottom.
- `Keyboard`: show or hide the piano keyboard view.
- `Rhythm`: show or hide the rhythm panel.

## Tools Menu

- `Preferences`: open the current preferences dialog.
- `Refresh MIDI Destinations`: rescan the available MIDI outputs.
- `Connect MIDI Destination`: connect the selected MIDI destination.
- `Disconnect MIDI Destinations`: disconnect all currently connected MIDI
  destinations.

## Help Menu

- `Help Contents`: open the general local help index.
- `User Guide`: open this guide.
- `About`: show project credits, clickable author links, license information,
  and the main technologies used in the Python/PyQt6 port.

## Toolbar

The toolbar exposes the main everyday actions:

- `Open`
- `Previous`
- `Play`
- `Pause`
- `Stop`
- `Next`

These are the quickest way to navigate and control playback once files are
loaded.

## Playlist Area

The `List` on the left is the current playlist.

- Single-click a row to select it.
- Double-click a row to load that song.
- Opening multiple MIDI files creates a temporary playlist automatically.
- Opening a `.lst` playlist loads that saved playlist.
- Duplicate rows are avoided by default. If you open a file that is already in
  the playlist, the existing row is reused.

If the window title shows a `*` before the playlist file name, the playlist has
unsaved changes.

## Song Information

The text line above the position slider shows a summary of the loaded file:

- file title
- MIDI format
- track count
- total tick length
- approximate duration in seconds

## Position Slider And Time Line

The horizontal slider shows the current playback position.

- Drag it to seek to a different point in the song.
- The line below it shows:
  - current time
  - total time
  - effective BPM
  - current bar and total bar count

## Playback Controls In The Main Panel

The first control row contains:

- `Pitch`: transpose the song between `-12` and `+12` semitones.
- `0`: reset pitch to normal.
- `Drums`: choose which MIDI channel should be treated as percussion and left
  untransposed.
- `Tempo`: scale playback speed from `50%` to `200%`.
- `100%` next to `Tempo`: reset tempo to normal speed.
- `Volume`: scale MIDI CC7 volume from `0%` to `200%`.
- `100%` next to `Volume`: reset volume to normal.
- `Bar -`: jump to the previous bar.
- `Bar +`: jump to the next bar.

## Jump And Loop Controls

The second control row contains:

- `Jump bar`: choose a target bar number.
- `Go`: seek directly to the chosen bar.
- `Loop`: enable or disable looping.
- `Start bar`: first bar in the loop range.
- `End bar`: last bar in the loop range.

When `Loop` is enabled, playback repeats between `Start bar` and `End bar`.

## Rhythm Panel

The rhythm panel shows live musical position information:

- current time signature, for example `4/4`
- current bar number
- current beat number
- current BPM
- a beat strip where the active beat is highlighted

This panel updates while the song plays and also when you seek manually.

## Channels Window

The `Channels` window is opened from the `View` menu. It shows one row for each
MIDI channel used by the loaded song.

Each row currently includes:

- `Channel`: the MIDI channel number
- `Label`: an editable text label for that channel
- `Mute`: silences that channel during playback
- `Solo`: keeps that channel at full level while reducing the others according
  to the current solo reduction preference
- `Program`: sends a program change for that channel and overrides later
  program-change events from the file. The selector now shows General MIDI
  instrument names instead of only raw program numbers
- `Lock`: ignores later program changes from the file for that channel
- `Volume`: adjusts the playback level for that channel from `0%` to `200%`
- `Level`: a live activity meter that follows note velocity while playback runs

This is still an early Python port slice of the channels view, so there are
still richer channel behaviors pending.

## Piano Player Window

The `Piano Player` window is opened from the `View` menu.

This first slice shows only MIDI-bearing tracks from the loaded file. Tracks
are split across tabs with up to 8 tracks per tab:

- the first tab opens by default
- tracks 1-8 appear in the first tab
- tracks 9-16 appear in the second tab when needed
- later tracks continue in a third tab when needed

Each visible row shows a track label, a channel summary, and a keyboard.
During playback, note activity is reflected in the keyboards for tracks whose
MIDI channels are active.

Each row also has a `Show` checkbox so you can collapse that track's keyboard
without removing the track heading. The window includes `Show All` and `Hide
All` buttons for quick visibility changes across every displayed track.

The window also includes a `Fullscreen` button. Press `Esc` to leave
fullscreen mode quickly.

In the current slice, each track keyboard is narrowed to the note range that
track actually uses, so low and high parts do not all share the same oversized
span.

Use the `Range` selector to switch between the exact note span of each track
and `Used octaves`, which expands the display to complete octaves for a more
comfortable reading layout.

Use the `Labels` selector to choose how note names appear on the keys:
`Never`, `Minimal`, `When active`, or `Always`.

Use the `Octaves` selector to choose the octave numbering convention for those
labels. The current options are `Scientific` and `Yamaha`.

Use the `Colors` selector to keep the current blue palette or switch to
`By channel`, which gives each track keyboard a channel-based color family.

The keyboard widget now includes black keys as part of that reduced range, so
the track view reads more like a real piano layout.

Active notes are also tinted by velocity, so softer and stronger hits are a
little easier to distinguish at a glance during playback.

## Lyrics Window

The `Lyrics` window is opened from the `View` menu. It shows text-related MIDI
meta events from the loaded song.

The filter at the top lets you switch between:

- `All tracks`
- `Track 1`, `Track 2`, and so on for tracks that contain text
- `All`
- `Lyrics`
- `Text`
- `Marker`
- `Cue Point`
- `Other`

When a file has text in multiple tracks, the window automatically starts on the
track that contains lyric meta events when one exists. If the file has text but
no dedicated lyric track, it falls back to the track with the most text events.
Switching back to `All tracks` shows the track number before each line so mixed
sources stay readable.

The `Encoding` selector controls how embedded MIDI text is decoded in the
window. `Auto` uses the built-in guesser, while `UTF-8`, `Latin-1`, and
`CP1252` let you override the display manually.

Use `Save` to write the currently filtered text to a file. When `Auto` is
selected, files are saved as `UTF-8`; otherwise the selected encoding is used.

Use `Print` to send the currently filtered text to a printer through the
standard Qt print dialog.

Use `Copy` to place the currently filtered text into the clipboard. Use `Font`
to choose a more comfortable display font for the lyrics pane. Use
`Fullscreen` to expand the lyrics window for rehearsal or singing along, and
press `Esc` to return to the normal window.

During playback, the visible lines are highlighted by state: earlier lines fade,
the current line is emphasized, and upcoming lines remain easy to spot.

## MIDI Destination Row

This row controls where MIDI events are sent:

- `MIDI destination`: choose a detected output port.
- `Refresh MIDI Destinations`: rescan ports.
- `Connect MIDI Destination`: connect the selected port.
- `Disconnect MIDI Destinations`: disconnect every connected port.

Remember that a MIDI player sends MIDI events, not audio. You still need a
software or hardware synthesizer connected to hear sound.

## Keyboard View

The keyboard view highlights notes as they are played. It is a compact visual
reference for incoming note activity.

## Status Bar

The status bar reports what the app is doing, for example:

- `Loading ...`
- `Ready: ...`
- `Playing`
- `Paused`
- `Stopped`
- `End of sequence`
- MIDI or file-loading errors

## Preferences Dialog

The current `General` tab includes:

- `Percussion channel`: the channel treated as drums.
- `Solo volume reduction`: reserved setting for upcoming channel-solo behavior.
- `Auto-play after loading a file`
- `Auto-advance to the next playlist item`
- `Send GM reset before playback`
- `Restore Defaults`: return the visible options to their default values.

## Useful Shortcuts

- `Ctrl+O`: Open
- `Space`: Play
- `P`: Pause
- `Esc`: Stop
- `Ctrl+Left`: Previous song
- `Ctrl+Right`: Next song
- `Alt+Left`: Previous bar
- `Alt+Right`: Next bar
- `Alt+Up`: Move selected playlist row up
- `Alt+Down`: Move selected playlist row down
- `Ctrl+J`: Jump to the selected bar

## Current Limits

This PyQt6 port is already useful, but some parts of the original application
are still being ported. In particular, channel editing, lyrics, advanced player
piano views, and song-specific settings are not complete yet.

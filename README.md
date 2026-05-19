# dmidiplayer PyQt6 port

This repository contains an ongoing port of Drumstick/dmidiplayer to Qt/Python
with PyQt6. The original C++ code is kept as a reference, and the Python version
lives in parallel packages inside the same source tree:

- `drumstick/drumstick_py`
- `dmidiplayer/dmidiplayer_py`

If the project is eventually prepared for Debian packaging, see
`Debian-Packaging-Notes.md` for repository-specific notes about archive
compatibility, format support, and licensing concerns.

## Current Test Environment

Manual testing is currently being done on MX Linux 23.

On that system, the RT kernel available from the MX Linux 23 repositories was
installed and configured together with the packages used during this migration,
including PyQt6, ALSA, and MIDI utilities.

For real MIDI playback, the test system also has:

- QjackCtl
- QSynth
- `fluid-soundfont-gm`

The soundfont used for testing is `FluidR3.sf2`, installed by the
`fluid-soundfont-gm` package. It is loaded in QSynth through the `Soundfonts`
configuration page.

With QjackCtl running and QSynth open, dmidiplayer PyQt6 can send MIDI events
through ALSA sequencer to QSynth. The application also includes an ALSA MIDI
destination selector so the output can be connected directly from the UI.

## Dependencies

Dependencies needed so far on MX Linux 23 / Debian 12:

```bash
sudo apt install python3-pyqt6 python3-alsaaudio alsa-utils
```

For good-quality MIDI playback through QSynth/FluidSynth:

```bash
sudo apt install qjackctl qsynth fluidsynth fluid-soundfont-gm
```

Packages used or expected during the migration:

```bash
sudo apt install uchardet pandoc pyqt6-dev-tools qt6-tools-dev-tools qttools5-dev-tools qtchooser linguist-qt6
```

The current tests use Python `unittest`, so `pytest` is not required yet. Later
these packages may be useful:

```bash
sudo apt install python3-pytest python3-pytestqt
```

Notes:

- `alsa-utils` provides `aconnect`, which is useful for inspecting ALSA MIDI
  ports.
- `python3-alsaaudio` is used only for PCM/card diagnostics. ALSA sequencer MIDI
  output is implemented with `ctypes` over `libasound.so.2`.
- ALSA sequencer requires `/dev/snd/seq`. If `aconnect -lo` fails with
  `open /dev/snd/seq failed`, the `snd-seq` kernel module usually needs to be
  loaded.
- `fluid-soundfont-gm` installs `FluidR3.sf2`, which can be loaded in QSynth
  from `Soundfonts`.
- `pyqt6-dev-tools` provides `pylupdate6` to extract translatable strings from
  Python code.
- `qt6-tools-dev-tools` / `qttools5-dev-tools` and `qtchooser` provide Qt
  Linguist and `lrelease`/`lupdate`, depending on the local Qt setup.
- MX Linux also provides `linguist-qt6`, which installs Qt Linguist for visually
  editing `.ts` files.

## Internationalization

The source language of the UI is English. The application loads compiled Qt
translations (`.qm`) from:

```text
dmidiplayer/dmidiplayer_py/translations/
```

English is used by default:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/test.mid
```

To request another language:

```bash
./dmidiplayer/dmidiplayer-py --language es dmidiplayer/examples/test.mid
./dmidiplayer/dmidiplayer-py --language system dmidiplayer/examples/test.mid
```

Portable settings are also available:

```bash
./dmidiplayer/dmidiplayer-py --portable dmidiplayer/examples/test.mid
./dmidiplayer/dmidiplayer-py --file my-portable.conf dmidiplayer/examples/test.mid
./dmidiplayer/dmidiplayer-py --driver dummy --connection "Practice Port" dmidiplayer/examples/test.mid
```

If the requested `.qm` file does not exist, the application falls back to
English.

Translation workflow with Qt Linguist:

```bash
pylupdate6 dmidiplayer/dmidiplayer_py --ts dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.ts
linguist dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.ts
lrelease dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.ts -qm dmidiplayer/dmidiplayer_py/translations/dmidiplayer_py_es.qm
```

After saving and compiling the `.qm`, run:

```bash
./dmidiplayer/dmidiplayer-py --language es dmidiplayer/examples/test.mid
```

## How To Test

Use one of the `.mid` files under `dmidiplayer/examples`, for example:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/test.mid
```

The current parser also accepts RIFF-wrapped MIDI files such as `.rmi`.

Another useful example:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/mozart_diesirae.mid
```

There is also a bundled example playlist with several songs:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/examples.lst
```

You can open the same curated set from the app with `File -> Open Example Playlist`.

Several files can also be passed at once. They become a temporary playlist, and
`Previous` / `Next` navigate through it:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/test.mid dmidiplayer/examples/haendel_hallelujah.mid
```

The application window should open and playback should be available:

![](vx_images/01-dmidiplayer_port-qt_py.png)

Other examples:

```bash
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/Schubert_Standchen.mid
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/haendel_hallelujah.mid
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/mozart_aveverum.mid
```

Run these commands from the repository root:

```bash
cd /home/wachin/Dev/dmidiplayer
./dmidiplayer/dmidiplayer-py dmidiplayer/examples/test.mid
```

If QSynth is already open, the app tries to connect automatically to a
destination that looks like QSynth/FluidSynth. If it does not, use the `MIDI
destination` selector, press `Refresh`, and then press `Connect`.

Below the position slider there are initial controls split across two rows: one
for `Pitch`, `Tempo`, `Volume`, and bar navigation, and another for direct
bar jump plus the basic bar-based loop.

`Pitch` transposes between -12 and +12 semitones without changing the GM
percussion channel 10. `Tempo` plays between 50% and 200% of the original speed.
`Volume` sends MIDI CC7 to channels and scales CC7 events from the file between
0% and 200%. `Loop` repeats the range between `Start bar` and `End bar`. The top
toolbar is reserved for primary actions such as open, playlist navigation, play,
pause, and stop. The line below the slider shows current/total time, effective
BPM, and current/total bar. `Bar -` and `Bar +` jump to the beginning of the
previous or next bar. `Jump bar` plus `Go` seeks directly to the requested bar.

## Configuration

The application stores its configuration in the location selected by Qt
(`QStandardPaths.AppConfigLocation`).

## Desktop Integration

The repository already includes a desktop launcher definition for the PyQt6
port:

```text
dmidiplayer/org.dmidiplayer.dmidiplayer.desktop
```

It is configured to start the current launcher script:

```text
Exec=dmidiplayer-py %F
```

and advertises MIDI, Karaoke, and Cakewalk file associations for future
packaging work.

For local desktop integration from the current checkout, run:

```bash
./tools/install-local-desktop.sh
```

That helper installs:

- a desktop file under `~/.local/share/applications/`
- application icons under `~/.local/share/icons/hicolor/`

using the current repository launcher path.

On Linux this is normally equivalent to:

```text
~/.config/dmidiplayer/dmidiplayer-py/settings.ini
```

When `--portable` is used, settings are stored beside the launcher in a local
portable config file such as `dmidiplayer-py.conf`. When `--file name.conf` is
used, that portable config file name or path is used instead.

On Windows it corresponds to the user's AppData location, normally under
`%AppData%` or the equivalent path selected by Qt. The app currently stores the
last folder visited by the `Open MIDI` dialog, so the next file picker starts
there.

## Quick Verification

```bash
./dmidiplayer/dmidiplayer-py --help
PYTHONPATH=drumstick:dmidiplayer python3 -m compileall drumstick/drumstick_py dmidiplayer/dmidiplayer_py tests
PYTHONPATH=drumstick:dmidiplayer python3 -m unittest tests.test_smf_parser tests.test_alsa_event tests.test_sequence_player tests.test_i18n tests.test_settings tests.test_app_playlist
```

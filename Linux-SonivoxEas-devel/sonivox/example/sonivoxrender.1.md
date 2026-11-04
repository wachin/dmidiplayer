% SONIVOXRENDER(1) sonivoxrender 0.0.0 | Sonivox MIDI File Renderer
% Pedro López-Cabanillas <plcl@users.sf.net>

# NAME

**sonivoxrender** — Render standard MIDI files into raw PCM audio

# SYNOPSIS

| **sonivoxrender** [**-h|-\-help**] [**-v|-\-version**] [**-d|-\-dls** _soundfont_] [**-r|-\-reverb** _0..4_] [**-w|-\-wet** _0..32767_] [**-n|-\-dry** _0..32767_] [**-c|-\-chorus** _0..4_] [**-l|-\-level** _0..32767_] [**-g|-\-gain** _0..196_] [**-V|-\-Verbosity** _0..5_] [**-R|-\-reverb-post-mix**] [**-C|-\-chorus-post-mix**] [**-s|-\-sndlib** _1..3_] _midi_file_

# DESCRIPTION

This program is a MIDI file renderer based on the sonivox synthesizer library.
It reads .MID (Standard MIDI Files) file format, and writes an audio stream to the standard output as raw 16 bit stereo PCM samples.

## Options

-h, -\-help

:   Prints brief usage information.

-v, -\-version

:   Prints the version numbers.

-d, -\-dls  _soundfont_

:   Optional DLS or SF2 soundfont file name. If not provided, it uses an internal embedded soundfont.

-r, -\-reverb  _reverb_preset_

:   Reverb preset between 0 and 4: 0=no, 1=large hall, 2=hall, 3=chamber, 4=room.

-w, -\-wet  _reverb_wet_

:   Reverb wet level between 0 and 32767.

-n, -\-dry  _reverb_dry_

:   Reverb dry level between 0 and 32767.

-c, -\-chorus  _chorus_preset_

:   Chorus preset between 0 and 4: 0=no, 1..4=presets.

-l, -\-level _chorus_level_

:   Chorus level between 0 and 32767.

-g, -\-gain _master_gain_

:   Master gain between 0 and 196, default is 100 (+0dB). The number is relative to 100, in 1dB increments, e.g. 120 = +20dB, 80 = -20dB.

-V, -\-Verbosity _verbosity_

:   Verbosity level between 0 and 5, where 0=no, 1..5=severity levels.

-R, -\-reverb-post-mix

:   Ignore CC91 reverb send level. The reverb effect will apply to mixed output audio, which is the old behavior.

-C, -\-chorus-post-mix

:   Ignore CC93 chorus send level. See also **-\-reverb-post-mix**.

-s, -\-sndlib _index_

:   EAS sound library to use:

    * 1: wt_200k_G (default) - WT-only bank, used in Android devices. Also named "Common".
        Support 22050 Hz and 44100 Hz sample rates, 8-bit and 16-bit samples.
    * 2: GMdblib-3 - FM-only bank. Support all sample rates. Sample bit depth does not matter here.
    * 3: hybrid_22khz_mcu - Hybrid bank. Use WT synth for drums and FM for melodic instruments.
        This bank is a combination of `GMdblib-3` and `Sonic_20Khz_Drums`.
        Support 22050 Hz sample rate and 8-bit samples only.

    **Note:** This option does not affect DLS/SF2. They will always use the DLS synth engine. If the selected sound library is not compatible with the build configuration, the program will fail with an error message.

## Arguments

_midi_file_

:   Input MID file name.

# EXAMPLES

The following examples assume the default option USE_44KHZ=ON, which means an output sample rate = 44100 Hz.

Example 1: Render a MIDI file and save the rendered audio as a raw audio file:

    $ sonivoxrender ants.mid > ants.pcm

Example 2: pipe the rendered audio thru the Linux ALSA **aplay** utility:

    $ sonivoxrender ants.mid | aplay -c 2 -f S16_LE -r 44100

is equivalent to:

    $ sonivoxrender ants.mid | aplay -f cd

Example 3: pipe the rendered audio thru the **lame** utility creating a MP3 file:

    $ sonivoxrender ants.mid | lame -r -s 44100 - ants.mp3

Example 4: pipe the rendered audio thru the **sox** utility creating a WAV file:

    $ sonivoxrender ants.mid | sox -t s16 -c 2 -r 44100 - ants.wav

Example 5: pipe the rendered audio thru the PulseAudio's **pacat** utility:

    $ sonivoxrender ants.mid | pacat

Example 6: pipe the rendered audio thru the PipeWire's **pw-play** utility:

    $ sonivoxrender ants.mid | pw-play --rate 44100 -

# BUGS

See Tickets at GitHub <https://github.com/pedrolcl/sonivox/issues/>

# LICENSE AND COPYRIGHT

Licensed under the Apache License, Version 2.0

Copyright (c) 2022-2025 Pedro López-Cabanillas and contributors

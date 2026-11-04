"""FluidSynth realtime MIDI output backend for the PyQt6 port.

This mirrors Drumstick's ``FluidSynth`` RT backend
(``drumstick/library/rt-backends/fluidsynth``): a FluidSynth instance is
created inside the application, a General MIDI SoundFont is loaded, and MIDI
events are sent directly to ``fluid_synth_*`` functions.

The internal synth avoids depending on an external QSynth instance, its
SoundFont, or its current bank-select/channel-type state.  In particular the
percussion channel is explicitly kept in FluidSynth's DRUM mode so a drum
track cannot turn into a melodic part after a bank-select reset.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .rt import MidiConnection, MidiOutputError

FLUID_OK = 0
CHANNEL_TYPE_MELODIC = 0
CHANNEL_TYPE_DRUM = 1
DRUM_CHANNEL_INDEX = 9

_SOUNDFONT_CANDIDATES = (
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/default-GM.sf2",
    "/usr/share/sounds/sf2/default.sf2",
    "/usr/share/sounds/sf2/FluidR3.sf2",
)


def fluidsynth_available() -> bool:
    """Return True when libfluidsynth can be loaded on this host."""
    try:
        _FluidSynthLib()
    except Exception:
        return False
    return True


def default_soundfont_path() -> Path | None:
    """Return the SoundFont FluidSynth should load, or None.

    Explicit overrides, in order:
      * ``DMIDIPLAYER_SOUNDFONT``
      * ``$XDG_DATA_HOME/sounds/sf2/*.sf2``
      * ``~/.local/share/sounds/sf2/*.sf2``
      * the standard Debian/General MIDI locations.
    """
    explicit = os.environ.get("DMIDIPLAYER_SOUNDFONT", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    for candidate in _SOUNDFONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    data_home = os.environ.get("XDG_DATA_HOME", "").strip()
    search_dirs = []
    if data_home:
        search_dirs.append(Path(data_home) / "sounds" / "sf2")
    search_dirs.extend(
        [
            Path.home() / ".local" / "share" / "sounds" / "sf2",
            Path.home() / "soundfonts",
            Path.home() / "SoundFonts",
        ]
    )
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.sf2")):
            if path.is_file():
                return path
    return None


class _FluidSynthLib:
    """Thin ctypes binding for the subset of libfluidsynth we use."""

    def __init__(self) -> None:
        last_error: OSError | None = None
        for name in (
            "libfluidsynth.so.3",
            "libfluidsynth.so.2",
            "libfluidsynth.dylib",
            "fluidsynth.dll",
            "libfluidsynth.dll",
        ):
            try:
                self.lib = ctypes.CDLL(name)
                break
            except OSError as exc:
                last_error = exc
        else:
            raise MidiOutputError(f"FluidSynth library not found: {last_error}")
        self._setup_prototypes()

    def _setup_prototypes(self) -> None:
        lib = self.lib
        lib.new_fluid_settings.restype = ctypes.c_void_p
        lib.delete_fluid_settings.argtypes = [ctypes.c_void_p]
        lib.delete_fluid_settings.restype = None
        lib.fluid_settings_setstr.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.fluid_settings_setstr.restype = ctypes.c_int
        lib.fluid_settings_setint.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.fluid_settings_setint.restype = ctypes.c_int
        lib.fluid_settings_setnum.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double]
        lib.fluid_settings_setnum.restype = ctypes.c_int
        lib.new_fluid_synth.argtypes = [ctypes.c_void_p]
        lib.new_fluid_synth.restype = ctypes.c_void_p
        lib.delete_fluid_synth.argtypes = [ctypes.c_void_p]
        lib.delete_fluid_synth.restype = None
        lib.fluid_synth_sfload.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.fluid_synth_sfload.restype = ctypes.c_int
        lib.fluid_synth_sfunload.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int]
        lib.fluid_synth_sfunload.restype = ctypes.c_int
        lib.new_fluid_audio_driver.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.new_fluid_audio_driver.restype = ctypes.c_void_p
        lib.delete_fluid_audio_driver.argtypes = [ctypes.c_void_p]
        lib.delete_fluid_audio_driver.restype = None
        lib.fluid_synth_system_reset.argtypes = [ctypes.c_void_p]
        lib.fluid_synth_system_reset.restype = ctypes.c_int
        lib.fluid_synth_set_channel_type.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_set_channel_type.restype = ctypes.c_int
        lib.fluid_synth_noteon.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_noteon.restype = ctypes.c_int
        lib.fluid_synth_noteoff.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_noteoff.restype = ctypes.c_int
        lib.fluid_synth_cc.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_cc.restype = ctypes.c_int
        lib.fluid_synth_program_change.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_program_change.restype = ctypes.c_int
        lib.fluid_synth_bank_select.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_bank_select.restype = ctypes.c_int
        lib.fluid_synth_pitch_bend.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_pitch_bend.restype = ctypes.c_int
        lib.fluid_synth_channel_pressure.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_channel_pressure.restype = ctypes.c_int
        lib.fluid_synth_key_pressure.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.fluid_synth_key_pressure.restype = ctypes.c_int
        lib.fluid_synth_all_notes_off.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.fluid_synth_all_notes_off.restype = ctypes.c_int
        lib.fluid_synth_all_sounds_off.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.fluid_synth_all_sounds_off.restype = ctypes.c_int
        lib.fluid_synth_sysex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
        ]
        lib.fluid_synth_sysex.restype = ctypes.c_int
        lib.fluid_synth_get_channel_preset.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.fluid_synth_get_channel_preset.restype = ctypes.c_void_p
        lib.fluid_preset_get_name.argtypes = [ctypes.c_void_p]
        lib.fluid_preset_get_name.restype = ctypes.c_char_p
        lib.fluid_preset_get_banknum.argtypes = [ctypes.c_void_p]
        lib.fluid_preset_get_banknum.restype = ctypes.c_int
        lib.fluid_preset_get_num.argtypes = [ctypes.c_void_p]
        lib.fluid_preset_get_num.restype = ctypes.c_int


class FluidSynthOutput(QObject):
    """A self-contained FluidSynth MIDI output, like Drumstick's backend."""

    eventSent = pyqtSignal(object)
    driver = "fluidsynth"

    AUDIO_DRIVERS = ("pulseaudio", "pipewire", "alsa", "jack")

    def __init__(
        self,
        name: str = "FluidSynth",
        parent: QObject | None = None,
        *,
        soundfont: str | Path | None = None,
        audio_driver: str | None = None,
        start_audio: bool = True,
        percussion_channel: int = 9,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self._lib = _FluidSynthLib()
        self._settings: int | None = None
        self._synth: int | None = None
        self._driver: int | None = None
        self._soundfont_id = -1
        self._percussion_channel = percussion_channel
        self.audio_driver = ""
        chosen = Path(soundfont).expanduser() if soundfont else default_soundfont_path()
        if chosen is None or not chosen.is_file():
            raise MidiOutputError(
                "No General MIDI SoundFont was found. Set DMIDIPLAYER_SOUNDFONT "
                "or install /usr/share/sounds/sf2/FluidR3_GM.sf2."
            )
        self.soundfont = str(chosen)
        self._initialize(
            audio_driver=audio_driver
            or os.environ.get("DMIDIPLAYER_FLUIDSYNTH_AUDIO", "").strip()
            or None,
            start_audio=start_audio,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _initialize(self, *, audio_driver: str | None, start_audio: bool) -> None:
        lib = self._lib.lib
        settings = lib.new_fluid_settings()
        if not settings:
            raise MidiOutputError("Could not create FluidSynth settings")
        self._settings = settings
        try:
            lib.fluid_settings_setnum(settings, b"synth.sample-rate", 48_000.0)
            lib.fluid_settings_setint(settings, b"synth.polyphony", 256)
            lib.fluid_settings_setint(settings, b"synth.reverb.active", 1)
            lib.fluid_settings_setint(settings, b"synth.chorus.active", 0)
            # Drumstick's FluidSynth backend defaults to Gain 1.0.  FluidSynth
            # itself defaults to 0.2, which would make the internal output much
            # quieter than QSynth or the C++ application.
            lib.fluid_settings_setnum(settings, b"synth.gain", 1.0)
            # FluidSynth's default bank-select style, matching the C++
            # backend.  The percussion channel is forced to DRUM separately.
            lib.fluid_settings_setstr(settings, b"synth.midi-bank-select", b"gs")
            lib.fluid_settings_setint(settings, b"audio.period-size", 512)
            lib.fluid_settings_setint(settings, b"audio.periods", 8)
            synth = lib.new_fluid_synth(settings)
            if not synth:
                raise MidiOutputError("Could not create the FluidSynth synthesizer")
            self._synth = synth
            soundfont_id = lib.fluid_synth_sfload(synth, self.soundfont.encode(), 1)
            if soundfont_id < 0:
                raise MidiOutputError(f"Could not load SoundFont: {self.soundfont}")
            self._soundfont_id = soundfont_id
            # Establish a known GM state.  This also restores the drum channel
            # after a previous XG/bank-select experiment.
            lib.fluid_synth_system_reset(synth)
            self._apply_channel_types()
            if start_audio:
                self._start_audio(settings, synth, audio_driver)
        except Exception:
            self.close()
            raise

    def _start_audio(self, settings: int, synth: int, requested: str | None) -> None:
        lib = self._lib.lib
        candidates = []
        if requested:
            candidates.append(requested)
        for candidate in self.AUDIO_DRIVERS:
            if candidate not in candidates:
                candidates.append(candidate)
        errors: list[str] = []
        for candidate in candidates:
            lib.fluid_settings_setstr(settings, b"audio.driver", candidate.encode())
            driver = lib.new_fluid_audio_driver(settings, synth)
            if driver:
                self._driver = driver
                self.audio_driver = candidate
                return
            errors.append(candidate)
        raise MidiOutputError(
            "FluidSynth could not open an audio driver. Tried: "
            + ", ".join(errors)
            + ". Set DMIDIPLAYER_FLUIDSYNTH_AUDIO to a valid driver."
        )

    def close(self) -> None:
        lib = self._lib.lib
        if self._driver:
            lib.delete_fluid_audio_driver(self._driver)
            self._driver = None
        if self._synth:
            lib.delete_fluid_synth(self._synth)
            self._synth = None
        if self._settings:
            lib.delete_fluid_settings(self._settings)
            self._settings = None

    def __del__(self) -> None:  # pragma: no cover - best effort
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Channel state
    # ------------------------------------------------------------------
    def reset_for_new_song(self) -> None:
        """Reset FluidSynth state before the first event of a new song.

        Programs, banks, channel types, controllers, pitch bend and active
        voices otherwise survive between files.  A previous GS/XG file could
        leave a melodic channel on an unusable bank or a drum channel marked as
        melodic, making the next song sound incomplete until the application
        was restarted.
        """
        if not self._synth:
            return
        self._lib.lib.fluid_synth_system_reset(self._synth)
        self._apply_channel_types()

    def set_percussion_channel(self, channel: int) -> None:
        """Force the configured channel to DRUM and the old one to MELODIC."""
        channel = max(0, min(15, int(channel)))
        if channel == self._percussion_channel or not self._synth:
            return
        lib = self._lib.lib
        old_channel = self._percussion_channel
        lib.fluid_synth_set_channel_type(self._synth, old_channel, CHANNEL_TYPE_MELODIC)
        lib.fluid_synth_bank_select(self._synth, old_channel, 0)
        lib.fluid_synth_program_change(self._synth, old_channel, 0)
        self._percussion_channel = channel
        lib.fluid_synth_set_channel_type(self._synth, channel, CHANNEL_TYPE_DRUM)
        lib.fluid_synth_bank_select(self._synth, channel, 128)
        lib.fluid_synth_program_change(self._synth, channel, 0)

    def _apply_channel_types(self) -> None:
        """Keep the configured percussion channel in DRUM mode.

        Other channels are deliberately left alone: GS/XG files can use
        additional drum channels, and forcing them melodic would break those
        arrangements.
        """
        if not self._synth:
            return
        lib = self._lib.lib
        channel = self._percussion_channel
        lib.fluid_synth_set_channel_type(self._synth, channel, CHANNEL_TYPE_DRUM)
        # Setting the type alone does not re-select a preset.  If the
        # percussion channel currently points at a melodic bank, move it back
        # to the GM drum bank.
        if self.channel_preset_bank(channel) != 128:
            lib.fluid_synth_bank_select(self._synth, channel, 128)
            lib.fluid_synth_program_change(self._synth, channel, 0)

    # ------------------------------------------------------------------
    # MIDI
    # ------------------------------------------------------------------
    def send_event(self, event: object) -> None:
        if not self._synth:
            raise MidiOutputError("FluidSynth output is closed")
        kind = getattr(event, "kind", "")
        channel = getattr(event, "channel", None)
        data = bytes(getattr(event, "data", b""))
        lib = self._lib.lib
        synth = self._synth
        if channel is None:
            if kind == "sysex":
                payload = data
                if payload.startswith(b"\xf0"):
                    payload = payload[1:]
                if payload.endswith(b"\xf7"):
                    payload = payload[:-1]
                if payload:
                    lib.fluid_synth_sysex(synth, payload, len(payload), None, None, None, 0)
                # Some files switch to XG/GS mode; keep the drum channel safe.
                self._apply_channel_types()
            return
        if kind == "note_on" and len(data) >= 2:
            if data[1] == 0:
                lib.fluid_synth_noteoff(synth, channel, data[0])
            else:
                lib.fluid_synth_noteon(synth, channel, data[0], data[1])
        elif kind == "note_off" and len(data) >= 2:
            lib.fluid_synth_noteoff(synth, channel, data[0])
        elif kind == "key_pressure" and len(data) >= 2:
            lib.fluid_synth_key_pressure(synth, channel, data[0], data[1])
        elif kind == "control_change" and len(data) >= 2:
            controller = data[0]
            # Bank Select on the percussion channel is meaningless in GM and
            # is what can turn channel 10 melodic in other modes.
            if channel == self._percussion_channel and controller in (0, 32):
                return
            lib.fluid_synth_cc(synth, channel, controller, data[1])
        elif kind == "program_change" and data:
            if channel == self._percussion_channel:
                lib.fluid_synth_set_channel_type(synth, channel, CHANNEL_TYPE_DRUM)
                if self.channel_preset_bank(channel) != 128:
                    lib.fluid_synth_bank_select(synth, channel, 128)
            lib.fluid_synth_program_change(synth, channel, data[0])
        elif kind == "channel_pressure" and data:
            lib.fluid_synth_channel_pressure(synth, channel, data[0])
        elif kind == "pitch_bend" and len(data) >= 2:
            value = ((data[1] << 7) | data[0]) - 8192
            lib.fluid_synth_pitch_bend(synth, channel, value)
        self.eventSent.emit(event)

    def all_notes_off(self) -> None:
        if not self._synth:
            return
        lib = self._lib.lib
        for channel in range(16):
            lib.fluid_synth_all_notes_off(self._synth, channel)
            lib.fluid_synth_all_sounds_off(self._synth, channel)
        self._apply_channel_types()

    # ------------------------------------------------------------------
    # UI compatibility (FluidSynth is not an ALSA destination)
    # ------------------------------------------------------------------
    def connections(self) -> list[MidiConnection]:
        return [MidiConnection(driver=self.driver, name=self.name)]

    def connected_connections(self) -> list[MidiConnection]:
        return self.connections()

    def current_connection(self) -> MidiConnection:
        return self.connections()[0]

    def connect_to(self, connection: object) -> None:
        # The internal synth is always active; selecting it is enough.
        return

    def disconnect_all(self) -> None:
        return

    # ------------------------------------------------------------------
    # Diagnostics/tests
    # ------------------------------------------------------------------
    def channel_preset_name(self, channel: int) -> str:
        if not self._synth:
            return ""
        preset = self._lib.lib.fluid_synth_get_channel_preset(self._synth, channel)
        if not preset:
            return ""
        name = self._lib.lib.fluid_preset_get_name(preset)
        return name.decode(errors="replace") if name else ""

    def channel_preset_bank(self, channel: int) -> int:
        if not self._synth:
            return -1
        preset = self._lib.lib.fluid_synth_get_channel_preset(self._synth, channel)
        if not preset:
            return -1
        return int(self._lib.lib.fluid_preset_get_banknum(preset))

    def channel_preset_program(self, channel: int) -> int:
        if not self._synth:
            return -1
        preset = self._lib.lib.fluid_synth_get_channel_preset(self._synth, channel)
        if not preset:
            return -1
        return int(self._lib.lib.fluid_preset_get_num(preset))

"""SonivoxEAS realtime MIDI output backend for the PyQt6 port.

This is a Python/ctypes port of Drumstick's ``eassynth`` backend
(``drumstick/library/rt-backends/eassynth``).  It uses the Sonivox EAS
wave-table synthesizer, which is the first MIDI output backend the C++
application prefers on Linux.  Sonivox has its own embedded General MIDI
samples, so this backend does not load a SoundFont file.

Audio is rendered by EAS in a worker thread and written to PulseAudio through
``libpulse-simple``, mirroring the C++ ``SynthRenderer``.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .rt import MidiConnection, MidiOutputError

# EAS result / constants
EAS_SUCCESS = 0
EAS_MODULE_REVERB = 2
EAS_MODULE_CHORUS = 3
EAS_PARAM_REVERB_BYPASS = 1
EAS_PARAM_REVERB_PRESET = 2
EAS_PARAM_REVERB_WET = 3
EAS_PARAM_REVERB_HALL = 1
EAS_PARAM_CHORUS_BYPASS = 0
EAS_PARAM_CHORUS_LEVEL = 4

# PulseAudio simple API constants
PA_STREAM_PLAYBACK = 1
PA_SAMPLE_S16LE = 3

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_LOCAL_SONIVOX_BUILD = _REPO_ROOT / "Linux-SonivoxEas-devel" / "build" / "sonivox"
_SONIVOX_PATHS = (
    # Prefer the system 3.x library: the C++ 1.7.5 AppImage bundles
    # libsonivox 3.6.15, so this is the closest sample set.
    "/usr/lib/x86_64-linux-gnu/libsonivox.so.3",
    "/usr/lib/aarch64-linux-gnu/libsonivox.so.3",
    "/usr/lib64/libsonivox.so.3",
    "/usr/local/lib/libsonivox.so.3",
    "/opt/homebrew/lib/libsonivox.so.3",
    "/usr/lib/x86_64-linux-gnu/libsonivox.so.4",
    "/usr/lib/aarch64-linux-gnu/libsonivox.so.4",
    "/usr/lib64/libsonivox.so.4",
    "/usr/local/lib/libsonivox.so.4",
    "/opt/homebrew/lib/libsonivox.so.4",
    # Locally built sonivox 4.x from the bundled source tree.
    _LOCAL_SONIVOX_BUILD / "libsonivox.so",
    _LOCAL_SONIVOX_BUILD / "libsonivox.so.4",
    _LOCAL_SONIVOX_BUILD / "libsonivox.so.3",
)


def _find_sonivox_library() -> str | None:
    explicit = os.environ.get("DMIDIPLAYER_SONIVOX_LIB", "").strip()
    if explicit and Path(explicit).is_file():
        return explicit
    found = ctypes.util.find_library("sonivox")
    if found:
        return found
    for candidate in _SONIVOX_PATHS:
        if Path(candidate).is_file():
            return str(candidate)
    return None


def sonivox_available() -> bool:
    """Return True when both libsonivox and libpulse-simple are loadable."""
    try:
        _EASLib()
        _PulseLib()
    except Exception:
        return False
    return True


class _EASLibConfigV3(ctypes.Structure):
    # Sonivox 3.x/older EAS: EAS_U32/EAS_I32 are unsigned long/long,
    # i.e. 64-bit on x86-64 Linux.
    _fields_ = [
        ("libVersion", ctypes.c_ulong),
        ("checkedVersion", ctypes.c_uint),
        ("maxVoices", ctypes.c_long),
        ("numChannels", ctypes.c_long),
        ("sampleRate", ctypes.c_long),
        ("mixBufferSize", ctypes.c_long),
        ("filterEnabled", ctypes.c_uint),
        ("buildTimeStamp", ctypes.c_ulong),
        ("buildGUID", ctypes.c_char_p),
    ]


class _EASLibConfigV4(ctypes.Structure):
    # Sonivox 4.x: EAS_U32/EAS_I32 are uint32_t/int32_t.
    _fields_ = [
        ("libVersion", ctypes.c_uint32),
        ("checkedVersion", ctypes.c_uint32),
        ("maxVoices", ctypes.c_int32),
        ("numChannels", ctypes.c_int32),
        ("sampleRate", ctypes.c_int32),
        ("mixBufferSize", ctypes.c_int32),
        ("filterEnabled", ctypes.c_uint32),
        ("buildTimeStamp", ctypes.c_uint32),
        ("buildGUID", ctypes.c_char_p),
    ]


class _EASLib:
    def __init__(self) -> None:
        path = _find_sonivox_library()
        if not path:
            raise MidiOutputError(
                "SonivoxEAS library not found. Install the libsonivox3 package "
                "or set DMIDIPLAYER_SONIVOX_LIB."
            )
        self.lib = ctypes.CDLL(path)
        self.path = path
        lib = self.lib
        lib.EAS_Config.restype = ctypes.c_void_p
        lib.EAS_Init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        lib.EAS_Init.restype = ctypes.c_long
        lib.EAS_Shutdown.argtypes = [ctypes.c_void_p]
        lib.EAS_Shutdown.restype = ctypes.c_long
        lib.EAS_OpenMIDIStream.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
        ]
        lib.EAS_OpenMIDIStream.restype = ctypes.c_long
        lib.EAS_WriteMIDIStream.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
        ]
        lib.EAS_WriteMIDIStream.restype = ctypes.c_long
        lib.EAS_CloseMIDIStream.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.EAS_CloseMIDIStream.restype = ctypes.c_long
        lib.EAS_Render.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_short),
            ctypes.c_long,
            ctypes.POINTER(ctypes.c_long),
        ]
        lib.EAS_Render.restype = ctypes.c_long
        lib.EAS_SetParameter.argtypes = [
            ctypes.c_void_p,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_long,
        ]
        lib.EAS_SetParameter.restype = ctypes.c_long


class _PaSampleSpec(ctypes.Structure):
    _fields_ = [
        ("format", ctypes.c_int),
        ("rate", ctypes.c_uint32),
        ("channels", ctypes.c_ubyte),
    ]


class _PaBufferAttr(ctypes.Structure):
    _fields_ = [
        ("maxlength", ctypes.c_uint32),
        ("tlength", ctypes.c_uint32),
        ("prebuf", ctypes.c_uint32),
        ("minreq", ctypes.c_uint32),
        ("fragsize", ctypes.c_uint32),
    ]


class _PulseLib:
    def __init__(self) -> None:
        try:
            self.lib = ctypes.CDLL("libpulse-simple.so.0")
        except OSError as exc:
            raise MidiOutputError(f"libpulse-simple is not available: {exc}") from exc
        lib = self.lib
        lib.pa_simple_new.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(_PaSampleSpec),
            ctypes.c_void_p,
            ctypes.POINTER(_PaBufferAttr),
            ctypes.POINTER(ctypes.c_int),
        ]
        lib.pa_simple_new.restype = ctypes.c_void_p
        lib.pa_simple_write.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_int),
        ]
        lib.pa_simple_write.restype = ctypes.c_int
        lib.pa_simple_free.argtypes = [ctypes.c_void_p]
        lib.pa_simple_free.restype = None


class SonivoxOutput(QObject):
    """SonivoxEAS output, matching Drumstick's eassynth backend."""

    eventSent = pyqtSignal(object)
    driver = "sonivox"

    def __init__(self, name: str = "SonivoxEAS", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self._eas = _EASLib()
        self._pulse = _PulseLib()
        self._data: int | None = None
        self._stream: int | None = None
        self._pa: int | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._error = ""
        config_ptr = self._eas.lib.EAS_Config()
        if not config_ptr:
            raise MidiOutputError("EAS_Config returned null")
        version = ctypes.cast(config_ptr, ctypes.POINTER(ctypes.c_uint32)).contents.value
        major = (version >> 24) & 0xFF
        if major >= 4:
            cfg = ctypes.cast(config_ptr, ctypes.POINTER(_EASLibConfigV4)).contents
        else:
            cfg = ctypes.cast(config_ptr, ctypes.POINTER(_EASLibConfigV3)).contents
        self.sample_rate = int(cfg.sampleRate)
        self.mix_buffer_size = int(cfg.mixBufferSize)
        self.channels = int(cfg.numChannels)
        self._init_eas()
        self._init_pulse()
        self._stop.clear()
        self._thread = threading.Thread(target=self._render_loop, name="SonivoxEAS", daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _init_eas(self) -> None:
        lib = self._eas.lib
        data = ctypes.c_void_p()
        result = lib.EAS_Init(ctypes.byref(data))
        if result != EAS_SUCCESS:
            raise MidiOutputError(f"EAS_Init failed: {result}")
        self._data = data
        stream = ctypes.c_void_p()
        result = lib.EAS_OpenMIDIStream(self._data, ctypes.byref(stream), None)
        if result != EAS_SUCCESS:
            lib.EAS_Shutdown(self._data)
            self._data = None
            raise MidiOutputError(f"EAS_OpenMIDIStream failed: {result}")
        self._stream = stream
        # Drumstick's default Sonivox effects: Hall reverb, chorus disabled.
        lib.EAS_SetParameter(
            self._data, EAS_MODULE_REVERB, EAS_PARAM_REVERB_PRESET, EAS_PARAM_REVERB_HALL
        )
        lib.EAS_SetParameter(self._data, EAS_MODULE_REVERB, EAS_PARAM_REVERB_BYPASS, 0)
        lib.EAS_SetParameter(self._data, EAS_MODULE_REVERB, EAS_PARAM_REVERB_WET, 25800)
        lib.EAS_SetParameter(self._data, EAS_MODULE_CHORUS, EAS_PARAM_CHORUS_BYPASS, 1)
        lib.EAS_SetParameter(self._data, EAS_MODULE_CHORUS, EAS_PARAM_CHORUS_LEVEL, 0)

    def _init_pulse(self) -> None:
        spec = _PaSampleSpec(
            format=PA_SAMPLE_S16LE,
            rate=self.sample_rate,
            channels=self.channels,
        )
        # Drumstick's default Sonivox buffer time is 60 ms.
        tlength = int(self.sample_rate * 0.060) * self.channels * 2
        attr = _PaBufferAttr(
            maxlength=0xFFFFFFFF,
            tlength=tlength,
            prebuf=0xFFFFFFFF,
            minreq=0xFFFFFFFF,
            fragsize=0xFFFFFFFF,
        )
        error = ctypes.c_int(0)
        handle = self._pulse.lib.pa_simple_new(
            None,
            b"SonivoxEAS",
            PA_STREAM_PLAYBACK,
            None,
            b"Synthesizer output",
            ctypes.byref(spec),
            None,
            ctypes.byref(attr),
            ctypes.byref(error),
        )
        if not handle:
            self._shutdown_eas()
            raise MidiOutputError(f"PulseAudio connection failed: {error.value}")
        self._pa = handle

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_loop(self) -> None:
        lib = self._eas.lib
        frames = max(1, self.mix_buffer_size)
        buffer = (ctypes.c_short * (frames * self.channels))()
        generated = ctypes.c_long(0)
        while not self._stop.is_set():
            with self._lock:
                result = lib.EAS_Render(
                    self._data, buffer, frames, ctypes.byref(generated)
                )
            if result != EAS_SUCCESS:
                self._error = f"EAS_Render failed: {result}"
                break
            count = int(generated.value)
            if count > 0:
                size = count * ctypes.sizeof(ctypes.c_short) * self.channels
                error = ctypes.c_int(0)
                if (
                    self._pulse.lib.pa_simple_write(
                        self._pa, ctypes.byref(buffer), size, ctypes.byref(error)
                    )
                    < 0
                ):
                    self._error = f"PulseAudio write failed: {error.value}"
                    break

    # ------------------------------------------------------------------
    # MIDI
    # ------------------------------------------------------------------
    def _write(self, message: bytes) -> None:
        if not self._data or not self._stream:
            raise MidiOutputError("SonivoxEAS output is closed")
        with self._lock:
            result = self._eas.lib.EAS_WriteMIDIStream(
                self._data, self._stream, message, len(message)
            )
        if result != EAS_SUCCESS:
            raise MidiOutputError(f"EAS_WriteMIDIStream failed: {result}")

    def send_event(self, event: object) -> None:
        kind = getattr(event, "kind", "")
        channel = getattr(event, "channel", None)
        data = bytes(getattr(event, "data", b""))
        if channel is None:
            # The C++ Sonivox backend ignores SysEx; rely on its GM engine.
            return
        status_channel = channel & 0x0F
        if kind == "note_on" and len(data) >= 2:
            if data[1] == 0:
                self._write(bytes([0x80 | status_channel, data[0], 0]))
            else:
                self._write(bytes([0x90 | status_channel, data[0], data[1]]))
        elif kind == "note_off" and len(data) >= 2:
            self._write(bytes([0x80 | status_channel, data[0], data[1]]))
        elif kind == "key_pressure" and len(data) >= 2:
            self._write(bytes([0xA0 | status_channel, data[0], data[1]]))
        elif kind == "control_change" and len(data) >= 2:
            self._write(bytes([0xB0 | status_channel, data[0], data[1]]))
        elif kind == "program_change" and data:
            self._write(bytes([0xC0 | status_channel, data[0]]))
        elif kind == "channel_pressure" and data:
            self._write(bytes([0xD0 | status_channel, data[0]]))
        elif kind == "pitch_bend" and len(data) >= 2:
            self._write(bytes([0xE0 | status_channel, data[0], data[1]]))
        self.eventSent.emit(event)

    def all_notes_off(self) -> None:
        for channel in range(16):
            self._write(bytes([0xB0 | channel, 123, 0]))
            self._write(bytes([0xB0 | channel, 120, 0]))

    # ------------------------------------------------------------------
    # UI compatibility
    # ------------------------------------------------------------------
    def connections(self) -> list[MidiConnection]:
        return [MidiConnection(driver=self.driver, name=self.name)]

    def connected_connections(self) -> list[MidiConnection]:
        return self.connections()

    def current_connection(self) -> MidiConnection:
        return self.connections()[0]

    def connect_to(self, connection: object) -> None:
        return

    def disconnect_all(self) -> None:
        return

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _shutdown_eas(self) -> None:
        lib = self._eas.lib
        if self._stream and self._data:
            lib.EAS_CloseMIDIStream(self._data, self._stream)
            self._stream = None
        if self._data:
            lib.EAS_Shutdown(self._data)
            self._data = None

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self._shutdown_eas()
        if self._pa:
            self._pulse.lib.pa_simple_free(self._pa)
            self._pa = None

    def __del__(self) -> None:  # pragma: no cover - best effort
        try:
            self.close()
        except Exception:
            pass

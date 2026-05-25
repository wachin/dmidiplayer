"""Realtime MIDI abstractions for the Python port."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import Protocol

from PyQt6.QtCore import QObject, pyqtSignal

try:
    import alsaaudio
except ImportError:
    alsaaudio = None

MIDI_STD_CHANNELS = 16


class MidiOutput(Protocol):
    name: str

    def send_event(self, event: object) -> None:
        ...

    def all_notes_off(self) -> None:
        ...


class MidiOutputError(RuntimeError):
    """Raised when a realtime MIDI backend cannot be opened or used."""


@dataclass(slots=True)
class AlsaAudioInfo:
    available: bool
    cards: list[str]
    pcms: list[str]


def alsa_audio_info() -> AlsaAudioInfo:
    """Return PCM/card diagnostics from python3-alsaaudio when available."""

    if alsaaudio is None:
        return AlsaAudioInfo(available=False, cards=[], pcms=[])
    try:
        cards = [str(card) for card in alsaaudio.cards()]
    except Exception:
        cards = []
    try:
        pcms = [str(pcm) for pcm in alsaaudio.pcms()]
    except Exception:
        pcms = []
    return AlsaAudioInfo(available=True, cards=cards, pcms=pcms)


class DummyMidiOutput(QObject):
    eventSent = pyqtSignal(object)

    def __init__(self, name: str = "Dummy output", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.events: list[object] = []

    def send_event(self, event: object) -> None:
        self.events.append(event)
        self.eventSent.emit(event)

    def all_notes_off(self) -> None:
        self.events.clear()


class _SndSeqAddr(ctypes.Structure):
    _fields_ = [("client", ctypes.c_ubyte), ("port", ctypes.c_ubyte)]


class _SndSeqRealTime(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_uint), ("tv_nsec", ctypes.c_uint)]


class _SndSeqTimestamp(ctypes.Union):
    _fields_ = [("tick", ctypes.c_uint), ("time", _SndSeqRealTime)]


class _SndSeqEvNote(ctypes.Structure):
    _fields_ = [
        ("channel", ctypes.c_ubyte),
        ("note", ctypes.c_ubyte),
        ("velocity", ctypes.c_ubyte),
        ("off_velocity", ctypes.c_ubyte),
        ("duration", ctypes.c_uint),
    ]


class _SndSeqEvCtrl(ctypes.Structure):
    _fields_ = [
        ("channel", ctypes.c_ubyte),
        ("unused", ctypes.c_ubyte * 3),
        ("param", ctypes.c_uint),
        ("value", ctypes.c_int),
    ]


class _SndSeqEvExt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("len", ctypes.c_uint), ("ptr", ctypes.c_void_p)]


class _SndSeqEventData(ctypes.Union):
    _fields_ = [
        ("note", _SndSeqEvNote),
        ("control", _SndSeqEvCtrl),
        ("ext", _SndSeqEvExt),
        ("raw8", ctypes.c_ubyte * 12),
        ("raw32", ctypes.c_uint * 3),
    ]


class _SndSeqEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ubyte),
        ("flags", ctypes.c_ubyte),
        ("tag", ctypes.c_ubyte),
        ("queue", ctypes.c_ubyte),
        ("time", _SndSeqTimestamp),
        ("source", _SndSeqAddr),
        ("dest", _SndSeqAddr),
        ("data", _SndSeqEventData),
    ]


SND_SEQ_OPEN_OUTPUT = 1
SND_SEQ_ADDRESS_SUBSCRIBERS = 254
SND_SEQ_ADDRESS_UNKNOWN = 253
SND_SEQ_QUEUE_DIRECT = 253
SND_SEQ_EVENT_LENGTH_FIXED = 0 << 2
SND_SEQ_EVENT_LENGTH_VARIABLE = 1 << 2
SND_SEQ_EVENT_LENGTH_MASK = 3 << 2
SND_SEQ_PORT_CAP_READ = 1 << 0
SND_SEQ_PORT_CAP_WRITE = 1 << 1
SND_SEQ_PORT_CAP_SUBS_READ = 1 << 5
SND_SEQ_PORT_CAP_SUBS_WRITE = 1 << 6
SND_SEQ_PORT_TYPE_MIDI_GENERIC = 1 << 1
SND_SEQ_PORT_TYPE_APPLICATION = 1 << 20
SND_SEQ_EVENT_NOTEON = 6
SND_SEQ_EVENT_NOTEOFF = 7
SND_SEQ_EVENT_KEYPRESS = 8
SND_SEQ_EVENT_CONTROLLER = 10
SND_SEQ_EVENT_PGMCHANGE = 11
SND_SEQ_EVENT_CHANPRESS = 12
SND_SEQ_EVENT_PITCHBEND = 13
SND_SEQ_EVENT_SYSEX = 130


class _AlsaLib:
    def __init__(self) -> None:
        try:
            self.lib = ctypes.CDLL("libasound.so.2")
        except OSError as exc:
            raise MidiOutputError("No se pudo cargar libasound.so.2") from exc
        self._setup_prototypes()

    def _setup_prototypes(self) -> None:
        lib = self.lib
        lib.snd_seq_open.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_int,
        ]
        lib.snd_seq_open.restype = ctypes.c_int
        lib.snd_seq_close.argtypes = [ctypes.c_void_p]
        lib.snd_seq_close.restype = ctypes.c_int
        lib.snd_seq_client_id.argtypes = [ctypes.c_void_p]
        lib.snd_seq_client_id.restype = ctypes.c_int
        lib.snd_seq_set_client_name.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.snd_seq_set_client_name.restype = ctypes.c_int
        lib.snd_seq_create_simple_port.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        lib.snd_seq_create_simple_port.restype = ctypes.c_int
        lib.snd_seq_delete_simple_port.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.snd_seq_delete_simple_port.restype = ctypes.c_int
        lib.snd_seq_connect_to.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.snd_seq_connect_to.restype = ctypes.c_int
        lib.snd_seq_disconnect_to.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.snd_seq_disconnect_to.restype = ctypes.c_int
        lib.snd_seq_event_output_direct.argtypes = [ctypes.c_void_p, ctypes.POINTER(_SndSeqEvent)]
        lib.snd_seq_event_output_direct.restype = ctypes.c_int
        lib.snd_seq_sync_output_queue.argtypes = [ctypes.c_void_p]
        lib.snd_seq_sync_output_queue.restype = ctypes.c_int
        lib.snd_seq_client_info_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        lib.snd_seq_client_info_malloc.restype = ctypes.c_int
        lib.snd_seq_client_info_free.argtypes = [ctypes.c_void_p]
        lib.snd_seq_client_info_free.restype = None
        lib.snd_seq_client_info_set_client.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.snd_seq_client_info_set_client.restype = None
        lib.snd_seq_client_info_get_client.argtypes = [ctypes.c_void_p]
        lib.snd_seq_client_info_get_client.restype = ctypes.c_int
        lib.snd_seq_client_info_get_name.argtypes = [ctypes.c_void_p]
        lib.snd_seq_client_info_get_name.restype = ctypes.c_char_p
        lib.snd_seq_query_next_client.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.snd_seq_query_next_client.restype = ctypes.c_int
        lib.snd_seq_port_info_malloc.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        lib.snd_seq_port_info_malloc.restype = ctypes.c_int
        lib.snd_seq_port_info_free.argtypes = [ctypes.c_void_p]
        lib.snd_seq_port_info_free.restype = None
        lib.snd_seq_port_info_set_client.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.snd_seq_port_info_set_client.restype = None
        lib.snd_seq_port_info_set_port.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.snd_seq_port_info_set_port.restype = None
        lib.snd_seq_port_info_get_port.argtypes = [ctypes.c_void_p]
        lib.snd_seq_port_info_get_port.restype = ctypes.c_int
        lib.snd_seq_port_info_get_name.argtypes = [ctypes.c_void_p]
        lib.snd_seq_port_info_get_name.restype = ctypes.c_char_p
        lib.snd_seq_port_info_get_capability.argtypes = [ctypes.c_void_p]
        lib.snd_seq_port_info_get_capability.restype = ctypes.c_uint
        lib.snd_seq_query_next_port.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.snd_seq_query_next_port.restype = ctypes.c_int
        lib.snd_strerror.argtypes = [ctypes.c_int]
        lib.snd_strerror.restype = ctypes.c_char_p

    def error(self, code: int) -> str:
        message = self.lib.snd_strerror(code)
        if not message:
            return f"ALSA error {code}"
        return message.decode(errors="replace")


class AlsaSequencerOutput(QObject):
    eventSent = pyqtSignal(object)

    def __init__(self, name: str = "dmidiplayer PyQt6", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self._alsa = _AlsaLib()
        self._seq = ctypes.c_void_p()
        self._port = -1
        self._client = -1
        self._connected: dict[tuple[int, int], MidiConnection] = {}
        self._open()

    def _open(self) -> None:
        result = self._alsa.lib.snd_seq_open(ctypes.byref(self._seq), b"default", SND_SEQ_OPEN_OUTPUT, 0)
        if result < 0:
            raise MidiOutputError(
                f"No se pudo abrir ALSA sequencer: {self._alsa.error(result)}. "
                "Revisa que /dev/snd/seq exista; normalmente lo provee el modulo snd-seq."
            )
        self._client = self._alsa.lib.snd_seq_client_id(self._seq)
        self._alsa.lib.snd_seq_set_client_name(self._seq, self.name.encode())
        caps = SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ
        port_type = SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION
        self._port = self._alsa.lib.snd_seq_create_simple_port(self._seq, b"MIDI out", caps, port_type)
        if self._port < 0:
            error = self._alsa.error(self._port)
            self._alsa.lib.snd_seq_close(self._seq)
            self._seq = ctypes.c_void_p()
            raise MidiOutputError(f"No se pudo crear el puerto ALSA MIDI: {error}")

    def connections(self) -> list["MidiConnection"]:
        return _list_alsa_output_ports(self._alsa, self._seq, self._client)

    def connect_to(self, connection: "MidiConnection | str") -> None:
        if isinstance(connection, str):
            candidates = [port for port in self.connections() if port.matches(connection)]
            if not candidates:
                raise MidiOutputError(f"No se encontro el puerto ALSA MIDI: {connection}")
            connection = candidates[0]
        if connection.client is None or connection.port is None:
            raise MidiOutputError(f"Puerto ALSA invalido: {connection.name}")
        key = (connection.client, connection.port)
        if key in self._connected:
            return
        result = self._alsa.lib.snd_seq_connect_to(self._seq, self._port, connection.client, connection.port)
        if result < 0 and result != -16:
            raise MidiOutputError(f"No se pudo conectar a {connection.name}: {self._alsa.error(result)}")
        self._connected[key] = connection

    def disconnect_from(self, connection: "MidiConnection | str") -> None:
        if isinstance(connection, str):
            candidates = [port for port in self.connected_connections() if port.matches(connection)]
            if not candidates:
                raise MidiOutputError(f"No hay una conexion ALSA activa con: {connection}")
            connection = candidates[0]
        if connection.client is None or connection.port is None:
            raise MidiOutputError(f"Puerto ALSA invalido: {connection.name}")
        key = (connection.client, connection.port)
        if key not in self._connected:
            return
        result = self._alsa.lib.snd_seq_disconnect_to(self._seq, self._port, connection.client, connection.port)
        if result < 0 and result != -2:
            raise MidiOutputError(f"No se pudo desconectar de {connection.name}: {self._alsa.error(result)}")
        self._connected.pop(key, None)

    def disconnect_all(self) -> None:
        for connection in list(self._connected.values()):
            self.disconnect_from(connection)

    def connected_connections(self) -> list["MidiConnection"]:
        return list(self._connected.values())

    def close(self) -> None:
        if self._seq:
            if self._port >= 0:
                self._alsa.lib.snd_seq_delete_simple_port(self._seq, self._port)
                self._port = -1
            self._alsa.lib.snd_seq_close(self._seq)
            self._seq = ctypes.c_void_p()

    def send_event(self, event: object) -> None:
        alsa_event = self._event_to_alsa(event)
        if alsa_event is None:
            return
        result = self._alsa.lib.snd_seq_event_output_direct(self._seq, ctypes.byref(alsa_event))
        if result < 0:
            raise MidiOutputError(f"No se pudo enviar evento MIDI por ALSA: {self._alsa.error(result)}")
        self.eventSent.emit(event)

    def all_notes_off(self) -> None:
        for channel in range(MIDI_STD_CHANNELS):
            self._send_controller(channel, 123, 0)
            self._send_controller(channel, 120, 0)
        self._alsa.lib.snd_seq_sync_output_queue(self._seq)

    def _event_to_alsa(self, event: object) -> _SndSeqEvent | None:
        kind = getattr(event, "kind", "")
        channel = getattr(event, "channel", None)
        data = bytes(getattr(event, "data", b""))
        if channel is None:
            if kind == "sysex":
                return self._make_sysex_event(data)
            return None
        if kind == "note_on" and len(data) >= 2:
            event_type = SND_SEQ_EVENT_NOTEOFF if data[1] == 0 else SND_SEQ_EVENT_NOTEON
            return self._make_note_event(event_type, channel, data[0], data[1])
        if kind == "note_off" and len(data) >= 2:
            return self._make_note_event(SND_SEQ_EVENT_NOTEOFF, channel, data[0], data[1])
        if kind == "key_pressure" and len(data) >= 2:
            return self._make_note_event(SND_SEQ_EVENT_KEYPRESS, channel, data[0], data[1])
        if kind == "control_change" and len(data) >= 2:
            return self._make_control_event(SND_SEQ_EVENT_CONTROLLER, channel, data[0], data[1])
        if kind == "program_change" and data:
            return self._make_control_event(SND_SEQ_EVENT_PGMCHANGE, channel, 0, data[0])
        if kind == "channel_pressure" and data:
            return self._make_control_event(SND_SEQ_EVENT_CHANPRESS, channel, 0, data[0])
        if kind == "pitch_bend" and len(data) >= 2:
            value = ((data[1] << 7) | data[0]) - 8192
            return self._make_control_event(SND_SEQ_EVENT_PITCHBEND, channel, 0, value)
        return None

    def _base_event(self, event_type: int) -> _SndSeqEvent:
        event = _SndSeqEvent()
        event.type = event_type
        event.flags &= ~SND_SEQ_EVENT_LENGTH_MASK
        event.flags |= SND_SEQ_EVENT_LENGTH_FIXED
        event.queue = SND_SEQ_QUEUE_DIRECT
        event.source.port = self._port
        event.dest.client = SND_SEQ_ADDRESS_SUBSCRIBERS
        event.dest.port = SND_SEQ_ADDRESS_UNKNOWN
        return event

    def _make_note_event(self, event_type: int, channel: int, note: int, velocity: int) -> _SndSeqEvent:
        event = self._base_event(event_type)
        event.data.note.channel = channel
        event.data.note.note = note
        event.data.note.velocity = velocity
        return event

    def _make_control_event(self, event_type: int, channel: int, param: int, value: int) -> _SndSeqEvent:
        event = self._base_event(event_type)
        event.data.control.channel = channel
        event.data.control.param = param
        event.data.control.value = value
        return event

    def _make_sysex_event(self, data: bytes) -> _SndSeqEvent:
        event = self._base_event(SND_SEQ_EVENT_SYSEX)
        event.flags &= ~SND_SEQ_EVENT_LENGTH_MASK
        event.flags |= SND_SEQ_EVENT_LENGTH_VARIABLE
        payload = data if data.startswith(b"\xf0") else b"\xf0" + data
        if not payload.endswith(b"\xf7"):
            payload += b"\xf7"
        buffer = ctypes.create_string_buffer(payload)
        event.data.ext.len = len(payload)
        event.data.ext.ptr = ctypes.cast(buffer, ctypes.c_void_p)
        event._payload = buffer
        return event

    def _send_controller(self, channel: int, controller: int, value: int) -> None:
        event = self._make_control_event(SND_SEQ_EVENT_CONTROLLER, channel, controller, value)
        self._alsa.lib.snd_seq_event_output_direct(self._seq, ctypes.byref(event))

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


@dataclass(slots=True)
class MidiConnection:
    driver: str
    name: str
    client: int | None = None
    port: int | None = None
    client_name: str = ""
    port_name: str = ""
    capability: int = 0

    @property
    def address(self) -> str:
        if self.client is None or self.port is None:
            return ""
        return f"{self.client}:{self.port}"

    def matches(self, text: str) -> bool:
        query = text.casefold()
        return query in self.name.casefold() or query == self.address


class BackendManager(QObject):
    """Small stand-in for Drumstick::rt::BackendManager.

    Real ALSA/FluidSynth/PipeWire outputs are tracked in ROADMAP.md.  The dummy
    output lets the GUI, parser, and sequencer be ported and tested first.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._output = DummyMidiOutput(parent=self)

    def output_drivers(self) -> list[str]:
        return ["alsa", "dummy"]

    def connections(self, driver: str = "dummy") -> list[MidiConnection]:
        if driver == "alsa":
            try:
                return list_alsa_output_ports()
            except MidiOutputError:
                return []
        return [MidiConnection(driver=driver, name=self._output.name)]

    def alsa_audio_info(self) -> AlsaAudioInfo:
        return alsa_audio_info()

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> MidiOutput:
        if driver == "alsa":
            output = AlsaSequencerOutput("dmidiplayer PyQt6", parent=self)
            if connection:
                output.connect_to(connection)
            return output
        self._output.name = connection or self._output.name
        return self._output


def list_alsa_output_ports() -> list[MidiConnection]:
    alsa = _AlsaLib()
    seq = ctypes.c_void_p()
    result = alsa.lib.snd_seq_open(ctypes.byref(seq), b"default", SND_SEQ_OPEN_OUTPUT, 0)
    if result < 0:
        raise MidiOutputError(f"No se pudo abrir ALSA sequencer: {alsa.error(result)}")
    try:
        client = alsa.lib.snd_seq_client_id(seq)
        return _list_alsa_output_ports(alsa, seq, client)
    finally:
        alsa.lib.snd_seq_close(seq)


def _list_alsa_output_ports(alsa: _AlsaLib, seq: ctypes.c_void_p, own_client: int) -> list[MidiConnection]:
    client_info = ctypes.c_void_p()
    result = alsa.lib.snd_seq_client_info_malloc(ctypes.byref(client_info))
    if result < 0:
        raise MidiOutputError(f"No se pudo reservar informacion de clientes ALSA: {alsa.error(result)}")
    ports: list[MidiConnection] = []
    try:
        alsa.lib.snd_seq_client_info_set_client(client_info, -1)
        while alsa.lib.snd_seq_query_next_client(seq, client_info) >= 0:
            client = alsa.lib.snd_seq_client_info_get_client(client_info)
            if client == own_client:
                continue
            client_name = _decode_alsa_string(alsa.lib.snd_seq_client_info_get_name(client_info))
            ports.extend(_list_client_output_ports(alsa, seq, client, client_name))
    finally:
        alsa.lib.snd_seq_client_info_free(client_info)
    return ports


def _list_client_output_ports(
    alsa: _AlsaLib,
    seq: ctypes.c_void_p,
    client: int,
    client_name: str,
) -> list[MidiConnection]:
    port_info = ctypes.c_void_p()
    result = alsa.lib.snd_seq_port_info_malloc(ctypes.byref(port_info))
    if result < 0:
        raise MidiOutputError(f"No se pudo reservar informacion de puertos ALSA: {alsa.error(result)}")
    ports: list[MidiConnection] = []
    try:
        alsa.lib.snd_seq_port_info_set_client(port_info, client)
        alsa.lib.snd_seq_port_info_set_port(port_info, -1)
        while alsa.lib.snd_seq_query_next_port(seq, port_info) >= 0:
            capability = alsa.lib.snd_seq_port_info_get_capability(port_info)
            required = SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE
            if capability & required != required:
                continue
            port = alsa.lib.snd_seq_port_info_get_port(port_info)
            port_name = _decode_alsa_string(alsa.lib.snd_seq_port_info_get_name(port_info))
            ports.append(
                MidiConnection(
                    driver="alsa",
                    name=f"{client}:{port} {client_name}: {port_name}",
                    client=client,
                    port=port,
                    client_name=client_name,
                    port_name=port_name,
                    capability=capability,
                )
            )
    finally:
        alsa.lib.snd_seq_port_info_free(port_info)
    return ports


def _decode_alsa_string(value: bytes | None) -> str:
    if not value:
        return ""
    return value.decode(errors="replace")

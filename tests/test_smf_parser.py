from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from drumstick_py import MidiFileError, read_smf


def varlen(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= (value & 0x7F) | 0x80
        value >>= 7
    out = bytearray()
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            return bytes(out)


def chunk(name: bytes, payload: bytes) -> bytes:
    return name + struct.pack(">I", len(payload)) + payload


def smf_data(midi_format: int, division: int, tracks: list[bytes]) -> bytes:
    header = chunk(b"MThd", struct.pack(">HHH", midi_format, len(tracks), division))
    return header + b"".join(chunk(b"MTrk", track) for track in tracks)


def riff_chunk(name: bytes, payload: bytes) -> bytes:
    padding = b"\x00" if len(payload) % 2 else b""
    return name + struct.pack("<I", len(payload)) + payload + padding


def rmid_data(smf_payload: bytes, extra_chunks: list[bytes] | None = None, form: bytes = b"RMID") -> bytes:
    chunks = [riff_chunk(b"data", smf_payload)]
    if extra_chunks is not None:
        chunks.extend(extra_chunks)
    payload = form + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(payload)) + payload


def wrk_chunk(chunk_id: int, payload: bytes) -> bytes:
    return bytes([chunk_id]) + struct.pack("<I", len(payload)) + payload


def read_temp_smf(data: bytes, name: str = "test.mid"):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir, name)
        path.write_bytes(data)
        return read_smf(path)


class SmfParserTest(unittest.TestCase):
    def test_reads_example_test_mid_with_stable_timing(self) -> None:
        examples = Path(__file__).resolve().parents[1] / "dmidiplayer" / "examples"
        midi = read_smf(examples / "test.mid")
        self.assertEqual(midi.format, 0)
        self.assertEqual(midi.division, 120)
        self.assertEqual(len(midi.tracks), 1)
        self.assertEqual(midi.length_ticks, 480)
        self.assertEqual(midi.length_microseconds, 2_400_000)
        self.assertEqual(midi.bar_count, 2)
        self.assertEqual(midi.tempo_changes[0].microseconds_per_quarter, 600_000)
        self.assertEqual((midi.time_signatures[0].numerator, midi.time_signatures[0].denominator), (3, 4))
        self.assertEqual((midi.key_signatures[0].sharps_flats, midi.key_signatures[0].minor), (2, False))

    def test_reads_example_mozart_diesirae_mid_with_stable_timing(self) -> None:
        examples = Path(__file__).resolve().parents[1] / "dmidiplayer" / "examples"
        midi = read_smf(examples / "mozart_diesirae.mid")
        self.assertEqual(midi.title, "clarinet")
        self.assertEqual(midi.format, 1)
        self.assertEqual(midi.division, 480)
        self.assertEqual(len(midi.tracks), 12)
        self.assertEqual(midi.length_ticks, 132_479)
        self.assertEqual(midi.length_microseconds, 106_837_689)
        self.assertEqual(midi.bar_count, 69)
        self.assertEqual(midi.tempo_changes[0].microseconds_per_quarter, 387_096)

    def test_rejects_invalid_header(self) -> None:
        with self.assertRaisesRegex(MidiFileError, "Not a Standard MIDI File"):
            read_temp_smf(b"not midi", "not-midi.mid")

    def test_reads_empty_wrk_file(self) -> None:
        midi = read_temp_smf(b"CAKEWALK\x00\x01\x02\xff", "song.wrk")
        self.assertEqual(midi.format, 1)
        self.assertGreaterEqual(len(midi.tracks), 1)

    def test_reads_wrk_with_unknown_chunk(self) -> None:
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(7, b"\x01\x02\x03\x04") + b"\xff"
        midi = read_temp_smf(wrk, "memrgn.wrk")
        self.assertEqual(midi.format, 1)

    def test_rejects_invalid_wrk_file_format(self) -> None:
        with self.assertRaisesRegex(MidiFileError, "Invalid Cakewalk WRK file format"):
            read_temp_smf(b"not-a-wrk", "song.wrk")

    def test_rejects_corrupted_wrk_chunk_header(self) -> None:
        corrupted = b"CAKEWALK\x00\x01\x02" + bytes([10]) + struct.pack("<I", 20) + b"\x00\x00"
        with self.assertRaisesRegex(MidiFileError, "Corrupted Cakewalk WRK file"):
            read_temp_smf(corrupted, "broken.wrk")

    def test_reads_wrk_timebase_from_first_chunk(self) -> None:
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(10, struct.pack("<H", 120)) + b"\xff"
        midi = read_temp_smf(wrk, "timebase.wrk")
        self.assertEqual(midi.division, 120)

    def test_reads_wrk_software_version_from_first_chunk(self) -> None:
        payload = bytes([6]) + b"Cake 7"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(74, payload) + b"\xff"
        midi = read_temp_smf(wrk, "softver.wrk")
        self.assertEqual(midi.info.get("wrk_version"), "2.1")

    def test_reads_wrk_track_name_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 0) + bytes([5]) + b"Piano"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(24, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackname.wrk")
        self.assertEqual(midi.tracks[0].name, "Piano")

    def test_reads_wrk_classic_track_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 0)
            + bytes([5])
            + b"Piano"
            + bytes([4])
            + b"Part"
            + bytes([2, 40, 100, 1, 0x07])
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(1, payload) + b"\xff"
        midi = read_temp_smf(wrk, "track.wrk")
        self.assertEqual(midi.tracks[0].name, "Piano")

    def test_reads_wrk_comments_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 5) + b"Notes"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(8, payload) + b"\xff"
        midi = read_temp_smf(wrk, "comments.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_volume_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 0, 96)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(19, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackvol.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_bank_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 0, 2048)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(30, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackbank.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_patch_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 0) + bytes([33])
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(14, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackpatch.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_offset_from_first_chunk(self) -> None:
        payload = struct.pack("<Hh", 0, -24)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(9, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackoffset.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_repetitions_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 0, 3)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(12, payload) + b"\xff"
        midi = read_temp_smf(wrk, "trackreps.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_time_format_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 25, 40)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(11, payload) + b"\xff"
        midi = read_temp_smf(wrk, "timefmt.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_new_track_offset_from_first_chunk(self) -> None:
        payload = struct.pack("<HI", 0, 123456)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(27, payload) + b"\xff"
        midi = read_temp_smf(wrk, "newtrackoffset.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_track_chunk_summary_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 0)
            + bytes([5])
            + b"Piano"
            + bytes([4])
            + b"Part"
            + bytes([2, 40, 100, 1, 0])
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(36, payload) + b"\xff"
        midi = read_temp_smf(wrk, "ntrack.wrk")
        self.assertEqual(midi.tracks[0].name, "Piano")

    def test_reads_wrk_markers_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<I", 1)
            + bytes([24, 0])
            + bytes([0x39, 0x30, 0x00])
            + b"\x00\x00\x00\x00\x00"
            + bytes([5])
            + b"Intro"
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(21, payload) + b"\xff"
        midi = read_temp_smf(wrk, "markers.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_segment_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<HI", 0, 960)
            + b"\x00" * 8
            + bytes([5])
            + b"Verse"
            + b"\x00" * 20
            + struct.pack("<I", 12)
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(49, payload) + b"\xff"
        midi = read_temp_smf(wrk, "segment.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_lyrics_stream_from_first_chunk(self) -> None:
        payload = struct.pack("<HI", 0, 0)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(18, payload) + b"\xff"
        midi = read_temp_smf(wrk, "lyricsstream.wrk")
        self.assertEqual(midi.format, 1)

    def test_reports_wrk_classic_stream_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<HH", 0, 1)
            + bytes([0x7B, 0x00, 0x00])
            + bytes([0x90, 60, 100])
            + struct.pack("<H", 240)
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(2, payload) + b"\xff"
        midi = read_temp_smf(wrk, "stream.wrk")
        midi_events = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual([event.tick for event in midi_events], [123, 363])

    def test_reads_wrk_new_stream_from_first_chunk(self) -> None:
        event = b"\x10\x00\x00" + bytes([1]) + struct.pack("<I", 5) + b"Hello"
        payload = struct.pack("<H", 0) + bytes([5]) + b"Intro" + struct.pack("<I", 1) + event
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(45, payload) + b"\xff"
        midi = read_temp_smf(wrk, "nstream.wrk")
        meta_events = [event for event in midi.events if event.kind == "meta"]
        self.assertEqual(meta_events[0].tick, 16)
        self.assertEqual(meta_events[0].text, "Hello")

    def test_reads_wrk_string_table_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 2) + bytes([5]) + b"Verse" + bytes([3])
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(22, payload) + b"\xff"
        midi = read_temp_smf(wrk, "strtab.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_variable_record_from_first_chunk(self) -> None:
        payload = b"Tempo\x00" + (b"\x00" * 26) + b"\x10\x20\x30\x00"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(26, payload) + b"\xff"
        midi = read_temp_smf(wrk, "variable.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_global_vars_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<III", 120, 240, 960)
            + b"\x00" * 4
            + b"\x00"
            + b"\x00" * 5
            + struct.pack("<I", 0)
            + b"\x00"
            + struct.pack("<I", 0)
            + b"\x00" * 4
            + b"\x00" * 2
            + b"\x01"
            + b"\x00" * 19
            + b"\x00"
            + b"\x00" * 4
            + b"\x00" * 2
            + b"\x00"
            + struct.pack("<I", 0)
            + struct.pack("<I", 0)
            + struct.pack("<I", 1440)
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(3, payload) + b"\xff"
        midi = read_temp_smf(wrk, "vars.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_thru_from_first_chunk(self) -> None:
        payload = b"\x00\x00" + bytes([2, 5, 12, 7, 1, 3])
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(16, payload) + b"\xff"
        midi = read_temp_smf(wrk, "thru.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_meter_key_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 1) + struct.pack("<H", 8) + bytes([3, 2, 0xFE])
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(23, payload) + b"\xff"
        midi = read_temp_smf(wrk, "meterkey.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_meter_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 1)
            + b"\x00" * 4
            + struct.pack("<H", 12)
            + bytes([6, 3])
            + b"\x00" * 4
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(5, payload) + b"\xff"
        midi = read_temp_smf(wrk, "meter.wrk")
        self.assertEqual(midi.format, 1)

    def test_reads_wrk_tempo_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 1)
            + struct.pack("<I", 480)
            + b"\x00" * 4
            + struct.pack("<H", 120)
            + b"\x00" * 8
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(4, payload) + b"\xff"
        midi = read_temp_smf(wrk, "tempo.wrk")
        tempos = [event.tempo_us_per_quarter for event in midi.events if event.tempo_us_per_quarter is not None]
        self.assertIn(500_000, tempos)

    def test_reads_wrk_new_tempo_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 1)
            + struct.pack("<I", 960)
            + b"\x00" * 4
            + struct.pack("<H", 135)
            + b"\x00" * 8
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(15, payload) + b"\xff"
        midi = read_temp_smf(wrk, "ntempo.wrk")
        self.assertTrue(any(event.tempo_us_per_quarter is not None for event in midi.events))

    def test_reads_wrk_sysex_from_first_chunk(self) -> None:
        payload = (
            bytes([7])
            + struct.pack("<H", 3)
            + bytes([1, 3])
            + b"Old"
            + bytes([0xF0, 0x7E, 0xF7])
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(6, payload) + b"\xff"
        midi = read_temp_smf(wrk, "sysex.wrk")
        self.assertTrue(any(event.kind == "sysex" for event in midi.events))

    def test_reads_wrk_sysex2_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 2)
            + struct.pack("<I", 3)
            + bytes([0x21])
            + bytes([4])
            + b"Bank"
            + bytes([0xF0, 0x7E, 0xF7])
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(20, payload) + b"\xff"
        midi = read_temp_smf(wrk, "sysex2.wrk")
        self.assertTrue(any(event.kind == "sysex" for event in midi.events))

    def test_reads_wrk_new_sysex_from_first_chunk(self) -> None:
        payload = (
            struct.pack("<H", 3)
            + struct.pack("<I", 4)
            + struct.pack("<H", 9)
            + bytes([1, 5])
            + b"Patch"
            + bytes([0x01, 0x02, 0x03, 0x04])
        )
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(44, payload) + b"\xff"
        midi = read_temp_smf(wrk, "nsysex.wrk")
        self.assertTrue(any(event.kind == "sysex" for event in midi.events))

    def test_reads_rmid_wrapped_smf(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(4),
                b"RIFF",
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(480),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )

        midi = read_temp_smf(rmid_data(smf_data(0, 480, [track])), "wrapped.rmi")

        self.assertEqual(midi.title, "RIFF")
        self.assertEqual(midi.length_ticks, 480)
        self.assertEqual([event.kind for event in midi.events if event.kind in ("note_on", "note_off")], ["note_on", "note_off"])

    def test_rejects_unsupported_riff_form(self) -> None:
        midi_bytes = rmid_data(smf_data(0, 480, [b"\x00\xff\x2f\x00"]), form=b"WAVE")

        with self.assertRaisesRegex(MidiFileError, "Unsupported RIFF MIDI form"):
            read_temp_smf(midi_bytes, "bad-form.rmi")

    def test_rejects_rmid_without_data_chunk(self) -> None:
        info_chunk = riff_chunk(b"DISP", b"metadata")
        midi_bytes = b"RIFF" + struct.pack("<I", len(b"RMID" + info_chunk)) + b"RMID" + info_chunk

        with self.assertRaisesRegex(MidiFileError, "RIFF MIDI data chunk not found"):
            read_temp_smf(midi_bytes, "missing-data.rmi")

    def test_reads_rmid_info_metadata(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(4),
                b"RIFF",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        info_payload = b"".join(
            [
                riff_chunk(b"IART", b"OpenAI Band\x00"),
                riff_chunk(b"ISFT", b"dmidiplayer\x00"),
            ]
        )
        midi = read_temp_smf(
            rmid_data(smf_data(0, 480, [track]), extra_chunks=[riff_chunk(b"LIST", b"INFO" + info_payload)]),
            "info.rmi",
        )

        self.assertEqual(midi.info["Artist"], "OpenAI Band")
        self.assertEqual(midi.info["Software"], "dmidiplayer")
        self.assertEqual(midi.info_data["Artist"], b"OpenAI Band")
        self.assertEqual(midi.info_data["Software"], b"dmidiplayer")

    def test_rmid_info_name_auto_detects_cp1252_for_title(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(120),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        info_payload = b"".join(
            [
                riff_chunk(b"INAM", b"Precio \x8010\x00"),
            ]
        )
        midi = read_temp_smf(
            rmid_data(smf_data(0, 480, [track]), extra_chunks=[riff_chunk(b"LIST", b"INFO" + info_payload)]),
            "cp1252-title.rmi",
        )

        self.assertEqual(midi.title, "Precio €10")

    def test_uses_rmid_info_name_as_title_fallback(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(120),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        info_payload = b"".join(
            [
                riff_chunk(b"INAM", b"Info Title\x00"),
                riff_chunk(b"IART", b"OpenAI Band\x00"),
            ]
        )
        midi = read_temp_smf(
            rmid_data(smf_data(0, 480, [track]), extra_chunks=[riff_chunk(b"LIST", b"INFO" + info_payload)]),
            "info-title.rmi",
        )

        self.assertEqual(midi.title, "Info Title")

    def test_rejects_truncated_track_chunk(self) -> None:
        header = chunk(b"MThd", struct.pack(">HHH", 0, 1, 480))
        data = header + b"MTrk" + struct.pack(">I", 10) + b"\x00\xff\x2f\x00"

        with self.assertRaisesRegex(MidiFileError, "Unexpected end of file"):
            read_temp_smf(data, "truncated.mid")

    def test_rejects_invalid_variable_length_quantity(self) -> None:
        track = bytes([0x81, 0x81, 0x81, 0x81, 0x00, 0xFF, 0x2F, 0x00])

        with self.assertRaisesRegex(MidiFileError, "Invalid variable-length quantity"):
            read_temp_smf(smf_data(0, 480, [track]), "bad-varlen.mid")

    def test_reads_tempo_metadata_and_note_events(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(4),
                b"Test",
                varlen(0),
                b"\xff\x51",
                varlen(3),
                bytes([0x07, 0xA1, 0x20]),
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(480),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "simple.mid")

        note_events = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual(midi.title, "Test")
        self.assertEqual(midi.tempo_changes[0].microseconds_per_quarter, 500_000)
        self.assertEqual(midi.length_ticks, 480)
        self.assertEqual(midi.length_microseconds, 500_000)
        self.assertEqual(midi.bpm_at_tick(0), 120.0)
        self.assertEqual([event.kind for event in note_events], ["note_on", "note_off"])
        self.assertEqual(midi.microseconds_to_tick(250_000), 240)
        self.assertTrue(any(event.kind == "meta" and event.meta_type == 0x2F for event in midi.events))

    def test_reports_tempo_at_tick_after_tempo_change(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x51\x03\x07\xa1\x20",
                varlen(480),
                b"\xff\x51\x03\x0f\x42\x40",
                varlen(480),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "tempo.mid")

        self.assertEqual(midi.tempo_at_tick(0), 500_000)
        self.assertEqual(midi.tempo_at_tick(480), 1_000_000)
        self.assertEqual(midi.bpm_at_tick(480), 60.0)
        self.assertEqual(midi.length_microseconds, 1_500_000)
        self.assertEqual(midi.microseconds_to_tick(750_000), 600)

    def test_uses_smpte_division_for_timing(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(50),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 0xE728, [track]), "smpte.mid")

        self.assertEqual(midi.length_ticks, 50)
        self.assertEqual(midi.length_microseconds, 50_000)
        self.assertEqual(midi.tick_to_microseconds(25), 25_000)
        self.assertEqual(midi.microseconds_to_tick(25_000), 25)
        self.assertEqual(midi.tempo_at_tick(50), 500_000)

    def test_reports_bar_numbers_from_time_signature(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x58\x04\x03\x02\x18\x08",
                varlen(2880),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "bars.mid")

        self.assertEqual(midi.bar_count, 2)
        self.assertEqual(midi.bar_number_at_tick(0), 1)
        self.assertEqual(midi.bar_number_at_tick(1439), 1)
        self.assertEqual(midi.bar_number_at_tick(1440), 2)
        self.assertEqual(midi.tick_for_bar(2), 1440)

    def test_reports_bar_numbers_across_time_signature_changes(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x58\x04\x04\x02\x18\x08",
                varlen(3840),
                b"\xff\x58\x04\x03\x02\x18\x08",
                varlen(2880),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "changing-bars.mid")

        self.assertEqual(midi.bar_count, 4)
        self.assertEqual(midi.bar_number_at_tick(0), 1)
        self.assertEqual(midi.bar_number_at_tick(1919), 1)
        self.assertEqual(midi.bar_number_at_tick(1920), 2)
        self.assertEqual(midi.bar_number_at_tick(3840), 3)
        self.assertEqual(midi.bar_number_at_tick(5280), 4)
        self.assertEqual(midi.tick_for_bar(1), 0)
        self.assertEqual(midi.tick_for_bar(2), 1920)
        self.assertEqual(midi.tick_for_bar(3), 3840)
        self.assertEqual(midi.tick_for_bar(4), 5280)

    def test_reads_format_one_events_from_all_tracks_in_tick_order(self) -> None:
        conductor_track = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(9),
                b"Conductor",
                varlen(0),
                b"\xff\x51\x03\x07\xa1\x20",
                varlen(960),
                b"\xff\x2f\x00",
            ]
        )
        music_track = b"".join(
            [
                varlen(240),
                bytes([0x90, 60, 100]),
                varlen(240),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(1, 480, [conductor_track, music_track]), "format1.mid")

        self.assertEqual(midi.format, 1)
        self.assertEqual(len(midi.tracks), 2)
        self.assertEqual(midi.title, "Conductor")
        self.assertEqual(midi.length_ticks, 960)
        note_events = [event for event in midi.events if event.kind in ("note_on", "note_off")]
        self.assertEqual([event.tick for event in note_events], [240, 480])
        self.assertEqual([event.data for event in note_events], [bytes([60, 100]), bytes([60, 0])])

    def test_supports_running_status_channel_events(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(120),
                bytes([64, 96]),
                varlen(120),
                bytes([60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "running.mid")

        note_events = [event for event in midi.events if event.kind == "note_on"]
        self.assertEqual([event.tick for event in note_events], [0, 120, 240])
        self.assertEqual([event.channel for event in note_events], [0, 0, 0])
        self.assertEqual([event.data for event in note_events], [bytes([60, 100]), bytes([64, 96]), bytes([60, 0])])

    def test_reports_running_status_without_prior_status(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([60, 100]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )

        with self.assertRaisesRegex(MidiFileError, "Running status used before status byte"):
            read_temp_smf(smf_data(0, 480, [track]), "bad-running.mid")

    def test_reads_sysex_escape_and_continuation_events(self) -> None:
        track = b"".join(
            [
                varlen(0),
                bytes([0xF0]),
                varlen(5),
                bytes.fromhex("7e 7f 09 01 f7"),
                varlen(240),
                bytes([0xF7]),
                varlen(4),
                bytes.fromhex("43 12 00 f7"),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "sysex.mid")

        sysex_events = [event for event in midi.events if event.kind == "sysex"]
        self.assertEqual([event.tick for event in sysex_events], [0, 240])
        self.assertEqual(sysex_events[0].data, bytes.fromhex("7e 7f 09 01 f7"))
        self.assertEqual(sysex_events[1].data, bytes.fromhex("43 12 00 f7"))

    def test_reads_time_signature_key_signature_lyrics_and_markers(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x58\x04\x06\x03\x18\x08",
                varlen(0),
                b"\xff\x59\x02\xfd\x01",
                varlen(0),
                b"\xff\x05",
                varlen(5),
                b"Hello",
                varlen(240),
                b"\xff\x06",
                varlen(6),
                b"Verse1",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "metadata.mid")

        self.assertEqual(len(midi.time_signatures), 1)
        self.assertEqual(midi.time_signatures[0].numerator, 6)
        self.assertEqual(midi.time_signatures[0].denominator, 8)
        self.assertEqual(len(midi.key_signatures), 1)
        self.assertEqual(midi.key_signatures[0].sharps_flats, -3)
        self.assertTrue(midi.key_signatures[0].minor)
        self.assertEqual(
            [(event.track, event.tick, event.meta_type, event.text) for event in midi.text_events],
            [(0, 0, 0x05, "Hello"), (0, 240, 0x06, "Verse1")],
        )

    def test_preserves_track_and_instrument_names_as_track_metadata(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(5),
                b"Piano",
                varlen(0),
                b"\xff\x04",
                varlen(11),
                b"Grand Piano",
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(120),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "track-names.mid")

        self.assertEqual(midi.tracks[0].name, "Piano")
        self.assertEqual(midi.tracks[0].instrument_name, "Grand Piano")

    def test_preserves_original_track_numbers_for_meta_and_channel_events(self) -> None:
        track0 = b"".join(
            [
                varlen(0),
                b"\xff\x03",
                varlen(5),
                b"Intro",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        track1 = b"".join(
            [
                varlen(0),
                bytes([0x90, 60, 100]),
                varlen(120),
                bytes([0x80, 60, 0]),
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(1, 480, [track0, track1]), "track-numbers.mid")

        event_summary = [
            (event.track, event.kind, event.meta_type, event.channel, event.tick)
            for event in midi.events
        ]
        self.assertEqual(
            event_summary,
            [
                (0, "meta", 0x03, None, 0),
                (0, "meta", 0x2F, None, 0),
                (1, "note_on", None, 0, 0),
                (1, "note_off", None, 0, 120),
                (1, "meta", 0x2F, None, 120),
            ],
        )

    def test_auto_detects_cp1252_text_events(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x01",
                varlen(7),
                b"Euro \x801",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "cp1252.mid")

        self.assertEqual(midi.text_events[0].text, "Euro €1")

    def test_auto_detects_latin1_karaoke_lyrics(self) -> None:
        track = b"".join(
            [
                varlen(0),
                b"\xff\x05",
                varlen(3),
                b"Ol\xe1",
                varlen(0),
                b"\xff\x2f\x00",
            ]
        )
        midi = read_temp_smf(smf_data(0, 480, [track]), "latin1.kar")

        self.assertEqual(midi.text_events[0].meta_type, 0x05)
        self.assertEqual(midi.text_events[0].text, "Olá")


if __name__ == "__main__":
    unittest.main()

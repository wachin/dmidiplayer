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
    def test_rejects_invalid_header(self) -> None:
        with self.assertRaisesRegex(MidiFileError, "Not a Standard MIDI File"):
            read_temp_smf(b"not midi", "not-midi.mid")

    def test_rejects_wrk_files_with_explicit_message(self) -> None:
        with self.assertRaisesRegex(MidiFileError, r"Cakewalk WRK files are not supported yet \(detected version 2\.1\)"):
            read_temp_smf(b"CAKEWALK\x00\x01\x02\xff", "song.wrk")

    def test_rejects_invalid_wrk_file_format(self) -> None:
        with self.assertRaisesRegex(MidiFileError, "Invalid Cakewalk WRK file format"):
            read_temp_smf(b"not-a-wrk", "song.wrk")

    def test_rejects_corrupted_wrk_chunk_header(self) -> None:
        corrupted = b"CAKEWALK\x00\x01\x02" + bytes([10]) + struct.pack("<I", 20) + b"\x00\x00"
        with self.assertRaisesRegex(MidiFileError, "Corrupted Cakewalk WRK file"):
            read_temp_smf(corrupted, "broken.wrk")

    def test_reports_wrk_timebase_from_first_chunk(self) -> None:
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(10, struct.pack("<H", 120)) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, timebase 120\)",
        ):
            read_temp_smf(wrk, "timebase.wrk")

    def test_reports_wrk_software_version_from_first_chunk(self) -> None:
        payload = bytes([6]) + b"Cake 7"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(74, payload) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, saved by Cake 7\)",
        ):
            read_temp_smf(wrk, "softver.wrk")

    def test_reports_wrk_track_name_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 0) + bytes([5]) + b"Piano"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(24, payload) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, track 1 'Piano'\)",
        ):
            read_temp_smf(wrk, "trackname.wrk")

    def test_reports_wrk_comments_from_first_chunk(self) -> None:
        payload = struct.pack("<H", 5) + b"Notes"
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(8, payload) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, comments 'Notes'\)",
        ):
            read_temp_smf(wrk, "comments.wrk")

    def test_reports_wrk_track_volume_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 0, 96)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(19, payload) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, track 1 volume 96\)",
        ):
            read_temp_smf(wrk, "trackvol.wrk")

    def test_reports_wrk_track_bank_from_first_chunk(self) -> None:
        payload = struct.pack("<HH", 0, 2048)
        wrk = b"CAKEWALK\x00\x01\x02" + wrk_chunk(30, payload) + b"\xff"
        with self.assertRaisesRegex(
            MidiFileError,
            r"Cakewalk WRK files are not supported yet \(detected version 2\.1, track 1 bank 2048\)",
        ):
            read_temp_smf(wrk, "trackbank.wrk")

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


if __name__ == "__main__":
    unittest.main()

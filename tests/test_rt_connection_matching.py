from __future__ import annotations

import unittest

from drumstick_py.rt import MidiConnection


class MidiConnectionMatchingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MidiConnection(
            driver="alsa",
            name="128:0 FLUID Synth: Synth input port",
            client=128,
            port=0,
            client_name="FLUID Synth",
            port_name="Synth input port",
        )

    def test_matches_exact_address(self) -> None:
        self.assertTrue(self.connection.matches("128:0"))

    def test_matches_address_with_whitespace(self) -> None:
        self.assertTrue(self.connection.matches("  128 : 0  "))

    def test_matches_client_name_substring(self) -> None:
        self.assertTrue(self.connection.matches("fluid"))

    def test_matches_client_and_port_tokens_across_fields(self) -> None:
        self.assertTrue(self.connection.matches("fluid input"))

    def test_matches_port_name_substring(self) -> None:
        self.assertTrue(self.connection.matches("synth input"))

    def test_matches_client_port_compact_colon_format(self) -> None:
        self.assertTrue(self.connection.matches("fluid synth:synth input port"))

    def test_matches_ignores_punctuation(self) -> None:
        self.assertTrue(self.connection.matches("fluid-synth"))

    def test_empty_query_is_false(self) -> None:
        self.assertFalse(self.connection.matches(""))


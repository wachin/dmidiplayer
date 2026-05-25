from __future__ import annotations

import os
import unittest
from unittest import mock

from drumstick_py.rt import AlsaSequencerOutput, MidiConnection, MidiOutputError


class AlsaSubscriptionsTest(unittest.TestCase):
    def test_disconnect_all_uses_active_connections(self) -> None:
        """disconnect_all() should consult connected_connections() first.

        ALSA subscriptions can be created outside this process. Even without
        ALSA available, we can verify disconnect_all delegates to
        connected_connections() rather than internal bookkeeping.
        """

        output = AlsaSequencerOutput.__new__(AlsaSequencerOutput)
        c1 = MidiConnection(driver="alsa", name="128:0 Test: Port", client=128, port=0)
        c2 = MidiConnection(driver="alsa", name="129:1 Other: Port", client=129, port=1)
        disconnected: list[MidiConnection] = []

        with mock.patch.object(output, "connected_connections", return_value=[c1, c2]):
            with mock.patch.object(output, "disconnect_from", side_effect=lambda conn: disconnected.append(conn)):
                output.disconnect_all()

        self.assertEqual(disconnected, [c1, c2])

    def test_connected_connections_queries_kernel_state(self) -> None:
        if not os.path.exists("/dev/snd/seq"):
            self.skipTest("ALSA sequencer device (/dev/snd/seq) not available")

        try:
            output = AlsaSequencerOutput("dmidiplayer test")
        except MidiOutputError as exc:
            self.skipTest(str(exc))

        try:
            connections = output.connected_connections()
        finally:
            output.close()

        self.assertIsInstance(connections, list)

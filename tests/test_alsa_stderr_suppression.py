from __future__ import annotations

import os
import unittest

from drumstick_py.rt import _suppress_stderr_fd


def _capture_stderr_fd(callback) -> bytes:
    saved = os.dup(2)
    read_fd, write_fd = os.pipe()
    try:
        os.dup2(write_fd, 2)
        os.close(write_fd)
        callback()
    finally:
        os.dup2(saved, 2)
        os.close(saved)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(read_fd, 4096)
        if not chunk:
            break
        chunks.append(chunk)
    os.close(read_fd)
    return b"".join(chunks)


class AlsaStderrSuppressionTest(unittest.TestCase):
    def test_suppressed_context_drops_fd2_writes(self) -> None:
        def run() -> None:
            with _suppress_stderr_fd(True):
                os.write(2, b"alsa-noise")

        data = _capture_stderr_fd(run)
        self.assertEqual(data, b"")

    def test_disabled_context_keeps_fd2_writes(self) -> None:
        def run() -> None:
            with _suppress_stderr_fd(False):
                os.write(2, b"alsa-noise")

        data = _capture_stderr_fd(run)
        self.assertIn(b"alsa-noise", data)


from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.guiplayer_ui import GuiPlayerUiWindow
from dmidiplayer_py.rhythmview import RhythmView
from tests.test_sequence_player import OutputStub


class FakeBackendManager:
    def __init__(self) -> None:
        self.output = OutputStub()
        self.output.name = "Dummy output"

    def create_output(self, driver: str = "dummy", connection: str | None = None) -> OutputStub:
        return self.output


class TestGuiPlayerUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_can_load_guiplayer_ui(self) -> None:
        window = GuiPlayerUiWindow(backend=FakeBackendManager())
        self.assertIsNotNone(window.actionOpen)
        self.assertIsNotNone(window.actionPlay)
        self.assertIsNotNone(window.actionStop)
        self.assertIsInstance(window.rhythm, RhythmView)


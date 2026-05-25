from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from dmidiplayer_py.loopdialog_ui import LoopDialog


class TestLoopDialogUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_can_load_loopdialog_ui(self) -> None:
        dialog = LoopDialog()
        self.assertIsNotNone(dialog.spinFrom)
        self.assertIsNotNone(dialog.spinTo)
        dialog.set_bar_range(1, 10)
        dialog.set_bars(2, 5)
        self.assertEqual(dialog.bars(), (2, 5))


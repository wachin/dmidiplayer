from __future__ import annotations

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog


class LoopDialog(QDialog):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parents[1] / "loopdialog.ui"
        uic.loadUi(str(ui_path), self, package="dmidiplayer_py")

    def set_bar_range(self, minimum: int, maximum: int) -> None:
        minimum = max(1, minimum)
        maximum = max(minimum, maximum)
        self.spinFrom.setRange(minimum, maximum)
        self.spinTo.setRange(minimum, maximum)

    def set_bars(self, start_bar: int, end_bar: int) -> None:
        start_bar = max(1, start_bar)
        end_bar = max(start_bar, end_bar)
        self.spinFrom.setValue(start_bar)
        self.spinTo.setValue(end_bar)

    def bars(self) -> tuple[int, int]:
        start_bar = max(1, int(self.spinFrom.value()))
        end_bar = max(start_bar, int(self.spinTo.value()))
        return (start_bar, end_bar)


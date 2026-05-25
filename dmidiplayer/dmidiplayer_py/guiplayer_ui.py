from __future__ import annotations

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from drumstick_py import BackendManager, MidiFileError

from .player import SequencePlayer


class GuiPlayerUiWindow(QMainWindow):
    def __init__(self, backend: BackendManager | None = None) -> None:
        super().__init__()
        ui_path = Path(__file__).resolve().parents[1] / "guiplayer.ui"
        uic.loadUi(str(ui_path), self, package="dmidiplayer_py")

        self._backend = backend or BackendManager(self)
        self._output = self._backend.create_output()
        self._player = SequencePlayer(self._output, self)
        self._player.positionChanged.connect(self._on_position_changed)

        self.actionOpen.triggered.connect(self._open_file)
        self.actionQuit.triggered.connect(self.close)
        self.actionPlay.triggered.connect(self._player.play)
        self.actionStop.triggered.connect(self._player.stop)
        self.actionPause.toggled.connect(self._on_pause_toggled)

        self.actionBackward.triggered.connect(self._seek_previous_bar)
        self.actionForward.triggered.connect(self._seek_next_bar)

        self.sliderTempo.valueChanged.connect(self._on_tempo_changed)
        self.btnTempo.clicked.connect(self._reset_tempo)
        self.volumeSlider.valueChanged.connect(self._on_volume_changed)
        self.btnVolume.clicked.connect(self._reset_volume)
        self.spinPitch.valueChanged.connect(self._on_pitch_changed)

        self.positionSlider.setTracking(False)
        self.positionSlider.valueChanged.connect(self._on_position_slider_changed)

        self._sync_controls_from_player()

    def _sync_controls_from_player(self) -> None:
        self.sliderTempo.setValue(self._player.tempo_percent)
        self.volumeSlider.setValue(self._player.volume_percent)
        self.spinPitch.setValue(self._player.pitch_shift)
        self.btnTempo.setText(f"tempo={self._player.tempo_percent}%")
        self.lblVolume.setText(f"{self._player.volume_percent}%")
        self.lblOther.setText(f"{self._player.sequence.bpm_at_tick(0):.0f} BPM")

    def _open_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open MIDI File"),
            "",
            self.tr("MIDI files (*.mid *.midi *.kar *.rmi);;All files (*.*)"),
        )
        if not file_name:
            return
        try:
            self._player.load_file(file_name)
        except MidiFileError as exc:
            QMessageBox.critical(self, self.tr("Failed to load MIDI file"), str(exc))
            return
        self.lblName.setText(Path(file_name).name)
        self._sync_controls_from_player()

    def _on_pause_toggled(self, enabled: bool) -> None:
        if enabled:
            self._player.pause()
        else:
            self._player.play()

    def _on_tempo_changed(self, value: int) -> None:
        self._player.set_tempo_percent(value)
        self.btnTempo.setText(f"tempo={self._player.tempo_percent}%")

    def _reset_tempo(self) -> None:
        self.sliderTempo.setValue(100)

    def _on_volume_changed(self, value: int) -> None:
        self._player.set_volume_percent(value)
        self.lblVolume.setText(f"{self._player.volume_percent}%")

    def _reset_volume(self) -> None:
        self.volumeSlider.setValue(100)

    def _on_pitch_changed(self, value: int) -> None:
        self._player.set_pitch_shift(value)

    def _on_position_changed(self, tick: int, total: int) -> None:
        self.positionSlider.setMaximum(max(0, total))
        with QSignalBlocker(self.positionSlider):
            self.positionSlider.setValue(max(0, min(tick, total)))
        bar = self._player.sequence.bar_number_at_tick(tick)
        self.lblPos.setText(self.tr("Bar {bar}").format(bar=bar))
        self.lblOther.setText(f"{self._player.sequence.bpm_at_tick(tick):.0f} BPM")

    def _on_position_slider_changed(self, tick: int) -> None:
        self._player.seek(tick)

    def _seek_previous_bar(self) -> None:
        current_bar = self._player.sequence.bar_number_at_tick(self.positionSlider.value())
        target_bar = max(1, current_bar - 1)
        self._player.seek(self._player.sequence.tick_for_bar(target_bar))

    def _seek_next_bar(self) -> None:
        current_bar = self._player.sequence.bar_number_at_tick(self.positionSlider.value())
        target_bar = min(self._player.sequence.bar_count, current_bar + 1)
        self._player.seek(self._player.sequence.tick_for_bar(target_bar))


def main() -> int:
    app = QApplication([])
    window = GuiPlayerUiWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


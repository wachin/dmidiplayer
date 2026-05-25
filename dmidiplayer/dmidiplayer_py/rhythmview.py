from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class RhythmView(QWidget):
    MAX_BEATS = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rhythm_view")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.summary_label = QLabel(self.tr("Rhythm: 4/4 - Bar 1 Beat 1 - 120 BPM"), self)
        self.summary_label.setObjectName("rhythm_summary_label")
        layout.addWidget(self.summary_label)

        beats_row = QWidget(self)
        beats_row.setObjectName("rhythm_beats_row")
        beats_layout = QHBoxLayout(beats_row)
        beats_layout.setContentsMargins(0, 0, 0, 0)
        beats_layout.setSpacing(4)
        self.beat_labels: list[QLabel] = []
        for index in range(self.MAX_BEATS):
            label = QLabel(str(index + 1), beats_row)
            label.setObjectName(f"rhythm_beat_{index + 1}")
            label.setMinimumWidth(24)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFrameShape(QFrame.Shape.Box)
            beats_layout.addWidget(label)
            self.beat_labels.append(label)
        beats_layout.addStretch(1)
        layout.addWidget(beats_row)

        self.update_state(4, 4, 1, 1, 120.0)

    def update_state(self, numerator: int, denominator: int, bar: int, beat: int, bpm: float) -> None:
        visible_beats = max(1, min(self.MAX_BEATS, numerator))
        current_beat = max(1, min(visible_beats, beat))
        self.summary_label.setText(
            self.tr("Rhythm: {numerator}/{denominator} - Bar {bar} Beat {beat} - {bpm:.0f} BPM").format(
                numerator=numerator,
                denominator=denominator,
                bar=bar,
                beat=current_beat,
                bpm=bpm,
            )
        )
        for index, label in enumerate(self.beat_labels):
            beat_number = index + 1
            is_visible = beat_number <= visible_beats
            label.setVisible(is_visible)
            if not is_visible:
                continue
            marker = "X" if beat_number == current_beat else "-"
            label.setText(f"{beat_number}:{marker}")

    def clear(self) -> None:
        self.update_state(4, 4, 1, 1, 120.0)


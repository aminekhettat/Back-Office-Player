"""
Waveform display widget.

Draws an RMS-envelope waveform with A/B markers, segment ticks, and a
playhead.  Left-clicking emits ``seek_requested(float)`` with the
corresponding audio position in seconds.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.1
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class WaveformWidget(QWidget):
    """
    Read-only waveform visualisation with seek-by-click.

    Signals
    -------
    seek_requested : float
        Emitted when the user left-clicks the widget, carrying the
        requested audio position in seconds.
    """

    seek_requested = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._audio: Optional[np.ndarray] = None
        self._sr: int = 0
        self._envelope: Optional[np.ndarray] = None
        self._position: float = 0.0
        self._duration: float = 0.0
        self._point_a: Optional[float] = None
        self._point_b: Optional[float] = None
        self._segments: list = []

        self.setMinimumHeight(80)
        self.setAccessibleName("Waveform display")
        self.setAccessibleDescription(
            "Visual representation of the audio waveform. "
            "Shows the current playback position, A and B loop points, "
            "and named segments. Left-click to seek to that position."
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_audio_data(self, audio: np.ndarray, sr: int) -> None:
        """
        Load new audio data and recompute the RMS envelope.

        Parameters
        ----------
        audio : np.ndarray
            Mono float32 audio samples.
        sr : int
            Sample rate in Hz.
        """
        self._audio = audio
        self._sr = sr
        self._duration = len(audio) / sr if sr > 0 else 0.0
        self._position = 0.0
        self._compute_envelope()
        self.update()

    def set_position(self, seconds: float) -> None:
        """Update the playhead without triggering a repaint storm."""
        self._position = seconds
        self.update()

    def set_point_a(self, seconds: Optional[float]) -> None:
        """Set or clear the A loop marker."""
        self._point_a = seconds
        self.update()

    def set_point_b(self, seconds: Optional[float]) -> None:
        """Set or clear the B loop marker."""
        self._point_b = seconds
        self.update()

    def set_segments(self, segments: list) -> None:
        """
        Provide the list of :class:`~core.segment.Segment` objects to
        draw as tick marks.
        """
        self._segments = list(segments)
        self.update()

    def clear(self) -> None:
        """Reset all state and clear the display."""
        self._audio = None
        self._sr = 0
        self._envelope = None
        self._position = 0.0
        self._duration = 0.0
        self._point_a = None
        self._point_b = None
        self._segments = []
        self.update()

    # ------------------------------------------------------------------ #
    # Qt overrides
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        # Dark background
        painter.fillRect(0, 0, w, h, QColor(30, 30, 30))

        # Waveform bars
        if self._envelope is not None and len(self._envelope) > 0:
            n = len(self._envelope)
            mid = h / 2
            painter.setPen(QPen(QColor(100, 180, 255), 1))
            for i, v in enumerate(self._envelope):
                x = int(i * w / n)
                bar_h = int(v * mid * 0.9)
                painter.drawLine(x, int(mid - bar_h), x, int(mid + bar_h))

        if self._duration <= 0:
            painter.end()
            return

        # Segment ticks (dotted purple)
        seg_pen = QPen(QColor(160, 80, 220), 1)
        seg_pen.setStyle(Qt.DotLine)
        for seg in self._segments:
            sx = int(seg.start_sec / self._duration * w)
            ex = int(seg.end_sec / self._duration * w)
            painter.setPen(seg_pen)
            painter.drawLine(sx, 0, sx, h)
            painter.drawLine(ex, 0, ex, h)

        # A marker (green)
        if self._point_a is not None:
            ax = int(self._point_a / self._duration * w)
            painter.setPen(QPen(QColor(0, 200, 0), 2))
            painter.drawLine(ax, 0, ax, h)
            painter.setPen(QPen(QColor(0, 200, 0), 1))
            painter.drawText(ax + 2, 12, "A")

        # B marker (red)
        if self._point_b is not None:
            bx = int(self._point_b / self._duration * w)
            painter.setPen(QPen(QColor(220, 0, 0), 2))
            painter.drawLine(bx, 0, bx, h)
            painter.setPen(QPen(QColor(220, 0, 0), 1))
            painter.drawText(bx + 2, 12, "B")

        # Playhead (orange)
        px = int(self._position / self._duration * w)
        painter.setPen(QPen(QColor(255, 140, 0), 2))
        painter.drawLine(px, 0, px, h)

        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._duration > 0:
            ratio = event.position().x() / self.width()
            self.seek_requested.emit(ratio * self._duration)

    def resizeEvent(self, event) -> None:
        # Recompute envelope at new width
        self._compute_envelope()
        super().resizeEvent(event)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    def _compute_envelope(self) -> None:
        """Compute the RMS amplitude envelope used for rendering."""
        if self._audio is None or len(self._audio) == 0:
            self._envelope = None
            return

        n_frames = max(self.width(), 800) if self.width() > 0 else 800
        total = len(self._audio)
        hop = max(1, total // n_frames)

        frames = []
        for i in range(0, total, hop):
            chunk = self._audio[i : i + hop]
            if len(chunk) > 0:
                rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
            else:  # pragma: no cover
                rms = 0.0
            frames.append(rms)

        env = np.array(frames, dtype=np.float32)
        max_val = env.max()
        if max_val > 0:
            env = env / max_val
        self._envelope = env

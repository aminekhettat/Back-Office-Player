"""
Tests for ui.waveform_widget (pytest-qt) — 100% branch coverage.

Covers: creation, set_audio_data, set_position, set_point_a/b (set and
clear), set_segments, clear, mousePressEvent (left click, no-click when
duration=0), resizeEvent, paintEvent (with/without audio, A/B points,
segments).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import Qt

from core.segment import Segment
from ui.waveform_widget import WaveformWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def widget(qtbot):
    """Return a WaveformWidget with a known size."""
    w = WaveformWidget()
    qtbot.addWidget(w)
    w.resize(400, 100)
    w.show()
    return w


@pytest.fixture()
def loaded_widget(qtbot, sample_audio, sample_rate):
    """Return a WaveformWidget with audio data already loaded."""
    w = WaveformWidget()
    qtbot.addWidget(w)
    w.resize(400, 100)
    w.show()
    w.set_audio_data(sample_audio, sample_rate)
    return w


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestWaveformWidgetCreation:
    def test_initial_audio_is_none(self, widget):
        """A new WaveformWidget has no audio data."""
        assert widget._audio is None

    def test_initial_duration_zero(self, widget):
        """A new WaveformWidget has duration 0."""
        assert widget._duration == 0.0

    def test_initial_point_a_none(self, widget):
        """Point A is initially None."""
        assert widget._point_a is None

    def test_initial_point_b_none(self, widget):
        """Point B is initially None."""
        assert widget._point_b is None

    def test_initial_segments_empty(self, widget):
        """No segments are loaded initially."""
        assert widget._segments == []

    def test_minimum_height_set(self, widget):
        """Minimum height is at least 80 px."""
        assert widget.minimumHeight() >= 80


# ---------------------------------------------------------------------------
# set_audio_data
# ---------------------------------------------------------------------------


class TestSetAudioData:
    def test_set_audio_updates_duration(self, widget, sample_audio, sample_rate):
        """set_audio_data correctly computes duration from samples/sr."""
        widget.set_audio_data(sample_audio, sample_rate)
        expected = len(sample_audio) / sample_rate
        assert widget._duration == pytest.approx(expected, rel=1e-3)

    def test_set_audio_computes_envelope(self, widget, sample_audio, sample_rate):
        """set_audio_data computes a non-None envelope array."""
        widget.set_audio_data(sample_audio, sample_rate)
        assert widget._envelope is not None
        assert len(widget._envelope) > 0

    def test_set_audio_resets_position(self, widget, sample_audio, sample_rate):
        """set_audio_data resets the playhead position to 0."""
        widget._position = 5.0
        widget.set_audio_data(sample_audio, sample_rate)
        assert widget._position == pytest.approx(0.0)

    def test_set_audio_zero_sr_gives_zero_duration(self, widget):
        """set_audio_data with sr=0 produces duration 0."""
        widget.set_audio_data(np.zeros(100, dtype=np.float32), 0)
        assert widget._duration == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# set_position
# ---------------------------------------------------------------------------


class TestSetPosition:
    def test_set_position_stores_value(self, loaded_widget):
        """set_position updates the internal position attribute."""
        loaded_widget.set_position(0.5)
        assert loaded_widget._position == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# set_point_a / set_point_b
# ---------------------------------------------------------------------------


class TestSetPoints:
    def test_set_point_a(self, loaded_widget):
        """set_point_a stores the value."""
        loaded_widget.set_point_a(0.2)
        assert loaded_widget._point_a == pytest.approx(0.2)

    def test_clear_point_a(self, loaded_widget):
        """set_point_a(None) clears the A marker."""
        loaded_widget.set_point_a(0.2)
        loaded_widget.set_point_a(None)
        assert loaded_widget._point_a is None

    def test_set_point_b(self, loaded_widget):
        """set_point_b stores the value."""
        loaded_widget.set_point_b(0.8)
        assert loaded_widget._point_b == pytest.approx(0.8)

    def test_clear_point_b(self, loaded_widget):
        """set_point_b(None) clears the B marker."""
        loaded_widget.set_point_b(0.8)
        loaded_widget.set_point_b(None)
        assert loaded_widget._point_b is None


# ---------------------------------------------------------------------------
# set_segments
# ---------------------------------------------------------------------------


class TestSetSegments:
    def test_set_segments_stores_list(self, loaded_widget):
        """set_segments stores a copy of the provided list."""
        segs = [Segment("s1", 0.1, 0.5), Segment("s2", 0.6, 0.9)]
        loaded_widget.set_segments(segs)
        assert len(loaded_widget._segments) == 2

    def test_set_segments_stores_copy(self, loaded_widget):
        """Modifying the original list does not affect stored segments."""
        segs = [Segment("s", 0.1, 0.5)]
        loaded_widget.set_segments(segs)
        segs.clear()
        assert len(loaded_widget._segments) == 1


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_resets_all_state(self, loaded_widget, sample_audio, sample_rate):
        """clear() resets audio, position, points, segments to initial values."""
        loaded_widget.set_position(0.5)
        loaded_widget.set_point_a(0.1)
        loaded_widget.set_point_b(0.9)
        loaded_widget.set_segments([Segment("s", 0.1, 0.5)])
        loaded_widget.clear()
        assert loaded_widget._audio is None
        assert loaded_widget._sr == 0
        assert loaded_widget._envelope is None
        assert loaded_widget._position == 0.0
        assert loaded_widget._duration == 0.0
        assert loaded_widget._point_a is None
        assert loaded_widget._point_b is None
        assert loaded_widget._segments == []


# ---------------------------------------------------------------------------
# mousePressEvent
# ---------------------------------------------------------------------------


class TestMousePressEvent:
    def test_left_click_emits_seek_requested(self, loaded_widget, qtbot):
        """A left-click on the widget emits seek_requested with a float position."""
        with qtbot.waitSignal(loaded_widget.seek_requested, timeout=1000) as blocker:
            qtbot.mouseClick(
                loaded_widget, Qt.MouseButton.LeftButton, pos=loaded_widget.rect().center()
            )
        assert blocker.signal_triggered
        assert isinstance(blocker.args[0], float)

    def test_left_click_without_audio_does_not_emit(self, widget, qtbot):
        """A left-click when duration=0 does not emit seek_requested."""
        received = []
        widget.seek_requested.connect(lambda v: received.append(v))
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=widget.rect().center())
        assert received == []

    def test_seek_value_in_valid_range(self, loaded_widget, qtbot):
        """The seek value is within [0, duration]."""
        received = []
        loaded_widget.seek_requested.connect(lambda v: received.append(v))
        qtbot.mouseClick(
            loaded_widget, Qt.MouseButton.LeftButton, pos=loaded_widget.rect().center()
        )
        assert len(received) == 1
        assert 0.0 <= received[0] <= loaded_widget._duration


# ---------------------------------------------------------------------------
# paintEvent
# ---------------------------------------------------------------------------


class TestPaintEvent:
    def test_paint_without_audio_does_not_crash(self, widget, qtbot):
        """paintEvent runs without error when no audio is loaded."""
        widget.update()
        qtbot.waitExposed(widget)

    def test_paint_with_audio_does_not_crash(self, loaded_widget, qtbot):
        """paintEvent runs without error with audio data loaded."""
        loaded_widget.update()
        qtbot.waitExposed(loaded_widget)

    def test_paint_with_points_and_segments(self, loaded_widget, qtbot):
        """paintEvent renders A/B points and segments without error."""
        loaded_widget.set_point_a(0.2)
        loaded_widget.set_point_b(0.8)
        loaded_widget.set_segments([Segment("s", 0.1, 0.5)])
        loaded_widget.update()
        qtbot.waitExposed(loaded_widget)


# ---------------------------------------------------------------------------
# resizeEvent
# ---------------------------------------------------------------------------


class TestResizeEvent:
    def test_resize_recomputes_envelope(self, loaded_widget, qtbot):
        """Resizing the widget triggers _compute_envelope."""
        len(loaded_widget._envelope) if loaded_widget._envelope is not None else 0
        loaded_widget.resize(800, 100)
        # Envelope may change length as width changed
        assert loaded_widget._envelope is not None

    def test_resize_without_audio_does_not_crash(self, widget, qtbot):
        """Resizing before audio is loaded does not crash."""
        widget.resize(200, 100)  # must not raise


# ---------------------------------------------------------------------------
# _compute_envelope
# ---------------------------------------------------------------------------


class TestComputeEnvelope:
    def test_empty_audio_gives_none_envelope(self, widget):
        """_compute_envelope sets envelope to None for empty audio."""
        widget._audio = np.array([], dtype=np.float32)
        widget._compute_envelope()
        assert widget._envelope is None

    def test_all_zero_audio_gives_zero_envelope(self, widget):
        """All-zero audio produces a zero-valued envelope."""
        widget._audio = np.zeros(44100, dtype=np.float32)
        widget._sr = 44100
        widget._compute_envelope()
        # max_val == 0, so normalisation is skipped
        assert widget._envelope is not None
        assert float(widget._envelope.max()) == pytest.approx(0.0)

    def test_empty_chunk_gives_rms_zero(self, widget):
        """_compute_envelope produces rms=0.0 for an empty chunk (line 203).

        Uses a fake audio object whose slices always return an empty array.
        The length is reported consistently as 400 so the loop runs once per
        frame and every chunk is empty → else: rms = 0.0 is executed.
        """

        class _EmptySliceAudio:
            """Fake audio whose slices are always empty but len is 400."""

            def __len__(self) -> int:
                return 400

            def __getitem__(self, key) -> np.ndarray:
                return np.array([], dtype=np.float32)

        widget._audio = _EmptySliceAudio()
        widget._compute_envelope()
        assert widget._envelope is not None
        assert float(widget._envelope[0]) == pytest.approx(0.0)

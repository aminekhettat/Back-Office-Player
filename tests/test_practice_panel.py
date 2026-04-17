"""
Tests for ui.practice_panel (pytest-qt) — 100% branch coverage.

Covers: creation, get_session, start_session, stop_session, reset_session,
get_active_session (active / None), _tick, _on_progressive_changed.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import pytest

from core.practice_session import PracticeSession
from ui.practice_panel import PracticePanel


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def panel(qtbot):
    """Return a PracticePanel widget."""
    p = PracticePanel()
    qtbot.addWidget(p)
    p.show()
    return p


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

class TestPracticePanelCreation:
    def test_widget_is_created(self, panel):
        """PracticePanel instantiates without error."""
        assert panel is not None

    def test_initial_label_is_zero(self, panel):
        """Session time label shows '00:00:00' before any session starts."""
        assert panel.lbl_session_time.text() == "00:00:00"

    def test_progressive_controls_hidden_initially(self, panel):
        """Progressive tempo controls are hidden when checkbox is unchecked."""
        assert not panel.chk_progressive.isChecked()
        # The spinboxes should be hidden
        assert not panel.spn_tempo_start.isVisible()
        assert not panel.spn_tempo_step.isVisible()
        assert not panel.spn_tempo_target.isVisible()


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------

class TestGetSession:
    def test_returns_practice_session(self, panel):
        """get_session returns a PracticeSession instance."""
        s = panel.get_session()
        assert isinstance(s, PracticeSession)

    def test_get_session_loop_count(self, panel):
        """get_session reflects the loop count spinbox value."""
        panel.spn_loop_count.setValue(5)
        s = panel.get_session()
        assert s.loop_count == 5

    def test_get_session_loop_delay(self, panel):
        """get_session reflects the loop delay spinbox value."""
        panel.spn_loop_delay.setValue(2.0)
        s = panel.get_session()
        assert s.loop_delay == pytest.approx(2.0)

    def test_get_session_progressive_false(self, panel):
        """get_session reflects progressive=False when checkbox unchecked."""
        panel.chk_progressive.setChecked(False)
        s = panel.get_session()
        assert s.progressive_tempo is False

    def test_get_session_progressive_true(self, panel):
        """get_session reflects progressive=True when checkbox is checked."""
        panel.chk_progressive.setChecked(True)
        s = panel.get_session()
        assert s.progressive_tempo is True

    def test_get_session_tempo_values(self, panel):
        """get_session reflects start/step/target spinbox values."""
        panel.chk_progressive.setChecked(True)
        panel.spn_tempo_start.setValue(0.7)
        panel.spn_tempo_step.setValue(0.1)
        panel.spn_tempo_target.setValue(1.0)
        s = panel.get_session()
        assert s.tempo_start == pytest.approx(0.7)
        assert s.tempo_step == pytest.approx(0.1)
        assert s.tempo_target == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------

class TestStartSession:
    def test_start_session_returns_active_session(self, panel):
        """start_session returns an active PracticeSession."""
        s = panel.start_session()
        assert isinstance(s, PracticeSession)
        assert s.is_active

    def test_start_session_resets_label(self, panel):
        """start_session resets the elapsed-time label to '00:00:00'."""
        panel.lbl_session_time.setText("99:99:99")
        panel.start_session()
        assert panel.lbl_session_time.text() == "00:00:00"

    def test_start_session_starts_timer(self, panel):
        """start_session starts the internal QTimer."""
        panel.start_session()
        assert panel._timer.isActive()
        panel.stop_session()


# ---------------------------------------------------------------------------
# stop_session
# ---------------------------------------------------------------------------

class TestStopSession:
    def test_stop_session_stops_timer(self, panel):
        """stop_session stops the internal QTimer."""
        panel.start_session()
        panel.stop_session()
        assert not panel._timer.isActive()

    def test_stop_session_deactivates_session(self, panel):
        """stop_session deactivates the current PracticeSession."""
        panel.start_session()
        panel.stop_session()
        # _session is still set, but is no longer active
        assert panel._session is not None
        assert not panel._session.is_active


# ---------------------------------------------------------------------------
# reset_session
# ---------------------------------------------------------------------------

class TestResetSession:
    def test_reset_clears_session(self, panel):
        """reset_session sets _session to None."""
        panel.start_session()
        panel.reset_session()
        assert panel._session is None

    def test_reset_resets_label(self, panel):
        """reset_session resets the elapsed-time label to '00:00:00'."""
        panel.start_session()
        panel.lbl_session_time.setText("01:00:00")
        panel.reset_session()
        assert panel.lbl_session_time.text() == "00:00:00"

    def test_reset_session_before_start_no_error(self, panel):
        """reset_session before any start() does not raise."""
        panel.reset_session()  # _session is None — must not raise


# ---------------------------------------------------------------------------
# get_active_session
# ---------------------------------------------------------------------------

class TestGetActiveSession:
    def test_returns_none_when_not_started(self, panel):
        """get_active_session returns None before start."""
        assert panel.get_active_session() is None

    def test_returns_session_when_active(self, panel):
        """get_active_session returns the active session after start."""
        panel.start_session()
        assert panel.get_active_session() is not None
        panel.stop_session()

    def test_returns_none_after_stop(self, panel):
        """get_active_session returns None after stop."""
        panel.start_session()
        panel.stop_session()
        assert panel.get_active_session() is None


# ---------------------------------------------------------------------------
# _tick
# ---------------------------------------------------------------------------

class TestTick:
    def test_tick_without_session_does_not_crash(self, panel):
        """_tick with no session does not raise."""
        panel._session = None
        panel._tick()  # must not raise

    def test_tick_updates_label(self, panel):
        """_tick updates the session time label from the session."""
        panel.start_session()
        panel._tick()
        # Label should still be a valid HH:MM:SS string
        text = panel.lbl_session_time.text()
        parts = text.split(":")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
        panel.stop_session()


# ---------------------------------------------------------------------------
# _on_progressive_changed
# ---------------------------------------------------------------------------

class TestOnProgressiveChanged:
    def test_check_shows_widgets(self, panel, qtbot):
        """Checking the progressive checkbox makes the spinboxes visible."""
        panel.chk_progressive.setChecked(True)
        assert panel.spn_tempo_start.isVisible()
        assert panel.spn_tempo_step.isVisible()
        assert panel.spn_tempo_target.isVisible()

    def test_uncheck_hides_widgets(self, panel, qtbot):
        """Unchecking the progressive checkbox hides the spinboxes."""
        panel.chk_progressive.setChecked(True)
        panel.chk_progressive.setChecked(False)
        assert not panel.spn_tempo_start.isVisible()

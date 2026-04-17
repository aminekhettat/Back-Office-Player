"""
Tests for core.practice_session — 100% branch coverage.

Covers: start/stop lifecycle, is_active, current_loop, current_tempo,
on_loop_completed (finite/infinite, progressive/not, stop trigger),
and get_elapsed() formatting.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import time

import pytest

from core.practice_session import PracticeSession


class TestPracticeSessionLifecycle:
    def test_initial_state_inactive(self):
        """A new session is not active before start() is called."""
        s = PracticeSession()
        assert not s.is_active

    def test_start_activates_session(self):
        """start() sets is_active to True."""
        s = PracticeSession()
        s.start()
        assert s.is_active

    def test_stop_deactivates_session(self):
        """stop() sets is_active to False."""
        s = PracticeSession()
        s.start()
        s.stop()
        assert not s.is_active

    def test_start_resets_loop_counter(self):
        """Calling start() again resets the loop counter to 0."""
        s = PracticeSession(loop_count=3)
        s.start()
        s.on_loop_completed()
        assert s.current_loop == 1
        s.start()
        assert s.current_loop == 0

    def test_start_resets_tempo(self):
        """Calling start() again resets tempo to tempo_start."""
        s = PracticeSession(
            progressive_tempo=True,
            tempo_start=0.8,
            tempo_step=0.1,
            tempo_target=1.0,
        )
        s.start()
        s.on_loop_completed()  # tempo becomes 0.9
        s.start()
        assert s.current_tempo == pytest.approx(0.8)

    def test_properties_read_correctly(self):
        """current_loop and current_tempo properties return internal state."""
        s = PracticeSession(tempo_start=0.75)
        assert s.current_loop == 0
        assert s.current_tempo == pytest.approx(0.75)


class TestLoopCompletion:
    def test_infinite_loops_never_stop(self):
        """loop_count=0 means infinite — on_loop_completed never returns True."""
        s = PracticeSession(loop_count=0)
        s.start()
        for _ in range(50):
            stop, _ = s.on_loop_completed()
            assert stop is False

    def test_finite_loops_stop_on_target(self):
        """on_loop_completed returns True at exactly loop_count loops."""
        s = PracticeSession(loop_count=3)
        s.start()
        results = [s.on_loop_completed() for _ in range(3)]
        stops = [r[0] for r in results]
        assert stops == [False, False, True]

    def test_finite_loops_deactivate_session(self):
        """Session becomes inactive after reaching loop_count."""
        s = PracticeSession(loop_count=2)
        s.start()
        s.on_loop_completed()
        s.on_loop_completed()
        assert not s.is_active

    def test_loop_counter_increments(self):
        """current_loop increments by 1 on each on_loop_completed call."""
        s = PracticeSession()
        s.start()
        for n in range(1, 5):
            s.on_loop_completed()
            assert s.current_loop == n

    def test_progressive_tempo_increments(self):
        """Progressive mode increases tempo by tempo_step per loop."""
        s = PracticeSession(
            progressive_tempo=True,
            tempo_start=0.8,
            tempo_step=0.1,
            tempo_target=1.0,
        )
        s.start()
        _, t1 = s.on_loop_completed()
        assert t1 == pytest.approx(0.9)
        _, t2 = s.on_loop_completed()
        assert t2 == pytest.approx(1.0)

    def test_progressive_tempo_capped_at_target(self):
        """Progressive tempo does not exceed tempo_target."""
        s = PracticeSession(
            progressive_tempo=True,
            tempo_start=0.95,
            tempo_step=0.1,
            tempo_target=1.0,
        )
        s.start()
        _, t = s.on_loop_completed()
        assert t == pytest.approx(1.0)

    def test_no_progressive_tempo_unchanged(self):
        """Non-progressive mode keeps tempo constant."""
        s = PracticeSession(progressive_tempo=False, tempo_start=0.8)
        s.start()
        _, t = s.on_loop_completed()
        assert t == pytest.approx(0.8)

    def test_returned_tempo_matches_current_tempo(self):
        """The tempo value in the tuple matches current_tempo property."""
        s = PracticeSession(
            progressive_tempo=True,
            tempo_start=0.7,
            tempo_step=0.05,
            tempo_target=1.0,
        )
        s.start()
        _, t = s.on_loop_completed()
        assert t == pytest.approx(s.current_tempo)


class TestElapsedTime:
    def test_elapsed_before_start_is_zero(self):
        """get_elapsed returns '00:00:00' before the session is started."""
        s = PracticeSession()
        assert s.get_elapsed() == "00:00:00"

    def test_elapsed_format_is_hhmmss(self):
        """get_elapsed returns a properly formatted HH:MM:SS string."""
        s = PracticeSession()
        s.start()
        elapsed = s.get_elapsed()
        parts = elapsed.split(":")
        assert len(parts) == 3
        assert all(len(p) == 2 for p in parts)
        assert all(p.isdigit() for p in parts)

    def test_elapsed_increases_with_time(self):
        """get_elapsed grows over time after start()."""
        s = PracticeSession()
        s.start()
        e1 = s.get_elapsed()
        time.sleep(0.05)
        # We can only test that it remains a valid "00:00:XX" string —
        # wall-clock precision varies on CI machines.
        e2 = s.get_elapsed()
        # Both must be valid HH:MM:SS
        assert len(e2.split(":")) == 3
        # seconds part of e1 should be <= seconds part of e2
        sec1 = int(e1.split(":")[2])
        sec2 = int(e2.split(":")[2])
        assert sec2 >= sec1


class TestPracticeSessionDefaults:
    def test_default_constructor_values(self):
        """Default constructor produces expected attribute values."""
        s = PracticeSession()
        assert s.loop_count == 0
        assert s.progressive_tempo is False
        assert s.tempo_start == pytest.approx(1.0)
        assert s.tempo_step == pytest.approx(0.05)
        assert s.tempo_target == pytest.approx(1.0)
        assert s.loop_delay == pytest.approx(0.0)

    def test_custom_constructor_values(self):
        """Custom constructor values are stored correctly."""
        s = PracticeSession(
            loop_count=5,
            progressive_tempo=True,
            tempo_start=0.6,
            tempo_step=0.1,
            tempo_target=1.2,
            loop_delay=1.5,
        )
        assert s.loop_count == 5
        assert s.progressive_tempo is True
        assert s.loop_delay == pytest.approx(1.5)

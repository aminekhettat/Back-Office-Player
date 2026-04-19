"""
Property-based tests using Hypothesis.

Tests domain invariants that must hold for *any* valid input, not just
hand-picked examples:
  - Segment serialisation roundtrip
  - SegmentManager insertion-order preservation
  - CommandHistory undo/redo stack invariants

Run with:  pytest tests/test_properties.py -m property

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import pytest

try:
    from hypothesis import given
    from hypothesis import settings as h_settings
    from hypothesis import strategies as st

    _HYPOTHESIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _HYPOTHESIS_AVAILABLE = False

pytestmark = pytest.mark.property

if not _HYPOTHESIS_AVAILABLE:  # pragma: no cover
    pytest.skip("hypothesis not installed — run: pip install hypothesis", allow_module_level=True)

from core.commands import AddSegmentCommand, CommandHistory
from core.segment import Segment
from core.segment_manager import SegmentManager

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_segment_name = st.text(min_size=1, max_size=50).filter(lambda s: s.strip())
_seconds = st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False)
_color = st.one_of(
    st.just(""),
    st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True),
)
_notes = st.text(max_size=200)
_category = st.text(max_size=50)
_count = st.integers(min_value=0, max_value=9999)


def _segment_strategy():
    return st.builds(
        Segment,
        name=_segment_name,
        start_sec=_seconds,
        end_sec=_seconds,
        notes=_notes,
        color=_color,
        category=_category,
        practice_count=_count,
    )


# ---------------------------------------------------------------------------
# Segment invariants
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestSegmentProperties:
    @given(_segment_strategy())
    def test_roundtrip_identity(self, seg: Segment) -> None:
        """Any Segment survives to_dict → from_dict without data loss."""
        assert Segment.from_dict(seg.to_dict()) == seg

    @given(_seconds, _seconds)
    def test_duration_never_negative(self, start: float, end: float) -> None:
        """duration() is always ≥ 0, regardless of start/end ordering."""
        seg = Segment("s", start, end)
        assert seg.duration() >= 0.0

    @given(_seconds, _seconds)
    def test_duration_correct_when_start_le_end(self, a: float, b: float) -> None:
        """When start ≤ end, duration equals end - start."""
        start, end = min(a, b), max(a, b)
        seg = Segment("s", start, end)
        assert seg.duration() == pytest.approx(end - start)

    @given(_segment_strategy())
    def test_to_dict_contains_required_keys(self, seg: Segment) -> None:
        """to_dict() always contains the mandatory keys."""
        d = seg.to_dict()
        for key in ("name", "start_sec", "end_sec", "notes", "color", "category", "practice_count"):
            assert key in d

    @given(st.text(min_size=1), _seconds, _seconds)
    def test_from_dict_minimal_keys_sufficient(self, name: str, start: float, end: float) -> None:
        """from_dict works with only the mandatory keys; optional keys default."""
        seg = Segment.from_dict({"name": name, "start_sec": start, "end_sec": end})
        assert seg.name == name
        assert seg.notes == ""
        assert seg.practice_count == 0


# ---------------------------------------------------------------------------
# SegmentManager invariants
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestSegmentManagerProperties:
    @given(st.lists(_segment_name, min_size=0, max_size=20, unique=True))
    def test_insertion_order_preserved(self, names: list[str]) -> None:
        """Segments are always returned in insertion order."""
        mgr = SegmentManager()
        for n in names:
            mgr.add_segment(Segment(n, 0.0, 1.0))
        assert [s.name for s in mgr.list_segments()] == names

    @given(st.lists(_segment_name, min_size=1, max_size=15, unique=True))
    def test_serialisation_roundtrip_preserves_names(self, names: list[str]) -> None:
        """to_dict → from_dict preserves names in the same order."""
        mgr = SegmentManager()
        for n in names:
            mgr.add_segment(Segment(n, 0.0, 1.0))
        mgr2 = SegmentManager.from_dict(mgr.to_dict())
        assert [s.name for s in mgr2.list_segments()] == names

    @given(st.lists(_segment_name, min_size=2, max_size=20, unique=True))
    def test_remove_decrements_count(self, names: list[str]) -> None:
        """Removing any segment decrements the total count by exactly 1."""
        mgr = SegmentManager()
        for n in names:
            mgr.add_segment(Segment(n, 0.0, 1.0))
        target = names[len(names) // 2]
        before = len(mgr.list_segments())
        mgr.remove_segment(target)
        assert len(mgr.list_segments()) == before - 1
        assert mgr.get_segment(target) is None

    @given(st.lists(_segment_name, min_size=1, max_size=20, unique=True))
    def test_list_segments_returns_copy(self, names: list[str]) -> None:
        """Mutating the list returned by list_segments does not affect the manager."""
        mgr = SegmentManager()
        for n in names:
            mgr.add_segment(Segment(n, 0.0, 1.0))
        lst = mgr.list_segments()
        original_count = len(lst)
        lst.clear()
        assert len(mgr.list_segments()) == original_count

    @given(
        st.lists(_segment_name, min_size=1, max_size=10, unique=True),
        st.text(max_size=20),
    )
    def test_filter_by_category_subset(self, names: list[str], category: str) -> None:
        """list_by_category always returns a subset of list_segments."""
        mgr = SegmentManager()
        for i, n in enumerate(names):
            cat = category if i % 2 == 0 else "other"
            mgr.add_segment(Segment(n, 0.0, 1.0, category=cat))
        filtered = mgr.list_by_category(category)
        all_names = {s.name for s in mgr.list_segments()}
        assert all(s.name in all_names for s in filtered)


# ---------------------------------------------------------------------------
# CommandHistory invariants
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestCommandHistoryProperties:
    @given(st.lists(_segment_name, min_size=1, max_size=10, unique=True))
    def test_undo_all_empties_manager(self, names: list[str]) -> None:
        """Undoing every add command leaves the manager empty."""
        mgr = SegmentManager()
        history = CommandHistory()
        for n in names:
            history.execute(AddSegmentCommand(mgr, Segment(n, 0.0, 1.0)))
        for _ in names:
            history.undo()
        assert mgr.list_segments() == []

    @given(st.lists(_segment_name, min_size=1, max_size=10, unique=True))
    def test_undo_all_then_redo_all_restores_state(self, names: list[str]) -> None:
        """Undoing and redoing all commands fully restores original state."""
        mgr = SegmentManager()
        history = CommandHistory()
        for n in names:
            history.execute(AddSegmentCommand(mgr, Segment(n, 0.0, 1.0)))

        for _ in names:
            history.undo()
        for _ in names:
            history.redo()

        assert sorted(s.name for s in mgr.list_segments()) == sorted(names)

    @given(st.lists(_segment_name, min_size=1, max_size=10, unique=True))
    def test_can_undo_reflects_stack_state(self, names: list[str]) -> None:
        """can_undo() is True iff at least one command has been executed."""
        mgr = SegmentManager()
        history = CommandHistory()
        assert not history.can_undo()
        for n in names:
            history.execute(AddSegmentCommand(mgr, Segment(n, 0.0, 1.0)))
        assert history.can_undo()

    @given(st.integers(min_value=1, max_value=10))
    @h_settings(max_examples=20)
    def test_max_size_respected(self, extra: int) -> None:
        """CommandHistory never exceeds max_size undo entries."""
        max_size = 5
        mgr = SegmentManager()
        history = CommandHistory(max_size=max_size)
        names = [f"s{i}" for i in range(max_size + extra)]
        for n in names:
            history.execute(AddSegmentCommand(mgr, Segment(n, 0.0, 1.0)))
        assert len(history.history()) <= max_size

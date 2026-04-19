"""
Tests for core.segment — 100% branch coverage of Segment.

Covers: duration(), to_dict(), from_dict() with and without optional fields,
and the dataclass equality / roundtrip behaviour.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import pytest

from core.segment import Segment
from core.segment_manager import SegmentManager

# ── Segment ────────────────────────────────────────────────────────────

class TestSegmentDuration:
    def test_duration_positive(self):
        """duration() returns end_sec - start_sec for a normal segment."""
        s = Segment("s", 1.0, 3.5)
        assert s.duration() == pytest.approx(2.5)

    def test_duration_zero_when_equal(self):
        """duration() returns 0 when start equals end."""
        s = Segment("s", 5.0, 5.0)
        assert s.duration() == 0.0

    def test_duration_zero_when_inverted(self):
        """duration() is clamped to 0 when end_sec < start_sec."""
        s = Segment("s", 5.0, 2.0)
        assert s.duration() == 0.0


class TestSegmentToDict:
    def test_to_dict_includes_all_fields(self):
        """to_dict() serialises all fields including optional ones."""
        s = Segment(
            "v", 0.0, 1.0,
            notes="n", color="#ff0000", category="c", practice_count=3,
        )
        d = s.to_dict()
        assert d["name"] == "v"
        assert d["start_sec"] == 0.0
        assert d["end_sec"] == 1.0
        assert d["notes"] == "n"
        assert d["color"] == "#ff0000"
        assert d["category"] == "c"
        assert d["practice_count"] == 3

    def test_to_dict_defaults_are_empty(self):
        """to_dict() reflects default values for optional fields."""
        s = Segment("x", 2.0, 4.0)
        d = s.to_dict()
        assert d["notes"] == ""
        assert d["color"] == ""
        assert d["category"] == ""
        assert d["practice_count"] == 0


class TestSegmentFromDict:
    def test_from_dict_full(self):
        """from_dict() correctly deserialises all fields."""
        d = {
            "name": "verse",
            "start_sec": 10.0,
            "end_sec": 20.0,
            "notes": "hard part",
            "color": "#00ff00",
            "category": "difficult",
            "practice_count": 5,
        }
        s = Segment.from_dict(d)
        assert s.name == "verse"
        assert s.start_sec == 10.0
        assert s.end_sec == 20.0
        assert s.notes == "hard part"
        assert s.color == "#00ff00"
        assert s.category == "difficult"
        assert s.practice_count == 5

    def test_from_dict_backwards_compat(self):
        """from_dict() fills missing optional keys with defaults."""
        old = {"name": "x", "start_sec": 1.0, "end_sec": 2.0}
        s = Segment.from_dict(old)
        assert s.notes == ""
        assert s.color == ""
        assert s.category == ""
        assert s.practice_count == 0

    def test_from_dict_practice_count_as_string(self):
        """from_dict() converts practice_count strings to int."""
        d = {
            "name": "x", "start_sec": 0.0, "end_sec": 1.0,
            "practice_count": "7",
        }
        s = Segment.from_dict(d)
        assert s.practice_count == 7

    def test_from_dict_start_sec_as_string(self):
        """from_dict() converts start_sec/end_sec strings to float."""
        d = {"name": "x", "start_sec": "1.5", "end_sec": "3.5"}
        s = Segment.from_dict(d)
        assert s.start_sec == pytest.approx(1.5)
        assert s.end_sec == pytest.approx(3.5)


class TestSegmentRoundtrip:
    def test_roundtrip_preserves_all_fields(self):
        """to_dict → from_dict reconstructs an identical Segment."""
        s = Segment(
            "rt", 2.5, 7.3,
            notes="test", color="#abc", category="easy", practice_count=1,
        )
        assert Segment.from_dict(s.to_dict()) == s


# ── SegmentManager ─────────────────────────────────────────────────────

class TestSegmentManager:
    def _manager_with(self, *names) -> SegmentManager:
        """Helper: build a manager with segments named after the given names."""
        m = SegmentManager()
        for i, n in enumerate(names):
            m.add_segment(Segment(n, float(i), float(i + 1)))
        return m

    def test_add_and_list(self):
        """add_segment appends in order; list_segments returns all."""
        m = self._manager_with("a", "b", "c")
        assert [s.name for s in m.list_segments()] == ["a", "b", "c"]

    def test_add_replaces_same_name(self):
        """Adding a segment with an existing name replaces the old one."""
        m = self._manager_with("x")
        m.add_segment(Segment("x", 5.0, 6.0))
        segs = m.list_segments()
        assert len(segs) == 1
        assert segs[0].start_sec == 5.0

    def test_remove(self):
        """remove_segment deletes the matching segment."""
        m = self._manager_with("a", "b")
        m.remove_segment("a")
        assert [s.name for s in m.list_segments()] == ["b"]

    def test_remove_nonexistent_is_noop(self):
        """remove_segment on an unknown name does not raise."""
        m = self._manager_with("a")
        m.remove_segment("z")  # must not raise
        assert len(m.list_segments()) == 1

    def test_get_segment_found(self):
        """get_segment returns the matching segment."""
        m = self._manager_with("x", "y")
        s = m.get_segment("x")
        assert s is not None
        assert s.name == "x"

    def test_get_segment_not_found(self):
        """get_segment returns None for an unknown name."""
        m = self._manager_with("a")
        assert m.get_segment("z") is None

    def test_move_up_middle(self):
        """move_up swaps segment with the one before it."""
        m = self._manager_with("a", "b", "c")
        assert m.move_up("b") is True
        assert [s.name for s in m.list_segments()] == ["b", "a", "c"]

    def test_move_up_already_first(self):
        """move_up returns False when segment is already first."""
        m = self._manager_with("a", "b")
        assert m.move_up("a") is False
        assert [s.name for s in m.list_segments()] == ["a", "b"]

    def test_move_up_not_found(self):
        """move_up returns False for an unknown segment name."""
        m = self._manager_with("a")
        assert m.move_up("z") is False

    def test_move_down_middle(self):
        """move_down swaps segment with the one after it."""
        m = self._manager_with("a", "b", "c")
        assert m.move_down("b") is True
        assert [s.name for s in m.list_segments()] == ["a", "c", "b"]

    def test_move_down_already_last(self):
        """move_down returns False when segment is already last."""
        m = self._manager_with("a", "b")
        assert m.move_down("b") is False

    def test_move_down_not_found(self):
        """move_down returns False for an unknown segment name."""
        m = self._manager_with("a")
        assert m.move_down("z") is False

    def test_list_by_category(self):
        """list_by_category filters by the category field."""
        m = SegmentManager()
        m.add_segment(Segment("s1", 0, 1, category="hard"))
        m.add_segment(Segment("s2", 1, 2, category="easy"))
        m.add_segment(Segment("s3", 2, 3, category="hard"))
        hard = m.list_by_category("hard")
        assert [s.name for s in hard] == ["s1", "s3"]

    def test_list_by_category_empty_result(self):
        """list_by_category returns empty list for unknown category."""
        m = self._manager_with("a", "b")
        assert m.list_by_category("unknown") == []

    def test_serialisation_roundtrip(self):
        """to_dict → from_dict preserves segment names."""
        m = self._manager_with("a", "b")
        m2 = SegmentManager.from_dict(m.to_dict())
        assert [s.name for s in m2.list_segments()] == ["a", "b"]

    def test_from_dict_empty_segments(self):
        """from_dict handles a dict with an empty segments list."""
        m = SegmentManager.from_dict({"segments": []})
        assert m.list_segments() == []

    def test_from_dict_missing_key(self):
        """from_dict handles a dict that has no 'segments' key."""
        m = SegmentManager.from_dict({})
        assert m.list_segments() == []

    def test_list_segments_returns_copy(self):
        """list_segments returns a copy; modifying it does not affect manager."""
        m = self._manager_with("a")
        lst = m.list_segments()
        lst.pop()
        assert len(m.list_segments()) == 1

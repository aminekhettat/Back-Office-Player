"""
Dedicated tests for core.segment_manager, providing targeted branch coverage.

The main test_segment.py already includes SegmentManager tests; this module
adds focused corner-case tests for complete branch coverage.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import pytest

from core.segment import Segment
from core.segment_manager import SegmentManager


def _mgr(*names) -> SegmentManager:
    """Helper that builds a SegmentManager from a list of names."""
    m = SegmentManager()
    for i, n in enumerate(names):
        m.add_segment(Segment(n, float(i), float(i + 1)))
    return m


class TestSegmentManagerAdd:
    def test_add_new_segment_appends(self):
        """Adding a new name appends to the end."""
        m = _mgr("a")
        m.add_segment(Segment("b", 1.0, 2.0))
        assert len(m.list_segments()) == 2
        assert m.list_segments()[-1].name == "b"

    def test_add_duplicate_replaces_and_appends(self):
        """Replacing a segment puts the new one at the end."""
        m = _mgr("a", "b")
        m.add_segment(Segment("a", 99.0, 100.0))
        names = [s.name for s in m.list_segments()]
        # "a" is removed first, then appended at end
        assert names == ["b", "a"]
        assert m.get_segment("a").start_sec == 99.0


class TestSegmentManagerRemove:
    def test_remove_first_element(self):
        """Removing the first element leaves the rest intact."""
        m = _mgr("a", "b", "c")
        m.remove_segment("a")
        assert [s.name for s in m.list_segments()] == ["b", "c"]

    def test_remove_last_element(self):
        """Removing the last element leaves the rest intact."""
        m = _mgr("a", "b", "c")
        m.remove_segment("c")
        assert [s.name for s in m.list_segments()] == ["a", "b"]

    def test_remove_middle_element(self):
        """Removing a middle element closes the gap."""
        m = _mgr("a", "b", "c")
        m.remove_segment("b")
        assert [s.name for s in m.list_segments()] == ["a", "c"]


class TestSegmentManagerGet:
    def test_get_first(self):
        """get_segment finds the first element."""
        m = _mgr("x", "y")
        assert m.get_segment("x").name == "x"

    def test_get_last(self):
        """get_segment finds the last element."""
        m = _mgr("x", "y")
        assert m.get_segment("y").name == "y"

    def test_get_missing_returns_none(self):
        """get_segment returns None for an unknown name."""
        m = _mgr("a")
        assert m.get_segment("missing") is None


class TestSegmentManagerMoveUp:
    def test_move_up_second_element(self):
        """move_up on the second element swaps with first."""
        m = _mgr("a", "b")
        assert m.move_up("b") is True
        assert [s.name for s in m.list_segments()] == ["b", "a"]

    def test_move_up_first_returns_false(self):
        """move_up on the first element returns False."""
        m = _mgr("a", "b")
        assert m.move_up("a") is False

    def test_move_up_not_found_returns_false(self):
        """move_up on an unknown name returns False."""
        m = _mgr("a")
        assert m.move_up("z") is False


class TestSegmentManagerMoveDown:
    def test_move_down_second_to_last_element(self):
        """move_down on the penultimate element swaps with last."""
        m = _mgr("a", "b")
        assert m.move_down("a") is True
        assert [s.name for s in m.list_segments()] == ["b", "a"]

    def test_move_down_last_returns_false(self):
        """move_down on the last element returns False."""
        m = _mgr("a", "b")
        assert m.move_down("b") is False

    def test_move_down_not_found_returns_false(self):
        """move_down on an unknown name returns False."""
        m = _mgr("a")
        assert m.move_down("z") is False


class TestSegmentManagerListByCategory:
    def test_all_same_category(self):
        """list_by_category returns all when all match."""
        m = SegmentManager()
        m.add_segment(Segment("a", 0, 1, category="hard"))
        m.add_segment(Segment("b", 1, 2, category="hard"))
        assert len(m.list_by_category("hard")) == 2

    def test_no_match_returns_empty(self):
        """list_by_category returns [] when no segment matches."""
        m = _mgr("a", "b")
        assert m.list_by_category("nonexistent") == []

    def test_empty_category_segments_not_included(self):
        """Segments with empty category are not in any category filter."""
        m = SegmentManager()
        m.add_segment(Segment("a", 0, 1, category=""))
        assert m.list_by_category("") == [m.get_segment("a")]


class TestSegmentManagerSerialization:
    def test_to_dict_has_segments_key(self):
        """to_dict always contains the 'segments' key."""
        m = SegmentManager()
        assert "segments" in m.to_dict()

    def test_to_dict_empty_manager(self):
        """to_dict of an empty manager has an empty list."""
        m = SegmentManager()
        assert m.to_dict() == {"segments": []}

    def test_from_dict_empty(self):
        """from_dict with empty segments creates an empty manager."""
        m = SegmentManager.from_dict({"segments": []})
        assert m.list_segments() == []

    def test_from_dict_no_segments_key(self):
        """from_dict without 'segments' key creates an empty manager."""
        m = SegmentManager.from_dict({})
        assert m.list_segments() == []

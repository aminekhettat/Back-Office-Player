"""
Tests for core.commands — 100% branch coverage.

Covers: AddSegmentCommand (execute, undo, description),
RemoveSegmentCommand (execute with found/not-found segment, undo at various
indices, description), CommandHistory (execute, undo empty/non-empty,
redo empty/non-empty, can_undo, can_redo, history, clear, max_size
enforcement).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from core.commands import (
    AddSegmentCommand,
    CommandHistory,
    RemoveSegmentCommand,
)
from core.segment import Segment
from core.segment_manager import SegmentManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mgr(*names) -> SegmentManager:
    m = SegmentManager()
    for i, n in enumerate(names):
        m.add_segment(Segment(n, float(i), float(i + 1)))
    return m


# ---------------------------------------------------------------------------
# AddSegmentCommand
# ---------------------------------------------------------------------------

class TestAddSegmentCommand:
    def test_execute_adds_segment(self):
        """execute() adds the segment to the manager."""
        m = SegmentManager()
        seg = Segment("A", 0.0, 1.0)
        cmd = AddSegmentCommand(m, seg)
        cmd.execute()
        assert m.get_segment("A") is not None

    def test_undo_removes_segment(self):
        """undo() removes the previously added segment."""
        m = SegmentManager()
        seg = Segment("A", 0.0, 1.0)
        cmd = AddSegmentCommand(m, seg)
        cmd.execute()
        cmd.undo()
        assert m.get_segment("A") is None

    def test_description_contains_segment_name(self):
        """description property contains the segment name."""
        seg = Segment("MySeg", 0.0, 1.0)
        cmd = AddSegmentCommand(SegmentManager(), seg)
        assert "MySeg" in cmd.description


# ---------------------------------------------------------------------------
# RemoveSegmentCommand
# ---------------------------------------------------------------------------

class TestRemoveSegmentCommand:
    def test_execute_removes_segment(self):
        """execute() removes the named segment from the manager."""
        m = _mgr("A", "B", "C")
        cmd = RemoveSegmentCommand(m, "B")
        cmd.execute()
        assert m.get_segment("B") is None
        assert len(m.list_segments()) == 2

    def test_execute_nonexistent_name_does_not_crash(self):
        """execute() on a non-existent name does nothing."""
        m = _mgr("A")
        cmd = RemoveSegmentCommand(m, "Z")
        cmd.execute()  # must not raise
        assert len(m.list_segments()) == 1

    def test_undo_restores_segment(self):
        """undo() re-adds the removed segment."""
        m = _mgr("A", "B", "C")
        cmd = RemoveSegmentCommand(m, "B")
        cmd.execute()
        cmd.undo()
        assert m.get_segment("B") is not None

    def test_undo_restores_at_original_index(self):
        """undo() places the segment back at its original position."""
        m = _mgr("A", "B", "C")
        cmd = RemoveSegmentCommand(m, "B")
        cmd.execute()
        cmd.undo()
        names = [s.name for s in m.list_segments()]
        assert names.index("B") == 1

    def test_undo_when_not_executed_does_not_crash(self):
        """undo() before execute() (segment is None) is a no-op."""
        m = _mgr("A")
        cmd = RemoveSegmentCommand(m, "A")
        cmd.undo()  # must not raise — _segment is None

    def test_description_contains_segment_name(self):
        """description property contains the segment name."""
        cmd = RemoveSegmentCommand(SegmentManager(), "MySeg")
        assert "MySeg" in cmd.description

    def test_undo_at_index_zero(self):
        """undo() correctly restores the first-position segment."""
        m = _mgr("A", "B")
        cmd = RemoveSegmentCommand(m, "A")
        cmd.execute()
        cmd.undo()
        assert m.list_segments()[0].name == "A"

    def test_undo_at_last_index(self):
        """undo() correctly restores the last-position segment."""
        m = _mgr("A", "B", "C")
        cmd = RemoveSegmentCommand(m, "C")
        cmd.execute()
        cmd.undo()
        names = [s.name for s in m.list_segments()]
        assert names[-1] == "C"


# ---------------------------------------------------------------------------
# CommandHistory
# ---------------------------------------------------------------------------

class TestCommandHistory:
    def test_execute_runs_command_and_adds_to_undo(self):
        """execute() runs the command and pushes it to the undo stack."""
        m = SegmentManager()
        h = CommandHistory()
        cmd = AddSegmentCommand(m, Segment("A", 0, 1))
        h.execute(cmd)
        assert m.get_segment("A") is not None
        assert h.can_undo()

    def test_undo_reverts_command(self):
        """undo() revertes the last executed command."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        result = h.undo()
        assert result is True
        assert m.get_segment("A") is None

    def test_undo_empty_returns_false(self):
        """undo() on an empty stack returns False."""
        h = CommandHistory()
        assert h.undo() is False

    def test_redo_after_undo(self):
        """redo() re-applies the last undone command."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        h.undo()
        result = h.redo()
        assert result is True
        assert m.get_segment("A") is not None

    def test_redo_empty_returns_false(self):
        """redo() on an empty redo stack returns False."""
        h = CommandHistory()
        assert h.redo() is False

    def test_new_execute_clears_redo_stack(self):
        """Executing a new command after undo clears the redo stack."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        h.undo()
        assert h.can_redo()
        h.execute(AddSegmentCommand(m, Segment("B", 1, 2)))
        assert not h.can_redo()

    def test_can_undo_true_after_execute(self):
        """can_undo() returns True after at least one execute()."""
        h = CommandHistory()
        h.execute(AddSegmentCommand(SegmentManager(), Segment("A", 0, 1)))
        assert h.can_undo() is True

    def test_can_undo_false_when_empty(self):
        """can_undo() returns False on an empty stack."""
        assert CommandHistory().can_undo() is False

    def test_can_redo_true_after_undo(self):
        """can_redo() returns True after undo."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        h.undo()
        assert h.can_redo() is True

    def test_can_redo_false_when_empty(self):
        """can_redo() returns False when there is nothing to redo."""
        assert CommandHistory().can_redo() is False

    def test_history_returns_undo_stack(self):
        """history() returns a copy of the undo stack."""
        m = SegmentManager()
        h = CommandHistory()
        cmd = AddSegmentCommand(m, Segment("A", 0, 1))
        h.execute(cmd)
        hist = h.history()
        assert len(hist) == 1
        assert hist[0] is cmd

    def test_history_is_a_copy(self):
        """Modifying the list returned by history() does not affect the stack."""
        h = CommandHistory()
        h.execute(AddSegmentCommand(SegmentManager(), Segment("A", 0, 1)))
        hist = h.history()
        hist.clear()
        assert h.can_undo()  # stack is unaffected

    def test_clear_empties_both_stacks(self):
        """clear() empties both undo and redo stacks."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        h.undo()
        h.clear()
        assert not h.can_undo()
        assert not h.can_redo()

    def test_max_size_enforced(self):
        """The undo stack never exceeds max_size."""
        m = SegmentManager()
        h = CommandHistory(max_size=3)
        for i in range(5):
            h.execute(AddSegmentCommand(m, Segment(f"S{i}", float(i), float(i + 1))))
        assert len(h.history()) == 3

    def test_redo_stack_cleared_after_new_execute(self):
        """Redo stack is empty after a fresh execute following an undo."""
        m = SegmentManager()
        h = CommandHistory()
        h.execute(AddSegmentCommand(m, Segment("A", 0, 1)))
        h.undo()
        h.execute(AddSegmentCommand(m, Segment("B", 1, 2)))
        assert not h.can_redo()

"""
Command pattern for undoable segment operations.

Provides a lightweight undo/redo stack whose commands operate on a
:class:`~core.segment_manager.SegmentManager`.  Each command exposes an
:meth:`execute` / :meth:`undo` pair; the :class:`CommandHistory` class
manages the stack and exposes :meth:`~CommandHistory.undo` /
:meth:`~CommandHistory.redo` to callers.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2026-04-19
:version: 1.1.3
:disclaimer: Distributed on an "AS IS" basis, WITHOUT WARRANTIES OR
             CONDITIONS OF ANY KIND. See the LICENSE file for the full
             terms of the Apache License, Version 2.0.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.segment import Segment
from core.segment_manager import SegmentManager


# ── Abstract base ──────────────────────────────────────────────────────────

class Command(ABC):
    """Abstract base class for all undoable commands."""

    @abstractmethod
    def execute(self) -> None:
        """Apply the command."""

    @abstractmethod
    def undo(self) -> None:
        """Revert the command."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description shown in the history dialog."""


# ── Concrete commands ──────────────────────────────────────────────────────

class AddSegmentCommand(Command):
    """
    Add a :class:`~core.segment.Segment` to a :class:`SegmentManager`.

    Parameters
    ----------
    manager : SegmentManager
        Target manager.
    segment : Segment
        Segment to add.
    """

    def __init__(self, manager: SegmentManager, segment: Segment) -> None:
        self._manager = manager
        self._segment = segment

    def execute(self) -> None:
        self._manager.add_segment(self._segment)

    def undo(self) -> None:
        self._manager.remove_segment(self._segment.name)

    @property
    def description(self) -> str:
        return f"Ajouter le segment « {self._segment.name} »"


class RemoveSegmentCommand(Command):
    """
    Remove a :class:`~core.segment.Segment` from a :class:`SegmentManager`.

    The segment is stored internally so that :meth:`undo` can re-add it
    at the **same index** it occupied before removal.

    Parameters
    ----------
    manager : SegmentManager
        Target manager.
    name : str
        Name of the segment to remove.
    """

    def __init__(self, manager: SegmentManager, name: str) -> None:
        self._manager = manager
        self._name = name
        self._segment: Optional[Segment] = None
        self._index: int = -1

    def execute(self) -> None:
        segments = self._manager.list_segments()
        for i, seg in enumerate(segments):
            if seg.name == self._name:
                self._segment = seg
                self._index = i
                break
        if self._segment is not None:
            self._manager.remove_segment(self._name)

    def undo(self) -> None:
        if self._segment is None:
            return
        # Re-insert at the original position by rebuilding the list.
        segments = self._manager.list_segments()
        # Remove all, then re-insert with the old segment at _index.
        for seg in segments:
            self._manager.remove_segment(seg.name)
        insert_idx = max(0, min(self._index, len(segments)))
        combined = segments[:insert_idx] + [self._segment] + segments[insert_idx:]
        for seg in combined:
            self._manager.add_segment(seg)

    @property
    def description(self) -> str:
        return f"Supprimer le segment « {self._name} »"


# ── History stack ──────────────────────────────────────────────────────────

class CommandHistory:
    """
    Undo/redo stack for :class:`Command` objects.

    Parameters
    ----------
    max_size : int, optional
        Maximum number of commands kept in the undo stack (default 50).
    """

    def __init__(self, max_size: int = 50) -> None:
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_size = max_size

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def execute(self, command: Command) -> None:
        """
        Execute *command* and push it onto the undo stack.

        Clears the redo stack (a new action invalidates future redos).

        Parameters
        ----------
        command : Command
            The command to run.
        """
        command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> bool:
        """
        Undo the last executed command.

        Returns
        -------
        bool
            ``True`` if a command was undone, ``False`` if the stack is empty.
        """
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns
        -------
        bool
            ``True`` if a command was redone, ``False`` if the stack is empty.
        """
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        return True

    def can_undo(self) -> bool:
        """Return ``True`` if there is at least one command to undo."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Return ``True`` if there is at least one command to redo."""
        return bool(self._redo_stack)

    def history(self) -> List[Command]:
        """Return the undo stack (oldest first) as a read-only list."""
        return list(self._undo_stack)

    def clear(self) -> None:
        """Clear both stacks (e.g. when a new file is loaded)."""
        self._undo_stack.clear()
        self._redo_stack.clear()

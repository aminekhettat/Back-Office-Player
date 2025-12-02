"""
Segment manager module.

This module defines the :class:`SegmentManager` class, which manages
a collection of segments for a given audio file.

Features
--------
- Add, remove, retrieve segments by name.
- List all segments.
- Serialize/deserialize the collection to/from a dictionary for JSON storage.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:c
opyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.1.0
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any

from .segment import Segment


class SegmentManager:
    """
    Manages a collection of segments for an audio file.

    This class is independent from the user interface and can be used
    in any context where multiple named segments must be managed.
    """

    def __init__(self) -> None:
        """
        Initialize an empty :class:`SegmentManager`.
        """
        # Internal list of segments.
        self._segments: List[Segment] = []

    # ------------------------------------------------------------------ #
    # Segment operations
    # ------------------------------------------------------------------ #
    def add_segment(self, segment: Segment) -> None:
        """
        Add a segment to the collection.

        If a segment with the same name already exists, it is replaced.

        Parameters
        ----------
        segment : Segment
            Segment to add.
        """
        existing = self.get_segment(segment.name)
        if existing is not None:
            # Remove the old one before adding the new one.
            self.remove_segment(segment.name)

        self._segments.append(segment)

    def remove_segment(self, name: str) -> None:
        """
        Remove all segments with a given name.

        Parameters
        ----------
        name : str
            Name of the segment(s) to remove.
        """
        self._segments = [s for s in self._segments if s.name != name]

    def get_segment(self, name: str) -> Optional[Segment]:
        """
        Return the first segment with a given name.

        Parameters
        ----------
        name : str
            Name of the segment to retrieve.

        Returns
        -------
        Segment or None
            Matching segment, or ``None`` if not found.
        """
        for s in self._segments:
            if s.name == name:
                return s
        return None

    def list_segments(self) -> List[Segment]:
        """
        Return a list of all segments.

        Returns
        -------
        list[Segment]
            Copy of the internal segments list.
        """
        return list(self._segments)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the collection of segments to a dictionary.

        Returns
        -------
        dict
            Dictionary containing the list of serialized segments.
        """
        return {
            "segments": [s.to_dict() for s in self._segments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SegmentManager":
        """
        Build a :class:`SegmentManager` from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with key ``"segments"`` containing a list of
            dictionaries compatible with :meth:`Segment.from_dict`.

        Returns
        -------
        SegmentManager
            Instance filled with the provided segments.
        """
        manager = cls()
        for seg_data in data.get("segments", []):
            manager.add_segment(Segment.from_dict(seg_data))
        return manager

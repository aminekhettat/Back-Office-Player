"""
Segment module.

This module defines the :class:`Segment` class, which represents an A–B
segment in an audio file.

A segment is defined by:
- a name (e.g. "Verse 1"),
- a start time in seconds,
- an end time in seconds,
- optional notes, color, category, and practice count.

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

from dataclasses import dataclass, asdict, field
from typing import Dict, Any


@dataclass
class Segment:
    """
    Represents an A–B segment in an audio file.

    Attributes
    ----------
    name : str
        Name of the segment (e.g. "Verse 1", "Chorus", etc.).
    start_sec : float
        Segment start time (seconds).
    end_sec : float
        Segment end time (seconds).
    notes : str
        Optional free-text notes for this segment.
    color : str
        CSS-style color string for display (e.g. "#FF0000").
    category : str
        Optional category label (e.g. "difficult", "verse", etc.).
    practice_count : int
        Number of times this segment has been practiced.
    """

    name: str
    start_sec: float
    end_sec: float
    notes: str = field(default="")
    color: str = field(default="")
    category: str = field(default="")
    practice_count: int = field(default=0)

    def duration(self) -> float:
        """
        Return the segment duration in seconds.

        Returns
        -------
        float
            Segment duration (``end_sec - start_sec``), clamped to ``0.0``
            if ``end_sec < start_sec``.
        """
        return max(0.0, self.end_sec - self.start_sec)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the segment to a dictionary.

        Returns
        -------
        dict
            Dictionary containing all segment fields.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Segment":
        """
        Build a :class:`Segment` from a dictionary.

        Parameters
        ----------
        data : dict
            Dictionary with segment fields. Unknown keys are ignored;
            missing optional keys fall back to their defaults, ensuring
            backward compatibility with older ``.segments.json`` files.

        Returns
        -------
        Segment
            Segment instance created from the dictionary.
        """
        return cls(
            name=data["name"],
            start_sec=float(data["start_sec"]),
            end_sec=float(data["end_sec"]),
            notes=data.get("notes", ""),
            color=data.get("color", ""),
            category=data.get("category", ""),
            practice_count=int(data.get("practice_count", 0)),
        )

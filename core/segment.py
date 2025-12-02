"""
Segment module.

This module defines the :class:`Segment` class, which represents an A–B
segment in an audio file.

A segment is defined by:
- a name (e.g. "Verse 1"),
- a start time in seconds,
- an end time in seconds.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
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
    """

    name: str
    start_sec: float
    end_sec: float

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
            Dictionary with keys ``"name"``, ``"start_sec"`` and ``"end_sec"``.

        Returns
        -------
        Segment
            Segment instance created from the dictionary.
        """
        return cls(
            name=data["name"],
            start_sec=float(data["start_sec"]),
            end_sec=float(data["end_sec"]),
        )

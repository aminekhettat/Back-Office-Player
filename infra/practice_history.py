"""
Practice history module.

Stores a log of practice sessions as a JSON file in the user-data
directory and provides CSV export.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.1
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from platformdirs import user_data_dir

_logger = logging.getLogger(__name__)


@dataclass
class PracticeHistoryEntry:
    """
    A single practice session record.

    Attributes
    ----------
    timestamp : str
        ISO-8601 timestamp of when the session started.
    audio_file : str
        Absolute path (or name) of the audio file practiced.
    duration_seconds : float
        Wall-clock duration of the session in seconds.
    loops_completed : int
        Total number of A-B loops completed during the session.
    avg_tempo : float
        Average tempo factor used (1.0 = 100 %).
    notes : str
        Optional free-text notes.
    """

    timestamp: str
    audio_file: str
    duration_seconds: float
    loops_completed: int
    avg_tempo: float
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PracticeHistoryEntry":
        return cls(
            timestamp=data["timestamp"],
            audio_file=data["audio_file"],
            duration_seconds=float(data["duration_seconds"]),
            loops_completed=int(data["loops_completed"]),
            avg_tempo=float(data["avg_tempo"]),
            notes=data.get("notes", ""),
        )


class PracticeHistory:
    """
    Persisted log of :class:`PracticeHistoryEntry` objects.

    Parameters
    ----------
    data_dir : Path, optional
        Directory in which to store ``practice_history.json``.
        Defaults to the BOP user-data directory.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        if data_dir is None:
            data_dir = Path(user_data_dir("BOP", "BLINDSYSTEMS"))
        self._path = data_dir / "practice_history.json"

    # ------------------------------------------------------------------ #
    # Read / write
    # ------------------------------------------------------------------ #
    def get_sessions(self) -> List[PracticeHistoryEntry]:
        """
        Return all stored practice sessions (oldest first).

        Returns an empty list if the file does not exist or is corrupt.
        """
        if not self._path.is_file():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return [PracticeHistoryEntry.from_dict(d) for d in data]
        except Exception:
            return []

    def add_session(self, entry: PracticeHistoryEntry) -> None:
        """
        Append *entry* to the history file.

        Parameters
        ----------
        entry : PracticeHistoryEntry
            Session record to store.
        """
        sessions = self.get_sessions()
        sessions.append(entry)
        self._save(sessions)

    def _save(self, sessions: List[PracticeHistoryEntry]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(
                    [s.to_dict() for s in sessions],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as exc:
            _logger.error("Error saving practice history: %s", exc)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def export_csv(self, output_path: Path) -> None:
        """
        Export all sessions to a CSV file.

        Parameters
        ----------
        output_path : Path
            Destination ``.csv`` file path.
        """
        sessions = self.get_sessions()
        fieldnames = [
            "timestamp",
            "audio_file",
            "duration_seconds",
            "loops_completed",
            "avg_tempo",
            "notes",
        ]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in sessions:
                writer.writerow(s.to_dict())

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #
    @staticmethod
    def make_entry(
        audio_file: str,
        duration_seconds: float,
        loops_completed: int,
        avg_tempo: float,
        notes: str = "",
    ) -> PracticeHistoryEntry:
        """
        Convenience constructor that fills ``timestamp`` automatically.

        Parameters
        ----------
        audio_file : str
            Path or name of the practiced file.
        duration_seconds : float
            Session duration in seconds.
        loops_completed : int
            Number of loops completed.
        avg_tempo : float
            Average tempo factor.
        notes : str, optional
            Free-text notes.

        Returns
        -------
        PracticeHistoryEntry
        """
        return PracticeHistoryEntry(
            timestamp=datetime.now().isoformat(),
            audio_file=audio_file,
            duration_seconds=duration_seconds,
            loops_completed=loops_completed,
            avg_tempo=avg_tempo,
            notes=notes,
        )

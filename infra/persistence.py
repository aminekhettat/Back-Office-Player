"""
Persistence module.

This module provides functions to save and load segments associated
with an audio file.

Segments are stored in a JSON file whose name is derived from
the original audio file name.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 1.1.0
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from core.segment_manager import SegmentManager

_logger = logging.getLogger(__name__)


def get_metadata_path(audio_file_path: Optional[Path]) -> Optional[Path]:
    """
    Compute the path of the metadata (segments) file for an audio file.

    Parameters
    ----------
    audio_file_path : Path or None
        Path to the original audio file, or ``None``.

    Returns
    -------
    Path or None
        Path to the JSON segment file, or ``None`` if ``audio_file_path`` is ``None``.

    Notes
    -----
    By convention, if the audio file is ``myfile.mp3``,
    segments are stored in ``myfile.mp3.segments.json``.
    """
    if audio_file_path is None:
        return None

    audio_path = Path(audio_file_path)

    # Example: "myfile.mp3" -> "myfile.mp3.segments.json"
    return audio_path.with_suffix(audio_path.suffix + ".segments.json")


def load_segments(audio_file_path: Optional[Path]) -> SegmentManager:
    """
    Load segments associated with an audio file.

    Parameters
    ----------
    audio_file_path : Path or None
        Path to the audio file whose segments must be loaded.

    Returns
    -------
    SegmentManager
        Segment manager instance. If no JSON file is found, or in case
        of any error, an empty manager is returned.
    """
    manager = SegmentManager()

    meta_path = get_metadata_path(audio_file_path)
    if meta_path is None:
        # No audio file => no associated segments.
        return manager

    if not meta_path.is_file():
        # No JSON file found => return empty manager.
        return manager

    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return SegmentManager.from_dict(data)
    except Exception:
        # On any error (file corruption, invalid JSON, etc.), return empty manager.
        return SegmentManager()


def save_segments(audio_file_path: Optional[Path], manager: SegmentManager) -> None:
    """
    Save segments of an audio file to a JSON file.

    Parameters
    ----------
    audio_file_path : Path or None
        Path to the audio file whose segments are to be saved.
        If ``None``, the function does nothing.
    manager : SegmentManager
        Segment manager to save.
    """
    meta_path = get_metadata_path(audio_file_path)
    if meta_path is None:
        # No audio file => cannot associate a metadata file.
        return

    try:
        # Ensure the parent directory exists.
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(manager.to_dict(), f, ensure_ascii=False, indent=2)
    except Exception as exc:
        _logger.error("Error while saving segments: %s", exc)


def export_segments_text(
    audio_file_path: Optional[Path],
    manager: SegmentManager,
    output_path: Path,
    fmt: str = "csv",
) -> None:
    """
    Export all segments to a plain-text file (CSV or TXT).

    Parameters
    ----------
    audio_file_path : Path or None
        Path to the audio file (used for the ``audio_file`` column).
    manager : SegmentManager
        Segment manager whose segments are exported.
    output_path : Path
        Destination file path.
    fmt : str
        Format: ``"csv"`` (default) produces a CSV with a header row;
        ``"txt"`` produces one segment per line in human-readable form.

    Raises
    ------
    ValueError
        If *fmt* is not ``"csv"`` or ``"txt"``.
    """
    import csv as csv_mod

    if fmt not in ("csv", "txt"):
        raise ValueError(f"Unknown format: {fmt!r}. Use 'csv' or 'txt'.")

    audio_name = str(audio_file_path) if audio_file_path else ""
    segments = manager.list_segments()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        with output_path.open("w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "audio_file",
                "name",
                "start_sec",
                "end_sec",
                "duration_sec",
                "category",
                "notes",
                "practice_count",
                "color",
            ]
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for seg in segments:
                writer.writerow(
                    {
                        "audio_file": audio_name,
                        "name": seg.name,
                        "start_sec": f"{seg.start_sec:.3f}",
                        "end_sec": f"{seg.end_sec:.3f}",
                        "duration_sec": f"{seg.duration():.3f}",
                        "category": seg.category,
                        "notes": seg.notes,
                        "practice_count": seg.practice_count,
                        "color": seg.color,
                    }
                )
    else:  # txt
        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"Segments for: {audio_name}\n")
            f.write("-" * 60 + "\n")
            for i, seg in enumerate(segments, 1):
                f.write(
                    f"{i}. {seg.name}\n"
                    f"   Start : {seg.start_sec:.3f} s\n"
                    f"   End   : {seg.end_sec:.3f} s\n"
                    f"   Dur.  : {seg.duration():.3f} s\n"
                )
                if seg.category:
                    f.write(f"   Cat.  : {seg.category}\n")
                if seg.notes:
                    f.write(f"   Notes : {seg.notes}\n")
                f.write("\n")

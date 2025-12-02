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
:version: 0.1.0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.segment_manager import SegmentManager


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
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(manager.to_dict(), f, ensure_ascii=False, indent=2)
    except Exception as exc:
        # In a real application, you would use logging instead of print.
        print(f"Error while saving segments: {exc}")

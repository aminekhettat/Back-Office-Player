"""
Settings module.

This module manages a JSON configuration file stored in the platform-
appropriate user-data directory (e.g. ``%APPDATA%\\BLINDSYSTEMS\\BOP`` on
Windows, ``~/.local/share/BLINDSYSTEMS/BOP`` on Linux).

Features
--------
- Deep-merge of loaded values with defaults (nested keys are not lost).
- Automatic migration of a legacy ``settings.json`` in the CWD.
- ``add_recent_file()`` helper to maintain a bounded recent-files list.

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

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from platformdirs import user_data_dir

_logger = logging.getLogger(__name__)

# Default application settings.
DEFAULT_SETTINGS: Dict[str, Any] = {
    "last_opened_folder": "",
    "default_volume": 80,
    "recent_files": [],
    "theme": "default",
    "pitch_preserving": False,
    "loop_count": 0,
    "progressive_tempo": False,
    "tempo_step": 0.05,
    "tempo_target": 1.0,
    "loop_delay": 0.0,
    "position_announce_interval": 5,
    "shortcuts": {
        "open": "Ctrl+O",
        "play_pause": "Space",
        "play": "Ctrl+P",
        "pause": "Ctrl+Shift+P",
        "stop": "Ctrl+S",
        "set_a": "Ctrl+Shift+A",
        "set_b": "Ctrl+Shift+B",
        "save_segment": "Ctrl+Shift+S",
        "export_config": "Ctrl+E",
        "import_config": "Ctrl+I",
        "next_segment": "Ctrl+Right",
        "prev_segment": "Ctrl+Left",
        "volume_up": "Ctrl+Alt+Up",
        "volume_down": "Ctrl+Alt+Down",
        "tempo_up": "Ctrl+Up",
        "tempo_down": "Ctrl+Down",
        "pitch_up": "Shift+Up",
        "pitch_down": "Shift+Down",
        "toggle_loop": "Ctrl+L",
    },
}


def get_settings_path() -> Path:
    """
    Return the path to the settings file in the user-data directory.

    On first call, if a legacy ``settings.json`` exists in the current
    working directory and no file exists at the new location, it is
    copied automatically (migration).

    Returns
    -------
    Path
        Absolute path to ``settings.json`` inside the BOP user-data dir.
    """
    data_dir = Path(user_data_dir("BOP", "BLINDSYSTEMS"))
    new_path = data_dir / "settings.json"

    # --- Migrate from legacy CWD location --------------------------------
    legacy_path = Path("settings.json").absolute()
    if legacy_path.is_file() and not new_path.is_file():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, new_path)

    return new_path


def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge *update* into *base*.

    Nested dicts are merged rather than replaced, so loading a file
    that only has ``shortcuts.open`` will not wipe ``shortcuts.stop``.

    Parameters
    ----------
    base : dict
        Source dictionary (typically defaults).
    update : dict
        Values to apply on top of *base*.

    Returns
    -------
    dict
        Merged dictionary (does not modify *base* or *update*).
    """
    result = base.copy()
    for key, value in update.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> Dict[str, Any]:
    """
    Load application settings from the JSON file.

    Returns
    -------
    dict
        Settings dictionary.  Missing keys are filled with defaults.
        If the file does not exist or is corrupt, defaults are returned.
    """
    path = get_settings_path()
    if not path.is_file():
        return _deep_merge(DEFAULT_SETTINGS, {})

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _deep_merge(DEFAULT_SETTINGS, data)
    except Exception:
        return _deep_merge(DEFAULT_SETTINGS, {})


def save_settings(settings: Dict[str, Any]) -> None:
    """
    Save application settings to the JSON file.

    Parameters
    ----------
    settings : dict
        Settings dictionary to persist.
    """
    path = get_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        _logger.error("Error while saving settings: %s", exc)


def add_recent_file(
    settings: Dict[str, Any], path: str, max_files: int = 10
) -> None:
    """
    Prepend *path* to ``settings["recent_files"]``, keeping at most
    *max_files* entries.  Duplicates are removed before inserting.

    Parameters
    ----------
    settings : dict
        Settings dictionary to modify in-place.
    path : str
        Absolute path to prepend.
    max_files : int
        Maximum number of recent files to keep.
    """
    recent: List[str] = settings.get("recent_files", [])
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    settings["recent_files"] = recent[:max_files]

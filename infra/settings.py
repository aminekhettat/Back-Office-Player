"""
Settings module.

This module manages a small JSON configuration file used to store
simple user preferences, such as:

- Last opened folder used for selecting audio files.
- Default application volume.

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
from typing import Dict, Any

# Default application settings.
DEFAULT_SETTINGS: Dict[str, Any] = {
    "last_opened_folder": "",
    "default_volume": 80,
}


def get_settings_path() -> Path:
    """
    Return the path to the settings file.

    Returns
    -------
    Path
        Absolute path to the ``settings.json`` file in the current directory.
    """
    return Path("settings.json").absolute()


def load_settings() -> Dict[str, Any]:
    """
    Load application settings from the JSON file.

    Returns
    -------
    dict
        Settings dictionary. If the file does not exist or cannot be read,
        default values are returned.

    Notes
    -----
    If some keys are missing in the file, they are filled with default values.
    """
    path = get_settings_path()
    if not path.is_file():
        # No settings file => return default settings.
        return DEFAULT_SETTINGS.copy()

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Start from defaults and update with file content.
        settings = DEFAULT_SETTINGS.copy()
        settings.update(data)
        return settings
    except Exception:
        # On any error, return default settings.
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """
    Save application settings to the JSON file.

    Parameters
    ----------
    settings : dict
        Settings dictionary to save.
    """
    path = get_settings_path()
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        # In a real application, prefer logging instead of print.
        print(f"Error while saving settings: {exc}")

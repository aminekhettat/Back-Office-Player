"""
Shared pytest fixtures for the Back-Office Player test suite.

Provides reusable fixtures for settings-path isolation, temporary
directories, and common domain objects used across multiple test modules.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# Ensure the project root is importable regardless of how pytest is invoked.
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.i18n import get_language, set_language

# ---------------------------------------------------------------------------
# Language isolation — force English so status-text assertions are stable
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _force_english(monkeypatch):
    """Force English language for every test; restore the original on teardown."""
    prev = get_language()
    set_language("en")
    yield
    set_language(prev)


# ---------------------------------------------------------------------------
# Settings path isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings_path(tmp_path, monkeypatch):
    """
    Monkeypatch get_settings_path to a temp directory.

    Returns the Path to the temporary settings.json location so tests never
    touch the real user-data dir.
    """
    path = tmp_path / "settings.json"
    import infra.settings as _settings_mod

    monkeypatch.setattr(_settings_mod, "get_settings_path", lambda: path)
    return path


# Alias used by some existing tests
@pytest.fixture()
def tmp_settings_dir(settings_path):
    """Alias for settings_path fixture."""
    return settings_path


# ---------------------------------------------------------------------------
# Common audio fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_rate() -> int:
    """Standard 44100 Hz sample rate."""
    return 44100


@pytest.fixture()
def sample_audio(sample_rate: int) -> np.ndarray:
    """One second of 440 Hz sine wave at 44100 Hz."""
    t = np.linspace(0, 1.0, sample_rate, endpoint=False)
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


@pytest.fixture()
def audio_path(tmp_path: Path) -> Path:
    """A temporary file that acts as a placeholder audio path."""
    p = tmp_path / "test_audio.mp3"
    p.touch()
    return p


# ---------------------------------------------------------------------------
# Common domain-object fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def basic_segment():
    """Return a simple Segment for use in tests."""
    return Segment(name="Verse 1", start_sec=0.0, end_sec=10.0)


@pytest.fixture()
def segment_manager_with_two():
    """Return a SegmentManager pre-populated with two segments."""
    mgr = SegmentManager()
    mgr.add_segment(Segment(name="Intro", start_sec=0.0, end_sec=5.0, category="easy"))
    mgr.add_segment(Segment(name="Chorus", start_sec=5.0, end_sec=15.0, category="hard"))
    return mgr


# ---------------------------------------------------------------------------
# Mock AudioPlayer (for UI tests that must not touch sounddevice/librosa)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_audio_player():
    """Return a MagicMock that mimics the AudioPlayer public API."""
    player = MagicMock()
    player.get_position.return_value = 0.0
    player.get_duration.return_value = 0.0
    player.get_volume.return_value = 80
    player.get_tempo.return_value = 1.0
    player.get_pitch_semitones.return_value = 0.0
    player.get_pitch_preserving.return_value = False
    player._audio_data = None
    player._sample_rate = 0
    player._lock = threading.RLock()
    return player

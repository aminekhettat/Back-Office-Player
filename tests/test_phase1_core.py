"""
Functional tests for Back-Office Player Phase 1 (core only).

Legacy standalone tests, converted to clean pytest format.
Tests core functionality without requiring librosa/sounddevice.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.persistence import get_metadata_path, load_segments, save_segments


@pytest.mark.integration
def test_segments():
    """Segment creation, retrieval, deletion, replacement, and serialisation."""
    seg1 = Segment(name="Verse 1", start_sec=0.0, end_sec=20.5)
    seg2 = Segment(name="Chorus", start_sec=20.5, end_sec=35.0)

    assert seg1.name == "Verse 1"
    assert seg1.duration() == pytest.approx(20.5)

    manager = SegmentManager()
    manager.add_segment(seg1)
    manager.add_segment(seg2)
    assert len(manager.list_segments()) == 2

    retrieved = manager.get_segment("Verse 1")
    assert retrieved is not None
    assert retrieved.start_sec == 0.0

    manager.remove_segment("Chorus")
    assert len(manager.list_segments()) == 1

    dict_repr = manager.to_dict()
    assert "segments" in dict_repr

    manager2 = SegmentManager.from_dict(dict_repr)
    assert len(manager2.list_segments()) == 1

    # Replacement
    seg_duplicate = Segment(name="Verse 1", start_sec=10.0, end_sec=22.0)
    manager.add_segment(seg_duplicate)
    assert len(manager.list_segments()) == 1
    replaced = manager.get_segment("Verse 1")
    assert replaced is not None
    assert replaced.start_sec == pytest.approx(10.0)


@pytest.mark.integration
def test_persistence():
    """Segment persistence round-trip via filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "test_audio.mp3"
        audio_path.touch()

        manager = SegmentManager()
        manager.add_segment(Segment(name="Part A", start_sec=5.0, end_sec=15.0))
        manager.add_segment(Segment(name="Part B", start_sec=15.0, end_sec=30.0))

        save_segments(audio_path, manager)

        meta_path = get_metadata_path(audio_path)
        assert meta_path is not None
        assert meta_path.exists()

        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "segments" in data
        assert len(data["segments"]) == 2

        loaded_manager = load_segments(audio_path)
        assert len(loaded_manager.list_segments()) == 2

        part_a = loaded_manager.get_segment("Part A")
        assert part_a is not None
        assert part_a.duration() == pytest.approx(10.0)


@pytest.mark.integration
def test_config_export_import():
    """Configuration export/import round-trip for .bop files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.bop"

        config_data = {
            "audio_file": "/path/to/song.mp3",
            "segments": [
                {"name": "Intro", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "Verse", "start_sec": 5.0, "end_sec": 25.0},
                {"name": "Chorus", "start_sec": 25.0, "end_sec": 40.0},
            ],
            "settings": {"volume": 75, "tempo": 0.8},
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        assert config_path.exists()
        assert config_path.stat().st_size > 0

        with open(config_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data["audio_file"] == "/path/to/song.mp3"
        assert len(loaded_data["segments"]) == 3
        assert loaded_data["settings"]["tempo"] == pytest.approx(0.8)

        manager = SegmentManager.from_dict({"segments": loaded_data["segments"]})
        assert len(manager.list_segments()) == 3
        chorus = manager.get_segment("Chorus")
        assert chorus is not None
        assert chorus.start_sec == pytest.approx(25.0)

        settings = loaded_data.get("settings", {})
        assert 0 <= settings["volume"] <= 100
        assert 0.5 <= settings["tempo"] <= 2.0


@pytest.mark.integration
def test_settings_management():
    """Application settings persistence (load/save/reload)."""
    import infra.settings as settings_mod
    from infra.settings import load_settings, save_settings

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        original_get_path = settings_mod.get_settings_path
        settings_mod.get_settings_path = lambda: settings_path

        try:
            settings = load_settings()
            assert "default_volume" in settings
            assert "last_opened_folder" in settings

            settings["default_volume"] = 75
            settings["last_opened_folder"] = "/home/user/music"
            save_settings(settings)

            reloaded = load_settings()
            assert reloaded["default_volume"] == 75
            assert reloaded["last_opened_folder"] == "/home/user/music"
        finally:
            settings_mod.get_settings_path = original_get_path

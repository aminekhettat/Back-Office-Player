"""
Functional tests for Back-Office Player Phase 1 (without audio player tests).

This script tests core functionality without requiring librosa/sounddevice.

Run: python tests/test_phase1_core.py

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
"""

import sys
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.persistence import save_segments, load_segments, get_metadata_path


def test_segments():
    """Test Segment and SegmentManager."""
    print("\n" + "="*60)
    print("TEST: Segments and SegmentManager")
    print("="*60)

    # Create segments
    seg1 = Segment(name="Verse 1", start_sec=0.0, end_sec=20.5)
    seg2 = Segment(name="Chorus", start_sec=20.5, end_sec=35.0)

    assert seg1.name == "Verse 1", "Segment name should be 'Verse 1'"
    assert seg1.duration() == 20.5, "Segment duration should be 20.5"
    print("✓ Segment creation working")

    # Test SegmentManager
    manager = SegmentManager()
    manager.add_segment(seg1)
    manager.add_segment(seg2)

    segments = manager.list_segments()
    assert len(segments) == 2, "Manager should have 2 segments"
    print(f"✓ Added 2 segments to manager")

    # Test retrieval
    retrieved = manager.get_segment("Verse 1")
    assert retrieved is not None, "Should retrieve 'Verse 1'"
    assert retrieved.start_sec == 0.0, "Retrieved segment should match"
    print("✓ Segment retrieval working")

    # Test deletion
    manager.remove_segment("Chorus")
    assert len(manager.list_segments()) == 1, "Should have 1 segment left"
    print("✓ Segment deletion working")

    # Test serialization
    dict_repr = manager.to_dict()
    assert "segments" in dict_repr, "Serialized dict should have 'segments' key"
    print("✓ Segment serialization to dict working")

    # Test deserialization
    manager2 = SegmentManager.from_dict(dict_repr)
    assert len(manager2.list_segments()) == 1, "Deserialized manager should have 1 segment"
    print("✓ Segment deserialization from dict working")

    # Test duplicate handling (should replace)
    seg_duplicate = Segment(name="Verse 1", start_sec=10.0, end_sec=22.0)
    manager.add_segment(seg_duplicate)
    segments = manager.list_segments()
    assert len(segments) == 1, "Should still have 1 segment (replaced)"
    replaced = manager.get_segment("Verse 1")
    assert replaced.start_sec == 10.0, "Segment should be updated"
    print("✓ Segment replacement working")

    print("\n✓ Segments test PASSED\n")


def test_persistence():
    """Test segment persistence to disk."""
    print("="*60)
    print("TEST: Segment Persistence")
    print("="*60)

    # Create temporary audio file path
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "test_audio.mp3"
        audio_path.touch()  # Create dummy file

        # Create segments
        manager = SegmentManager()
        seg1 = Segment(name="Part A", start_sec=5.0, end_sec=15.0)
        seg2 = Segment(name="Part B", start_sec=15.0, end_sec=30.0)
        manager.add_segment(seg1)
        manager.add_segment(seg2)

        # Save segments
        save_segments(audio_path, manager)
        print("✓ Segments saved to disk")

        # Check metadata file created
        meta_path = get_metadata_path(audio_path)
        assert meta_path is not None, "Metadata path should not be None"
        assert meta_path.exists(), "Metadata file should exist"
        print(f"✓ Metadata file created: {meta_path.name}")

        # Verify JSON structure
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "segments" in data, "JSON should have 'segments' key"
        assert len(data["segments"]) == 2, "JSON should have 2 segments"
        print("✓ JSON structure verified")

        # Load segments
        loaded_manager = load_segments(audio_path)
        assert len(loaded_manager.list_segments()) == 2, "Should load 2 segments"
        print("✓ Segments loaded from disk")

        # Verify content
        part_a = loaded_manager.get_segment("Part A")
        assert part_a is not None, "Part A should be loaded"
        assert part_a.duration() == 10.0, "Part A duration should be 10.0"
        print("✓ Persisted segments verified")

    print("\n✓ Persistence test PASSED\n")


def test_config_export_import():
    """Test configuration export and import."""
    print("="*60)
    print("TEST: Configuration Export/Import (.bop files)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.bop"

        # Create configuration data (represents Phase 1 features)
        config_data = {
            "audio_file": "/path/to/song.mp3",
            "segments": [
                {"name": "Intro", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "Verse", "start_sec": 5.0, "end_sec": 25.0},
                {"name": "Chorus", "start_sec": 25.0, "end_sec": 40.0},
            ],
            "settings": {
                "volume": 75,
                "tempo": 0.8,
            },
        }

        # Export
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print("✓ Configuration exported to .bop file")
        print(f"  Path: {config_path}")

        # Verify file exists and is readable
        assert config_path.exists(), "Config file should exist"
        assert config_path.stat().st_size > 0, "Config file should not be empty"
        print("✓ Config file created successfully")

        # Import
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data["audio_file"] == "/path/to/song.mp3", "Audio file path should match"
        assert len(loaded_data["segments"]) == 3, "Should have 3 segments"
        assert loaded_data["settings"]["tempo"] == 0.8, "Tempo setting should match"
        print("✓ Configuration imported from .bop file")

        # Verify segments in imported config
        manager = SegmentManager.from_dict({"segments": loaded_data["segments"]})
        assert len(manager.list_segments()) == 3, "Manager should have 3 segments"
        chorus = manager.get_segment("Chorus")
        assert chorus.start_sec == 25.0, "Chorus start should be 25.0"
        print("✓ Imported segments verified")

        # Verify settings
        settings = loaded_data.get("settings", {})
        assert "volume" in settings, "Settings should have volume"
        assert "tempo" in settings, "Settings should have tempo"
        assert 0 <= settings["volume"] <= 100, "Volume should be 0-100"
        assert 0.5 <= settings["tempo"] <= 2.0, "Tempo should be 0.5-2.0"
        print("✓ Settings verified (Phase 1 compatible)")

    print("\n✓ Config export/import test PASSED\n")


def test_settings_management():
    """Test application settings persistence."""
    print("="*60)
    print("TEST: Settings Management")
    print("="*60)

    from infra.settings import load_settings, save_settings

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override settings path for testing
        import infra.settings
        original_get_path = infra.settings.get_settings_path

        settings_path = Path(tmpdir) / "settings.json"

        def mock_get_settings_path():
            return settings_path

        infra.settings.get_settings_path = mock_get_settings_path

        try:
            # Test default settings
            settings = load_settings()
            assert "default_volume" in settings, "Should have default_volume"
            assert "last_opened_folder" in settings, "Should have last_opened_folder"
            print("✓ Default settings loaded")

            # Test save settings
            settings["default_volume"] = 75
            settings["last_opened_folder"] = "/home/user/music"
            save_settings(settings)
            print("✓ Settings saved to disk")

            # Test reload
            reloaded = load_settings()
            assert reloaded["default_volume"] == 75, "Volume should be persisted"
            assert reloaded["last_opened_folder"] == "/home/user/music", "Folder should be persisted"
            print("✓ Settings reloaded successfully")

        finally:
            # Restore original
            infra.settings.get_settings_path = original_get_path

    print("\n✓ Settings test PASSED\n")


def run_all_tests():
    """Run all tests."""
    print("\n" + "█"*60)
    print("█  BACK-OFFICE PLAYER - PHASE 1 CORE TESTS")
    print("█  Testing segments, persistence, config export/import")
    print("█"*60)

    try:
        test_segments()
        test_persistence()
        test_config_export_import()
        test_settings_management()

        print("█"*60)
        print("█  ✓ ALL TESTS PASSED!")
        print("█  Core functionality is verified")
        print("█  Audio player requires: librosa, sounddevice")
        print("█  Ready for Phase 2 development")
        print("█"*60 + "\n")
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

"""
Functional tests for Back-Office Player Phase 1.

This script tests the core functionality without requiring full GUI.

Run: python tests/test_phase1.py

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

from core.audio_player_native import AudioPlayer
from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.persistence import save_segments, load_segments, get_metadata_path


def test_audio_player_basics():
    """Test basic AudioPlayer functionality."""
    print("\n" + "="*60)
    print("TEST: AudioPlayer Basics")
    print("="*60)

    player = AudioPlayer()
    print("✓ AudioPlayer initialized")

    # Check initial state
    assert player.get_duration() == 0.0, "Duration should be 0 when no file loaded"
    assert player.get_position() == 0.0, "Position should be 0 when no file loaded"
    assert player.get_volume() == 80, "Default volume should be 80"
    assert player.get_tempo() == 1.0, "Default tempo should be 1.0"
    print("✓ Initial state correct (duration=0, position=0, volume=80, tempo=1.0)")

    # Test volume
    player.set_volume(50)
    assert player.get_volume() == 50, "Volume should be 50"
    player.set_volume(150)  # Should clamp to 100
    assert player.get_volume() == 100, "Volume should be clamped to 100"
    print("✓ Volume control working (clamped to 0-100)")

    # Test tempo
    player.set_tempo(0.5)
    assert player.get_tempo() == 0.5, "Tempo should be 0.5"
    player.set_tempo(2.0)
    assert player.get_tempo() == 2.0, "Tempo should be 2.0"
    player.set_tempo(5.0)  # Should clamp to 2.0
    assert player.get_tempo() == 2.0, "Tempo should be clamped to 2.0"
    print("✓ Tempo control working (clamped to 0.5-2.0)")

    print("\n✓ AudioPlayer basics test PASSED\n")


def test_segments():
    """Test Segment and SegmentManager."""
    print("="*60)
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
        assert meta_path.exists(), "Metadata file should exist"
        print(f"✓ Metadata file created: {meta_path.name}")

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
    print("TEST: Configuration Export/Import")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.bop"

        # Create configuration data
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
            json.dump(config_data, f)
        print("✓ Configuration exported to .bop file")

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

    print("\n✓ Config export/import test PASSED\n")


def run_all_tests():
    """Run all tests."""
    print("\n" + "█"*60)
    print("█  BACK-OFFICE PLAYER - PHASE 1 TESTS")
    print("█  Running functional tests...")
    print("█"*60)

    try:
        test_audio_player_basics()
        test_segments()
        test_persistence()
        test_config_export_import()

        print("█"*60)
        print("█  ✓ ALL TESTS PASSED!")
        print("█  Application is ready for Phase 2 development")
        print("█"*60 + "\n")
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

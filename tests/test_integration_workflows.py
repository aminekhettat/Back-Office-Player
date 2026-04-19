"""
Integration tests: complete user workflows.

These tests exercise the full stack (AudioPlayer + SegmentManager +
persistence + CommandHistory) without the UI layer.  Audio files are
written as real WAV files so that librosa loads them without mocking;
only sounddevice.OutputStream is mocked to avoid real hardware.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from core.audio_player_native import AudioPlayer
from core.commands import AddSegmentCommand, CommandHistory, RemoveSegmentCommand
from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.persistence import load_segments, save_segments

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def wav_file(tmp_path: Path, sample_audio: np.ndarray, sample_rate: int) -> Path:
    """Write a real 1-second WAV file and return its path."""
    path = tmp_path / "song.wav"
    wavfile.write(str(path), sample_rate, sample_audio)
    return path


@pytest.fixture()
def real_player(wav_file: Path) -> AudioPlayer:
    """Return an AudioPlayer with a real WAV file loaded (no sounddevice)."""
    player = AudioPlayer()
    player.load_file(wav_file)
    return player


# ---------------------------------------------------------------------------
# File → segment → save → reload workflow
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFileSegmentWorkflow:
    def test_load_add_save_reload(self, wav_file, real_player):
        """Open file → add segment → save → reload cold → segment persists."""
        mgr = SegmentManager()
        mgr.add_segment(Segment("Verse", 0.1, 0.5, notes="hard part"))
        save_segments(wav_file, mgr)

        mgr2 = load_segments(wav_file)
        verse = mgr2.get_segment("Verse")
        assert verse is not None
        assert verse.start_sec == pytest.approx(0.1)
        assert verse.end_sec == pytest.approx(0.5)
        assert verse.notes == "hard part"

    def test_multiple_segments_order_preserved(self, wav_file):
        """Multiple segments reload in insertion order."""
        mgr = SegmentManager()
        for name, start, end in [
            ("Intro", 0.0, 0.2),
            ("Verse", 0.2, 0.6),
            ("Chorus", 0.6, 0.9),
        ]:
            mgr.add_segment(Segment(name, start, end))
        save_segments(wav_file, mgr)

        mgr2 = load_segments(wav_file)
        assert [s.name for s in mgr2.list_segments()] == ["Intro", "Verse", "Chorus"]

    def test_overwrite_save_removes_deleted_segment(self, wav_file):
        """Saving after removing a segment makes deletion permanent on reload."""
        mgr = SegmentManager()
        mgr.add_segment(Segment("A", 0.0, 0.3))
        mgr.add_segment(Segment("B", 0.3, 0.6))
        save_segments(wav_file, mgr)

        mgr.remove_segment("A")
        save_segments(wav_file, mgr)

        mgr2 = load_segments(wav_file)
        assert mgr2.get_segment("A") is None
        assert mgr2.get_segment("B") is not None

    def test_reload_no_file_returns_empty(self, tmp_path):
        """load_segments returns an empty manager when no JSON file exists."""
        audio = tmp_path / "nosave.mp3"
        audio.touch()
        mgr = load_segments(audio)
        assert mgr.list_segments() == []

    def test_segment_all_optional_fields_survive_roundtrip(self, wav_file):
        """All optional fields (color, category, practice_count) persist."""
        mgr = SegmentManager()
        mgr.add_segment(
            Segment(
                "Solo",
                0.0,
                0.5,
                notes="very hard",
                color="#ff0000",
                category="difficult",
                practice_count=7,
            )
        )
        save_segments(wav_file, mgr)

        solo = load_segments(wav_file).get_segment("Solo")
        assert solo is not None
        assert solo.color == "#ff0000"
        assert solo.category == "difficult"
        assert solo.practice_count == 7


# ---------------------------------------------------------------------------
# Undo / redo workflow
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUndoRedoWorkflow:
    def test_add_undo_redo_state(self):
        """Add → undo (removed) → redo (re-added): correct state at each step."""
        mgr = SegmentManager()
        history = CommandHistory()

        history.execute(AddSegmentCommand(mgr, Segment("Chorus", 0.3, 0.7)))
        assert mgr.get_segment("Chorus") is not None

        history.undo()
        assert mgr.get_segment("Chorus") is None
        assert history.can_redo()

        history.redo()
        assert mgr.get_segment("Chorus") is not None

    def test_remove_undo_restores_at_original_index(self):
        """RemoveSegmentCommand.undo() re-inserts at the original position."""
        mgr = SegmentManager()
        for n in ["A", "B", "C"]:
            mgr.add_segment(Segment(n, 0.0, 1.0))
        history = CommandHistory()

        history.execute(RemoveSegmentCommand(mgr, "B"))
        assert [s.name for s in mgr.list_segments()] == ["A", "C"]

        history.undo()
        assert [s.name for s in mgr.list_segments()] == ["A", "B", "C"]

    def test_new_action_clears_redo_stack(self):
        """A new execute() after undo clears the redo stack."""
        mgr = SegmentManager()
        history = CommandHistory()

        history.execute(AddSegmentCommand(mgr, Segment("X", 0.0, 1.0)))
        history.undo()
        assert history.can_redo()

        history.execute(AddSegmentCommand(mgr, Segment("Y", 1.0, 2.0)))
        assert not history.can_redo()

    def test_add_save_undo_save_reload_empty(self, wav_file):
        """Add → save → undo → save again → reload shows no segment."""
        mgr = SegmentManager()
        history = CommandHistory()

        history.execute(AddSegmentCommand(mgr, Segment("Solo", 0.1, 0.4)))
        save_segments(wav_file, mgr)

        history.undo()
        save_segments(wav_file, mgr)

        mgr2 = load_segments(wav_file)
        assert mgr2.get_segment("Solo") is None

    def test_multiple_undo_redo_cycles(self):
        """Repeated undo/redo cycles keep state consistent."""
        mgr = SegmentManager()
        history = CommandHistory()

        segs = [Segment(f"S{i}", float(i), float(i + 1)) for i in range(3)]
        for seg in segs:
            history.execute(AddSegmentCommand(mgr, seg))

        assert len(mgr.list_segments()) == 3

        history.undo()
        history.undo()
        assert len(mgr.list_segments()) == 1

        history.redo()
        history.redo()
        assert len(mgr.list_segments()) == 3


# ---------------------------------------------------------------------------
# AudioPlayer position and state after real load
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPlayerStateAfterLoad:
    def test_duration_matches_file(self, real_player, sample_audio, sample_rate):
        """get_duration() reflects the actual WAV file length."""
        expected = float(len(sample_audio)) / sample_rate
        assert real_player.get_duration() == pytest.approx(expected, rel=1e-3)

    def test_position_starts_at_zero(self, real_player):
        """Position is 0 immediately after load."""
        assert real_player.get_position() == pytest.approx(0.0)

    def test_position_clamped_above_duration(self, real_player, sample_audio, sample_rate):
        """set_position beyond duration clamps to the file duration."""
        duration = float(len(sample_audio)) / sample_rate
        real_player.set_position(duration + 999.0)
        assert real_player.get_position() == pytest.approx(duration, rel=1e-3)

    def test_position_clamped_below_zero(self, real_player):
        """set_position below zero clamps to 0."""
        real_player.set_position(-5.0)
        assert real_player.get_position() == pytest.approx(0.0)

    def test_set_and_get_position_midfile(self, real_player, sample_audio, sample_rate):
        """set_position to a valid mid-file time is preserved by get_position."""
        duration = float(len(sample_audio)) / sample_rate
        mid = duration * 0.5
        real_player.set_position(mid)
        assert real_player.get_position() == pytest.approx(mid, abs=1.0 / sample_rate)

    def test_play_stop_resets_position(self, real_player):
        """play() then stop() resets position to 0."""
        mock_stream = MagicMock()
        with patch("sounddevice.OutputStream", return_value=mock_stream):
            real_player.set_position(0.3)
            real_player.play()
            real_player.stop()
        assert real_player.get_position() == pytest.approx(0.0)

    def test_audio_snapshot_returns_array_and_rate(self, real_player, sample_rate):
        """get_audio_snapshot() returns a non-None array and the correct SR."""
        audio, sr = real_player.get_audio_snapshot()
        assert audio is not None
        assert sr == sample_rate
        assert len(audio) > 0

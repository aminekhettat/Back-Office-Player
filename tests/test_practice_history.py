"""
Tests for infra.practice_history — 100% branch coverage.

Covers: PracticeHistoryEntry.to_dict / from_dict, PracticeHistory.get_sessions
(no file, corrupt, valid), add_session, export_csv, make_entry.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from infra.practice_history import PracticeHistory, PracticeHistoryEntry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def history(tmp_path: Path) -> PracticeHistory:
    """Return a PracticeHistory pointing at a temp directory."""
    return PracticeHistory(data_dir=tmp_path)


def _entry(**kwargs) -> PracticeHistoryEntry:
    """Helper: create a PracticeHistoryEntry with sensible defaults."""
    defaults = dict(
        timestamp="2025-01-01T00:00:00",
        audio_file="/test.mp3",
        duration_seconds=120.0,
        loops_completed=5,
        avg_tempo=0.9,
        notes="",
    )
    defaults.update(kwargs)
    return PracticeHistoryEntry(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PracticeHistoryEntry
# ---------------------------------------------------------------------------

class TestPracticeHistoryEntry:
    def test_to_dict_contains_all_fields(self):
        """to_dict() serialises all fields."""
        e = _entry(notes="great session")
        d = e.to_dict()
        assert d["timestamp"] == "2025-01-01T00:00:00"
        assert d["audio_file"] == "/test.mp3"
        assert d["duration_seconds"] == 120.0
        assert d["loops_completed"] == 5
        assert d["avg_tempo"] == pytest.approx(0.9)
        assert d["notes"] == "great session"

    def test_from_dict_roundtrip(self):
        """from_dict(to_dict(e)) reproduces the original entry."""
        e = _entry(notes="roundtrip")
        assert PracticeHistoryEntry.from_dict(e.to_dict()) == e

    def test_from_dict_missing_notes_defaults_empty(self):
        """from_dict uses empty string when 'notes' key is absent."""
        d = {
            "timestamp": "2025-01-01T00:00:00",
            "audio_file": "/x.mp3",
            "duration_seconds": 60.0,
            "loops_completed": 2,
            "avg_tempo": 1.0,
        }
        e = PracticeHistoryEntry.from_dict(d)
        assert e.notes == ""

    def test_from_dict_converts_numeric_strings(self):
        """from_dict converts numeric string fields to float/int."""
        d = {
            "timestamp": "2025-01-01T00:00:00",
            "audio_file": "/x.mp3",
            "duration_seconds": "90.5",
            "loops_completed": "3",
            "avg_tempo": "0.8",
        }
        e = PracticeHistoryEntry.from_dict(d)
        assert e.duration_seconds == pytest.approx(90.5)
        assert e.loops_completed == 3
        assert e.avg_tempo == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# PracticeHistory.get_sessions
# ---------------------------------------------------------------------------

class TestGetSessions:
    def test_empty_initially(self, history: PracticeHistory):
        """get_sessions returns [] when no history file exists."""
        assert history.get_sessions() == []

    def test_corrupt_file_returns_empty(self, tmp_path: Path):
        """get_sessions returns [] when the history file is corrupt."""
        ph = PracticeHistory(data_dir=tmp_path)
        (tmp_path / "practice_history.json").write_text("INVALID", encoding="utf-8")
        assert ph.get_sessions() == []

    def test_valid_file_returns_entries(self, history: PracticeHistory):
        """get_sessions returns all stored sessions after add_session."""
        history.add_session(_entry(audio_file="/a.mp3"))
        history.add_session(_entry(audio_file="/b.mp3"))
        sessions = history.get_sessions()
        assert len(sessions) == 2
        assert sessions[0].audio_file == "/a.mp3"
        assert sessions[1].audio_file == "/b.mp3"


# ---------------------------------------------------------------------------
# PracticeHistory.add_session
# ---------------------------------------------------------------------------

class TestAddSession:
    def test_add_creates_file(self, history: PracticeHistory, tmp_path: Path):
        """add_session creates the history JSON file."""
        history.add_session(_entry())
        assert (tmp_path / "practice_history.json").is_file()

    def test_add_multiple_sessions_appended(self, history: PracticeHistory):
        """add_session appends; all sessions are present when re-read."""
        for i in range(3):
            history.add_session(_entry(audio_file=f"/{i}.mp3"))
        assert len(history.get_sessions()) == 3

    def test_save_write_error_is_silenced(self, tmp_path: Path):
        """_save() silently handles write errors (no exception raised)."""
        ph = PracticeHistory(data_dir=tmp_path)
        with patch("infra.practice_history.json.dump", side_effect=OSError("disk full")):
            ph._save([_entry()])  # must not raise


# ---------------------------------------------------------------------------
# PracticeHistory.export_csv
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_export_csv_creates_file(self, history: PracticeHistory, tmp_path: Path):
        """export_csv creates the output file."""
        history.add_session(_entry())
        out = tmp_path / "history.csv"
        history.export_csv(out)
        assert out.is_file()

    def test_export_csv_header_row(self, history: PracticeHistory, tmp_path: Path):
        """CSV output starts with the expected header."""
        history.add_session(_entry())
        out = tmp_path / "history.csv"
        history.export_csv(out)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("timestamp")

    def test_export_csv_row_count(self, history: PracticeHistory, tmp_path: Path):
        """CSV output has one data row per session."""
        history.add_session(_entry(audio_file="/x.mp3"))
        out = tmp_path / "out.csv"
        history.export_csv(out)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2  # header + 1 row

    def test_export_csv_empty_history(self, history: PracticeHistory, tmp_path: Path):
        """export_csv with no sessions still produces a header-only CSV."""
        out = tmp_path / "empty.csv"
        history.export_csv(out)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1  # header only


# ---------------------------------------------------------------------------
# PracticeHistory.make_entry
# ---------------------------------------------------------------------------

class TestMakeEntry:
    def test_make_entry_sets_timestamp(self):
        """make_entry fills the timestamp automatically."""
        e = PracticeHistory.make_entry("/file.mp3", 60.0, 3, 1.0)
        assert e.timestamp  # non-empty string
        # Must be ISO-8601-like
        assert "T" in e.timestamp or "-" in e.timestamp

    def test_make_entry_fields(self):
        """make_entry stores all provided arguments correctly."""
        e = PracticeHistory.make_entry("/song.mp3", 180.0, 10, 0.85, notes="hard")
        assert e.audio_file == "/song.mp3"
        assert e.duration_seconds == pytest.approx(180.0)
        assert e.loops_completed == 10
        assert e.avg_tempo == pytest.approx(0.85)
        assert e.notes == "hard"

    def test_make_entry_default_notes_empty(self):
        """make_entry uses empty string for notes when not provided."""
        e = PracticeHistory.make_entry("/x.mp3", 30.0, 1, 1.0)
        assert e.notes == ""


# ---------------------------------------------------------------------------
# PracticeHistory init with default data_dir (coverage of platformdirs path)
# ---------------------------------------------------------------------------

class TestDefaultDataDir:
    def test_instantiation_without_data_dir(self, monkeypatch, tmp_path):
        """PracticeHistory can be created without a data_dir argument."""
        monkeypatch.setattr(
            "infra.practice_history.user_data_dir",
            lambda *a, **k: str(tmp_path),
        )
        ph = PracticeHistory()
        assert ph._path.parent == tmp_path

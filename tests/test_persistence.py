"""
Tests for infra.persistence — 100% branch coverage.

Covers: get_metadata_path (None / valid), load_segments (None path, missing
file, corrupt JSON, valid file), save_segments (None path, valid, write
error), export_segments_text (csv, txt, invalid format).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.persistence import (
    export_segments_text,
    get_metadata_path,
    load_segments,
    save_segments,
)


# ---------------------------------------------------------------------------
# get_metadata_path
# ---------------------------------------------------------------------------

class TestGetMetadataPath:
    def test_none_input_returns_none(self):
        """get_metadata_path(None) returns None."""
        assert get_metadata_path(None) is None

    def test_appends_segments_json_suffix(self, tmp_path):
        """get_metadata_path appends .segments.json to the audio filename."""
        p = tmp_path / "track.mp3"
        meta = get_metadata_path(p)
        assert meta is not None
        assert meta.name == "track.mp3.segments.json"

    def test_works_with_wav_file(self, tmp_path):
        """get_metadata_path works with any file extension."""
        p = tmp_path / "track.wav"
        meta = get_metadata_path(p)
        assert meta.name == "track.wav.segments.json"

    def test_string_path_accepted(self, tmp_path):
        """get_metadata_path accepts a string path."""
        p = str(tmp_path / "song.flac")
        meta = get_metadata_path(p)
        assert meta is not None
        assert meta.name == "song.flac.segments.json"


# ---------------------------------------------------------------------------
# load_segments
# ---------------------------------------------------------------------------

def _build_manager():
    """Helper: manager with two segments."""
    m = SegmentManager()
    m.add_segment(Segment("A", 1.0, 2.0))
    m.add_segment(Segment("B", 3.0, 4.0))
    return m


class TestLoadSegments:
    def test_none_path_returns_empty(self):
        """load_segments(None) returns an empty SegmentManager."""
        m = load_segments(None)
        assert m.list_segments() == []

    def test_missing_file_returns_empty(self, tmp_path):
        """load_segments returns empty when the JSON file does not exist."""
        audio = tmp_path / "nonexistent.mp3"
        m = load_segments(audio)
        assert m.list_segments() == []

    def test_corrupt_json_returns_empty(self, tmp_path):
        """load_segments returns empty when JSON is malformed."""
        audio = tmp_path / "old.mp3"
        meta = get_metadata_path(audio)
        meta.write_text("NOT JSON {{", encoding="utf-8")
        m = load_segments(audio)
        assert m.list_segments() == []

    def test_valid_file_loads_segments(self, tmp_path):
        """load_segments correctly restores all segments from disk."""
        audio = tmp_path / "song.mp3"
        mgr = _build_manager()
        save_segments(audio, mgr)
        m2 = load_segments(audio)
        assert [s.name for s in m2.list_segments()] == ["A", "B"]

    def test_backwards_compat_missing_new_fields(self, tmp_path):
        """load_segments handles old JSON that lacks optional fields."""
        audio = tmp_path / "old.mp3"
        meta = get_metadata_path(audio)
        old_data = {
            "segments": [{"name": "x", "start_sec": 0.0, "end_sec": 1.0}]
        }
        meta.write_text(json.dumps(old_data), encoding="utf-8")
        m = load_segments(audio)
        segs = m.list_segments()
        assert len(segs) == 1
        assert segs[0].notes == ""
        assert segs[0].practice_count == 0


# ---------------------------------------------------------------------------
# save_segments
# ---------------------------------------------------------------------------

class TestSaveSegments:
    def test_none_path_does_nothing(self):
        """save_segments(None, ...) is a no-op and does not raise."""
        save_segments(None, _build_manager())

    def test_save_creates_json_file(self, tmp_path):
        """save_segments creates the metadata JSON file."""
        audio = tmp_path / "song.mp3"
        save_segments(audio, _build_manager())
        meta = get_metadata_path(audio)
        assert meta is not None
        assert meta.is_file()

    def test_save_produces_valid_json(self, tmp_path):
        """The created file is valid JSON with a 'segments' key."""
        audio = tmp_path / "song.mp3"
        save_segments(audio, _build_manager())
        meta = get_metadata_path(audio)
        data = json.loads(meta.read_text(encoding="utf-8"))
        assert "segments" in data
        assert len(data["segments"]) == 2

    def test_save_write_error_is_silenced(self, tmp_path):
        """save_segments silently handles write errors."""
        audio = tmp_path / "song.mp3"
        meta = get_metadata_path(audio)
        with patch("infra.persistence.json.dump", side_effect=OSError("disk full")):
            save_segments(audio, _build_manager())  # must not raise


# ---------------------------------------------------------------------------
# export_segments_text
# ---------------------------------------------------------------------------

def _manager_with_notes():
    """Helper: manager with two segments, one with notes and category."""
    m = SegmentManager()
    m.add_segment(
        Segment("Verse", 0.0, 10.0, notes="hard", category="difficult")
    )
    m.add_segment(Segment("Chorus", 10.0, 20.0))
    return m


class TestExportSegmentsText:
    def test_export_csv_creates_file(self, tmp_path, audio_path):
        """export_segments_text with fmt='csv' creates a CSV file."""
        out = tmp_path / "out.csv"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="csv")
        assert out.is_file()

    def test_export_csv_has_header(self, tmp_path, audio_path):
        """CSV output starts with the expected header row."""
        out = tmp_path / "out.csv"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="csv")
        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("audio_file")

    def test_export_csv_row_count(self, tmp_path, audio_path):
        """CSV output has header + one row per segment."""
        out = tmp_path / "out.csv"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="csv")
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3  # header + 2 segments

    def test_export_txt_creates_file(self, tmp_path, audio_path):
        """export_segments_text with fmt='txt' creates a text file."""
        out = tmp_path / "out.txt"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="txt")
        assert out.is_file()

    def test_export_txt_contains_segment_names(self, tmp_path, audio_path):
        """TXT output contains segment names."""
        out = tmp_path / "out.txt"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="txt")
        content = out.read_text(encoding="utf-8")
        assert "Verse" in content
        assert "Chorus" in content

    def test_export_txt_includes_category_line(self, tmp_path, audio_path):
        """TXT output includes the 'Cat.' line for segments with a category."""
        out = tmp_path / "out.txt"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="txt")
        content = out.read_text(encoding="utf-8")
        assert "Cat." in content
        assert "difficult" in content

    def test_export_txt_includes_notes_line(self, tmp_path, audio_path):
        """TXT output includes the 'Notes' line for segments with notes."""
        out = tmp_path / "out.txt"
        export_segments_text(audio_path, _manager_with_notes(), out, fmt="txt")
        content = out.read_text(encoding="utf-8")
        assert "Notes" in content
        assert "hard" in content

    def test_export_txt_no_category_no_cat_line(self, tmp_path, audio_path):
        """TXT output omits 'Cat.' line for segments without a category."""
        m = SegmentManager()
        m.add_segment(Segment("Solo", 5.0, 10.0))  # no category
        out = tmp_path / "out.txt"
        export_segments_text(audio_path, m, out, fmt="txt")
        content = out.read_text(encoding="utf-8")
        assert "Cat." not in content

    def test_invalid_format_raises_value_error(self, tmp_path, audio_path):
        """export_segments_text raises ValueError for an unknown format."""
        with pytest.raises(ValueError, match="Unknown format"):
            export_segments_text(
                audio_path, _manager_with_notes(), tmp_path / "x.xml", fmt="xml"
            )

    def test_export_csv_none_audio_path(self, tmp_path):
        """export_segments_text works with None as audio_file_path."""
        out = tmp_path / "out.csv"
        export_segments_text(None, SegmentManager(), out, fmt="csv")
        assert out.is_file()

    def test_export_txt_none_audio_path(self, tmp_path):
        """TXT export works with None as audio_file_path."""
        out = tmp_path / "out.txt"
        export_segments_text(None, SegmentManager(), out, fmt="txt")
        assert out.is_file()

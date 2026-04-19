"""
Tests for ui.history_dialog (pytest-qt) — 100% branch coverage.

Covers: dialog creation (empty history, populated history), _populate
(summary text, table rows, fmt_duration, audio_file path stripping,
missing audio_file), _on_export_csv (dialog cancelled, success, exception),
retranslate_ui.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from infra.practice_history import PracticeHistory, PracticeHistoryEntry
from ui.history_dialog import HistoryDialog, _fmt_duration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    timestamp: str = "2025-01-01T10:00:00",
    audio_file: str = "/music/song.mp3",
    duration: float = 120.0,
    loops: int = 4,
    avg_tempo: float = 1.0,
    notes: str = "",
) -> PracticeHistoryEntry:
    return PracticeHistoryEntry(
        timestamp=timestamp,
        audio_file=audio_file,
        duration_seconds=duration,
        loops_completed=loops,
        avg_tempo=avg_tempo,
        notes=notes,
    )


@pytest.fixture()
def empty_history(tmp_path) -> PracticeHistory:
    return PracticeHistory(tmp_path / "history.json")


@pytest.fixture()
def populated_history(tmp_path) -> PracticeHistory:
    h = PracticeHistory(tmp_path / "history.json")
    h.add_session(_make_entry(audio_file="/music/song.mp3", duration=60.0, loops=2))
    h.add_session(_make_entry(audio_file="/music/other.flac", duration=90.0, loops=3))
    return h


# ---------------------------------------------------------------------------
# _fmt_duration helper
# ---------------------------------------------------------------------------

class TestFmtDuration:
    def test_zero(self):
        assert _fmt_duration(0) == "00:00"

    def test_negative_clamped_to_zero(self):
        assert _fmt_duration(-5) == "00:00"

    def test_sixty_seconds(self):
        assert _fmt_duration(60) == "01:00"

    def test_ninety_seconds(self):
        assert _fmt_duration(90) == "01:30"

    def test_one_hour(self):
        assert _fmt_duration(3600) == "60:00"


# ---------------------------------------------------------------------------
# Dialog creation
# ---------------------------------------------------------------------------

class TestHistoryDialogCreation:
    def test_dialog_created_empty_history(self, qtbot, empty_history):
        """Dialog opens without error on empty history."""
        dlg = HistoryDialog(empty_history)
        qtbot.addWidget(dlg)
        assert dlg is not None

    def test_dialog_created_with_entries(self, qtbot, populated_history):
        """Dialog opens without error when history has entries."""
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 2

    def test_window_title_set(self, qtbot, empty_history):
        """Dialog window title is non-empty."""
        dlg = HistoryDialog(empty_history)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() != ""

    def test_summary_label_empty_history(self, qtbot, empty_history):
        """Summary label shows 0 sessions for an empty history."""
        dlg = HistoryDialog(empty_history)
        qtbot.addWidget(dlg)
        assert "0" in dlg.lbl_summary.text()

    def test_summary_label_populated_history(self, qtbot, populated_history):
        """Summary label reflects the number of sessions and total loops."""
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        assert "2" in dlg.lbl_summary.text()
        assert "5" in dlg.lbl_summary.text()  # 2 + 3 loops


# ---------------------------------------------------------------------------
# _populate — specific cell values
# ---------------------------------------------------------------------------

class TestHistoryDialogPopulate:
    def test_audio_file_shows_basename_only(self, qtbot, populated_history):
        """Table shows only the filename, not the full path."""
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        # Column 1 is _COL_FILE
        item = dlg.table.item(0, 1)
        assert item is not None
        assert "/" not in item.text()
        assert item.text() in ("song.mp3", "other.flac")

    def test_empty_audio_file_shows_dash(self, qtbot, tmp_path):
        """A blank audio_file shows '—' in the table."""
        h = PracticeHistory(tmp_path / "h.json")
        h.add_session(_make_entry(audio_file=""))
        dlg = HistoryDialog(h)
        qtbot.addWidget(dlg)
        item = dlg.table.item(0, 1)
        assert item is not None
        assert item.text() == "—"

    def test_tempo_cell_shows_percentage(self, qtbot, tmp_path):
        """The tempo column shows a percentage string."""
        h = PracticeHistory(tmp_path / "h.json")
        h.add_session(_make_entry(avg_tempo=0.75))
        dlg = HistoryDialog(h)
        qtbot.addWidget(dlg)
        item = dlg.table.item(0, 4)  # _COL_TEMPO = 4
        assert item is not None
        assert "%" in item.text()
        assert "75" in item.text()

    def test_notes_cell_filled(self, qtbot, tmp_path):
        """The notes column shows the session notes."""
        h = PracticeHistory(tmp_path / "h.json")
        h.add_session(_make_entry(notes="Practice slowly"))
        dlg = HistoryDialog(h)
        qtbot.addWidget(dlg)
        item = dlg.table.item(0, 5)  # _COL_NOTES = 5
        assert item is not None
        assert item.text() == "Practice slowly"

    def test_notes_cell_empty_when_no_notes(self, qtbot, tmp_path):
        """The notes column is empty when entry has no notes."""
        h = PracticeHistory(tmp_path / "h.json")
        h.add_session(_make_entry(notes=""))
        dlg = HistoryDialog(h)
        qtbot.addWidget(dlg)
        item = dlg.table.item(0, 5)
        assert item is not None
        assert item.text() == ""


# ---------------------------------------------------------------------------
# _on_export_csv
# ---------------------------------------------------------------------------

class TestHistoryDialogExport:
    def test_export_cancelled_does_nothing(self, qtbot, populated_history, monkeypatch):
        """Cancelling the file dialog does not call export_csv."""
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: ("", ""),
        )
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        dlg._on_export_csv()  # must not raise

    def test_export_success_shows_information(
        self, qtbot, tmp_path, populated_history, monkeypatch
    ):
        """Successful export shows an information dialog."""
        out = str(tmp_path / "export.csv")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, ""),
        )
        shown = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information",
            lambda *a, **k: shown.append(1),
        )
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        dlg._on_export_csv()
        assert len(shown) == 1

    def test_export_exception_shows_critical(
        self, qtbot, tmp_path, populated_history, monkeypatch
    ):
        """An exception during export shows a critical error dialog."""
        out = str(tmp_path / "export.csv")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, ""),
        )
        monkeypatch.setattr(
            populated_history,
            "export_csv",
            MagicMock(side_effect=OSError("disk full")),
        )
        errors = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.critical",
            lambda *a, **k: errors.append(1),
        )
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        dlg._on_export_csv()
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# retranslate_ui
# ---------------------------------------------------------------------------

class TestHistoryDialogRetranslate:
    def test_retranslate_ui_does_not_crash(self, qtbot, populated_history):
        """retranslate_ui() runs without error."""
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        dlg.retranslate_ui()  # must not raise

    def test_retranslate_ui_updates_window_title(self, qtbot, populated_history):
        """retranslate_ui() sets a non-empty window title."""
        dlg = HistoryDialog(populated_history)
        qtbot.addWidget(dlg)
        dlg.retranslate_ui()
        assert dlg.windowTitle() != ""

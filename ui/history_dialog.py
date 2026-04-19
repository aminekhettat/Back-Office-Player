"""
PySide6 practice history dialog.

A QDialog that displays all past practice sessions in a read-only table
and allows the user to export the history to CSV.

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

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from infra.i18n import tr
from infra.practice_history import PracticeHistory

# Column indices
_COL_DATE = 0
_COL_FILE = 1
_COL_DURATION = 2
_COL_LOOPS = 3
_COL_TEMPO = 4
_COL_NOTES = 5
_NUM_COLS = 6


def _fmt_duration(seconds: float) -> str:
    """Format *seconds* as ``mm:ss``."""
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class HistoryDialog(QDialog):
    """
    Read-only practice history viewer.

    Loads all entries from :class:`~infra.practice_history.PracticeHistory`
    and shows them in a :class:`~PySide6.QtWidgets.QTableWidget`.

    Parameters
    ----------
    history : PracticeHistory
        The history object to display.
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(self, history: PracticeHistory, parent=None) -> None:
        super().__init__(parent)
        self._history = history
        self.setWindowTitle(tr("history_title"))
        self.setAccessibleName(tr("history_title"))
        self.setAccessibleDescription(tr("history_accessible_desc"))
        self.resize(800, 450)
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Summary label (filled after population)
        self.lbl_summary = QLabel("")
        self.lbl_summary.setAccessibleName(tr("history_summary_label"))
        layout.addWidget(self.lbl_summary)

        # Table
        self.table = QTableWidget(0, _NUM_COLS)
        self.table.setHorizontalHeaderLabels(
            [
                tr("history_col_date"),
                tr("history_col_file"),
                tr("history_col_duration"),
                tr("history_col_loops"),
                tr("history_col_tempo"),
                tr("history_col_notes"),
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAccessibleName(tr("history_table_accessible_name"))
        self.table.setAccessibleDescription(tr("history_table_accessible_desc"))
        layout.addWidget(self.table)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.btn_export = QPushButton(tr("btn_export_csv_hist"))
        self.btn_export.setAccessibleName(tr("history_btn_export_accessible_name"))
        self.btn_export.setAccessibleDescription(tr("history_btn_export_accessible_desc"))
        self.btn_export.clicked.connect(self._on_export_csv)
        btn_row.addWidget(self.btn_export)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _populate(self) -> None:
        """Load history entries into the table."""
        sessions = self._history.get_sessions()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(sessions))

        total_loops = 0
        total_duration = 0.0

        for row, entry in enumerate(sessions):
            # Timestamp (strip microseconds for readability)
            ts = entry.timestamp[:19].replace("T", " ")
            self._set_cell(row, _COL_DATE, ts)

            # Audio file — show only the filename, not the full path
            fname = Path(entry.audio_file).name if entry.audio_file else "—"
            item_file = QTableWidgetItem(fname)
            item_file.setToolTip(entry.audio_file)
            self.table.setItem(row, _COL_FILE, item_file)

            self._set_cell(row, _COL_DURATION, _fmt_duration(entry.duration_seconds))

            item_loops = QTableWidgetItem()
            item_loops.setData(Qt.ItemDataRole.DisplayRole, entry.loops_completed)
            self.table.setItem(row, _COL_LOOPS, item_loops)

            self._set_cell(row, _COL_TEMPO, f"{entry.avg_tempo * 100:.0f} %")
            self._set_cell(row, _COL_NOTES, entry.notes or "")

            total_loops += entry.loops_completed
            total_duration += entry.duration_seconds

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

        # Summary
        n = len(sessions)
        dur_str = _fmt_duration(total_duration)
        self.lbl_summary.setText(tr("history_summary", n=n, loops=total_loops, dur=dur_str))

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def _on_export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("history_export_title"),
            tr("history_export_default"),
            tr("filter_csv"),
        )
        if not filename:
            return
        try:
            self._history.export_csv(Path(filename))
            QMessageBox.information(
                self,
                tr("dlg_exported_title"),
                tr("history_exported", path=filename),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("dlg_error_title"),
                tr("history_err_export", err=exc),
            )

    # ------------------------------------------------------------------ #
    # Retranslation
    # ------------------------------------------------------------------ #
    def retranslate_ui(self) -> None:
        """Apply the current language to all translatable widgets."""
        self.setWindowTitle(tr("history_title"))
        self.lbl_summary.setAccessibleName(tr("history_summary_label"))
        self.btn_export.setText(tr("btn_export_csv_hist"))
        self.btn_export.setAccessibleName(tr("history_btn_export_accessible_name"))
        self.btn_export.setAccessibleDescription(tr("history_btn_export_accessible_desc"))
        self.table.setHorizontalHeaderLabels(
            [
                tr("history_col_date"),
                tr("history_col_file"),
                tr("history_col_duration"),
                tr("history_col_loops"),
                tr("history_col_tempo"),
                tr("history_col_notes"),
            ]
        )
        self.table.setAccessibleName(tr("history_table_accessible_name"))
        self.table.setAccessibleDescription(tr("history_table_accessible_desc"))

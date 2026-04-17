"""
Segment list widget for Back-Office Player.

This module defines the SegmentListWidget which displays a list of
named segments and provides controls for navigation, reordering, and
management.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.0
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.i18n import tr


class SegmentListWidget(QWidget):
    """
    Widget displaying a list of segments with navigation controls.

    Allows users to:

    - View all segments (or filter by category).
    - Select a segment and jump to it.
    - Delete segments individually.
    - Move segments up or down in the list.

    Attributes
    ----------
    segment_manager : SegmentManager
        The segment manager whose segments are displayed.
    selected_callback : callable or None
        Called with the selected :class:`~core.segment.Segment` when the
        user clicks or double-clicks a list item.
    changed_callback : callable or None
        Called (no arguments) whenever the segment list is modified
        (add, delete, or reorder).  Typically used to persist changes.
    export_wav_callback : callable or None
        Called with the selected :class:`~core.segment.Segment` when the
        user clicks "Exporter WAV".  The caller is responsible for
        opening the save dialog and writing the file.
    delete_callback : callable or None
        Called with ``(segment_name: str)`` instead of removing the segment
        directly.  If ``None``, :meth:`on_delete_segment` removes the
        segment itself.  Set by the parent to enable undo via
        :class:`~core.commands.CommandHistory`.
    export_mp3_callback : callable or None
        Called with the selected :class:`~core.segment.Segment` when the
        user clicks "Exporter MP3".  The caller is responsible for
        opening the save dialog and writing the file.
    """

    def __init__(self, segment_manager: SegmentManager, parent=None) -> None:
        super().__init__(parent)
        self.segment_manager = segment_manager
        self.selected_callback = None
        self.changed_callback = None
        self.export_wav_callback = None
        self.export_mp3_callback = None
        # Optional: called with (segment_name: str) instead of removing directly.
        # If None, on_delete_segment removes the segment itself.
        self.delete_callback = None

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        """Build the segment list UI with full accessibility."""
        layout = QVBoxLayout(self)

        # Label + category filter row
        filter_row = QHBoxLayout()
        self.lbl_segments = QLabel(tr("segment_list_label"))
        self.lbl_segments.setAccessibleName(tr("segment_list_label"))
        self.cmb_category = QComboBox()
        self.cmb_category.setAccessibleName(
            tr("segment_list_category_filter_accessible_name")
        )
        self.cmb_category.setAccessibleDescription(
            tr("segment_list_category_filter_accessible_desc")
        )
        self.cmb_category.currentTextChanged.connect(self._on_category_filter_changed)
        self.lbl_category = QLabel(tr("segment_list_category_label"))
        filter_row.addWidget(self.lbl_segments)
        filter_row.addStretch()
        filter_row.addWidget(self.lbl_category)
        filter_row.addWidget(self.cmb_category)
        layout.addLayout(filter_row)

        # List widget for segments
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName(tr("segment_list_accessible_name"))
        self.list_widget.setAccessibleDescription(
            tr("segment_list_accessible_desc")
        )
        self.list_widget.itemClicked.connect(self.on_segment_selected)
        self.list_widget.itemDoubleClicked.connect(self.on_jump_to_segment)
        layout.addWidget(self.list_widget)

        # Buttons row
        buttons_layout = QHBoxLayout()

        self.btn_jump = QPushButton(tr("btn_jump"))
        self.btn_jump.setAccessibleName(tr("segment_btn_jump_accessible_name"))
        self.btn_jump.setAccessibleDescription(tr("segment_btn_jump_accessible_desc"))
        self.btn_jump.clicked.connect(self.on_jump_to_segment)

        self.btn_delete = QPushButton(tr("btn_delete_segment"))
        self.btn_delete.setAccessibleName(tr("segment_btn_delete_accessible_name"))
        self.btn_delete.setAccessibleDescription(
            tr("segment_btn_delete_accessible_desc")
        )
        self.btn_delete.clicked.connect(self.on_delete_segment)

        self.btn_move_up = QPushButton(tr("btn_move_up"))
        self.btn_move_up.setAccessibleName(tr("segment_btn_move_up_accessible_name"))
        self.btn_move_up.setAccessibleDescription(
            tr("segment_btn_move_up_accessible_desc")
        )
        self.btn_move_up.clicked.connect(self.on_move_up)

        self.btn_move_down = QPushButton(tr("btn_move_down"))
        self.btn_move_down.setAccessibleName(
            tr("segment_btn_move_down_accessible_name")
        )
        self.btn_move_down.setAccessibleDescription(
            tr("segment_btn_move_down_accessible_desc")
        )
        self.btn_move_down.clicked.connect(self.on_move_down)

        self.btn_export_wav = QPushButton(tr("btn_export_wav"))
        self.btn_export_wav.setAccessibleName(
            tr("segment_btn_export_wav_accessible_name")
        )
        self.btn_export_wav.setAccessibleDescription(
            tr("segment_btn_export_wav_accessible_desc")
        )
        self.btn_export_wav.clicked.connect(self.on_export_wav)

        self.btn_export_mp3 = QPushButton(tr("btn_export_mp3"))
        self.btn_export_mp3.setAccessibleName(
            tr("segment_btn_export_mp3_accessible_name")
        )
        self.btn_export_mp3.setAccessibleDescription(
            tr("segment_btn_export_mp3_accessible_desc")
        )
        self.btn_export_mp3.clicked.connect(self.on_export_mp3)

        buttons_layout.addWidget(self.btn_jump)
        buttons_layout.addWidget(self.btn_move_up)
        buttons_layout.addWidget(self.btn_move_down)
        buttons_layout.addWidget(self.btn_delete)
        buttons_layout.addWidget(self.btn_export_wav)
        buttons_layout.addWidget(self.btn_export_mp3)

        layout.addLayout(buttons_layout)

        self.refresh_list()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def refresh_list(self) -> None:
        """Refresh the list display with current segments."""
        selected_category = self.cmb_category.currentText()
        all_cat = tr("segment_list_all_categories")

        self.list_widget.clear()
        for segment in self.segment_manager.list_segments():
            if (
                selected_category
                and selected_category != all_cat
                and segment.category != selected_category
            ):
                continue

            duration = segment.duration()
            text = (
                f"{segment.name} "
                f"({segment.start_sec:.1f}s – {segment.end_sec:.1f}s) "
                f"[{duration:.1f}s]"
            )
            if segment.category:
                text += f" [{segment.category}]"

            item = QListWidgetItem(text)
            item.setData(256, segment)

            # Notes as tooltip
            if segment.notes:
                item.setToolTip(segment.notes)

            # Color
            if segment.color:
                try:
                    item.setForeground(QColor(segment.color))
                except Exception:  # pragma: no cover
                    pass

            self.list_widget.addItem(item)

        self._refresh_category_filter()

    def add_segment(self, segment: Segment) -> None:
        """
        Add a new segment to the manager and refresh the list.

        Parameters
        ----------
        segment : Segment
            The segment to add.
        """
        self.segment_manager.add_segment(segment)
        self.refresh_list()

    def set_segment_manager(self, segment_manager: SegmentManager) -> None:
        """
        Update the segment manager reference and refresh the list.

        Parameters
        ----------
        segment_manager : SegmentManager
            The new segment manager.
        """
        self.segment_manager = segment_manager
        self.refresh_list()

    # ------------------------------------------------------------------ #
    # Slots / callbacks
    # ------------------------------------------------------------------ #
    def on_segment_selected(self, item: QListWidgetItem) -> None:
        segment = item.data(256)
        if self.selected_callback and segment:
            self.selected_callback(segment)

    def on_jump_to_segment(self) -> None:
        current_item = self.list_widget.currentItem()
        if current_item:
            self.on_segment_selected(current_item)

    def on_delete_segment(self) -> None:
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                tr("dlg_no_selection_title"),
                tr("dlg_no_selection_delete_msg"),
            )
            return
        segment = current_item.data(256)
        if segment:
            if self.delete_callback:
                # Delegate to the parent (allows undo via CommandHistory).
                self.delete_callback(segment.name)
            else:
                self.segment_manager.remove_segment(segment.name)
                self.refresh_list()
                if self.changed_callback:
                    self.changed_callback()
            QMessageBox.information(
                self,
                tr("dlg_deleted_title"),
                tr("dlg_segment_deleted", name=segment.name),
            )

    def on_export_wav(self) -> None:
        """Delegate WAV export of the selected segment to the parent."""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                tr("dlg_no_selection_title"),
                tr("dlg_no_selection_export_wav_msg"),
            )
            return
        segment = current_item.data(256)
        if segment and self.export_wav_callback:
            self.export_wav_callback(segment)

    def on_export_mp3(self) -> None:
        """Delegate MP3 export of the selected segment to the parent."""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                tr("dlg_no_selection_title"),
                tr("dlg_no_selection_export_mp3_msg"),
            )
            return
        segment = current_item.data(256)
        if segment and self.export_mp3_callback:
            self.export_mp3_callback(segment)

    def on_move_up(self) -> None:
        """Move the selected segment one position earlier."""
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
        segment = current_item.data(256)
        if segment:
            moved = self.segment_manager.move_up(segment.name)
            if moved:
                self.refresh_list()
                # Re-select the moved segment
                self._reselect(segment.name)
                if self.changed_callback:
                    self.changed_callback()

    def on_move_down(self) -> None:
        """Move the selected segment one position later."""
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
        segment = current_item.data(256)
        if segment:
            moved = self.segment_manager.move_down(segment.name)
            if moved:
                self.refresh_list()
                self._reselect(segment.name)
                if self.changed_callback:
                    self.changed_callback()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    def _refresh_category_filter(self) -> None:
        """Rebuild the category filter combobox from current segments."""
        prev = self.cmb_category.currentText()
        self.cmb_category.blockSignals(True)
        self.cmb_category.clear()
        all_cat = tr("segment_list_all_categories")
        self.cmb_category.addItem(all_cat)

        categories = sorted(
            {s.category for s in self.segment_manager.list_segments() if s.category}
        )
        for cat in categories:
            self.cmb_category.addItem(cat)

        idx = self.cmb_category.findText(prev)
        self.cmb_category.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_category.blockSignals(False)

    def _on_category_filter_changed(self, _text: str) -> None:
        """Refresh the list whenever the category filter combo changes."""
        self.refresh_list()

    def retranslate_ui(self) -> None:
        """Apply the current language to all translatable widgets."""
        self.lbl_segments.setText(tr("segment_list_label"))
        self.lbl_category.setText(tr("segment_list_category_label"))
        self.btn_jump.setText(tr("btn_jump"))
        self.btn_delete.setText(tr("btn_delete_segment"))
        self.btn_move_up.setText(tr("btn_move_up"))
        self.btn_move_down.setText(tr("btn_move_down"))
        self.btn_export_wav.setText(tr("btn_export_wav"))
        self.btn_export_mp3.setText(tr("btn_export_mp3"))
        self.btn_export_mp3.setAccessibleName(
            tr("segment_btn_export_mp3_accessible_name")
        )
        self.cmb_category.setAccessibleName(
            tr("segment_list_category_filter_accessible_name")
        )
        self.list_widget.setAccessibleName(tr("segment_list_accessible_name"))
        self.refresh_list()

    def _reselect(self, name: str) -> None:
        """Re-select the list item whose segment has the given name."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            seg = item.data(256) if item else None
            if seg and seg.name == name:
                self.list_widget.setCurrentItem(item)
                break

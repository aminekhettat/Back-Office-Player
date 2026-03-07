"""
Segment list widget for Back-Office Player.

This module defines the SegmentListWidget which displays a list of
named segments and provides controls for navigation and management.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.1.0
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QInputDialog,
    QMessageBox,
)

from core.segment_manager import SegmentManager
from core.segment import Segment


class SegmentListWidget(QWidget):
    """
    Widget displaying a list of segments with navigation controls.

    Allows users to:

    - View all segments for the current audio file.
    - Select a segment and jump to it.
    - Delete segments individually.

    Attributes
    ----------
    segment_manager : SegmentManager
        The segment manager whose segments are displayed.
    selected_callback : callable or None
        Called with the selected :class:`~core.segment.Segment` when the
        user clicks or double-clicks a list item.
    changed_callback : callable or None
        Called (no arguments) whenever the segment list is modified
        (add or delete). Typically used to persist changes to disk.
    list_widget : QListWidget
        The Qt list widget showing all segments.
    btn_jump : QPushButton
        Button that jumps playback to the selected segment's start.
    btn_delete : QPushButton
        Button that deletes the selected segment.
    """

    def __init__(self, segment_manager: SegmentManager, parent=None) -> None:
        """
        Initialize the segment list widget.

        Parameters
        ----------
        segment_manager : SegmentManager
            The segment manager to display.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.segment_manager = segment_manager
        self.selected_callback = None  # Callback when segment is selected
        self.changed_callback = None   # Callback when the segment list is modified

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the segment list UI with full accessibility."""
        layout = QVBoxLayout(self)

        # Label for the list
        lbl_segments = QLabel("Segments for current audio file:")
        lbl_segments.setAccessibleName("Segments list label")

        # List widget for segments
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("Segments list")
        self.list_widget.setAccessibleDescription(
            "List of all named segments for the current audio file. "
            "Select a segment and press Enter or click 'Jump to Segment' to navigate to it."
        )
        self.list_widget.itemClicked.connect(self.on_segment_selected)
        self.list_widget.itemDoubleClicked.connect(self.on_jump_to_segment)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.btn_jump = QPushButton("Jump to Segment")
        self.btn_jump.setAccessibleName("Jump to selected segment")
        self.btn_jump.setAccessibleDescription(
            "Jump playback to the start of the selected segment."
        )
        self.btn_jump.clicked.connect(self.on_jump_to_segment)

        self.btn_delete = QPushButton("Delete Segment")
        self.btn_delete.setAccessibleName("Delete selected segment")
        self.btn_delete.setAccessibleDescription(
            "Remove the selected segment from the list. This cannot be undone unless you export and re-import."
        )
        self.btn_delete.clicked.connect(self.on_delete_segment)

        buttons_layout.addWidget(self.btn_jump)
        buttons_layout.addWidget(self.btn_delete)

        # Assemble layout
        layout.addWidget(lbl_segments)
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons_layout)

        self.refresh_list()

    def refresh_list(self) -> None:
        """
        Refresh the list display with current segments.
        """
        self.list_widget.clear()

        for segment in self.segment_manager.list_segments():
            duration = segment.duration()
            # Display: "Name (start - end) [duration]"
            text = f"{segment.name} ({segment.start_sec:.1f}s - {segment.end_sec:.1f}s) [{duration:.1f}s]"
            item = QListWidgetItem(text)
            item.setData(256, segment)  # Store segment object
            self.list_widget.addItem(item)

    def on_segment_selected(self, item: QListWidgetItem) -> None:
        """
        Callback when a segment is selected in the list.

        Parameters
        ----------
        item : QListWidgetItem
            The selected item.
        """
        segment = item.data(256)
        if self.selected_callback and segment:
            self.selected_callback(segment)

    def on_jump_to_segment(self) -> None:
        """
        Jump to the selected segment (emit callback).
        """
        current_item = self.list_widget.currentItem()
        if current_item:
            self.on_segment_selected(current_item)

    def on_delete_segment(self) -> None:
        """
        Delete the selected segment.
        """
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a segment to delete.")
            return

        segment = current_item.data(256)
        if segment:
            self.segment_manager.remove_segment(segment.name)
            self.refresh_list()
            if self.changed_callback:
                self.changed_callback()
            QMessageBox.information(self, "Deleted", f"Segment '{segment.name}' deleted.")

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

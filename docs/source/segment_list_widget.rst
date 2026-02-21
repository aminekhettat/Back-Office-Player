Segment List Widget
===================

.. automodule:: ui.segment_list_widget
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The `segment_list_widget` module provides a Qt widget for displaying and managing
audio segments. It allows users to:

- View all named segments for the current audio file
- Select a segment to jump to its start position
- Delete segments
- Integrate with the main window for seamless workflow

Key Features (Phase 1)
~~~~~~~~~~~~~~~~~~~~~~

- **Segment List Display**: Shows all segments with time ranges and durations
- **Accessible**: Full keyboard navigation and screen reader support
- **Jump Navigation**: Select a segment and jump to its start position
- **Delete Support**: Remove unwanted segments
- **Auto-Refresh**: List updates automatically when segments are added/deleted
- **Double-Click Support**: Double-click a segment to jump to it

SegmentListWidget Class
-----------------------

.. autoclass:: ui.segment_list_widget.SegmentListWidget
   :members:
   :private-members:
   :special-members: __init__
   :show-inheritance:

Example Usage
~~~~~~~~~~~~~

.. code-block:: python

    from core.segment_manager import SegmentManager
    from ui.segment_list_widget import SegmentListWidget

    # Create a segment manager and widget
    manager = SegmentManager()
    widget = SegmentListWidget(manager)

    # Set up callback for when a segment is selected
    def on_segment_selected(segment):
        print(f"User selected: {segment.name} ({segment.start_sec}s - {segment.end_sec}s)")

    widget.selected_callback = on_segment_selected

    # Add a segment to the manager
    from core.segment import Segment
    seg = Segment(name="Verse 1", start_sec=0.0, end_sec=20.5)
    widget.add_segment(seg)

    # Update the manager reference
    new_manager = SegmentManager()
    widget.set_segment_manager(new_manager)

Accessibility Features
~~~~~~~~~~~~~~~~~~~~~~

The widget is fully accessible to screen readers and keyboard users:

- **Accessible Names**: All controls have clear, descriptive names
- **Accessible Descriptions**: Buttons and widgets describe their function
- **Keyboard Navigation**: Tab/Shift+Tab to move between controls
- **List Navigation**: Arrow keys to move between segments
- **Double-Click & Enter**: Both methods jump to selected segment
- **Screen Reader Announcements**: Status updates announced to assistive tech

Integration with Main Window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In `ui/main_window.py`, the segment list is integrated as:

.. code-block:: python

    self.segment_list_widget = SegmentListWidget(self.segment_manager)
    self.segment_list_widget.selected_callback = self.on_segment_selected

    # When user selects a segment:
    def on_segment_selected(self, segment):
        self.audio_player.set_position(segment.start_sec)
        self.lbl_status.setText(f"Jumped to '{segment.name}'...")

Segment Display Format
~~~~~~~~~~~~~~~~~~~~~~

Segments are displayed in the list with the following format:

.. code-block:: text

    Segment Name (12.5s - 45.0s) [32.5s duration]

Components:

- **Segment Name**: User-defined name (e.g., "Verse 1", "Chorus")
- **Start Time**: In seconds, formatted to 1 decimal place
- **End Time**: In seconds, formatted to 1 decimal place
- **Duration**: Calculated as (end_sec - start_sec), always ≥ 0

Storage Format
~~~~~~~~~~~~~~

Segments are serialized to JSON (via `Segment.to_dict()`) as:

.. code-block:: json

    {
      "name": "Verse 1",
      "start_sec": 12.5,
      "end_sec": 45.0
    }

This allows for:

- Saving segments to `.bop` configuration files
- Importing/exporting practice configurations
- Persistence to `.segments.json` metadata files

See Also
~~~~~~~~

- :mod:`core.segment` — Individual segment data class
- :mod:`core.segment_manager` — Manage collections of segments
- :mod:`ui.main_window` — Main application window
- :mod:`infra.persistence` — Save/load segments from disk

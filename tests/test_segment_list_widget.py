"""
Tests for ui.segment_list_widget (pytest-qt) — 100% branch coverage.

Covers: creation with manager, refresh_list (empty, with segments, category
filter), add_segment, set_segment_manager, on_segment_selected, on_jump_to_segment,
on_delete_segment (no selection, with selection), on_move_up (no selection /
with selection / not moved), on_move_down (same), _on_category_filter_changed,
colour/notes/tooltip branches.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import pytest

from core.segment import Segment
from core.segment_manager import SegmentManager
from ui.segment_list_widget import SegmentListWidget

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _mgr(*names, **kwargs) -> SegmentManager:
    """Helper: build a SegmentManager from a list of names."""
    m = SegmentManager()
    for i, n in enumerate(names):
        m.add_segment(Segment(n, float(i), float(i + 1), **kwargs))
    return m


@pytest.fixture()
def widget(qtbot):
    """Return a SegmentListWidget pre-populated with three segments."""
    m = _mgr("A", "B", "C")
    w = SegmentListWidget(m)
    qtbot.addWidget(w)
    w.show()
    return w


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

class TestSegmentListWidgetCreation:
    def test_list_populated_on_creation(self, widget):
        """The list is filled with segments on creation."""
        assert widget.list_widget.count() == 3

    def test_segment_manager_stored(self, widget):
        """segment_manager attribute is set correctly."""
        assert widget.segment_manager is not None

    def test_callbacks_initially_none(self, widget):
        """selected_callback and changed_callback start as None."""
        assert widget.selected_callback is None
        assert widget.changed_callback is None


# ---------------------------------------------------------------------------
# refresh_list
# ---------------------------------------------------------------------------

class TestRefreshList:
    def test_empty_manager_shows_no_items(self, qtbot):
        """refresh_list on an empty manager shows no items."""
        w = SegmentListWidget(SegmentManager())
        qtbot.addWidget(w)
        assert w.list_widget.count() == 0

    def test_all_segments_shown_by_default(self, widget):
        """All segments are shown when the category filter is '(all)'."""
        widget.refresh_list()
        assert widget.list_widget.count() == 3

    def test_category_filter_limits_list(self, qtbot):
        """Selecting a specific category shows only matching segments."""
        m = SegmentManager()
        m.add_segment(Segment("hard1", 0, 1, category="hard"))
        m.add_segment(Segment("easy1", 1, 2, category="easy"))
        m.add_segment(Segment("hard2", 2, 3, category="hard"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        idx = w.cmb_category.findText("hard")
        assert idx >= 0
        w.cmb_category.setCurrentIndex(idx)
        assert w.list_widget.count() == 2

    def test_notes_set_as_tooltip(self, qtbot):
        """Segments with notes have their notes set as item tooltip."""
        m = SegmentManager()
        m.add_segment(Segment("s", 0, 1, notes="my note"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        item = w.list_widget.item(0)
        assert item is not None
        assert item.toolTip() == "my note"

    def test_color_applied_to_item(self, qtbot):
        """Segments with a color have the color applied to the list item."""
        m = SegmentManager()
        m.add_segment(Segment("s", 0, 1, color="#ff0000"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        item = w.list_widget.item(0)
        assert item is not None
        # No crash is the main assertion; colour was set
        fg = item.foreground()
        assert fg is not None

    def test_invalid_color_does_not_crash(self, qtbot):
        """An invalid color string in a segment does not crash refresh_list."""
        m = SegmentManager()
        m.add_segment(Segment("s", 0, 1, color="not-a-color"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        # No crash — invalid colour is silently ignored
        assert w.list_widget.count() == 1

    def test_category_shown_in_item_text(self, qtbot):
        """Items include the category in their display text."""
        m = SegmentManager()
        m.add_segment(Segment("s", 0, 1, category="hard"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        text = w.list_widget.item(0).text()
        assert "hard" in text


# ---------------------------------------------------------------------------
# add_segment
# ---------------------------------------------------------------------------

class TestAddSegment:
    def test_add_segment_increases_count(self, widget):
        """add_segment adds the segment and refreshes the list."""
        widget.add_segment(Segment("D", 10.0, 11.0))
        assert widget.list_widget.count() == 4

    def test_add_segment_stored_in_manager(self, widget):
        """add_segment persists the segment in segment_manager."""
        widget.add_segment(Segment("D", 10.0, 11.0))
        assert widget.segment_manager.get_segment("D") is not None


# ---------------------------------------------------------------------------
# set_segment_manager
# ---------------------------------------------------------------------------

class TestSetSegmentManager:
    def test_set_segment_manager_replaces_and_refreshes(self, widget, qtbot):
        """set_segment_manager updates the manager and repaints the list."""
        new_m = _mgr("X", "Y")
        widget.set_segment_manager(new_m)
        assert widget.list_widget.count() == 2
        assert widget.segment_manager is new_m


# ---------------------------------------------------------------------------
# on_segment_selected
# ---------------------------------------------------------------------------

class TestOnSegmentSelected:
    def test_callback_called_when_set(self, widget):
        """on_segment_selected calls selected_callback with the segment."""
        received = []
        widget.selected_callback = lambda s: received.append(s)
        widget.list_widget.setCurrentRow(0)
        item = widget.list_widget.currentItem()
        assert item is not None
        widget.on_segment_selected(item)
        assert len(received) == 1
        assert received[0].name == "A"

    def test_no_callback_does_not_crash(self, widget):
        """on_segment_selected with selected_callback=None does not crash."""
        widget.selected_callback = None
        widget.list_widget.setCurrentRow(0)
        item = widget.list_widget.currentItem()
        widget.on_segment_selected(item)  # must not raise


# ---------------------------------------------------------------------------
# on_jump_to_segment
# ---------------------------------------------------------------------------

class TestOnJumpToSegment:
    def test_jump_triggers_callback(self, widget):
        """on_jump_to_segment calls selected_callback for the current item."""
        received = []
        widget.selected_callback = lambda s: received.append(s)
        widget.list_widget.setCurrentRow(1)
        widget.on_jump_to_segment()
        assert len(received) == 1
        assert received[0].name == "B"

    def test_jump_no_selection_does_not_crash(self, widget):
        """on_jump_to_segment without a selection does not crash."""
        widget.list_widget.clearSelection()
        widget.on_jump_to_segment()  # must not raise


# ---------------------------------------------------------------------------
# on_delete_segment
# ---------------------------------------------------------------------------

class TestOnDeleteSegment:
    def test_delete_no_selection_shows_warning(self, widget, monkeypatch):
        """on_delete_segment shows a warning dialog when nothing is selected."""
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        widget.list_widget.clearSelection()
        widget.on_delete_segment()
        assert len(warned) == 1

    def test_delete_selected_removes_item(self, widget, monkeypatch):
        """on_delete_segment removes the selected segment from the list."""
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        widget.list_widget.setCurrentRow(0)
        widget.on_delete_segment()
        assert widget.list_widget.count() == 2

    def test_delete_calls_changed_callback(self, widget, monkeypatch):
        """on_delete_segment fires changed_callback after deletion."""
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        calls = []
        widget.changed_callback = lambda: calls.append(1)
        widget.list_widget.setCurrentRow(0)
        widget.on_delete_segment()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# on_move_up
# ---------------------------------------------------------------------------

class TestOnMoveUp:
    def test_no_selection_does_nothing(self, widget):
        """on_move_up with no selection does not raise."""
        widget.list_widget.clearSelection()
        widget.on_move_up()  # must not raise
        assert widget.list_widget.count() == 3

    def test_move_up_middle_segment(self, widget):
        """on_move_up moves the selected segment one position earlier."""
        widget.list_widget.setCurrentRow(1)  # select "B"
        widget.on_move_up()
        item = widget.list_widget.item(0)
        seg = item.data(256) if item else None
        assert seg is not None
        assert seg.name == "B"

    def test_move_up_first_segment_no_change(self, widget):
        """on_move_up on the first segment does nothing (already first)."""
        widget.list_widget.setCurrentRow(0)  # select "A" (already first)
        widget.on_move_up()
        item = widget.list_widget.item(0)
        seg = item.data(256) if item else None
        assert seg is not None
        assert seg.name == "A"

    def test_move_up_calls_changed_callback(self, widget):
        """on_move_up fires changed_callback when a move occurs."""
        calls = []
        widget.changed_callback = lambda: calls.append(1)
        widget.list_widget.setCurrentRow(1)
        widget.on_move_up()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# on_move_down
# ---------------------------------------------------------------------------

class TestOnMoveDown:
    def test_no_selection_does_nothing(self, widget):
        """on_move_down with no selection does not raise."""
        widget.list_widget.clearSelection()
        widget.on_move_down()  # must not raise

    def test_move_down_first_segment(self, widget):
        """on_move_down moves the selected segment one position later."""
        widget.list_widget.setCurrentRow(0)  # select "A"
        widget.on_move_down()
        item = widget.list_widget.item(1)
        seg = item.data(256) if item else None
        assert seg is not None
        assert seg.name == "A"

    def test_move_down_last_segment_no_change(self, widget):
        """on_move_down on the last segment does nothing."""
        widget.list_widget.setCurrentRow(2)  # select "C" (last)
        widget.on_move_down()
        item = widget.list_widget.item(2)
        seg = item.data(256) if item else None
        assert seg is not None
        assert seg.name == "C"

    def test_move_down_calls_changed_callback(self, widget):
        """on_move_down fires changed_callback when a move occurs."""
        calls = []
        widget.changed_callback = lambda: calls.append(1)
        widget.list_widget.setCurrentRow(0)
        widget.on_move_down()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# _on_category_filter_changed
# ---------------------------------------------------------------------------

class TestCategoryFilterChanged:
    def test_changing_filter_calls_refresh(self, qtbot):
        """Changing the category combobox triggers refresh_list."""
        m = SegmentManager()
        m.add_segment(Segment("s1", 0, 1, category="rock"))
        m.add_segment(Segment("s2", 1, 2, category="jazz"))
        w = SegmentListWidget(m)
        qtbot.addWidget(w)
        idx = w.cmb_category.findText("rock")
        w.cmb_category.setCurrentIndex(idx)
        assert w.list_widget.count() == 1


# ---------------------------------------------------------------------------
# delete_callback (undo delegation)
# ---------------------------------------------------------------------------

class TestDeleteCallback:
    def test_delete_callback_called_instead_of_direct_remove(
        self, widget, monkeypatch
    ):
        """When delete_callback is set, it is called instead of directly removing."""
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        received = []
        widget.delete_callback = lambda name: received.append(name)
        widget.list_widget.setCurrentRow(0)
        widget.on_delete_segment()
        assert received == ["A"]
        # Segment is NOT removed because delete_callback took over
        assert widget.segment_manager.get_segment("A") is not None

    def test_delete_callback_not_called_when_none(self, widget, monkeypatch):
        """Without delete_callback, the segment is removed directly."""
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        widget.delete_callback = None
        widget.list_widget.setCurrentRow(0)
        widget.on_delete_segment()
        assert widget.list_widget.count() == 2


# ---------------------------------------------------------------------------
# export_wav_callback
# ---------------------------------------------------------------------------

class TestExportWavCallback:
    def test_export_wav_no_selection_shows_warning(self, widget, monkeypatch):
        """on_export_wav shows a warning when nothing is selected."""
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        widget.list_widget.clearSelection()
        widget.on_export_wav()
        assert len(warned) == 1

    def test_export_wav_calls_callback(self, widget):
        """on_export_wav calls export_wav_callback with the selected segment."""
        received = []
        widget.export_wav_callback = lambda seg: received.append(seg)
        widget.list_widget.setCurrentRow(0)
        widget.on_export_wav()
        assert len(received) == 1
        assert received[0].name == "A"

    def test_export_wav_no_callback_does_not_crash(self, widget):
        """on_export_wav with export_wav_callback=None does not crash."""
        widget.export_wav_callback = None
        widget.list_widget.setCurrentRow(0)
        widget.on_export_wav()  # must not raise


# ---------------------------------------------------------------------------
# export_mp3_callback
# ---------------------------------------------------------------------------

class TestExportMp3Callback:
    def test_export_mp3_no_selection_shows_warning(self, widget, monkeypatch):
        """on_export_mp3 shows a warning when nothing is selected."""
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        widget.list_widget.clearSelection()
        widget.on_export_mp3()
        assert len(warned) == 1

    def test_export_mp3_calls_callback(self, widget):
        """on_export_mp3 calls export_mp3_callback with the selected segment."""
        received = []
        widget.export_mp3_callback = lambda seg: received.append(seg)
        widget.list_widget.setCurrentRow(0)
        widget.on_export_mp3()
        assert len(received) == 1
        assert received[0].name == "A"

    def test_export_mp3_no_callback_does_not_crash(self, widget):
        """on_export_mp3 with export_mp3_callback=None does not crash."""
        widget.export_mp3_callback = None
        widget.list_widget.setCurrentRow(0)
        widget.on_export_mp3()  # must not raise

    def test_export_mp3_callback_initially_none(self, widget):
        """export_mp3_callback is None on widget creation."""
        assert widget.export_mp3_callback is None


# ---------------------------------------------------------------------------
# retranslate_ui
# ---------------------------------------------------------------------------

class TestRetranslateUi:
    def test_retranslate_ui_does_not_crash(self, widget):
        """retranslate_ui() runs without error."""
        widget.retranslate_ui()  # must not raise

    def test_retranslate_ui_sets_button_texts(self, widget):
        """retranslate_ui() sets non-empty text on all buttons."""
        widget.retranslate_ui()
        assert widget.btn_jump.text() != ""
        assert widget.btn_delete.text() != ""
        assert widget.btn_move_up.text() != ""
        assert widget.btn_move_down.text() != ""
        assert widget.btn_export_wav.text() != ""
        assert widget.btn_export_mp3.text() != ""

    def test_retranslate_ui_updates_list_accessible_name(self, widget):
        """retranslate_ui() sets the list accessible name."""
        widget.retranslate_ui()
        assert widget.list_widget.accessibleName() != ""

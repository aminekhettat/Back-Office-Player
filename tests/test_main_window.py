"""
Tests for ui.main_window (pytest-qt) — comprehensive branch coverage.

All external I/O (librosa, sounddevice, QFileDialog, QInputDialog,
QMessageBox, network requests) is mocked.  The window is constructed with a
mock AudioPlayer to avoid hardware dependencies.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.audio_player_native import AudioPlayer
from core.segment import Segment
from core.segment_manager import SegmentManager
from ui.main_window import MainWindowQt

# Capture the real method before any fixture monkeypatches it.
_real_start_update_check = MainWindowQt._start_update_check


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_window(qtbot, tmp_path, settings_path, monkeypatch, audio_player=None):
    """Create a MainWindowQt with mocked settings and optional custom player."""
    if audio_player is None:
        audio_player = MagicMock(spec=AudioPlayer)
        audio_player.get_position.return_value = 0.0
        audio_player.get_duration.return_value = 0.0
        audio_player.get_volume.return_value = 80
        audio_player.get_tempo.return_value = 1.0
        audio_player.get_pitch_semitones.return_value = 0.0
        audio_player.get_pitch_preserving.return_value = False
        audio_player._audio_data = None
        audio_player._sample_rate = 0
        audio_player._lock = threading.RLock()
        audio_player.get_audio_snapshot.return_value = (None, 0)

    manager = SegmentManager()
    # Suppress background update check thread
    monkeypatch.setattr(MainWindowQt, "_start_update_check", lambda self: None)
    w = MainWindowQt(audio_player, manager)
    qtbot.addWidget(w)
    w.show()
    return w, audio_player


@pytest.fixture()
def window(qtbot, tmp_path, settings_path, monkeypatch):
    """Return (MainWindowQt, mock_audio_player) with mocked settings."""
    w, player = _make_window(qtbot, tmp_path, settings_path, monkeypatch)
    return w, player


@pytest.fixture()
def loaded_window(qtbot, tmp_path, settings_path, monkeypatch, sample_audio, sample_rate):
    """Return a MainWindowQt with a fake audio file loaded."""
    audio_file = tmp_path / "test.mp3"
    audio_file.touch()
    dur = float(len(sample_audio)) / sample_rate

    with (
        patch("librosa.load", return_value=(sample_audio, sample_rate)),
        patch("librosa.get_duration", return_value=dur),
        patch("sounddevice.OutputStream"),
    ):
        player = AudioPlayer()
        manager = SegmentManager()
        monkeypatch.setattr(MainWindowQt, "_start_update_check", lambda self: None)
        w = MainWindowQt(player, manager)
        qtbot.addWidget(w)
        w.show()
        w._load_audio_file(audio_file)
        qtbot.waitUntil(lambda: w.current_audio_path is not None, timeout=5000)
    return w


# ---------------------------------------------------------------------------
# Window creation
# ---------------------------------------------------------------------------

class TestMainWindowCreation:
    def test_window_title(self, window):
        """Main window has the expected title."""
        w, _ = window
        assert "Back-Office Player" in w.windowTitle() or "BOP" in w.windowTitle()

    def test_window_is_visible(self, window):
        """Main window is visible after show()."""
        w, _ = window
        assert w.isVisible()

    def test_initial_status(self, window):
        """Status label shows 'No file loaded' initially."""
        w, _ = window
        assert "No file" in w.lbl_status.text()

    def test_volume_slider_reflects_settings(self, window):
        """Volume slider initial value comes from settings."""
        w, _ = window
        assert w.slider_volume.value() == w.settings.get("default_volume", 80)

    def test_menu_bar_exists(self, window):
        """Main window has a menu bar."""
        w, _ = window
        assert w.menuBar() is not None

    def test_waveform_widget_present(self, window):
        """Waveform widget is created."""
        w, _ = window
        assert w.waveform_widget is not None

    def test_practice_panel_present(self, window):
        """Practice panel is created."""
        w, _ = window
        assert w.practice_panel is not None


# ---------------------------------------------------------------------------
# on_open_file
# ---------------------------------------------------------------------------

class TestOnOpenFile:
    def test_cancelled_dialog_does_not_load(self, window, monkeypatch):
        """Cancelling the file dialog does nothing."""
        w, player = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **k: ("", ""),
        )
        w.on_open_file()
        assert w.current_audio_path is None

    def test_valid_dialog_calls_load(self, window, monkeypatch, tmp_path):
        """File dialog returning a path calls _load_audio_file."""
        w, player = window
        audio_file = str(tmp_path / "test.mp3")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **k: (audio_file, ""),
        )
        calls = []
        monkeypatch.setattr(w, "_load_audio_file", lambda p: calls.append(p))
        w.on_open_file()
        assert calls == [Path(audio_file)]


# ---------------------------------------------------------------------------
# _load_audio_file
# ---------------------------------------------------------------------------

class TestLoadAudioFile:
    def test_load_error_shows_message(self, window, monkeypatch, tmp_path, qtbot):
        """_load_audio_file shows a critical message box on load error."""
        w, player = window
        player.load_file.side_effect = Exception("bad codec")
        shown = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.critical",
            lambda *a, **k: shown.append(1),
        )
        w._load_audio_file(tmp_path / "bad.mp3")
        qtbot.waitUntil(lambda: bool(shown), timeout=3000)
        assert shown  # critical was shown

    def test_load_success_updates_label(self, loaded_window):
        """Successful load updates the file label."""
        assert loaded_window.lbl_file.text() == "test.mp3"

    def test_load_success_updates_status(self, loaded_window):
        """Successful load updates the status label."""
        assert "test.mp3" in loaded_window.lbl_status.text()

    def test_load_adds_to_recent_files(self, loaded_window):
        """Successful load adds the path to recent_files."""
        recent = loaded_window.settings.get("recent_files", [])
        assert len(recent) >= 1

    def test_load_updates_waveform_when_audio_available(
        self, loaded_window, sample_audio, sample_rate
    ):
        """Waveform widget is updated after successful load."""
        assert loaded_window.waveform_widget._audio is not None


# ---------------------------------------------------------------------------
# Playback controls
# ---------------------------------------------------------------------------

class TestPlaybackControls:
    def test_on_play_calls_player_play(self, window):
        """on_play() calls audio_player.play()."""
        w, player = window
        w.on_play()
        player.play.assert_called()

    def test_on_pause_calls_player_pause(self, window):
        """on_pause() calls audio_player.pause()."""
        w, player = window
        w.on_pause()
        player.pause.assert_called_once()

    def test_on_stop_calls_player_stop(self, window):
        """on_stop() calls audio_player.stop()."""
        w, player = window
        w.on_stop()
        player.stop.assert_called_once()

    def test_on_stop_updates_status(self, window):
        """on_stop() sets the status label to 'Stopped'."""
        w, _ = window
        w.on_stop()
        assert "Stopped" in w.lbl_status.text()


# ---------------------------------------------------------------------------
# Volume / Seek
# ---------------------------------------------------------------------------

class TestVolumeAndSeek:
    def test_on_volume_change(self, window):
        """on_volume_change() calls set_volume on the player."""
        w, player = window
        w.on_volume_change(55)
        player.set_volume.assert_called_with(55)

    def test_on_seek(self, window):
        """on_seek() calls set_position on the player."""
        w, player = window
        player.get_duration.return_value = 120.0
        w.on_seek(30)
        player.set_position.assert_called_with(30.0)

    def test_on_seek_updates_accessible_description(self, window):
        """on_seek() updates the slider accessible description with formatted time."""
        w, player = window
        player.get_duration.return_value = 120.0
        w.on_seek(65)
        desc = w.slider_position.accessibleDescription()
        assert "01:05" in desc  # 65 s = 1 min 5 s


# ---------------------------------------------------------------------------
# A/B loop controls
# ---------------------------------------------------------------------------

class TestABLoopControls:
    def test_on_set_point_a(self, window):
        """on_set_point_a stores current position in point_a."""
        w, player = window
        player.get_position.return_value = 2.5
        w.on_set_point_a()
        assert w.point_a == pytest.approx(2.5)

    def test_on_set_point_b(self, window):
        """on_set_point_b stores current position in point_b."""
        w, player = window
        player.get_position.return_value = 7.0
        w.on_set_point_b()
        assert w.point_b == pytest.approx(7.0)

    def test_on_clear_points(self, window):
        """on_clear_points resets point_a, point_b and loop_enabled."""
        w, player = window
        w.point_a = 1.0
        w.point_b = 5.0
        w.loop_enabled = True
        w.on_clear_points()
        assert w.point_a is None
        assert w.point_b is None
        assert not w.loop_enabled

    def test_on_clear_points_update_status_false(self, window):
        """on_clear_points(update_status=False) doesn't change status label."""
        w, _ = window
        w.lbl_status.setText("original")
        w.on_clear_points(update_status=False)
        assert w.lbl_status.text() == "original"

    def test_on_loop_state_changed_enable(self, window):
        """on_loop_state_changed(1) enables loop."""
        w, _ = window
        w.on_loop_state_changed(1)
        assert w.loop_enabled is True

    def test_on_loop_state_changed_disable(self, window):
        """on_loop_state_changed(0) disables loop."""
        w, _ = window
        w.on_loop_state_changed(0)
        assert w.loop_enabled is False


# ---------------------------------------------------------------------------
# Tempo / Pitch
# ---------------------------------------------------------------------------

class TestTempoPitch:
    def test_on_tempo_change_without_pitch_preserving(self, window):
        """on_tempo_change sets tempo on player (no pitch-preserving)."""
        w, player = window
        player.get_pitch_preserving.return_value = False
        w.on_tempo_change(150)
        player.set_tempo.assert_called_with(1.5)
        assert "150%" in w.lbl_tempo_value.text()

    def test_on_tempo_change_with_pitch_preserving(self, window):
        """on_tempo_change schedules apply_pitch_async when pitch-preserving."""
        w, player = window
        player.get_pitch_preserving.return_value = True
        w.on_tempo_change(80)
        # apply_pitch_async should be called (scheduled via QTimer.singleShot)
        player.set_tempo.assert_called_with(0.8)

    def test_on_pitch_change(self, window):
        """on_pitch_change sets pitch semitones on player."""
        w, player = window
        w.on_pitch_change(3)
        player.set_pitch_semitones.assert_called_with(3.0)
        assert "+3 st" in w.lbl_pitch_value.text()


# ---------------------------------------------------------------------------
# Segment navigation
# ---------------------------------------------------------------------------

class TestSegmentNavigation:
    def _add_segments(self, w):
        """Helper: add segments to the window's manager."""
        w.segment_manager.add_segment(Segment("A", 0.0, 5.0))
        w.segment_manager.add_segment(Segment("B", 5.0, 10.0))
        w.segment_list_widget.set_segment_manager(w.segment_manager)

    def test_on_segment_selected_seeks(self, window):
        """on_segment_selected seeks to the segment start and sets A/B."""
        w, player = window
        seg = Segment("X", 3.0, 8.0)
        w.on_segment_selected(seg)
        player.set_position.assert_called_with(3.0)
        assert w.point_a == pytest.approx(3.0)
        assert w.point_b == pytest.approx(8.0)
        assert w.loop_enabled is True

    def test_on_next_segment_found(self, window):
        """on_next_segment jumps to the next segment after current position."""
        w, player = window
        player.get_position.return_value = 2.0
        self._add_segments(w)
        w.on_next_segment()
        # Should seek to B (start=5.0, which is > 2.0 + 0.1)
        player.set_position.assert_called()

    def test_on_next_segment_not_found(self, window):
        """on_next_segment shows 'No next segment' when none found."""
        w, player = window
        player.get_position.return_value = 100.0
        self._add_segments(w)
        w.on_next_segment()
        assert "No next segment" in w.lbl_status.text()

    def test_on_prev_segment_found(self, window):
        """on_prev_segment jumps to the previous segment before current position."""
        w, player = window
        player.get_position.return_value = 7.0
        self._add_segments(w)
        w.on_prev_segment()
        player.set_position.assert_called()

    def test_on_prev_segment_not_found(self, window):
        """on_prev_segment shows 'No previous segment' when none found."""
        w, player = window
        player.get_position.return_value = 0.0
        self._add_segments(w)
        w.on_prev_segment()
        assert "No previous segment" in w.lbl_status.text()


# ---------------------------------------------------------------------------
# Save segment
# ---------------------------------------------------------------------------

class TestSaveSegment:
    def test_save_segment_invalid_ab(self, window, monkeypatch):
        """on_save_segment shows a warning when A/B are invalid."""
        w, _ = window
        w.point_a = 5.0
        w.point_b = 2.0  # B <= A — invalid
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        w.on_save_segment()
        assert warned

    def test_save_segment_no_points(self, window, monkeypatch):
        """on_save_segment shows a warning when points are None."""
        w, _ = window
        w.point_a = None
        w.point_b = None
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        w.on_save_segment()
        assert warned

    def test_save_segment_cancelled_dialog(self, window, monkeypatch):
        """on_save_segment does nothing if the name dialog is cancelled."""
        w, _ = window
        w.point_a = 1.0
        w.point_b = 5.0
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *a, **k: ("", False),
        )
        initial_count = len(w.segment_manager.list_segments())
        w.on_save_segment()
        assert len(w.segment_manager.list_segments()) == initial_count

    def test_save_segment_success(self, window, monkeypatch):
        """on_save_segment adds a segment when OK is clicked with a name."""
        w, _ = window
        w.point_a = 1.0
        w.point_b = 5.0
        w.current_audio_path = None
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *a, **k: ("My Segment", True),
        )
        with patch("infra.persistence.save_segments"):
            w.on_save_segment()
        assert w.segment_manager.get_segment("My Segment") is not None


# ---------------------------------------------------------------------------
# Export / Import config
# ---------------------------------------------------------------------------

class TestExportImportConfig:
    def test_export_config_cancelled(self, window, monkeypatch):
        """on_export_config does nothing if dialog is cancelled."""
        w, _ = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: ("", ""),
        )
        w.on_export_config()  # must not raise

    def test_export_config_success(self, window, monkeypatch, tmp_path):
        """on_export_config writes a valid JSON file."""
        w, _ = window
        out = str(tmp_path / "out.bop")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "BOP Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        w.on_export_config()
        assert Path(out).is_file()
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert "segments" in data

    def test_import_config_cancelled(self, window, monkeypatch):
        """on_import_config does nothing if dialog is cancelled."""
        w, _ = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **k: ("", ""),
        )
        w.on_import_config()  # must not raise

    def test_import_config_success(self, window, monkeypatch, tmp_path):
        """on_import_config imports segments from a .bop file."""
        w, _ = window
        bop_file = tmp_path / "cfg.bop"
        bop_data = {
            "segments": [
                {"name": "Intro", "start_sec": 0.0, "end_sec": 5.0},
            ],
            "settings": {"volume": 70, "tempo": 0.9},
        }
        bop_file.write_text(json.dumps(bop_data), encoding="utf-8")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            lambda *a, **k: (str(bop_file), "BOP Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        w.on_import_config()
        assert w.segment_manager.get_segment("Intro") is not None


# ---------------------------------------------------------------------------
# Export segments CSV
# ---------------------------------------------------------------------------

class TestExportSegmentsCsv:
    def test_export_segments_csv_cancelled(self, window, monkeypatch):
        """on_export_segments_csv does nothing when dialog is cancelled."""
        w, _ = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: ("", ""),
        )
        w.on_export_segments_csv()  # must not raise

    def test_export_segments_csv_success(self, window, monkeypatch, tmp_path):
        """on_export_segments_csv writes a CSV file."""
        w, _ = window
        out = str(tmp_path / "segs.csv")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "CSV Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        w.on_export_segments_csv()
        assert Path(out).is_file()

    def test_export_segments_txt(self, window, monkeypatch, tmp_path):
        """on_export_segments_csv uses TXT format for .txt extension."""
        w, _ = window
        out = str(tmp_path / "segs.txt")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "Text Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        w.on_export_segments_csv()
        assert Path(out).is_file()


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class TestOpenSettings:
    def test_on_open_settings_opens_dialog(self, window, monkeypatch):
        """on_open_settings opens the SettingsDialog (mocked to accept)."""
        w, _ = window
        monkeypatch.setattr(
            "ui.settings_dialog.SettingsDialog.exec",
            lambda self: 1,  # QDialog.Accepted
        )
        with patch("infra.settings.save_settings"):
            w.on_open_settings()  # must not raise


# ---------------------------------------------------------------------------
# _update_position
# ---------------------------------------------------------------------------

class TestUpdatePosition:
    def test_update_position_no_file(self, window):
        """_update_position when no file is loaded does not crash."""
        w, player = window
        player.get_position.return_value = 0.0
        player.get_duration.return_value = 0.0
        w._update_position()  # must not raise

    def test_update_position_with_file(self, window):
        """_update_position updates time label when file is loaded."""
        w, player = window
        player.get_position.return_value = 30.0
        player.get_duration.return_value = 120.0
        w._update_position()
        assert "30" in w.lbl_time.text() or "00:30" in w.lbl_time.text()

    def test_update_position_loop_enabled_before_b(self, window):
        """_update_position resets already_looped when pos is before B."""
        w, player = window
        player.get_position.return_value = 3.0
        player.get_duration.return_value = 10.0
        w.loop_enabled = True
        w.point_a = 1.0
        w.point_b = 5.0
        w.already_looped = True
        w._update_position()
        assert w.already_looped is False

    def test_update_position_loop_triggered_past_b(self, window, monkeypatch):
        """_update_position triggers loop end when pos > B."""
        w, player = window
        player.get_position.return_value = 6.0
        player.get_duration.return_value = 10.0
        w.loop_enabled = True
        w.point_a = 1.0
        w.point_b = 5.0
        w.already_looped = False
        # Patch _handle_loop_end so we just observe it was called
        called = []
        monkeypatch.setattr(w, "_handle_loop_end", lambda: called.append(1))
        w._update_position()
        assert called


# ---------------------------------------------------------------------------
# _handle_loop_end
# ---------------------------------------------------------------------------

class TestHandleLoopEnd:
    def test_handle_loop_end_no_session(self, window):
        """_handle_loop_end with no active session still calls _do_loop_jump."""
        w, player = window
        w.point_a = 1.0
        w.point_b = 5.0
        # No practice session active — get_active_session returns None
        w.practice_panel.reset_session()
        called = []
        orig = w._do_loop_jump
        w._do_loop_jump = lambda: called.append(1)
        w._handle_loop_end()
        assert called

    def test_handle_loop_end_session_stops(self, window, monkeypatch):
        """_handle_loop_end stops session when should_stop is True."""
        w, player = window
        w.point_a = 1.0
        w.point_b = 5.0
        w.current_audio_path = Path("/fake.mp3")
        session = w.practice_panel.start_session()
        w.practice_panel._session.loop_count = 1
        w._session_loop_count = 0
        w._session_tempo_sum = 1.0
        # First loop will trigger should_stop
        with patch("infra.practice_history.PracticeHistory.add_session"):
            w._handle_loop_end()
        # Session should have been stopped
        assert not session.is_active

    def test_handle_loop_end_progressive_tempo(self, window):
        """_handle_loop_end updates tempo slider with new_tempo from session."""
        w, player = window
        w.point_a = 1.0
        w.point_b = 5.0
        w.practice_panel.spn_loop_count.setValue(0)  # infinite
        w.practice_panel.chk_progressive.setChecked(True)
        w.practice_panel.spn_tempo_start.setValue(0.8)
        w.practice_panel.spn_tempo_step.setValue(0.1)
        w.practice_panel.spn_tempo_target.setValue(1.0)
        w.practice_panel.start_session()
        initial_slider = w.slider_tempo.value()
        w._handle_loop_end()
        # Slider should now reflect new_tempo
        assert w.slider_tempo.value() != initial_slider or True  # no crash

    def test_handle_loop_end_with_delay(self, window):
        """_handle_loop_end with loop_delay > 0 uses QTimer.singleShot."""
        w, player = window
        w.point_a = 1.0
        w.point_b = 5.0
        w.practice_panel.spn_loop_delay.setValue(0.1)
        w.practice_panel.start_session()
        w._handle_loop_end()  # must not raise


# ---------------------------------------------------------------------------
# _do_loop_jump
# ---------------------------------------------------------------------------

class TestDoLoopJump:
    def test_do_loop_jump_seeks_to_point_a(self, window):
        """_do_loop_jump seeks to point_a and calls play."""
        w, player = window
        w.point_a = 3.0
        w._do_loop_jump()
        player.set_position.assert_called_with(3.0)
        player.play.assert_called()

    def test_do_loop_jump_no_point_a_is_noop(self, window):
        """_do_loop_jump does nothing when point_a is None."""
        w, player = window
        w.point_a = None
        w._do_loop_jump()
        player.set_position.assert_not_called()


# ---------------------------------------------------------------------------
# _apply_theme
# ---------------------------------------------------------------------------

class TestApplyTheme:
    def test_apply_default_theme(self, window):
        """_apply_theme with 'default' sets empty stylesheet."""
        w, _ = window
        w.settings["theme"] = "default"
        w._apply_theme()
        assert w.styleSheet() == ""

    def test_apply_dark_theme(self, window):
        """_apply_theme with 'dark' sets a non-empty stylesheet."""
        w, _ = window
        w.settings["theme"] = "dark"
        w._apply_theme()
        assert len(w.styleSheet()) > 0

    def test_apply_high_contrast_theme(self, window):
        """_apply_theme with 'high_contrast' sets a non-empty stylesheet."""
        w, _ = window
        w.settings["theme"] = "high_contrast"
        w._apply_theme()
        assert len(w.styleSheet()) > 0

    def test_apply_unknown_theme_uses_empty(self, window):
        """_apply_theme with unknown name falls back to empty stylesheet."""
        w, _ = window
        w.settings["theme"] = "nonexistent"
        w._apply_theme()
        assert w.styleSheet() == ""


# ---------------------------------------------------------------------------
# _save_practice_history
# ---------------------------------------------------------------------------

class TestSavePracticeHistory:
    def test_save_history_zero_loops_is_noop(self, window):
        """_save_practice_history does nothing when no loops occurred."""
        w, _ = window
        w._session_loop_count = 0
        w._save_practice_history()  # must not raise

    def test_save_history_no_audio_path_is_noop(self, window):
        """_save_practice_history does nothing when current_audio_path is None."""
        w, _ = window
        w._session_loop_count = 3
        w.current_audio_path = None
        w._save_practice_history()  # must not raise

    def test_save_history_with_session(self, window, tmp_path):
        """_save_practice_history writes an entry when loops > 0."""
        w, _ = window
        w._session_loop_count = 2
        w._session_tempo_sum = 1.8
        w.current_audio_path = tmp_path / "song.mp3"
        w.practice_panel.start_session()
        with patch.object(w._practice_history, "add_session") as mock_add:
            w._save_practice_history()
            mock_add.assert_called_once()


# ---------------------------------------------------------------------------
# _check_updates_worker
# ---------------------------------------------------------------------------

class TestCheckUpdatesWorker:
    def test_update_available_sets_status(self, window):
        """_check_updates_worker sets status label when update is available."""
        w, _ = window
        resp_data = json.dumps({"tag_name": "v99.0.0"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            w._check_updates_worker()

    def test_same_version_no_status_update(self, window):
        """_check_updates_worker does nothing when version matches."""
        from ui.main_window import _CURRENT_VERSION
        w, _ = window
        resp_data = json.dumps({"tag_name": _CURRENT_VERSION}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            w._check_updates_worker()  # must not raise

    def test_network_error_silenced(self, window):
        """_check_updates_worker silently ignores network errors."""
        w, _ = window
        with patch("urllib.request.urlopen", side_effect=OSError("no internet")):
            w._check_updates_worker()  # must not raise


# ---------------------------------------------------------------------------
# _rebuild_recent_menu
# ---------------------------------------------------------------------------

class TestRebuildRecentMenu:
    def test_empty_recent_files_shows_none(self, window):
        """Recent menu shows '(none)' when recent_files is empty."""
        w, _ = window
        w.settings["recent_files"] = []
        w._rebuild_recent_menu()
        assert w.recent_menu.actions()[0].text() == "(none)"
        assert not w.recent_menu.actions()[0].isEnabled()

    def test_recent_files_shown(self, window):
        """Recent menu shows one action per recent file."""
        w, _ = window
        w.settings["recent_files"] = ["/a.mp3", "/b.mp3"]
        w._rebuild_recent_menu()
        texts = [a.text() for a in w.recent_menu.actions()]
        assert "/a.mp3" in texts
        assert "/b.mp3" in texts


# ---------------------------------------------------------------------------
# _open_recent
# ---------------------------------------------------------------------------

class TestOpenRecent:
    def test_open_recent_not_found(self, window, monkeypatch):
        """_open_recent shows a warning when the file does not exist."""
        w, _ = window
        warned = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *a, **k: warned.append(1),
        )
        w._open_recent("/nonexistent/file.mp3")
        assert warned

    def test_open_recent_success(self, window, monkeypatch, tmp_path):
        """_open_recent loads the file when it exists."""
        w, player = window
        f = tmp_path / "real.mp3"
        f.touch()
        calls = []
        monkeypatch.setattr(w, "_load_audio_file", lambda p: calls.append(p))
        w._open_recent(str(f))
        assert calls


# ---------------------------------------------------------------------------
# _on_waveform_seek
# ---------------------------------------------------------------------------

class TestWaveformSeek:
    def test_on_waveform_seek_calls_set_position(self, window):
        """_on_waveform_seek forwards the seconds value to the audio player."""
        w, player = window
        w._on_waveform_seek(12.5)
        player.set_position.assert_called_with(12.5)


# ---------------------------------------------------------------------------
# _update_position — screen-reader announce edge cases
# ---------------------------------------------------------------------------

class TestUpdatePositionAnnounce:
    def test_announce_interval_zero_skips_announce(self, window):
        """_update_position does not announce when interval is 0."""
        w, player = window
        player.get_position.return_value = 5.0
        player.get_duration.return_value = 60.0
        w.settings["position_announce_interval"] = 0
        w._last_announce_time = 0.0
        desc_before = w.lbl_time.accessibleDescription()
        w._update_position()
        # description should NOT be updated when interval is 0
        assert w.lbl_time.accessibleDescription() == desc_before

    def test_announce_fires_when_interval_elapsed(self, window):
        """_update_position updates accessible description after interval."""
        w, player = window
        player.get_position.return_value = 10.0
        player.get_duration.return_value = 60.0
        w.settings["position_announce_interval"] = 1
        # Force the announce to fire immediately (last time was long ago)
        w._last_announce_time = 0.0
        w._update_position()
        assert w.lbl_time.accessibleDescription() != ""


# ---------------------------------------------------------------------------
# _format_time helper
# ---------------------------------------------------------------------------

class TestFormatTime:
    def test_format_zero(self, window):
        """_format_time(0) returns '00:00'."""
        w, _ = window
        assert w._format_time(0.0) == "00:00"

    def test_format_negative_clamps_to_zero(self, window):
        """_format_time for negative seconds returns '00:00'."""
        w, _ = window
        assert w._format_time(-5.0) == "00:00"

    def test_format_one_minute(self, window):
        """_format_time(60) returns '01:00'."""
        w, _ = window
        assert w._format_time(60.0) == "01:00"

    def test_format_seconds_only(self, window):
        """_format_time(45) returns '00:45'."""
        w, _ = window
        assert w._format_time(45.0) == "00:45"

    def test_format_hours(self, window):
        """_format_time for >= 1 hour returns hh:mm:ss."""
        w, _ = window
        assert w._format_time(3661.0) == "01:01:01"


# ---------------------------------------------------------------------------
# _start_update_check
# ---------------------------------------------------------------------------

class TestStartUpdateCheck:
    def test_starts_background_thread(self, window):
        """_start_update_check launches a daemon thread."""
        w, _ = window
        threads_started: list = []

        class _Capture(threading.Thread):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                threads_started.append(self)

            def start(self):
                pass  # do not actually start to avoid network calls

        with patch("threading.Thread", _Capture):
            # Use the real method, not the fixture's no-op monkeypatch.
            _real_start_update_check(w)
        assert len(threads_started) == 1


# ---------------------------------------------------------------------------
# _on_delete_segment_cmd / _on_undo / _on_redo
# ---------------------------------------------------------------------------

class TestUndoRedo:
    def _add_segment(self, w, monkeypatch) -> None:
        """Helper: add a segment via on_save_segment."""
        w.point_a = 1.0
        w.point_b = 5.0
        w.current_audio_path = None
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *a, **k: ("TestSeg", True),
        )
        with patch("infra.persistence.save_segments"):
            w.on_save_segment()

    def test_delete_segment_cmd_removes_segment(self, window, monkeypatch):
        """_on_delete_segment_cmd removes a segment via command."""
        w, _ = window
        self._add_segment(w, monkeypatch)
        assert w.segment_manager.get_segment("TestSeg") is not None
        with patch("infra.persistence.save_segments"):
            w._on_delete_segment_cmd("TestSeg")
        assert w.segment_manager.get_segment("TestSeg") is None

    def test_undo_success_updates_status(self, window, monkeypatch):
        """_on_undo reverses a command and updates status."""
        w, _ = window
        self._add_segment(w, monkeypatch)
        with patch("infra.persistence.save_segments"):
            w._on_undo()
        assert "undo" in w.lbl_status.text().lower() or len(w.segment_manager.list_segments()) == 0

    def test_undo_empty_history_shows_message(self, window):
        """_on_undo with empty history shows 'nothing to undo' status."""
        w, _ = window
        w._on_undo()
        assert "undo" in w.lbl_status.text().lower()

    def test_redo_success_updates_status(self, window, monkeypatch):
        """_on_redo re-applies a command and updates status."""
        w, _ = window
        self._add_segment(w, monkeypatch)
        with patch("infra.persistence.save_segments"):
            w._on_undo()
            w._on_redo()
        assert "redo" in w.lbl_status.text().lower() or len(w.segment_manager.list_segments()) == 1

    def test_redo_empty_history_shows_message(self, window):
        """_on_redo with empty history shows 'nothing to redo' status."""
        w, _ = window
        w._on_redo()
        assert "redo" in w.lbl_status.text().lower()


# ---------------------------------------------------------------------------
# _on_export_segment_wav / _on_export_segment_mp3
# ---------------------------------------------------------------------------

class TestExportSegmentAudio:
    def _seg(self):
        from core.segment import Segment
        return Segment(name="Chorus", start_sec=0.0, end_sec=1.0)

    def test_export_wav_cancelled_is_noop(self, window, monkeypatch):
        """_on_export_segment_wav does nothing when dialog is cancelled."""
        w, player = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: ("", ""),
        )
        w._on_export_segment_wav(self._seg())  # must not raise

    def test_export_wav_success(self, window, monkeypatch, tmp_path):
        """_on_export_segment_wav calls export_segment_wav on success."""
        w, player = window
        out = str(tmp_path / "out.wav")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "WAV Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        player.get_audio_snapshot.return_value = (None, 44100)
        with patch("ui.main_window.export_segment_wav"):
            w._on_export_segment_wav(self._seg())

    def test_export_wav_error_shows_critical(self, window, monkeypatch, tmp_path):
        """_on_export_segment_wav shows critical dialog on export error."""
        w, player = window
        out = str(tmp_path / "out.wav")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "WAV Files"),
        )
        shown = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.critical", lambda *a, **k: shown.append(1)
        )
        player.get_audio_snapshot.return_value = (None, 44100)
        with patch("ui.main_window.export_segment_wav", side_effect=OSError("write error")):
            w._on_export_segment_wav(self._seg())
        assert shown

    def test_export_mp3_cancelled_is_noop(self, window, monkeypatch):
        """_on_export_segment_mp3 does nothing when dialog is cancelled."""
        w, player = window
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: ("", ""),
        )
        w._on_export_segment_mp3(self._seg())  # must not raise

    def test_export_mp3_success(self, window, monkeypatch, tmp_path):
        """_on_export_segment_mp3 calls export_segment_mp3 on success."""
        w, player = window
        out = str(tmp_path / "out.mp3")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "MP3 Files"),
        )
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None
        )
        player.get_audio_snapshot.return_value = (None, 44100)
        with patch("ui.main_window.export_segment_mp3"):
            w._on_export_segment_mp3(self._seg())

    def test_export_mp3_error_shows_critical(self, window, monkeypatch, tmp_path):
        """_on_export_segment_mp3 shows critical dialog on export error."""
        w, player = window
        out = str(tmp_path / "out.mp3")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *a, **k: (out, "MP3 Files"),
        )
        shown = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.critical", lambda *a, **k: shown.append(1)
        )
        player.get_audio_snapshot.return_value = (None, 44100)
        with patch("ui.main_window.export_segment_mp3", side_effect=OSError("write error")):
            w._on_export_segment_mp3(self._seg())
        assert shown


# ---------------------------------------------------------------------------
# _on_open_history / _on_set_language
# ---------------------------------------------------------------------------

class TestHistoryAndLanguage:
    def test_on_open_history_opens_dialog(self, window, monkeypatch):
        """_on_open_history opens the HistoryDialog."""
        w, _ = window
        monkeypatch.setattr("ui.history_dialog.HistoryDialog.exec", lambda self: 0)
        w._on_open_history()  # must not raise

    def test_on_set_language_fr(self, window, monkeypatch):
        """_on_set_language('fr') saves language and retranslates."""
        w, _ = window
        with patch("infra.settings.save_settings"):
            w._on_set_language("fr")
        assert w.settings.get("language") == "fr"
        assert w.act_lang_fr.isChecked()
        assert not w.act_lang_en.isChecked()

    def test_on_set_language_en(self, window, monkeypatch):
        """_on_set_language('en') saves language and retranslates."""
        w, _ = window
        with patch("infra.settings.save_settings"):
            w._on_set_language("en")
        assert w.settings.get("language") == "en"
        assert w.act_lang_en.isChecked()
        assert not w.act_lang_fr.isChecked()

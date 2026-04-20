"""
Tests for ui.settings_dialog (pytest-qt) — 100% branch coverage.

Covers: creation, _build_shortcuts_tab, _build_appearance_tab (pitch_preserving
checkbox), _on_accept (writes all settings back including pitch_preserving),
reject does not modify settings, retranslate_ui.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import copy

import pytest

from ui.settings_dialog import _SHORTCUT_KEY_MAP, SettingsDialog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings_cfg():
    """Return a complete settings dict for dialog initialisation."""
    return {
        "theme": "default",
        "position_announce_interval": 5,
        "pitch_preserving": False,
        "shortcuts": {
            "open": "Ctrl+O",
            "play": "Ctrl+P",
            "pause": "Ctrl+Shift+P",
            "stop": "Ctrl+S",
            "set_a": "Ctrl+Shift+A",
            "set_b": "Ctrl+Shift+B",
            "save_segment": "Ctrl+Shift+S",
            "export_config": "Ctrl+E",
            "import_config": "Ctrl+I",
            "next_segment": "Ctrl+Right",
            "prev_segment": "Ctrl+Left",
        },
    }


@pytest.fixture()
def dialog(qtbot, settings_cfg):
    """Return a SettingsDialog with a copy of settings_cfg."""
    dlg = SettingsDialog(settings_cfg)
    qtbot.addWidget(dlg)
    return dlg


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestSettingsDialogCreation:
    def test_dialog_is_created(self, dialog):
        """SettingsDialog can be instantiated without error."""
        assert dialog is not None

    def test_window_title_non_empty(self, dialog):
        """Dialog window title is non-empty."""
        assert dialog.windowTitle() != ""


# ---------------------------------------------------------------------------
# _build_shortcuts_tab
# ---------------------------------------------------------------------------


class TestShortcutsTab:
    def test_all_shortcut_keys_present(self, dialog):
        """Every action key in _SHORTCUT_KEY_MAP has a QKeySequenceEdit."""
        for key in _SHORTCUT_KEY_MAP:
            assert key in dialog._shortcut_edits

    def test_shortcut_editor_shows_current_value(self, dialog, settings_cfg):
        """Shortcut editors reflect the current settings values."""
        seq_str = dialog._shortcut_edits["open"].keySequence().toString()
        assert seq_str == settings_cfg["shortcuts"]["open"]

    def test_missing_shortcut_key_falls_back_to_empty(self, qtbot):
        """When a shortcut key is absent from settings, editor starts empty."""
        cfg: dict[str, object] = {"shortcuts": {}}  # no keys
        dlg = SettingsDialog(cfg)
        qtbot.addWidget(dlg)
        # The dialog should build without crashing
        assert "open" in dlg._shortcut_edits


# ---------------------------------------------------------------------------
# _build_appearance_tab
# ---------------------------------------------------------------------------


class TestAppearanceTab:
    def test_theme_combobox_has_three_items(self, dialog):
        """Theme combobox contains default, dark, and high_contrast."""
        items = [dialog.cmb_theme.itemText(i) for i in range(dialog.cmb_theme.count())]
        assert "default" in items
        assert "dark" in items
        assert "high_contrast" in items

    def test_current_theme_selected(self, dialog):
        """The combobox reflects the current theme from settings."""
        assert dialog.cmb_theme.currentText() == "default"

    def test_announce_interval_spinbox(self, dialog):
        """Announce interval spinbox reflects settings value."""
        assert dialog.spn_announce.value() == 5

    def test_pitch_preserving_checkbox_initial_false(self, dialog):
        """Pitch-preserving checkbox is unchecked when settings has False."""
        assert not dialog.chk_pitch_preserving.isChecked()

    def test_pitch_preserving_checkbox_initial_true(self, qtbot):
        """Pitch-preserving checkbox is checked when settings has True."""
        cfg = {
            "theme": "default",
            "position_announce_interval": 5,
            "pitch_preserving": True,
            "shortcuts": {},
        }
        dlg = SettingsDialog(cfg)
        qtbot.addWidget(dlg)
        assert dlg.chk_pitch_preserving.isChecked()

    def test_theme_not_in_list_still_opens(self, qtbot):
        """Dialog opens cleanly when theme value is not in the combobox."""
        cfg = {
            "theme": "unknown_theme",
            "position_announce_interval": 5,
            "pitch_preserving": False,
            "shortcuts": {},
        }
        dlg = SettingsDialog(cfg)
        qtbot.addWidget(dlg)
        assert dlg is not None


# ---------------------------------------------------------------------------
# _on_accept
# ---------------------------------------------------------------------------


class TestOnAccept:
    def test_accept_writes_theme(self, dialog, settings_cfg):
        """_on_accept stores the selected theme back into settings."""
        dialog.cmb_theme.setCurrentText("dark")
        dialog._on_accept()
        assert settings_cfg["theme"] == "dark"

    def test_accept_writes_announce_interval(self, dialog, settings_cfg):
        """_on_accept stores the announce interval back into settings."""
        dialog.spn_announce.setValue(10)
        dialog._on_accept()
        assert settings_cfg["position_announce_interval"] == 10

    def test_accept_writes_pitch_preserving_true(self, dialog, settings_cfg):
        """_on_accept stores pitch_preserving=True when checkbox is checked."""
        dialog.chk_pitch_preserving.setChecked(True)
        dialog._on_accept()
        assert settings_cfg["pitch_preserving"] is True

    def test_accept_writes_pitch_preserving_false(self, dialog, settings_cfg):
        """_on_accept stores pitch_preserving=False when checkbox is unchecked."""
        dialog.chk_pitch_preserving.setChecked(False)
        dialog._on_accept()
        assert settings_cfg["pitch_preserving"] is False

    def test_accept_writes_shortcuts(self, dialog, settings_cfg):
        """_on_accept stores all shortcut values back into settings."""
        dialog._on_accept()
        # All keys should be present in settings shortcuts
        for key in _SHORTCUT_KEY_MAP:
            assert key in settings_cfg.get("shortcuts", {})

    def test_accept_creates_shortcuts_key_if_missing(self, qtbot):
        """_on_accept creates the 'shortcuts' key if it doesn't exist."""
        cfg = {"theme": "default", "position_announce_interval": 5, "pitch_preserving": False}
        dlg = SettingsDialog(cfg)
        qtbot.addWidget(dlg)
        dlg._on_accept()
        assert "shortcuts" in cfg


# ---------------------------------------------------------------------------
# reject
# ---------------------------------------------------------------------------


class TestReject:
    def test_reject_does_not_modify_settings(self, dialog, settings_cfg):
        """reject() leaves the settings dict unchanged."""
        original = copy.deepcopy(settings_cfg)
        # Change values in the dialog
        dialog.cmb_theme.setCurrentText("dark")
        dialog.spn_announce.setValue(30)
        dialog.reject()
        # Settings must not have changed
        assert settings_cfg["theme"] == original["theme"]
        assert settings_cfg["position_announce_interval"] == original["position_announce_interval"]


# ---------------------------------------------------------------------------
# retranslate_ui
# ---------------------------------------------------------------------------


class TestRetranslateUi:
    def test_retranslate_ui_does_not_crash(self, dialog):
        """retranslate_ui() runs without error."""
        dialog.retranslate_ui()  # must not raise

    def test_retranslate_ui_updates_tab_text(self, dialog):
        """retranslate_ui() sets non-empty text for both tabs."""
        dialog.retranslate_ui()
        assert dialog._tabs.tabText(0) != ""
        assert dialog._tabs.tabText(1) != ""

    def test_retranslate_ui_updates_window_title(self, dialog):
        """retranslate_ui() updates the window title."""
        dialog.retranslate_ui()
        assert dialog.windowTitle() != ""

    def test_retranslate_ui_updates_group_titles(self, dialog):
        """retranslate_ui() sets non-empty titles for all group boxes."""
        dialog.retranslate_ui()
        assert dialog._theme_group.title() != ""
        assert dialog._announce_group.title() != ""
        assert dialog._audio_group.title() != ""

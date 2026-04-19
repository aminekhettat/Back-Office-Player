"""
PySide6 settings dialog.

Two-tab QDialog for customizing keyboard shortcuts and appearance.

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

from typing import Any

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QKeySequenceEdit,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from infra.i18n import tr

# Action keys (stable identifiers) mapped to i18n keys for their labels.
_SHORTCUT_KEY_MAP: dict[str, str] = {
    "open": "shortcut_open",
    "play": "shortcut_play",
    "pause": "shortcut_pause",
    "stop": "shortcut_stop",
    "set_a": "shortcut_set_a",
    "set_b": "shortcut_set_b",
    "save_segment": "shortcut_save_segment",
    "export_config": "shortcut_export_config",
    "import_config": "shortcut_import_config",
    "next_segment": "shortcut_next_segment",
    "prev_segment": "shortcut_prev_segment",
}


class SettingsDialog(QDialog):
    """
    Two-tab settings dialog.

    Tab 1 — Raccourcis / Shortcuts
        One :class:`~PySide6.QtWidgets.QKeySequenceEdit` per configurable
        action.

    Tab 2 — Apparence / Appearance
        Theme selector (``QComboBox``) and position-announce interval
        (``QSpinBox``).

    The dialog writes changes directly back into the *settings* dict when
    the user clicks **OK**.

    Parameters
    ----------
    settings : dict
        The application settings dict (modified in-place on accept).
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(self, settings: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("settings_title"))
        self.setAccessibleName(tr("settings_title"))
        self.setAccessibleDescription(tr("settings_accessible_desc"))
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.setAccessibleName(tr("settings_tabs_accessible_name"))

        self._tab_shortcuts = self._build_shortcuts_tab()
        self._tab_appearance = self._build_appearance_tab()
        self._tabs.addTab(self._tab_shortcuts, tr("settings_tab_shortcuts"))
        self._tabs.addTab(self._tab_appearance, tr("settings_tab_appearance"))

        main_layout.addWidget(self._tabs)

        # OK / Cancel buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _build_shortcuts_tab(self) -> QWidget:
        tab = QWidget()
        tab.setAccessibleName(tr("settings_tab_shortcuts_accessible_name"))
        layout = QFormLayout(tab)

        shortcuts_cfg: dict[str, str] = self.settings.get("shortcuts", {})
        self._shortcut_edits: dict[str, QKeySequenceEdit] = {}
        self._shortcut_labels: dict[str, QLabel] = {}

        for action_key, i18n_key in _SHORTCUT_KEY_MAP.items():
            label_text = tr(i18n_key)
            current_seq = shortcuts_cfg.get(action_key, "")
            editor = QKeySequenceEdit(QKeySequence(current_seq))
            editor.setAccessibleName(f"{tr('settings_tab_shortcuts')}: {label_text}")
            editor.setAccessibleDescription(
                f"{tr('settings_tab_shortcuts')}: {label_text}"
            )
            self._shortcut_edits[action_key] = editor
            lbl = QLabel(label_text)
            self._shortcut_labels[action_key] = lbl
            layout.addRow(lbl, editor)

        return tab

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        tab.setAccessibleName(tr("settings_tab_appearance_accessible_name"))
        layout = QVBoxLayout(tab)

        # Theme
        self._theme_group = QGroupBox(tr("settings_theme_group"))
        self._theme_group.setAccessibleName(
            tr("settings_theme_group_accessible_name")
        )
        theme_layout = QFormLayout(self._theme_group)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["default", "dark", "high_contrast"])
        current_theme = self.settings.get("theme", "default")
        idx = self.cmb_theme.findText(current_theme)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)
        self.cmb_theme.setAccessibleName(
            tr("settings_theme_combo_accessible_name")
        )
        self.cmb_theme.setAccessibleDescription(
            tr("settings_theme_combo_accessible_desc")
        )
        self._theme_label = QLabel(tr("settings_theme_label"))
        theme_layout.addRow(self._theme_label, self.cmb_theme)
        layout.addWidget(self._theme_group)

        # Position announce interval
        self._announce_group = QGroupBox(tr("settings_accessibility_group"))
        self._announce_group.setAccessibleName(
            tr("settings_accessibility_group_accessible_name")
        )
        announce_layout = QFormLayout(self._announce_group)
        self.spn_announce = QSpinBox()
        self.spn_announce.setRange(1, 60)
        self.spn_announce.setSuffix(" s")
        self.spn_announce.setValue(
            int(self.settings.get("position_announce_interval", 5))
        )
        self.spn_announce.setAccessibleName(
            tr("settings_announce_spin_accessible_name")
        )
        self.spn_announce.setAccessibleDescription(
            tr("settings_announce_spin_accessible_desc")
        )
        self._announce_label = QLabel(tr("settings_announce_label"))
        announce_layout.addRow(self._announce_label, self.spn_announce)
        layout.addWidget(self._announce_group)

        # Audio processing
        self._audio_group = QGroupBox(tr("settings_audio_group"))
        self._audio_group.setAccessibleName(
            tr("settings_audio_group_accessible_name")
        )
        audio_layout = QFormLayout(self._audio_group)
        self.chk_pitch_preserving = QCheckBox(tr("settings_pitch_preserving"))
        self.chk_pitch_preserving.setChecked(
            bool(self.settings.get("pitch_preserving", False))
        )
        self.chk_pitch_preserving.setAccessibleName(
            tr("settings_pitch_preserving_accessible_name")
        )
        self.chk_pitch_preserving.setAccessibleDescription(
            tr("settings_pitch_preserving_accessible_desc")
        )
        audio_layout.addRow(self.chk_pitch_preserving)
        layout.addWidget(self._audio_group)

        layout.addStretch()

        return tab

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #
    def _on_accept(self) -> None:
        """Write widget values back into ``self.settings`` then accept."""
        # Shortcuts
        shortcuts: dict[str, str] = self.settings.setdefault("shortcuts", {})
        for action_key, editor in self._shortcut_edits.items():
            seq = editor.keySequence()
            shortcuts[action_key] = seq.toString()

        # Appearance
        self.settings["theme"] = self.cmb_theme.currentText()
        self.settings["position_announce_interval"] = self.spn_announce.value()

        # Audio processing
        self.settings["pitch_preserving"] = self.chk_pitch_preserving.isChecked()

        self.accept()

    # ------------------------------------------------------------------ #
    # Retranslation
    # ------------------------------------------------------------------ #
    def retranslate_ui(self) -> None:
        """Apply the current language to all translatable widgets."""
        self.setWindowTitle(tr("settings_title"))
        self._tabs.setTabText(0, tr("settings_tab_shortcuts"))
        self._tabs.setTabText(1, tr("settings_tab_appearance"))
        self._tabs.setAccessibleName(tr("settings_tabs_accessible_name"))

        # Shortcut tab labels
        for action_key, i18n_key in _SHORTCUT_KEY_MAP.items():
            label_text = tr(i18n_key)
            if action_key in self._shortcut_labels:
                self._shortcut_labels[action_key].setText(label_text)
            if action_key in self._shortcut_edits:
                editor = self._shortcut_edits[action_key]
                editor.setAccessibleName(
                    f"{tr('settings_tab_shortcuts')}: {label_text}"
                )

        # Appearance tab
        self._theme_group.setTitle(tr("settings_theme_group"))
        self._theme_label.setText(tr("settings_theme_label"))
        self._announce_group.setTitle(tr("settings_accessibility_group"))
        self._announce_label.setText(tr("settings_announce_label"))
        self._audio_group.setTitle(tr("settings_audio_group"))
        self.chk_pitch_preserving.setText(tr("settings_pitch_preserving"))
        self.cmb_theme.setAccessibleName(tr("settings_theme_combo_accessible_name"))
        self.spn_announce.setAccessibleName(
            tr("settings_announce_spin_accessible_name")
        )
        self.chk_pitch_preserving.setAccessibleName(
            tr("settings_pitch_preserving_accessible_name")
        )

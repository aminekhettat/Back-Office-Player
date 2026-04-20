"""
PySide6 main window module for Back-Office Player.

This module defines the :class:`MainWindowQt` class, which implements the
main application window using PySide6 (Qt for Python).

Responsibilities
----------------
- Build widgets (buttons, labels, sliders, waveform, practice panel, etc.).
- Handle user interactions (clicks, keyboard shortcuts from settings).
- Coordinate the audio logic (:class:`AudioPlayer`).
- Load and save user settings (platformdirs).
- Provide A–B loop practice with loop count, progressive tempo, and loop delay.
- Show a waveform with seek-by-click.
- Open a settings dialog for shortcut customisation and theme selection.
- Maintain a practice history log.
- Check for available updates in the background.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2026-04-19
:version: 1.1.4
:disclaimer: Distributed on an "AS IS" basis, WITHOUT WARRANTIES OR
             CONDITIONS OF ANY KIND. See the LICENSE file for the full
             terms of the Apache License, Version 2.0.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QAccessible,
    QAction,
    QIcon,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAccessibleWidget,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from __version__ import __version__ as _APP_VERSION
from core.audio_loader import AudioLoaderThread
from core.audio_player_native import AudioPlayer
from core.commands import AddSegmentCommand, CommandHistory, RemoveSegmentCommand
from core.segment import Segment
from core.segment_manager import SegmentManager
from infra.audio_export import export_segment_mp3, export_segment_wav
from infra.i18n import get_language, set_language, tr
from infra.persistence import export_segments_text, load_segments, save_segments
from infra.practice_history import PracticeHistory
from infra.settings import add_recent_file, load_settings, save_settings
from ui.history_dialog import HistoryDialog
from ui.practice_panel import PracticePanel
from ui.segment_list_widget import SegmentListWidget
from ui.settings_dialog import SettingsDialog
from ui.waveform_widget import WaveformWidget

_logger = logging.getLogger(__name__)

_CURRENT_VERSION = f"v{_APP_VERSION}"

# ── Stylesheets ────────────────────────────────────────────────────────
_THEMES = {
    "default": "",
    "dark": (
        "QWidget { background-color: #2b2b2b; color: #f0f0f0; }"
        "QPushButton { background-color: #3c3f41; color: #f0f0f0; border: 1px solid #555; }"
        "QPushButton:hover { background-color: #4c5052; }"
        "QSlider::groove:horizontal { background: #555; height: 6px; border-radius: 3px; }"
        "QSlider::handle:horizontal { background: #aaa; width: 14px; height: 14px; border-radius: 7px; margin: -4px 0; }"
        "QLabel { color: #f0f0f0; }"
        "QListWidget { background-color: #3c3f41; color: #f0f0f0; }"
        "QGroupBox { color: #f0f0f0; }"
    ),
    "high_contrast": (
        "QWidget { background-color: #000000; color: #ffffff; }"
        "QPushButton { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; font-weight: bold; }"
        "QPushButton:hover { background-color: #ffffff; color: #000000; }"
        "QSlider::groove:horizontal { background: #ffffff; height: 6px; }"
        "QSlider::handle:horizontal { background: #ffff00; width: 14px; height: 14px; border-radius: 7px; margin: -4px 0; }"
        "QLabel { color: #ffffff; }"
        "QListWidget { background-color: #000000; color: #ffffff; border: 2px solid #ffffff; }"
        "QGroupBox { color: #ffffff; border: 2px solid #ffffff; }"
    ),
}


class TimeSlider(QSlider):
    """QSlider that reports its value as a formatted mm:ss time string
    to assistive technologies (JAWS, NVDA, Narrator), rather than the
    raw integer in seconds. The formatted text is read via the widget
    property ``formattedTime`` (set by the owner on every value update)."""


class _TimeSliderAccessible(QAccessibleWidget):
    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget, QAccessible.Role.Slider)

    def text(self, t):
        if t in (QAccessible.Text.Value, QAccessible.Text.Description):
            w = self.object()
            if w is not None:
                formatted = w.property("formattedTime")
                if formatted:
                    return str(formatted)
        return super().text(t)


# Strong refs to prevent Python from GC'ing the interface objects
# before Qt is done with them.
_time_slider_accessibles: list[_TimeSliderAccessible] = []


def _time_slider_accessible_factory(key, obj):
    if isinstance(obj, TimeSlider):
        iface = _TimeSliderAccessible(obj)
        _time_slider_accessibles.append(iface)
        return iface
    return None


class MainWindowQt(QMainWindow):
    """
    Qt main window for Back-Office Player.

    Attributes
    ----------
    audio_player : AudioPlayer
        Native audio player instance.
    segment_manager : SegmentManager
        Segment manager for the currently loaded audio file.
    settings : dict
        Persisted user settings.
    current_audio_path : Path or None
        Path to the currently loaded audio file.
    point_a / point_b : float or None
        A–B loop boundary positions in seconds.
    loop_enabled : bool
        Whether A–B looping is active.
    already_looped : bool
        Prevents double-triggering per loop cycle.
    """

    _accessible_factory_installed: bool = False

    def __init__(self, audio_player: AudioPlayer, segment_manager: SegmentManager) -> None:
        super().__init__()

        # Install QAccessible factory once per process (requires QApplication).
        if not MainWindowQt._accessible_factory_installed:
            QAccessible.installFactory(_time_slider_accessible_factory)
            MainWindowQt._accessible_factory_installed = True

        self.audio_player = audio_player
        self.segment_manager = segment_manager
        self.settings = load_settings()

        self.current_audio_path: Path | None = None

        # A–B loop state
        self.point_a: float | None = None
        self.point_b: float | None = None
        self.loop_enabled: bool = False
        self.already_looped: bool = False

        # Pitch / practice
        self._pitch_semitones: float = 0.0
        self._practice_history = PracticeHistory()
        self._session_loop_count: int = 0
        self._session_tempo_sum: float = 0.0
        self._last_announce_time: float = 0.0
        self._qt_shortcuts: list[QShortcut] = []  # keeps shortcuts alive
        self._loader_thread: AudioLoaderThread | None = None
        self._command_history = CommandHistory()
        self._save_settings_timer: QTimer  # assigned in _configure_timer
        self._pitch_debounce_timer: QTimer  # assigned in _configure_timer
        self._tempo_debounce_timer: QTimer  # assigned in _configure_timer
        self._playing: bool = False  # track play state for toggle button

        self._build_ui()
        self._build_menu_bar()
        self._configure_shortcuts()
        self._configure_timer()
        self._apply_theme()
        self._start_update_check()
        self.setAcceptDrops(True)

        # Apply initial volume from settings
        initial_volume = int(self.settings.get("default_volume", 80))
        self.slider_volume.setValue(initial_volume)
        self.audio_player.set_volume(initial_volume)

        # Restore last tempo from settings (after _configure_timer so debounce is ready)
        initial_tempo = int(self.settings.get("last_tempo", 100))
        self.slider_tempo.setValue(initial_tempo)
        self.audio_player.set_tempo(initial_tempo / 100.0)

        # Apply pitch-preserving setting
        self.audio_player.set_pitch_preserving(bool(self.settings.get("pitch_preserving", False)))

    def showEvent(self, event) -> None:
        """Give btn_open initial keyboard focus so Space/Enter work immediately."""
        super().showEvent(event)
        QTimer.singleShot(0, lambda: self.btn_open.setFocus())

    # ================================================================== #
    # UI construction
    # ================================================================== #
    def _build_ui(self) -> None:
        """Build the main Qt widgets and layout."""
        self.setWindowIcon(QIcon("resources/BOP.ico"))

        central = QWidget()
        main_layout = QVBoxLayout(central)

        # ── Row 0: file selection ──────────────────────────────────────
        file_layout = QHBoxLayout()
        self.btn_open = QPushButton()
        self.btn_open.clicked.connect(self.on_open_file)
        self.lbl_file = QLabel()
        self.lbl_file.setAccessibleName("Nom du fichier en cours")
        file_layout.addWidget(self.btn_open)
        file_layout.addWidget(self.lbl_file)

        # ── Row 1: playback controls + volume ─────────────────────────
        controls_layout = QHBoxLayout()
        self.btn_play = QPushButton()
        self.btn_play.clicked.connect(self.on_play_pause_toggle)
        self.btn_stop = QPushButton()
        self.btn_stop.clicked.connect(self.on_stop)
        self.lbl_volume = QLabel()
        self.lbl_volume.setAccessibleName("Étiquette volume")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setAccessibleName("Curseur de volume")
        self.slider_volume.valueChanged.connect(self.on_volume_change)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addWidget(self.lbl_volume)
        controls_layout.addWidget(self.slider_volume)

        # ── Row 2: position + time ─────────────────────────────────────
        position_layout = QHBoxLayout()
        self.lbl_position = QLabel()
        self.lbl_position.setAccessibleName("Étiquette de position")
        self.slider_position = TimeSlider(Qt.Orientation.Horizontal)
        self.slider_position.setRange(0, 0)
        self.slider_position.setAccessibleName("Position 00:00 / 00:00")
        self.slider_position.setSingleStep(1)
        self.slider_position.setProperty("formattedTime", "00:00 / 00:00")
        self.slider_position.valueChanged.connect(self.on_seek)
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setAccessibleName("Temps de lecture")
        self.lbl_time.setAccessibleDescription("Position actuelle et durée totale au format mm:ss.")
        position_layout.addWidget(self.lbl_position)
        position_layout.addWidget(self.slider_position)
        position_layout.addWidget(self.lbl_time)

        # ── Row 3: A–B loop controls ───────────────────────────────────
        loop_layout = QHBoxLayout()
        self.btn_set_a = QPushButton()
        self.btn_set_a.clicked.connect(self.on_set_point_a)
        self.btn_set_b = QPushButton()
        self.btn_set_b.clicked.connect(self.on_set_point_b)
        self.btn_clear_ab = QPushButton()
        self.btn_clear_ab.clicked.connect(self.on_clear_points)
        self.chk_loop = QCheckBox()
        self.chk_loop.stateChanged.connect(self.on_loop_state_changed)
        loop_layout.addWidget(self.btn_set_a)
        loop_layout.addWidget(self.btn_set_b)
        loop_layout.addWidget(self.btn_clear_ab)
        loop_layout.addWidget(self.chk_loop)

        # ── Row 4: Tempo control ───────────────────────────────────────
        tempo_layout = QHBoxLayout()
        self.lbl_tempo = QLabel()
        self.lbl_tempo.setAccessibleName("Étiquette tempo")
        self.slider_tempo = QSlider(Qt.Orientation.Horizontal)
        self.slider_tempo.setRange(50, 200)
        self.slider_tempo.setValue(100)
        self.slider_tempo.setAccessibleName("Curseur de tempo")
        self.slider_tempo.setAccessibleDescription(
            "Réglez la vitesse de lecture de 50 % à 200 %. "
            "Utilisez les flèches haut/bas par pas de 5 %."
        )
        self.slider_tempo.setSingleStep(5)
        self.slider_tempo.valueChanged.connect(self.on_tempo_change)
        self.lbl_tempo_value = QLabel("100 %")
        self.lbl_tempo_value.setAccessibleName("Valeur du tempo")
        self.lbl_tempo_value.setAccessibleDescription("Vitesse de lecture actuelle en pourcentage.")
        self.lbl_tempo_value.setMaximumWidth(50)
        tempo_layout.addWidget(self.lbl_tempo)
        tempo_layout.addWidget(self.slider_tempo)
        tempo_layout.addWidget(self.lbl_tempo_value)

        # ── Row 5: Pitch control ───────────────────────────────────────
        pitch_layout = QHBoxLayout()
        self.lbl_pitch = QLabel()
        self.lbl_pitch.setAccessibleName("Étiquette tonalité")
        self.slider_pitch = QSlider(Qt.Orientation.Horizontal)
        self.slider_pitch.setRange(-12, 12)
        self.slider_pitch.setValue(0)
        self.slider_pitch.setAccessibleName("Curseur de tonalité")
        self.slider_pitch.setAccessibleDescription(
            "Décaler la hauteur vers le haut ou le bas par demi-tons. "
            "0 = aucun décalage ; plage de -12 à +12 demi-tons."
        )
        self.slider_pitch.setSingleStep(1)
        self.slider_pitch.valueChanged.connect(self.on_pitch_change)
        self.lbl_pitch_value = QLabel("0 dt")
        self.lbl_pitch_value.setAccessibleName("Valeur de la tonalité")
        self.lbl_pitch_value.setAccessibleDescription("Décalage de tonalité actuel en demi-tons.")
        self.lbl_pitch_value.setMaximumWidth(50)
        pitch_layout.addWidget(self.lbl_pitch)
        pitch_layout.addWidget(self.slider_pitch)
        pitch_layout.addWidget(self.lbl_pitch_value)

        # ── Row 5b: Pitch-preserving tempo checkbox ─────────────────────
        self.chk_pitch_preserving = QCheckBox()
        self.chk_pitch_preserving.setChecked(bool(self.settings.get("pitch_preserving", False)))
        self.chk_pitch_preserving.toggled.connect(self._on_pitch_preserving_toggled)

        # ── Waveform widget ────────────────────────────────────────────
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setMinimumHeight(80)
        self.waveform_widget.setAccessibleName("Forme d'onde")
        self.waveform_widget.setAccessibleDescription(
            "Représentation graphique du signal audio. " "Cliquez pour positionner la lecture."
        )
        self.waveform_widget.seek_requested.connect(self._on_waveform_seek)

        # ── Practice panel ─────────────────────────────────────────────
        self.practice_panel = PracticePanel()

        # ── Segment list ───────────────────────────────────────────────
        self.segment_list_widget = SegmentListWidget(self.segment_manager)
        self.segment_list_widget.selected_callback = self.on_segment_selected
        self.segment_list_widget.changed_callback = self._on_segments_changed
        self.segment_list_widget.export_wav_callback = self._on_export_segment_wav
        self.segment_list_widget.export_mp3_callback = self._on_export_segment_mp3
        self.segment_list_widget.delete_callback = self._on_delete_segment_cmd
        self.segment_list_widget.setMaximumHeight(200)

        # Segment buttons
        segment_buttons_layout = QHBoxLayout()
        self.btn_save_segment = QPushButton()
        self.btn_save_segment.setAccessibleName("Sauvegarder le segment A-B actuel")
        self.btn_save_segment.setAccessibleDescription(
            "Sauvegarder la boucle A-B actuelle comme segment nommé. "
            "Les points A et B doivent être définis et B doit être après A."
        )
        self.btn_save_segment.clicked.connect(self.on_save_segment)
        self.btn_export_config = QPushButton()
        self.btn_export_config.setAccessibleName("Exporter les segments et paramètres")
        self.btn_export_config.setAccessibleDescription(
            "Exporter tous les segments et les paramètres actuels dans un fichier .bop."
        )
        self.btn_export_config.clicked.connect(self.on_export_config)
        self.btn_import_config = QPushButton()
        self.btn_import_config.setAccessibleName("Importer les segments et paramètres")
        self.btn_import_config.setAccessibleDescription(
            "Importer les segments et paramètres depuis un fichier .bop exporté précédemment."
        )
        self.btn_import_config.clicked.connect(self.on_import_config)
        segment_buttons_layout.addWidget(self.btn_save_segment)
        segment_buttons_layout.addWidget(self.btn_export_config)
        segment_buttons_layout.addWidget(self.btn_import_config)

        segment_section = QWidget()
        segment_section_layout = QVBoxLayout(segment_section)
        segment_section_layout.addWidget(self.segment_list_widget)
        segment_section_layout.addLayout(segment_buttons_layout)

        # ── Status label ───────────────────────────────────────────────
        self.lbl_status = QLabel()
        self.lbl_status.setAccessibleName("Message de statut")
        self.lbl_status.setAccessibleDescription(
            "Affiche l'état courant de l'application : lecture, chargement, erreur, etc."
        )

        # ── Assemble main layout ───────────────────────────────────────
        main_layout.addLayout(file_layout)
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(position_layout)
        main_layout.addLayout(loop_layout)
        main_layout.addLayout(tempo_layout)
        main_layout.addLayout(pitch_layout)
        main_layout.addWidget(self.chk_pitch_preserving)
        main_layout.addWidget(self.waveform_widget)
        main_layout.addWidget(self.practice_panel)
        main_layout.addWidget(segment_section)
        main_layout.addWidget(self.lbl_status)

        self.setCentralWidget(central)

        # Tab order: transport controls first, then sliders, then segment tools
        QWidget.setTabOrder(self.btn_open, self.btn_play)
        QWidget.setTabOrder(self.btn_play, self.btn_stop)
        QWidget.setTabOrder(self.btn_stop, self.slider_volume)
        QWidget.setTabOrder(self.slider_volume, self.slider_tempo)
        QWidget.setTabOrder(self.slider_tempo, self.slider_pitch)
        QWidget.setTabOrder(self.slider_pitch, self.chk_pitch_preserving)
        QWidget.setTabOrder(self.chk_pitch_preserving, self.slider_position)
        QWidget.setTabOrder(self.slider_position, self.btn_set_a)
        QWidget.setTabOrder(self.btn_set_a, self.btn_set_b)
        QWidget.setTabOrder(self.btn_set_b, self.btn_clear_ab)
        QWidget.setTabOrder(self.btn_clear_ab, self.chk_loop)
        QWidget.setTabOrder(self.chk_loop, self.btn_save_segment)
        QWidget.setTabOrder(self.btn_save_segment, self.btn_export_config)
        QWidget.setTabOrder(self.btn_export_config, self.btn_import_config)

        self.retranslate_ui()

    # ================================================================== #
    # Retranslation (i18n)
    # ================================================================== #
    def retranslate_ui(self) -> None:
        """
        Apply the current language to every translatable UI element.

        Called once during :meth:`_build_ui` and again whenever the user
        switches the active language at runtime.
        """
        self.setWindowTitle("Back-Office Player (BOP)")
        self.btn_open.setText(tr("btn_open"))
        self.btn_open.setAccessibleName(tr("btn_open"))
        self.btn_open.setAccessibleDescription(
            "Ouvrir un fichier audio pour la lecture et la pratique."
            if get_language() == "fr"
            else "Open an audio file for playback and practice."
        )
        self.lbl_file.setText(tr("lbl_no_file"))

        self._update_play_pause_button()
        self.btn_stop.setText(tr("btn_stop"))
        self.btn_stop.setAccessibleName(tr("btn_stop"))
        self.btn_stop.setAccessibleDescription(
            "Arrêter la lecture et revenir au début."
            if get_language() == "fr"
            else "Stop playback and return to the beginning."
        )
        self.lbl_volume.setText(tr("lbl_volume"))
        self.slider_volume.setAccessibleDescription(
            "Réglez le volume de 0 à 100. Utilisez les flèches gauche/droite."
            if get_language() == "fr"
            else "Adjust volume from 0 to 100. Use left/right arrow keys."
        )

        self.lbl_position.setText(tr("lbl_position"))
        self.slider_position.setAccessibleDescription(
            "Position de lecture. Utilisez les flèches gauche/droite pour avancer "
            "ou reculer d'une seconde. La position s'affiche au format mm:ss."
            if get_language() == "fr"
            else "Playback position. Use arrow keys to seek. Displayed as mm:ss."
        )

        self.btn_set_a.setText(tr("btn_set_a"))
        self.btn_set_a.setAccessibleName(
            "Définir le point A" if get_language() == "fr" else "Set point A"
        )
        self.btn_set_a.setAccessibleDescription(
            "Définir le point A (début de la boucle) à la position de lecture actuelle."
            if get_language() == "fr"
            else "Set point A (loop start) at the current playback position."
        )
        self.btn_set_b.setText(tr("btn_set_b"))
        self.btn_set_b.setAccessibleName(
            "Définir le point B" if get_language() == "fr" else "Set point B"
        )
        self.btn_set_b.setAccessibleDescription(
            "Définir le point B (fin de la boucle) à la position de lecture actuelle."
            if get_language() == "fr"
            else "Set point B (loop end) at the current playback position."
        )
        self.btn_clear_ab.setText(tr("btn_clear_ab"))
        self.btn_clear_ab.setAccessibleName(
            "Effacer les points A et B" if get_language() == "fr" else "Clear A and B points"
        )
        self.btn_clear_ab.setAccessibleDescription(
            "Effacer les points de boucle A et B et désactiver la boucle A–B."
            if get_language() == "fr"
            else "Clear A and B loop points and disable A–B looping."
        )
        self.chk_loop.setText(tr("lbl_loop"))
        self.chk_loop.setAccessibleName(
            "Case à cocher boucle A-B" if get_language() == "fr" else "A-B loop checkbox"
        )
        self.chk_loop.setAccessibleDescription(
            "Activer ou désactiver la répétition en boucle entre les points A et B."
            if get_language() == "fr"
            else "Enable or disable looping between A and B points."
        )

        self.lbl_tempo.setText(tr("lbl_tempo"))
        self.lbl_pitch.setText(tr("lbl_pitch"))

        self.chk_pitch_preserving.setText(tr("chk_pitch_preserving_main"))
        self.chk_pitch_preserving.setAccessibleName(tr("settings_pitch_preserving_accessible_name"))
        self.chk_pitch_preserving.setAccessibleDescription(
            tr("settings_pitch_preserving_accessible_desc")
        )

        self.btn_save_segment.setText(tr("btn_save_segment"))
        self.btn_export_config.setText(tr("btn_export_config"))
        self.btn_import_config.setText(tr("btn_import_config"))

        if not self.current_audio_path:
            self.lbl_status.setText(tr("lbl_no_file_loaded"))

        # Propagate to child panels
        self.practice_panel.retranslate_ui()
        self.segment_list_widget.retranslate_ui()

    # ================================================================== #
    # Menu bar
    # ================================================================== #
    def _build_menu_bar(self) -> None:
        """Build the application menu bar (File / Edit / Playback / Settings / Help)."""
        menubar: QMenuBar = self.menuBar()

        # ── File menu ────────────────────────────────────────────────────
        file_menu: QMenu = menubar.addMenu(tr("menu_file"))
        file_menu.setAccessibleName("Menu Fichier" if get_language() == "fr" else "File menu")

        self.act_open = QAction(tr("menu_open"), self)
        self.act_open.triggered.connect(self.on_open_file)
        file_menu.addAction(self.act_open)

        self.recent_menu = QMenu(tr("menu_recent"), self)
        self.recent_menu.setAccessibleName(
            "Sous-menu des fichiers récents" if get_language() == "fr" else "Recent files submenu"
        )
        file_menu.addMenu(self.recent_menu)
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        self.act_export_bop = QAction(tr("menu_export_bop"), self)
        self.act_export_bop.triggered.connect(self.on_export_config)
        file_menu.addAction(self.act_export_bop)

        self.act_import_bop = QAction(tr("menu_import_bop"), self)
        self.act_import_bop.triggered.connect(self.on_import_config)
        file_menu.addAction(self.act_import_bop)

        self.act_export_csv = QAction(tr("menu_export_csv"), self)
        self.act_export_csv.triggered.connect(self.on_export_segments_csv)
        file_menu.addAction(self.act_export_csv)

        file_menu.addSeparator()

        self.act_quit = QAction(tr("menu_quit"), self)
        self.act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_quit.triggered.connect(self.close)
        file_menu.addAction(self.act_quit)

        # ── Edit menu (Undo / Redo) ──────────────────────────────────────
        edit_menu: QMenu = menubar.addMenu(tr("menu_edit"))
        edit_menu.setAccessibleName("Menu Édition" if get_language() == "fr" else "Edit menu")

        self.act_undo = QAction(tr("menu_undo"), self)
        self.act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.act_undo.triggered.connect(self._on_undo)
        edit_menu.addAction(self.act_undo)

        self.act_redo = QAction(tr("menu_redo"), self)
        self.act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.act_redo.triggered.connect(self._on_redo)
        edit_menu.addAction(self.act_redo)

        # ── Playback menu ────────────────────────────────────────────────
        playback_menu: QMenu = menubar.addMenu(tr("menu_playback"))
        playback_menu.setAccessibleName(
            "Menu Lecture" if get_language() == "fr" else "Playback menu"
        )

        self.act_play_pause = QAction(tr("menu_play_pause"), self)
        self.act_play_pause.triggered.connect(self.on_play_pause_toggle)
        playback_menu.addAction(self.act_play_pause)

        self.act_stop = QAction(tr("menu_stop"), self)
        self.act_stop.triggered.connect(self.on_stop)
        playback_menu.addAction(self.act_stop)

        playback_menu.addSeparator()

        self.act_set_a = QAction(tr("menu_set_a"), self)
        self.act_set_a.triggered.connect(self.on_set_point_a)
        playback_menu.addAction(self.act_set_a)

        self.act_set_b = QAction(tr("menu_set_b"), self)
        self.act_set_b.triggered.connect(self.on_set_point_b)
        playback_menu.addAction(self.act_set_b)

        self.act_clear_ab = QAction(tr("menu_clear_ab"), self)
        self.act_clear_ab.triggered.connect(self.on_clear_points)
        playback_menu.addAction(self.act_clear_ab)

        self.act_toggle_loop = QAction(tr("menu_toggle_loop"), self)
        self.act_toggle_loop.triggered.connect(self.on_toggle_loop)
        playback_menu.addAction(self.act_toggle_loop)

        playback_menu.addSeparator()

        self.act_save_segment = QAction(tr("menu_save_segment"), self)
        self.act_save_segment.triggered.connect(self.on_save_segment)
        playback_menu.addAction(self.act_save_segment)

        self.act_next_segment = QAction(tr("menu_next_segment"), self)
        self.act_next_segment.triggered.connect(self.on_next_segment)
        playback_menu.addAction(self.act_next_segment)

        self.act_prev_segment = QAction(tr("menu_prev_segment"), self)
        self.act_prev_segment.triggered.connect(self.on_prev_segment)
        playback_menu.addAction(self.act_prev_segment)

        # ── Settings menu ────────────────────────────────────────────────
        settings_menu: QMenu = menubar.addMenu(tr("menu_settings"))
        settings_menu.setAccessibleName(
            "Menu Paramètres" if get_language() == "fr" else "Settings menu"
        )

        act_prefs = QAction(tr("menu_prefs"), self)
        act_prefs.triggered.connect(self.on_open_settings)
        settings_menu.addAction(act_prefs)

        self.act_history = QAction(tr("menu_history"), self)
        self.act_history.setShortcut(QKeySequence("Ctrl+H"))
        self.act_history.triggered.connect(self._on_open_history)
        settings_menu.addAction(self.act_history)

        settings_menu.addSeparator()

        # Language submenu
        lang_menu: QMenu = QMenu(tr("menu_language"), self)
        lang_menu.setAccessibleName(
            "Sous-menu de sélection de la langue"
            if get_language() == "fr"
            else "Language selection submenu"
        )

        self.act_lang_fr = QAction(tr("menu_lang_fr"), self)
        self.act_lang_fr.setCheckable(True)
        self.act_lang_fr.setChecked(get_language() == "fr")
        self.act_lang_fr.triggered.connect(lambda: self._on_set_language("fr"))
        lang_menu.addAction(self.act_lang_fr)

        self.act_lang_en = QAction(tr("menu_lang_en"), self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setChecked(get_language() == "en")
        self.act_lang_en.triggered.connect(lambda: self._on_set_language("en"))
        lang_menu.addAction(self.act_lang_en)

        settings_menu.addMenu(lang_menu)

        # ── Help menu ────────────────────────────────────────────────────
        help_menu: QMenu = menubar.addMenu(tr("menu_help"))
        help_menu.setAccessibleName("Menu Aide" if get_language() == "fr" else "Help menu")

        act_about = QAction(tr("menu_about"), self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _on_about(self) -> None:
        """Show the About dialog."""
        if get_language() == "fr":
            body = (
                f"<h3>Back-Office Player</h3>"
                f"<p>Version {_APP_VERSION}</p>"
                f"<p>Outil de pratique audio pour les élèves de musique, "
                f"développé par <b>BLIND SYSTEMS</b> pour l'association "
                f"<b>Culture Musique</b>.</p>"
                f"<p>Licence : Apache 2.0 &mdash; &copy; 2025 BLIND SYSTEMS.</p>"
                f'<p><a href="https://www.blindsystems.org">www.blindsystems.org</a></p>'
            )
        else:
            body = (
                f"<h3>Back-Office Player</h3>"
                f"<p>Version {_APP_VERSION}</p>"
                f"<p>Audio practice tool for music students, developed by "
                f"<b>BLIND SYSTEMS</b> for the <b>Culture Musique</b> "
                f"association.</p>"
                f"<p>License: Apache 2.0 &mdash; &copy; 2025 BLIND SYSTEMS.</p>"
                f'<p><a href="https://www.blindsystems.org">www.blindsystems.org</a></p>'
            )
        QMessageBox.about(self, tr("dlg_about_title"), body)

    def _rebuild_recent_menu(self) -> None:
        """Rebuild the Recent Files submenu from settings."""
        self.recent_menu.clear()
        recent: list = self.settings.get("recent_files", [])
        if not recent:
            act = QAction(tr("menu_recent_none"), self)
            act.setEnabled(False)
            self.recent_menu.addAction(act)
            return
        for path_str in recent:
            act = QAction(path_str, self)
            act.triggered.connect(lambda checked=False, p=path_str: self._open_recent(p))
            self.recent_menu.addAction(act)

    def _open_recent(self, path_str: str) -> None:
        """Open a file from the Recent Files list."""
        path = Path(path_str)
        if not path.is_file():
            QMessageBox.warning(
                self, tr("dlg_file_not_found_title"), f"Cannot find file:\n{path_str}"
            )
            return
        self._load_audio_file(path)

    # ================================================================== #
    # Keyboard shortcuts
    # ================================================================== #
    def _configure_shortcuts(self) -> None:
        """
        Configure keyboard shortcuts from ``settings["shortcuts"]``.

        Menu-covered actions receive their shortcut directly via
        ``QAction.setShortcut`` so the menu displays the binding and
        there is no ambiguity with a parallel ``QShortcut``. Only
        slider-only actions (with no menu entry) use ``QShortcut``.
        """
        # Remove old slider-only shortcuts
        for sc in self._qt_shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._qt_shortcuts = []

        sc_cfg: dict = self.settings.get("shortcuts", {})

        # Map each user-configurable action name to its QAction. Setting
        # an empty string clears the shortcut.
        menu_actions = {
            "open": (self.act_open, "Ctrl+O"),
            "play_pause": (self.act_play_pause, "Ctrl+P"),
            "stop": (self.act_stop, "Ctrl+S"),
            "set_a": (self.act_set_a, "Ctrl+Shift+A"),
            "set_b": (self.act_set_b, "Ctrl+Shift+B"),
            "save_segment": (self.act_save_segment, "Ctrl+Shift+S"),
            "export_config": (self.act_export_bop, "Ctrl+E"),
            "import_config": (self.act_import_bop, "Ctrl+I"),
            "next_segment": (self.act_next_segment, "Ctrl+Right"),
            "prev_segment": (self.act_prev_segment, "Ctrl+Left"),
            "toggle_loop": (self.act_toggle_loop, "Ctrl+L"),
        }
        for name, (action, default) in menu_actions.items():
            key_str = sc_cfg.get(name, default) or default
            action.setShortcut(QKeySequence(key_str))

        # Slider-only actions: no menu entry, keep as QShortcut.
        slider_bindings = {
            "volume_up": lambda: self.slider_volume.setValue(
                min(100, self.slider_volume.value() + 5)
            ),
            "volume_down": lambda: self.slider_volume.setValue(
                max(0, self.slider_volume.value() - 5)
            ),
            "tempo_up": lambda: self.slider_tempo.setValue(min(200, self.slider_tempo.value() + 5)),
            "tempo_down": lambda: self.slider_tempo.setValue(
                max(50, self.slider_tempo.value() - 5)
            ),
            "pitch_up": lambda: self.slider_pitch.setValue(min(12, self.slider_pitch.value() + 1)),
            "pitch_down": lambda: self.slider_pitch.setValue(
                max(-12, self.slider_pitch.value() - 1)
            ),
            # "play" / "pause" kept as extra shortcuts (no menu entry —
            # the menu offers a single Play/Pause toggle).
            "play": self.on_play,
            "pause": self.on_pause,
        }
        for name, slot in slider_bindings.items():
            key_str = sc_cfg.get(name, "")
            if key_str:
                sc = QShortcut(QKeySequence(key_str), self)
                sc.activated.connect(slot)
                self._qt_shortcuts.append(sc)

    # ================================================================== #
    # Timer
    # ================================================================== #
    def _configure_timer(self) -> None:
        """Start the 100 ms periodic timer."""
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._update_position)

        # Debounce timer: sauvegarde les paramètres 500 ms après le
        # dernier changement de volume pour éviter une écriture disque
        # à chaque tick du curseur.
        self._save_settings_timer = QTimer(self)
        self._save_settings_timer.setSingleShot(True)
        self._save_settings_timer.setInterval(500)
        self._save_settings_timer.timeout.connect(lambda: save_settings(self.settings))

        # Pitch debounce: apply pitch shift 150 ms after the last slider move.
        self._pitch_debounce_timer = QTimer(self)
        self._pitch_debounce_timer.setSingleShot(True)
        self._pitch_debounce_timer.setInterval(150)
        self._pitch_debounce_timer.timeout.connect(
            lambda: self.audio_player.apply_pitch_async(
                lambda: QTimer.singleShot(
                    0, lambda: self.audio_player.set_position(self.audio_player.get_position())
                )
            )
        )

        # Tempo debounce: re-process audio in pitch-preserving mode.
        self._tempo_debounce_timer = QTimer(self)
        self._tempo_debounce_timer.setSingleShot(True)
        self._tempo_debounce_timer.setInterval(150)
        self._tempo_debounce_timer.timeout.connect(
            lambda: self.audio_player.apply_pitch_async(
                lambda: QTimer.singleShot(
                    0, lambda: self.audio_player.set_position(self.audio_player.get_position())
                )
            )
        )

        self.timer.start()

    # ================================================================== #
    # Slots / callbacks
    # ================================================================== #
    def on_open_file(self) -> None:
        """Open a file dialog and load the selected audio file."""
        raw_dir = self.settings.get("last_opened_folder", "")
        initial_dir = raw_dir if raw_dir and Path(raw_dir).is_dir() else str(Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg_open_audio_title"),
            initial_dir,
            tr("filter_audio"),
        )
        if not filename:
            return
        self._load_audio_file(Path(filename))

    def _load_audio_file(self, path: Path) -> None:
        """
        Charge un fichier audio de façon asynchrone sans bloquer l'UI.

        L'interface est désactivée pendant le chargement et réactivée
        une fois le fichier prêt (ou en cas d'erreur).
        """
        # Annuler tout chargement précédent encore en cours
        if self._loader_thread is not None and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait(500)

        # Désactiver l'UI et indiquer le chargement
        self._set_ui_enabled(False)
        self.lbl_status.setText(tr("status_loading", name=path.name))
        self.lbl_file.setText(path.name)

        # Réinitialiser l'affichage pendant le chargement
        self.slider_position.setRange(0, 0)
        self.on_clear_points(update_status=False)

        # Lancer le thread de chargement
        self._loader_thread = AudioLoaderThread(self.audio_player, path, parent=self)
        self._loader_thread.loaded.connect(lambda: self._on_audio_loaded(path))
        self._loader_thread.error.connect(self._on_audio_load_error)
        self._loader_thread.start()

    def _set_ui_enabled(self, enabled: bool) -> None:
        """Active ou désactive les contrôles principaux de l'UI."""
        for widget in (
            self.btn_play,
            self.btn_stop,
            self.slider_volume,
            self.slider_position,
            self.slider_tempo,
            self.slider_pitch,
            self.btn_set_a,
            self.btn_set_b,
            self.btn_clear_ab,
            self.chk_loop,
            self.btn_save_segment,
            self.btn_export_config,
            self.btn_import_config,
            self.segment_list_widget,
        ):
            widget.setEnabled(enabled)

    def _on_audio_loaded(self, path: Path) -> None:
        """Appelé dans le thread Qt principal quand le chargement est terminé."""
        self.current_audio_path = path
        self.lbl_status.setText(tr("status_loaded", name=path.name))

        # Charger les segments associés
        self.segment_manager = load_segments(path)
        self.segment_list_widget.set_segment_manager(self.segment_manager)

        # Mettre à jour la forme d'onde
        audio, sr = self.audio_player.get_audio_snapshot()
        if audio is not None:
            self.waveform_widget.set_audio_data(audio, sr)
            self.waveform_widget.set_segments(self.segment_manager.list_segments())

        # Réinitialiser la session de pratique et l'historique des commandes
        self.practice_panel.reset_session()
        self._session_loop_count = 0
        self._session_tempo_sum = 0.0
        self._command_history.clear()

        # Mémoriser le fichier et le dossier récents
        add_recent_file(self.settings, str(path))
        self.settings["last_opened_folder"] = str(path.parent)
        save_settings(self.settings)
        self._rebuild_recent_menu()

        # Réactiver l'UI
        self._set_ui_enabled(True)

        # If pitch-preserving is enabled and tempo ≠ 100 % (or pitch ≠ 0),
        # pre-compute the stretched/shifted buffer so the first playback
        # block already uses the correct audio instead of falling back to
        # raw tape-rate playback (which would sound wrong).
        needs_preprocess = (
            self.audio_player.get_pitch_preserving()
            and (self.slider_tempo.value() != 100 or self.slider_pitch.value() != 0)
        ) or self.slider_pitch.value() != 0
        if needs_preprocess:
            self._pitch_debounce_timer.start()

    def _on_audio_load_error(self, message: str) -> None:
        """Appelé dans le thread Qt principal en cas d'erreur de chargement."""
        self._set_ui_enabled(True)
        self.lbl_status.setText(tr("status_load_error"))
        QMessageBox.critical(
            self, tr("dlg_error_title"), f"Impossible de charger le fichier :\n{message}"
        )

    def on_play_pause_toggle(self) -> None:
        """Toggle playback: play if paused/stopped, pause if playing."""
        if self._playing:
            self.on_pause()
        else:
            self.on_play()

    def on_play(self) -> None:
        """Start or resume playback; start a practice session if none active."""
        if self.practice_panel.get_active_session() is None:
            session = self.practice_panel.start_session()
            self._session_loop_count = 0
            self._session_tempo_sum = session.current_tempo
            # Only apply the session start tempo when progressive mode is enabled;
            # otherwise keep the current user-set slider value.
            if session.progressive_tempo:
                self.slider_tempo.setValue(int(session.current_tempo * 100))
        self.audio_player.play()
        self._playing = True
        self.lbl_status.setText(tr("status_playing"))
        self._update_play_pause_button()

    def on_pause(self) -> None:
        """Pause playback."""
        self.audio_player.pause()
        self._playing = False
        self.lbl_status.setText(tr("status_paused"))
        self._update_play_pause_button()

    def on_stop(self) -> None:
        """Stop playback and save practice history."""
        self.audio_player.stop()
        self._playing = False
        self._save_practice_history()
        self.practice_panel.stop_session()
        self.lbl_status.setText(tr("status_stopped"))
        self._update_play_pause_button()

    def on_toggle_loop(self) -> None:
        """Toggle A–B loop on/off."""
        self.chk_loop.setChecked(not self.chk_loop.isChecked())

    def _update_play_pause_button(self) -> None:
        """Update the play/pause toggle button label to reflect current state."""
        if self._playing:
            self.btn_play.setText(tr("btn_pause"))
            self.btn_play.setAccessibleName(tr("btn_pause"))
            self.btn_play.setAccessibleDescription(
                "Mettre la lecture en pause." if get_language() == "fr" else "Pause audio playback."
            )
        else:
            self.btn_play.setText(tr("btn_play"))
            self.btn_play.setAccessibleName(tr("btn_play"))
            self.btn_play.setAccessibleDescription(
                "Démarrer ou reprendre la lecture audio."
                if get_language() == "fr"
                else "Start or resume audio playback."
            )

    def on_volume_change(self, value: int) -> None:
        self.audio_player.set_volume(int(value))
        self.settings["default_volume"] = int(value)
        # Debounce : on déclenche la sauvegarde 500 ms après le dernier
        # changement pour ne pas écrire sur disque à chaque tick.
        self._save_settings_timer.start()

    def on_seek(self, value: int) -> None:
        self.audio_player.set_position(float(value))
        duration = self.audio_player.get_duration()
        announce_text = f"{self._format_time(value)} / {self._format_time(duration)}"
        self.lbl_time.setText(announce_text)
        # The TimeSlider accessibility factory reads this property and
        # exposes it as the slider's value to AT, so JAWS/NVDA speak
        # "01:23 / 03:45" instead of the raw integer "83". We deliberately
        # do NOT set accessibleDescription or call QAccessible.announce
        # here — both would cause the screen reader to speak the value
        # twice (once for the native ValueChange event, once for ours).
        self.slider_position.setProperty("formattedTime", announce_text)
        # accessibleName covers AT that read the name on focus enter but
        # do not query the custom value (e.g. before any ValueChange event).
        self.slider_position.setAccessibleName(f"Position {announce_text}")

    def _on_waveform_seek(self, seconds: float) -> None:
        """Seek triggered by clicking on the waveform widget."""
        self.audio_player.set_position(seconds)

    def on_set_point_a(self) -> None:
        current_pos = self.audio_player.get_position()
        self.point_a = current_pos
        self.waveform_widget.set_point_a(current_pos)
        self.lbl_status.setText(tr("status_point_a", time=self._format_time(current_pos)))

    def on_set_point_b(self) -> None:
        current_pos = self.audio_player.get_position()
        self.point_b = current_pos
        self.waveform_widget.set_point_b(current_pos)
        self.lbl_status.setText(tr("status_point_b", time=self._format_time(current_pos)))

    def on_clear_points(self, update_status: bool = True) -> None:
        self.point_a = None
        self.point_b = None
        self.loop_enabled = False
        self.already_looped = False
        self.chk_loop.setChecked(False)
        self.waveform_widget.set_point_a(None)
        self.waveform_widget.set_point_b(None)
        if update_status:
            self.lbl_status.setText(tr("status_ab_cleared"))

    def on_loop_state_changed(self, state: int) -> None:
        self.loop_enabled = state != 0

    def on_tempo_change(self, value: int) -> None:
        percentage = value / 100.0
        self.audio_player.set_tempo(percentage)
        announce_text = f"{value}%"
        self.lbl_tempo_value.setText(announce_text)
        self.slider_tempo.setAccessibleDescription(announce_text)
        self.slider_tempo.setAccessibleName(f"{tr('lbl_tempo').rstrip(':')} : {announce_text}")
        _announce = getattr(QAccessible, "announce", None)
        _priority_cls = getattr(QAccessible, "AnnouncementPriority", None)
        if _announce is not None and _priority_cls is not None:
            _announce(
                self.slider_tempo,
                _priority_cls.Assertive,
                announce_text,
            )
        # Persist the tempo so it survives app restart.
        self.settings["last_tempo"] = value
        self._save_settings_timer.start()
        # If pitch-preserving, reprocess audio after debounce.
        if self.audio_player.get_pitch_preserving():
            self._tempo_debounce_timer.start()

    def on_pitch_change(self, value: int) -> None:
        """Pitch slider moved — apply shift in real time."""
        self._pitch_semitones = float(value)
        announce_text = f"{value:+d} st"
        self.lbl_pitch_value.setText(announce_text)
        self.slider_pitch.setAccessibleDescription(announce_text)
        self.slider_pitch.setAccessibleName(f"{tr('lbl_pitch').rstrip(':')} : {announce_text}")
        _announce = getattr(QAccessible, "announce", None)
        _priority_cls = getattr(QAccessible, "AnnouncementPriority", None)
        if _announce is not None and _priority_cls is not None:
            _announce(
                self.slider_pitch,
                _priority_cls.Assertive,
                announce_text,
            )
        self.audio_player.set_pitch_semitones(float(value))
        # In tape mode, the playback worker applies pitch via real-time
        # resampling — no pre-compute needed, no debounce. Only schedule
        # the expensive librosa pitch_shift when pitch-preserving is on.
        if self.audio_player.get_pitch_preserving():
            self._pitch_debounce_timer.start()
        else:
            # Drop any stale pre-processed buffer so the worker falls back
            # to the raw audio and the rate multiplier handles the shift.
            self.audio_player.clear_processed_audio()

    def on_segment_selected(self, segment: Segment) -> None:
        """
        React to a segment selection: seek to its start and load A/B points.

        Automatically sets :attr:`point_a` / :attr:`point_b` from the
        segment boundaries and enables the A–B loop so the student can
        start practising immediately without having to re-set the markers.

        Parameters
        ----------
        segment : Segment
            The selected segment.  A falsy value is silently ignored.
        """
        if segment:
            self.audio_player.set_position(segment.start_sec)
            # Load segment boundaries into A/B points so the user can
            # immediately start looping the selected segment.
            self.point_a = segment.start_sec
            self.point_b = segment.end_sec
            self.waveform_widget.set_point_a(segment.start_sec)
            self.waveform_widget.set_point_b(segment.end_sec)
            self.loop_enabled = True
            self.already_looped = False
            self.chk_loop.setChecked(True)
            self.lbl_status.setText(
                tr(
                    "status_segment_jumped",
                    name=segment.name,
                    start=self._format_time(segment.start_sec),
                    end=self._format_time(segment.end_sec),
                )
            )

    def on_next_segment(self) -> None:
        """Jump to the segment immediately after the current playback position."""
        pos = self.audio_player.get_position()
        segments = self.segment_manager.list_segments()
        # Find the first segment whose start is strictly after the current position.
        candidate = next(
            (
                seg
                for seg in sorted(segments, key=lambda x: x.start_sec)
                if seg.start_sec > pos + 0.1
            ),
            None,
        )
        if candidate:
            self.on_segment_selected(candidate)
        else:
            self.lbl_status.setText(tr("status_no_next"))

    def on_prev_segment(self) -> None:
        """Jump to the segment immediately before the current playback position."""
        pos = self.audio_player.get_position()
        segments = self.segment_manager.list_segments()
        # Find the last segment whose start is strictly before the current position.
        candidates = [
            seg for seg in sorted(segments, key=lambda x: x.start_sec) if seg.start_sec < pos - 0.1
        ]
        if candidates:
            self.on_segment_selected(candidates[-1])
        else:
            self.lbl_status.setText(tr("status_no_prev"))

    def on_save_segment(self) -> None:
        if self.point_a is None or self.point_b is None or self.point_b <= self.point_a:
            QMessageBox.warning(
                self,
                tr("dlg_invalid_ab_title"),
                tr("dlg_invalid_ab_msg"),
            )
            return

        name, ok = QInputDialog.getText(
            self,
            tr("dlg_save_segment_title"),
            tr("dlg_save_segment_label"),
            text=f"Segment {len(self.segment_manager.list_segments()) + 1}",
        )
        if ok and name:
            segment = Segment(name=name, start_sec=self.point_a, end_sec=self.point_b)
            cmd = AddSegmentCommand(self.segment_manager, segment)
            self._command_history.execute(cmd)
            self.segment_list_widget.refresh_list()
            self.waveform_widget.set_segments(self.segment_manager.list_segments())
            save_segments(self.current_audio_path, self.segment_manager)
            self.lbl_status.setText(
                tr(
                    "status_segment_saved",
                    name=name,
                    start=self._format_time(self.point_a),
                    end=self._format_time(self.point_b),
                )
            )

    def _on_segments_changed(self) -> None:
        save_segments(self.current_audio_path, self.segment_manager)
        self.waveform_widget.set_segments(self.segment_manager.list_segments())

    def _on_delete_segment_cmd(self, name: str) -> None:
        """Execute a RemoveSegmentCommand so the deletion can be undone."""
        cmd = RemoveSegmentCommand(self.segment_manager, name)
        self._command_history.execute(cmd)
        self.segment_list_widget.refresh_list()
        self._on_segments_changed()

    def _on_pitch_preserving_toggled(self, checked: bool) -> None:
        """React to the pitch-preserving checkbox on the main UI."""
        self.settings["pitch_preserving"] = bool(checked)
        self.audio_player.set_pitch_preserving(bool(checked))
        if self._save_settings_timer is not None:
            self._save_settings_timer.start()
        # When enabling, regenerate processed audio with time-stretch.
        # When disabling, drop the processed buffer so tape mode kicks in.
        if checked:
            if self._pitch_debounce_timer is not None:
                self._pitch_debounce_timer.start()
        else:
            self.audio_player.clear_processed_audio()

    def _on_undo(self) -> None:
        """Undo the last segment command (Ctrl+Z)."""
        if self._command_history.undo():
            self.segment_list_widget.refresh_list()
            self._on_segments_changed()
            self.lbl_status.setText(tr("status_undo"))
        else:
            self.lbl_status.setText(tr("status_nothing_undo"))

    def _on_redo(self) -> None:
        """Redo the last undone segment command (Ctrl+Y)."""
        if self._command_history.redo():
            self.segment_list_widget.refresh_list()
            self._on_segments_changed()
            self.lbl_status.setText(tr("status_redo"))
        else:
            self.lbl_status.setText(tr("status_nothing_redo"))

    def _on_export_segment_wav(self, segment) -> None:
        """Export a single segment to a WAV file chosen by the user."""
        from PySide6.QtWidgets import QFileDialog

        default_name = segment.name.replace(" ", "_") + ".wav"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_export_wav_title"),
            default_name,
            tr("filter_wav"),
        )
        if not filename:
            return
        audio_data, sample_rate = self.audio_player.get_audio_snapshot()
        if audio_data is None:
            QMessageBox.critical(
                self,
                tr("dlg_error_title"),
                tr("dlg_err_export_wav", err="No audio loaded"),
            )
            return
        try:
            export_segment_wav(
                audio_data,
                sample_rate,
                segment.start_sec,
                segment.end_sec,
                Path(filename),
            )
            QMessageBox.information(
                self,
                tr("dlg_exported_title"),
                tr("dlg_wav_exported", name=segment.name, path=filename),
            )
            self.lbl_status.setText(tr("status_wav_exported", name=segment.name))
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("dlg_error_title"),
                tr("dlg_err_export_wav", err=exc),
            )

    def _on_export_segment_mp3(self, segment) -> None:
        """Export a single segment to an MP3 file chosen by the user."""
        from PySide6.QtWidgets import QFileDialog

        default_name = segment.name.replace(" ", "_") + ".mp3"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_export_mp3_title"),
            default_name,
            tr("filter_mp3"),
        )
        if not filename:
            return
        audio_data, sample_rate = self.audio_player.get_audio_snapshot()
        if audio_data is None:
            QMessageBox.critical(
                self,
                tr("dlg_error_title"),
                tr("dlg_err_export_mp3", err="No audio loaded"),
            )
            return
        try:
            export_segment_mp3(
                audio_data,
                sample_rate,
                segment.start_sec,
                segment.end_sec,
                Path(filename),
            )
            QMessageBox.information(
                self,
                tr("dlg_exported_title"),
                tr("dlg_wav_exported", name=segment.name, path=filename),
            )
            self.lbl_status.setText(tr("status_mp3_exported", name=segment.name))
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("dlg_error_title"),
                tr("dlg_err_export_mp3", err=exc),
            )

    def on_export_config(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_export_config_title"),
            "",
            tr("filter_bop"),
        )
        if not filename:
            return
        try:
            export_data = {
                "audio_file": str(self.current_audio_path) if self.current_audio_path else None,
                "segments": self.segment_manager.to_dict()["segments"],
                "settings": {
                    "volume": self.audio_player.get_volume(),
                    "tempo": self.audio_player.get_tempo(),
                },
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(
                self, tr("dlg_exported_title"), tr("dlg_config_saved", path=filename)
            )
            self.lbl_status.setText(tr("status_config_exported", path=filename))
        except Exception as exc:
            QMessageBox.critical(self, tr("dlg_error_title"), tr("dlg_err_export_config", err=exc))

    def on_import_config(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg_import_config_title"),
            "",
            tr("filter_bop"),
        )
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8") as f:
                import_data = json.load(f)
            self.segment_manager = SegmentManager.from_dict(
                {"segments": import_data.get("segments", [])}
            )
            self.segment_list_widget.set_segment_manager(self.segment_manager)
            settings = import_data.get("settings", {})
            if "volume" in settings:
                self.slider_volume.setValue(int(settings["volume"]))
            if "tempo" in settings:
                self.slider_tempo.setValue(int(settings["tempo"] * 100))
            QMessageBox.information(
                self, tr("dlg_imported_title"), tr("dlg_config_loaded", path=filename)
            )
            self.lbl_status.setText(
                tr("status_config_imported", count=len(self.segment_manager.list_segments()))
            )
        except Exception as exc:
            QMessageBox.critical(self, tr("dlg_error_title"), tr("dlg_err_import_config", err=exc))

    def on_export_segments_csv(self) -> None:
        """Export segments to a CSV file."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("dlg_export_csv_title"),
            "",
            tr("filter_csv"),
        )
        if not filename:
            return
        output_path = Path(filename)
        fmt = "txt" if output_path.suffix.lower() == ".txt" else "csv"
        try:
            export_segments_text(self.current_audio_path, self.segment_manager, output_path, fmt)
            QMessageBox.information(
                self, tr("dlg_exported_title"), tr("dlg_segments_exported", path=filename)
            )
            self.lbl_status.setText(tr("status_segments_exported", path=filename))
        except Exception as exc:
            QMessageBox.critical(
                self, tr("dlg_error_title"), tr("dlg_err_export_segments", err=exc)
            )

    def on_open_settings(self) -> None:
        """Open the Preferences dialog."""
        dlg = SettingsDialog(self.settings, parent=self)
        if dlg.exec():
            save_settings(self.settings)
            self._apply_theme()
            self._configure_shortcuts()
            # Apply pitch-preserving setting and sync the main-window checkbox.
            pp = bool(self.settings.get("pitch_preserving", False))
            self.audio_player.set_pitch_preserving(pp)
            self.chk_pitch_preserving.blockSignals(True)
            self.chk_pitch_preserving.setChecked(pp)
            self.chk_pitch_preserving.blockSignals(False)

    def _on_open_history(self) -> None:
        """Open the practice history dialog (Ctrl+H)."""
        dlg = HistoryDialog(self._practice_history, parent=self)
        dlg.exec()

    def _on_set_language(self, lang: str) -> None:
        """Switch the application language and retranslate the UI."""
        set_language(lang)
        self.settings["language"] = lang
        save_settings(self.settings)

        # Rebuild menu bar so all menu item labels are in the new language.
        self.menuBar().clear()
        self._build_menu_bar()
        # Re-apply shortcuts to the freshly created menu QActions.
        self._configure_shortcuts()

        # Retranslate this window and its children
        self.retranslate_ui()
        self.segment_list_widget.retranslate_ui()
        self.practice_panel.retranslate_ui()

    # ================================================================== #
    # Position update and A–B loop logic
    # ================================================================== #
    def _update_position(self) -> None:
        """
        Periodic callback (100 ms): update UI and apply A–B loop logic.
        """
        current_pos = self.audio_player.get_position()
        duration = self.audio_player.get_duration()

        if duration > 0:
            self.slider_position.setRange(0, int(duration))
        else:
            duration = 0.0

        self.slider_position.blockSignals(True)
        self.slider_position.setValue(int(current_pos))
        self.slider_position.blockSignals(False)

        # Format the time label as mm:ss / mm:ss (human-readable).
        time_text = f"{self._format_time(current_pos)} / {self._format_time(duration)}"
        self.lbl_time.setText(time_text)

        # ── Slider accessibility ───────────────────────────────────────────
        # Qt announces the raw integer value (e.g. "50") by default.
        # Override with a formatted time string so screen readers say
        # "0 minute 50 secondes" instead of an opaque number.
        pos_str = self._format_time(current_pos)
        dur_str = self._format_time(duration)
        accessible_value = f"{pos_str} sur {dur_str}"
        self.slider_position.setToolTip(accessible_value)
        # Keep the custom accessible value in sync during playback so AT
        # reads the current time if the user focuses the slider mid-play.
        self.slider_position.setProperty("formattedTime", accessible_value)
        self.slider_position.setAccessibleName(f"Position {accessible_value}")

        # Sync play/pause button with actual player state (e.g. natural end of track).
        actual_playing = self.audio_player.is_playing()
        if self._playing != actual_playing:
            self._playing = actual_playing
            self._update_play_pause_button()

        # Waveform playhead
        self.waveform_widget.set_position(current_pos)

        # Periodic position announcement for screen readers (status label).
        interval = int(self.settings.get("position_announce_interval", 5))
        now = time.monotonic()
        if interval > 0 and (now - self._last_announce_time) >= interval:
            self._last_announce_time = now
            self.lbl_time.setAccessibleDescription(f"Position actuelle : {pos_str} sur {dur_str}")

        # A–B loop logic
        if (
            self.loop_enabled
            and self.point_a is not None
            and self.point_b is not None
            and self.point_b > self.point_a
        ):
            if current_pos > self.point_b and not self.already_looped:
                self.already_looped = True
                self._handle_loop_end()
            elif current_pos <= self.point_b:
                self.already_looped = False

    def _handle_loop_end(self) -> None:
        """
        Called once each time the playhead passes point B.

        Handles loop count limit, progressive tempo, and loop delay.
        """
        session = self.practice_panel.get_active_session()
        if session is not None:
            self._session_loop_count += 1
            should_stop, new_tempo = session.on_loop_completed()
            self._session_tempo_sum += new_tempo

            if should_stop:
                self.audio_player.stop()
                self._save_practice_history()
                self.practice_panel.stop_session()
                self.lbl_status.setText(tr("status_session_done", count=self._session_loop_count))
                return

            # Apply progressive tempo
            self.slider_tempo.setValue(int(new_tempo * 100))

        # Loop with optional delay
        delay_ms = int(session.loop_delay * 1000) if session else 0
        if delay_ms > 0:
            QTimer.singleShot(delay_ms, self._do_loop_jump)
        else:
            self._do_loop_jump()

    def _do_loop_jump(self) -> None:
        """Perform the actual jump back to point A."""
        if self.point_a is not None:
            self.audio_player.set_position(self.point_a)
            self.audio_player.play()

    # ================================================================== #
    # Theme
    # ================================================================== #
    def _apply_theme(self) -> None:
        """Apply the Qt stylesheet for the current theme setting."""
        theme = self.settings.get("theme", "default")
        stylesheet = _THEMES.get(theme, "")
        self.setStyleSheet(stylesheet)

    # ================================================================== #
    # Practice history
    # ================================================================== #
    def _save_practice_history(self) -> None:
        """Persist the current session to the practice history log."""
        session = self.practice_panel.get_active_session()
        loops = self._session_loop_count
        if loops == 0 or self.current_audio_path is None:
            return
        avg_tempo = self._session_tempo_sum / loops if loops > 0 else 1.0
        elapsed_str = session.get_elapsed() if session else "00:00:00"
        parts = elapsed_str.split(":")
        try:
            total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except Exception:
            total_sec = 0
        entry = PracticeHistory.make_entry(
            audio_file=str(self.current_audio_path),
            duration_seconds=float(total_sec),
            loops_completed=loops,
            avg_tempo=avg_tempo,
        )
        self._practice_history.add_session(entry)
        self._session_loop_count = 0
        self._session_tempo_sum = 0.0

    # ================================================================== #
    # Update checker
    # ================================================================== #
    def _check_updates_worker(self) -> None:
        """Synchronous update check — runs in a background thread."""
        import urllib.request as _urlreq

        _URL = "https://api.github.com/repos/aminekhettat/Back-Office-Player/releases/latest"
        try:
            req = _urlreq.Request(_URL, headers={"User-Agent": "BOP-update-checker/1.0"})
            with _urlreq.urlopen(req, timeout=5) as resp:  # nosec B310
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "")
            if latest and latest != _CURRENT_VERSION:
                QTimer.singleShot(
                    0,
                    lambda: self.lbl_status.setText(tr("status_update", version=latest)),
                )
        except Exception as exc:
            _logger.debug("Update check failed: %s", exc)

    def _start_update_check(self) -> None:
        """Lance la vérification des mises à jour en arrière-plan."""
        import threading as _threading

        t = _threading.Thread(target=self._check_updates_worker, daemon=True)
        t.start()

    # ================================================================== #
    # Drag & drop
    # ================================================================== #
    def dragEnterEvent(self, event) -> None:
        """
        Accept drag events that carry at least one local audio file.

        Accepted MIME types: ``text/uri-list``.  Only events containing
        a file with a recognised audio extension are accepted.
        """
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    suffix = Path(url.toLocalFile()).suffix.lower()
                    if suffix in {
                        ".mp3",
                        ".wav",
                        ".flac",
                        ".ogg",
                        ".aac",
                        ".m4a",
                        ".wma",
                        ".opus",
                        ".aiff",
                    }:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event) -> None:
        """Load the first dropped audio file."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    suffix = path.suffix.lower()
                    if suffix in {
                        ".mp3",
                        ".wav",
                        ".flac",
                        ".ogg",
                        ".aac",
                        ".m4a",
                        ".wma",
                        ".opus",
                        ".aiff",
                    }:
                        self._load_audio_file(path)
                        event.acceptProposedAction()
                        return
        event.ignore()

    # ================================================================== #
    # Helpers
    # ================================================================== #
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format *seconds* as ``hh:mm:ss`` (or ``mm:ss`` when under one hour)."""
        if seconds < 0:
            seconds = 0.0
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

"""
Qt main window module for Back-Office Player.

This module defines the :class:`MainWindowQt` class, which implements the
main application window using PySide6 (Qt for Python).

Responsibilities
----------------
- Build widgets (buttons, labels, sliders, etc.).
- Handle user interactions (clicks, keyboard shortcuts).
- Coordinate the audio logic (:class:`AudioPlayer`).
- Load and save user settings.
- Provide basic A–B loop practice (select a part and loop it).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:c   opyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.4.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QFileDialog,
    QMessageBox,
    QCheckBox,
)

from core.audio_player import AudioPlayer
from core.segment_manager import SegmentManager
from infra.settings import load_settings, save_settings
from infra.persistence import load_segments


class MainWindowQt(QMainWindow):
    """
    Qt main window for Back-Office Player.

    The goal is to provide an accessible UI (screen reader + keyboard)
    while reusing the existing core and infra modules.
    """

    def __init__(self, audio_player: AudioPlayer, segment_manager: SegmentManager) -> None:
        """
        Initialize the main Qt window.

        Parameters
        ----------
        audio_player : AudioPlayer
            Audio player used to play files.
        segment_manager : SegmentManager
            Segment manager (initially empty at startup).
        """
        super().__init__()

        # Core / infra objects.
        self.audio_player = audio_player
        self.segment_manager = segment_manager
        self.settings = load_settings()

        # Path to the currently loaded audio file (None if no file).
        self.current_audio_path: Optional[Path] = None

        # A–B loop internal state.
        self.point_a: Optional[float] = None
        self.point_b: Optional[float] = None
        self.loop_enabled: bool = False

        # Build the user interface and timers.
        self._build_ui()
        self._configure_shortcuts()
        self._configure_timer()

        # Apply initial volume from settings.
        initial_volume = int(self.settings.get("default_volume", 80))
        self.slider_volume.setValue(initial_volume)
        self.audio_player.set_volume(initial_volume)

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        """
        Build the main Qt widgets and layout.

        Layout
        ------
        - Row 0: audio file selection.
        - Row 1: playback controls + volume.
        - Row 2: position slider + time display.
        - Row 3: A/B loop controls.
        - Row 4: status text area.
        """
        # Window title and icon.
        self.setWindowTitle("Back-Office Player (BOP)")
        self.setWindowIcon(QIcon("resources/BOP.ico"))

        # Central widget and main layout.
        central = QWidget()
        main_layout = QVBoxLayout(central)

        # ---------------- Row 0: file selection ------------------------- #
        file_layout = QHBoxLayout()

        self.btn_open = QPushButton("Open audio file...")
        self.btn_open.setAccessibleName("Open audio file")
        self.btn_open.setAccessibleDescription(
            "Open an audio file for playback and practice."
        )
        self.btn_open.clicked.connect(self.on_open_file)

        self.lbl_file = QLabel("No file.")
        self.lbl_file.setAccessibleName("Current file name")

        file_layout.addWidget(self.btn_open)
        file_layout.addWidget(self.lbl_file)

        # ---------------- Row 1: playback controls + volume ------------- #
        controls_layout = QHBoxLayout()

        self.btn_play = QPushButton("Play")
        self.btn_play.setAccessibleName("Play")
        self.btn_play.clicked.connect(self.on_play)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setAccessibleName("Pause")
        self.btn_pause.clicked.connect(self.on_pause)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setAccessibleName("Stop")
        self.btn_stop.clicked.connect(self.on_stop)

        lbl_volume = QLabel("Volume:")
        lbl_volume.setAccessibleName("Volume label")

        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setAccessibleName("Volume slider")
        self.slider_volume.valueChanged.connect(self.on_volume_change)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_pause)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addWidget(lbl_volume)
        controls_layout.addWidget(self.slider_volume)

        # ---------------- Row 2: position + time ------------------------ #
        position_layout = QHBoxLayout()

        lbl_position = QLabel("Position (seconds):")
        lbl_position.setAccessibleName("Position label")

        self.slider_position = QSlider(Qt.Horizontal)
        self.slider_position.setRange(0, 0)  # Duration unknown at startup.
        self.slider_position.setAccessibleName("Position slider")
        # Step of 1 second per arrow key.
        self.slider_position.setSingleStep(1)
        # IMPORTANT: use valueChanged so that keyboard arrows also trigger seeking.
        self.slider_position.valueChanged.connect(self.on_seek)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setAccessibleName("Time display")

        position_layout.addWidget(lbl_position)
        position_layout.addWidget(self.slider_position)
        position_layout.addWidget(self.lbl_time)

        # ---------------- Row 3: A–B loop controls ---------------------- #
        loop_layout = QHBoxLayout()

        self.btn_set_a = QPushButton("Set A")
        self.btn_set_a.setAccessibleName("Set point A")
        self.btn_set_a.setAccessibleDescription(
            "Set point A (start of the loop) at the current playback position."
        )
        self.btn_set_a.clicked.connect(self.on_set_point_a)

        self.btn_set_b = QPushButton("Set B")
        self.btn_set_b.setAccessibleName("Set point B")
        self.btn_set_b.setAccessibleDescription(
            "Set point B (end of the loop) at the current playback position."
        )
        self.btn_set_b.clicked.connect(self.on_set_point_b)

        self.btn_clear_ab = QPushButton("Clear A/B")
        self.btn_clear_ab.setAccessibleName("Clear A and B")
        self.btn_clear_ab.setAccessibleDescription(
            "Clear loop points A and B and disable the A–B loop."
        )
        self.btn_clear_ab.clicked.connect(self.on_clear_points)

        self.chk_loop = QCheckBox("Loop A–B")
        self.chk_loop.setAccessibleName("Loop A-B checkbox")
        self.chk_loop.setAccessibleDescription(
            "Enable or disable looping between points A and B."
        )
        self.chk_loop.stateChanged.connect(self.on_loop_state_changed)

        loop_layout.addWidget(self.btn_set_a)
        loop_layout.addWidget(self.btn_set_b)
        loop_layout.addWidget(self.btn_clear_ab)
        loop_layout.addWidget(self.chk_loop)

        # ---------------- Row 4: status label --------------------------- #
        self.lbl_status = QLabel("No file loaded.")
        self.lbl_status.setAccessibleName("Status message")

        # Assemble main layout.
        main_layout.addLayout(file_layout)
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(position_layout)
        main_layout.addLayout(loop_layout)
        main_layout.addWidget(self.lbl_status)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------ #
    # Keyboard shortcuts
    # ------------------------------------------------------------------ #
    def _configure_shortcuts(self) -> None:
        """
        Configure keyboard shortcuts for the application.

        Shortcuts configured
        --------------------
        - Ctrl+O: open an audio file.
        - Ctrl+P: play (or restart) playback.
        - Ctrl+Shift+P: pause playback.
        - Ctrl+S: stop playback.
        - Ctrl+Shift+A: set point A at the current position.
        - Ctrl+Shift+B: set point B at the current position.

        Notes
        -----
        There is intentionally no global shortcut on the space bar, so that
        Space/Enter keep activating the focused button (standard behavior).
        """
        # Ctrl+O -> Open audio file.
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self.on_open_file)

        # Ctrl+P -> Play.
        shortcut_play = QShortcut(QKeySequence("Ctrl+P"), self)
        shortcut_play.activated.connect(self.on_play)

        # Ctrl+Shift+P -> Pause.
        shortcut_pause = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        shortcut_pause.activated.connect(self.on_pause)

        # Ctrl+S -> Stop.
        shortcut_stop = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_stop.activated.connect(self.on_stop)

        # Ctrl+Shift+A -> Set point A.
        shortcut_set_a = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        shortcut_set_a.activated.connect(self.on_set_point_a)

        # Ctrl+Shift+B -> Set point B.
        shortcut_set_b = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
        shortcut_set_b.activated.connect(self.on_set_point_b)

    # ------------------------------------------------------------------ #
    # Timer to update position and A–B loop logic
    # ------------------------------------------------------------------ #
    def _configure_timer(self) -> None:
        """
        Configure the periodic timer used to update the position slider
        and apply A–B loop logic.
        """
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # milliseconds
        self.timer.timeout.connect(self._update_position)
        self.timer.start()

    # ------------------------------------------------------------------ #
    # Slots / callbacks
    # ------------------------------------------------------------------ #
    def on_open_file(self) -> None:
        """
        Open a file dialog to select an audio file.

        If a file is selected:
        - Load it into the :class:`AudioPlayer`.
        - Update the file label.
        - Load associated segments for that file.
        - Save the folder path into settings.
        """
        initial_dir = self.settings.get("last_opened_folder", str(Path.cwd()))

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an audio file",
            initial_dir,
            "Audio files (*.mp3 *.wav *.wma *.flac *.ogg);;All files (*.*)",
        )

        if not filename:
            return

        path = Path(filename)

        try:
            self.audio_player.load_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not load file: {exc}")
            return

        self.current_audio_path = path
        self.lbl_file.setText(path.name)
        self.lbl_status.setText(f"Loaded file: {path.name}")

        # Reset A/B points when a new file is loaded.
        self.on_clear_points(update_status=False)

        # Load segments associated with this file (for future features).
        self.segment_manager = load_segments(path)

        # Remember this folder for future opens.
        self.settings["last_opened_folder"] = str(path.parent)
        save_settings(self.settings)

    def on_play(self) -> None:
        """
        Start or resume playback and update the status text.
        """
        self.audio_player.play()
        self.lbl_status.setText("Playing.")

    def on_pause(self) -> None:
        """
        Pause playback and update the status text.
        """
        self.audio_player.pause()
        self.lbl_status.setText("Paused.")

    def on_stop(self) -> None:
        """
        Stop playback and update the status text.
        """
        self.audio_player.stop()
        self.lbl_status.setText("Stopped.")

    def on_volume_change(self, value: int) -> None:
        """
        Callback triggered when the user moves the volume slider.

        Parameters
        ----------
        value : int
            Slider value (0–100).
        """
        volume = int(value)
        self.audio_player.set_volume(volume)

        # Save this volume into settings.
        self.settings["default_volume"] = volume
        save_settings(self.settings)

    def on_seek(self, value: int) -> None:
        """
        Callback when the user changes the position slider.

        Parameters
        ----------
        value : int
            New slider value (position in seconds).

        Notes
        -----
        Because this method is connected to ``valueChanged``, it is called
        both when the user drags the slider with the mouse, and when they
        use the left/right arrow keys while the slider has focus.
        """
        seconds = float(value)
        self.audio_player.set_position(seconds)

    def on_set_point_a(self) -> None:
        """
        Set point A at the current playback position.
        """
        current_pos = self.audio_player.get_position()
        self.point_a = current_pos
        self.lbl_status.setText(
            f"Point A set at {self._format_time(current_pos)}."
        )

    def on_set_point_b(self) -> None:
        """
        Set point B at the current playback position.
        """
        current_pos = self.audio_player.get_position()
        self.point_b = current_pos
        self.lbl_status.setText(
            f"Point B set at {self._format_time(current_pos)}."
        )

    def on_clear_points(self, update_status: bool = True) -> None:
        """
        Clear points A and B and disable the loop.

        Parameters
        ----------
        update_status : bool, optional
            If True, update the status text. Default is True.
        """
        self.point_a = None
        self.point_b = None
        self.loop_enabled = False
        self.chk_loop.setChecked(False)

        if update_status:
            self.lbl_status.setText("Points A and B cleared, loop disabled.")

    def on_loop_state_changed(self, state: int) -> None:
        """
        Callback when the A–B loop checkbox is toggled.

        Parameters
        ----------
        state : int
            Qt check state (0 unchecked, 2 checked).
        """
        self.loop_enabled = state != 0

    # ------------------------------------------------------------------ #
    # Position update and A–B loop logic
    # ------------------------------------------------------------------ #
    def _update_position(self) -> None:
        """
        Update the position slider and time label, and apply A–B loop.

        This method is called periodically by the internal timer.
        """
        current_pos = self.audio_player.get_position()
        duration = self.audio_player.get_duration()

        # Update the slider range if duration is known.
        if duration > 0:
            self.slider_position.setRange(0, int(duration))
        else:
            duration = 0.0

        # Update slider value without triggering on_seek.
        self.slider_position.blockSignals(True)
        self.slider_position.setValue(int(current_pos))
        self.slider_position.blockSignals(False)

        # Update time label "mm:ss / mm:ss".
        self.lbl_time.setText(
            f"{self._format_time(current_pos)} / {self._format_time(duration)}"
        )

        # Apply A–B loop logic if enabled.
        if (
            self.loop_enabled
            and self.point_a is not None
            and self.point_b is not None
            and self.point_b > self.point_a
        ):
            if current_pos > self.point_b:
                # Jump back to point A and continue playback.
                self.audio_player.set_position(self.point_a)
                self.audio_player.play()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Format a time in seconds as ``mm:ss``.

        Parameters
        ----------
        seconds : float
            Time in seconds.

        Returns
        -------
        str
            Formatted string in ``mm:ss`` format.
        """
        if seconds < 0:
            seconds = 0.0
        total_seconds = int(seconds)
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"

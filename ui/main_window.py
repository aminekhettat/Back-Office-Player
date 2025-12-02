"""
Main window module.

This module defines the :class:`MainWindow` class, which implements the
main application window using Tkinter.

Responsibilities
----------------
- Build widgets (buttons, labels, sliders, etc.).
- Handle user interactions (clicks, keyboard shortcuts).
- Coordinate the audio logic (:class:`AudioPlayer`).
- Load and save user settings.
- Provide basic A–B loop practice (select a part and loop it).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.2.0
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

from core.audio_player import AudioPlayer
from core.segment_manager import SegmentManager
from infra.persistence import load_segments, save_segments
from infra.settings import load_settings, save_settings


class MainWindow:
    """
    Main window of the audio practice application.

    This class orchestrates:

    - The Tkinter UI (widgets, bindings, messages).
    - The audio player (:class:`AudioPlayer`).
    - The segment manager (:class:`SegmentManager`).
    - The user settings (folder, volume, etc.).
    - A simple A–B loop mechanism for practice.
    """

    def __init__(
        self,
        root: tk.Tk,
        audio_player: AudioPlayer,
        segment_manager: SegmentManager,
    ) -> None:
        """
        Initialize the main window.

        Parameters
        ----------
        root : tk.Tk
            Root Tkinter instance.
        audio_player : AudioPlayer
            Audio player used to play files.
        segment_manager : SegmentManager
            Segment manager (initially empty at startup).
        """
        # Root Tkinter window.
        self.root = root

        # Audio player (core logic).
        self.audio_player = audio_player

        # Segment manager (will be used in later steps for named segments).
        self.segment_manager = segment_manager

        # Load user settings (volume, last folder, etc.).
        self.settings = load_settings()

        # Path to the currently loaded audio file (None if no file).
        self.current_audio_path: Optional[Path] = None

        # ---------------- Tk variables for UI bindings ------------------- #
        # Status text displayed at the bottom of the window.
        self.var_status = tk.StringVar(value="No file loaded.")
        # Audio volume (0-100), initialized from settings.
        self.var_volume = tk.IntVar(value=self.settings.get("default_volume", 80))
        # Playback position in seconds (used by the position slider).
        self.var_position = tk.DoubleVar(value=0.0)
        # Loop enabled flag (for A–B loop).
        self.var_loop_enabled = tk.BooleanVar(value=False)

        # ---------------- A–B loop internal state ------------------------ #
        # Point A (in seconds), or None if not set.
        self.point_a: Optional[float] = None
        # Point B (in seconds), or None if not set.
        self.point_b: Optional[float] = None

        # Flag used to prevent recursion when updating the position slider.
        self._updating_slider: bool = False

        # ---------------- Build UI and configure bindings ---------------- #
        self._create_widgets()
        self._configure_bindings()

        # Apply initial volume to the audio player.
        self.audio_player.set_volume(self.var_volume.get())

        # Start periodic update of position and A–B loop handling.
        self._start_position_timer()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _create_widgets(self) -> None:
        """
        Create and place the Tkinter widgets for the main window.

        Layout
        ------
        - Row 0: audio file selection.
        - Row 1: playback controls + volume.
        - Row 2: position slider + time display + A/B loop buttons.
        - Row 3: status text area.
        """
        # Main frame containing all widgets.
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Let the main frame expand with the window.
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---------------- Row 0: file selection ------------------------- #
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Button to open an audio file.
        btn_open = ttk.Button(
            file_frame,
            text="Open audio file...",
            command=self.on_open_file,
        )
        btn_open.grid(row=0, column=0, sticky="w")

        # Label showing the loaded file name.
        self.lbl_file = ttk.Label(file_frame, text="No file.")
        self.lbl_file.grid(row=0, column=1, sticky="w", padx=(10, 0))

        # ---------------- Row 1: playback controls ---------------------- #
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Play / Pause / Stop buttons with explicit text.
        btn_play = ttk.Button(controls_frame, text="Play", command=self.on_play)
        btn_pause = ttk.Button(controls_frame, text="Pause", command=self.on_pause)
        btn_stop = ttk.Button(controls_frame, text="Stop", command=self.on_stop)

        btn_play.grid(row=0, column=0, padx=5)
        btn_pause.grid(row=0, column=1, padx=5)
        btn_stop.grid(row=0, column=2, padx=5)

        # Volume label.
        ttk.Label(controls_frame, text="Volume:").grid(
            row=0,
            column=3,
            padx=(20, 5),
        )

        # Volume slider (0 to 100), bound to self.var_volume.
        volume_scale = ttk.Scale(
            controls_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.var_volume,
            command=self.on_volume_change,
        )
        volume_scale.grid(row=0, column=4, sticky="ew")

        # Allow the volume slider column to expand horizontally.
        controls_frame.columnconfigure(4, weight=1)

        # ---------------- Row 2: position + A/B loop -------------------- #
        position_frame = ttk.Frame(main_frame)
        position_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Position label.
        ttk.Label(position_frame, text="Position (seconds):").grid(
            row=0,
            column=0,
            sticky="w",
        )

        # Position slider. Range will be updated dynamically based on duration.
        self.scale_position = ttk.Scale(
            position_frame,
            from_=0.0,
            to=0.0,
            orient="horizontal",
            variable=self.var_position,
            command=self.on_seek,
        )
        self.scale_position.grid(row=0, column=1, sticky="ew", padx=(5, 5))

        # Time label "current / total".
        self.lbl_time = ttk.Label(position_frame, text="00:00 / 00:00")
        self.lbl_time.grid(row=0, column=2, sticky="e")

        # Second row: A/B loop buttons and status.
        btn_set_a = ttk.Button(
            position_frame,
            text="Set A",
            command=self.on_set_point_a,
        )
        btn_set_b = ttk.Button(
            position_frame,
            text="Set B",
            command=self.on_set_point_b,
        )
        btn_clear_ab = ttk.Button(
            position_frame,
            text="Clear A/B",
            command=self.on_clear_points,
        )
        chk_loop = ttk.Checkbutton(
            position_frame,
            text="Loop A–B",
            variable=self.var_loop_enabled,
        )

        btn_set_a.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky="w")
        btn_set_b.grid(row=1, column=1, padx=(0, 5), pady=(5, 0), sticky="w")
        btn_clear_ab.grid(row=1, column=2, padx=(0, 5), pady=(5, 0), sticky="e")
        chk_loop.grid(row=1, column=3, padx=(5, 0), pady=(5, 0), sticky="e")

        # Column weights for position frame.
        position_frame.columnconfigure(0, weight=0)
        position_frame.columnconfigure(1, weight=1)
        position_frame.columnconfigure(2, weight=0)
        position_frame.columnconfigure(3, weight=0)

        # ---------------- Row 3: status area ---------------------------- #
        status_label = ttk.Label(main_frame, textvariable=self.var_status, anchor="w")
        status_label.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Allow main_frame columns to expand.
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ #
    # Keyboard shortcuts
    # ------------------------------------------------------------------ #
    def _configure_bindings(self) -> None:
        """
        Configure the main keyboard shortcuts for the application.

        Shortcuts configured so far
        ---------------------------
        - Space: start playback (later it can become a play/pause toggle).
        - Ctrl+O: open an audio file.
        - Ctrl+Shift+A: set point A at current position.
        - Ctrl+Shift+B: set point B at current position.
        """
        # Space bar: start playback (for now).
        self.root.bind("<space>", self._on_space)

        # Ctrl+O: open audio file.
        self.root.bind("<Control-o>", self._on_ctrl_o)

        # Ctrl+Shift+A: set point A.
        self.root.bind("<Control-Shift-A>", self._on_ctrl_shift_a)

        # Ctrl+Shift+B: set point B.
        self.root.bind("<Control-Shift-B>", self._on_ctrl_shift_b)

    # ------------------------------------------------------------------ #
    # UI callbacks (buttons)
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
        # Initial directory: last opened folder or current working directory.
        initial_dir = self.settings.get("last_opened_folder") or str(Path.cwd())

        # File filters for common audio formats.
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.wma *.flac *.ogg"),
            ("All files", "*.*"),
        ]

        filename = filedialog.askopenfilename(
            title="Choose an audio file",
            initialdir=initial_dir,
            filetypes=filetypes,
        )

        # If the user cancels, `filename` is an empty string.
        if not filename:
            return

        path = Path(filename)

        try:
            # Load file into the audio player.
            self.audio_player.load_file(path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load file: {exc}")
            return

        # Update current path and label.
        self.current_audio_path = path
        self.lbl_file.config(text=str(path.name))
        self.var_status.set(f"Loaded file: {path.name}")

        # Reset A/B points when a new file is loaded.
        self.on_clear_points(update_status=False)

        # Load segments associated with this file (for future use).
        self.segment_manager = load_segments(path)

        # Remember this folder for future opens.
        self.settings["last_opened_folder"] = str(path.parent)
        save_settings(self.settings)

    def on_play(self) -> None:
        """
        Callback for the "Play" button.

        Starts or resumes playback and updates the status text.
        """
        self.audio_player.play()
        self.var_status.set("Playing.")

    def on_pause(self) -> None:
        """
        Callback for the "Pause" button.

        Pauses playback and updates the status text.
        """
        self.audio_player.pause()
        self.var_status.set("Paused.")

    def on_stop(self) -> None:
        """
        Callback for the "Stop" button.

        Stops playback and updates the status text and position.
        """
        self.audio_player.stop()
        self.var_status.set("Stopped.")

    def on_volume_change(self, value: str) -> None:
        """
        Callback triggered when the user moves the volume slider.

        Parameters
        ----------
        value : str
            Slider value as a string (as provided by Tkinter).
        """
        try:
            # Convert the string value provided by Tkinter (str -> float -> int).
            vol = int(float(value))
        except ValueError:
            # If conversion fails, fall back to the current IntVar value.
            vol = self.var_volume.get()

        # Apply volume to the audio player.
        self.audio_player.set_volume(vol)

        # Save this volume into settings.
        self.settings["default_volume"] = vol
        save_settings(self.settings)

    def on_seek(self, value: str) -> None:
        """
        Callback when the user moves the position slider.

        Parameters
        ----------
        value : str
            New slider value (position in seconds), as provided by Tkinter.
        """
        if self._updating_slider:
            # Ignore updates triggered by the timer.
            return

        try:
            seconds = float(value)
        except ValueError:
            return

        # Set playback position in the audio player.
        self.audio_player.set_position(seconds)

    def on_set_point_a(self) -> None:
        """
        Set point A at the current playback position.
        """
        current_pos = self.audio_player.get_position()
        self.point_a = current_pos
        self.var_status.set(f"Point A set at {self._format_time(current_pos)}.")

    def on_set_point_b(self) -> None:
        """
        Set point B at the current playback position.
        """
        current_pos = self.audio_player.get_position()
        self.point_b = current_pos
        self.var_status.set(f"Point B set at {self._format_time(current_pos)}.")

    def on_clear_points(self, update_status: bool = True) -> None:
        """
        Clear points A and B and disable loop.

        Parameters
        ----------
        update_status : bool, optional
            If True, update the status text. Default is True.
        """
        self.point_a = None
        self.point_b = None
        self.var_loop_enabled.set(False)
        if update_status:
            self.var_status.set("Points A and B cleared, loop disabled.")

    # ------------------------------------------------------------------ #
    # Keyboard event handlers
    # ------------------------------------------------------------------ #
    def _on_space(self, event: tk.Event) -> None:
        """
        Handle the space bar key press.

        Parameters
        ----------
        event : tk.Event
            Keyboard event provided by Tkinter.

        Notes
        -----
        For now, this simply calls :meth:`AudioPlayer.play`.
        Later, it can be improved to toggle between play and pause.
        """
        self.audio_player.play()
        self.var_status.set("Playing (via space bar).")

    def _on_ctrl_o(self, event: tk.Event) -> None:
        """
        Handle the Ctrl+O keyboard shortcut to open a file.

        Parameters
        ----------
        event : tk.Event
            Keyboard event provided by Tkinter.
        """
        self.on_open_file()

    def _on_ctrl_shift_a(self, event: tk.Event) -> None:
        """
        Handle the Ctrl+Shift+A keyboard shortcut to set point A.

        Parameters
        ----------
        event : tk.Event
            Keyboard event provided by Tkinter.
        """
        self.on_set_point_a()

    def _on_ctrl_shift_b(self, event: tk.Event) -> None:
        """
        Handle the Ctrl+Shift+B keyboard shortcut to set point B.

        Parameters
        ----------
        event : tk.Event
            Keyboard event provided by Tkinter.
        """
        self.on_set_point_b()

    # ------------------------------------------------------------------ #
    # Position timer and A–B loop logic
    # ------------------------------------------------------------------ #
    def _start_position_timer(self) -> None:
        """
        Start the periodic timer used to update the position slider
        and apply A–B loop logic.

        The timer uses :meth:`tk.Tk.after` with a delay of 100 ms.
        """
        self._update_position()
        # Schedule next update in 100 ms.
        self.root.after(100, self._start_position_timer)

    def _update_position(self) -> None:
        """
        Update the position slider and time label, and apply A–B loop.

        This method is called periodically by the internal timer.
        """
        # Get current position and duration from the audio player.
        current_pos = self.audio_player.get_position()
        duration = self.audio_player.get_duration()

        # Update the scale range if duration is known.
        if duration > 0:
            self.scale_position.configure(to=duration)
        else:
            duration = 0.0

        # Update slider without triggering on_seek.
        self._updating_slider = True
        try:
            self.var_position.set(current_pos)
        finally:
            self._updating_slider = False

        # Update time label "mm:ss / mm:ss".
        self.lbl_time.config(
            text=f"{self._format_time(current_pos)} / {self._format_time(duration)}"
        )

        # Apply A–B loop logic if enabled.
        if (
            self.var_loop_enabled.get()
            and self.point_a is not None
            and self.point_b is not None
            and self.point_b > self.point_a
        ):
            # If we are beyond point B, jump back to A.
            if current_pos > self.point_b:
                self.audio_player.set_position(self.point_a)
                self.audio_player.play()

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

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        """
        Start the Tkinter main event loop.

        This method must be called once, usually from the application
        entry point.
        """
        self.root.mainloop()

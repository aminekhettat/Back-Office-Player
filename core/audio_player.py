"""
Audio player module.

This module defines the :class:`AudioPlayer` class, which wraps VLC
(via the ``python-vlc`` package) to play audio files, manage position,
duration, and volume.

The goal is to provide a simple API, independent from the UI layer,
so that the Tkinter interface can control audio playback without
knowing VLC internals.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import vlc  # Python bindings for the VLC media player


class AudioPlayer:
    """
    Audio player class using VLC.

    This class does not depend on Tkinter and can be tested separately
    from the UI.

    Attributes
    ----------
    _instance : vlc.Instance
        Global VLC instance.
    _player : vlc.MediaPlayer
        VLC media player associated with the current media.
    _media : Optional[vlc.Media]
        Currently loaded media, or ``None`` if no file is loaded.
    current_file_path : Optional[Path]
        Path to the currently loaded audio file, or ``None``.
    """

    def __init__(self) -> None:
        """
        Initialize the audio player.

        - Create a VLC instance.
        - Create a media player without media.
        """
        # Create VLC instance. Options could be passed here if needed.
        self._instance = vlc.Instance()

        # Create media player associated with this instance.
        self._player = self._instance.media_player_new()

        # Currently loaded media (None if nothing is loaded).
        self._media: Optional[vlc.Media] = None

        # Path to the current audio file (for information only).
        self.current_file_path: Optional[Path] = None

    # ------------------------------------------------------------------ #
    # File management
    # ------------------------------------------------------------------ #
    def load_file(self, path: str | Path) -> None:
        """
        Load an audio file.

        Parameters
        ----------
        path : str or Path
            Path to the audio file to load.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        """
        file_path = Path(path)

        # Check that the file exists.
        if not file_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Stop any current playback before loading a new media.
        self.stop()

        # Update the current path.
        self.current_file_path = file_path

        # Create VLC media from the file.
        self._media = self._instance.media_new(str(file_path))

        # Attach the media to the player.
        self._player.set_media(self._media)

    # ------------------------------------------------------------------ #
    # Playback controls
    # ------------------------------------------------------------------ #
    def play(self) -> None:
        """
        Start or resume playback of the current media.

        If no media is loaded, the method does nothing.
        """
        if self._media is None:
            return

        self._player.play()

    def pause(self) -> None:
        """
        Pause playback of the current media.

        If no media is loaded, the method does nothing.
        """
        if self._media is None:
            return

        self._player.pause()

    def stop(self) -> None:
        """
        Stop playback of the current media.

        If no media is loaded, the method does nothing.
        """
        if self._media is None:
            return

        self._player.stop()

    # ------------------------------------------------------------------ #
    # Position and duration
    # ------------------------------------------------------------------ #
    def set_position(self, seconds: float) -> None:
        """
        Set the playback position in seconds.

        Parameters
        ----------
        seconds : float
            Desired position in seconds.

        Notes
        -----
        VLC uses a normalized position between 0.0 and 1.0 internally.
        This method converts the position in seconds to a ratio based
        on the media duration.
        """
        if self._media is None:
            return

        duration = self.get_duration()
        if duration <= 0:
            return

        # Compute normalized position between 0.0 and 1.0.
        ratio = seconds / duration

        # Clamp the ratio to avoid out-of-range values.
        ratio = max(0.0, min(1.0, ratio))

        self._player.set_position(ratio)

    def get_position(self) -> float:
        """
        Return the current playback position in seconds.

        Returns
        -------
        float
            Current playback position in seconds, or ``0.0`` if the
            duration is unknown or no media is loaded.
        """
        if self._media is None:
            return 0.0

        duration = self.get_duration()
        if duration <= 0:
            return 0.0

        # Normalized position (between 0 and 1).
        pos = self._player.get_position()
        if pos < 0:
            # VLC may return -1.0 if the position is not known.
            pos = 0.0

        return duration * pos

    def get_duration(self) -> float:
        """
        Return the media duration in seconds.

        Returns
        -------
        float
            Duration of the media in seconds, or ``0.0`` if the duration
            is not available.

        Notes
        -----
        VLC only knows the duration after playback has started.
        This method may trigger a quick play/stop to force VLC
        to determine the duration.
        """
        if self._media is None:
            return 0.0

        # Duration in milliseconds.
        length_ms = self._player.get_length()

        # If duration is unknown, trigger a quick play/stop.
        if length_ms <= 0:
            self._player.play()
            self._player.stop()
            length_ms = self._player.get_length()

        if length_ms <= 0:
            return 0.0

        # Convert milliseconds to seconds.
        return length_ms / 1000.0

    # ------------------------------------------------------------------ #
    # Volume
    # ------------------------------------------------------------------ #
    def set_volume(self, volume: int) -> None:
        """
        Set the audio volume.

        Parameters
        ----------
        volume : int
            Desired volume between 0 (mute) and 100 (maximum).
        """
        # Clamp the volume value to the allowed range.
        v = max(0, min(100, volume))
        self._player.audio_set_volume(v)

    def get_volume(self) -> int:
        """
        Return the current audio volume.

        Returns
        -------
        int
            Current volume between 0 and 100.
        """
        return self._player.audio_get_volume()

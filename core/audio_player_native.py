"""
Native audio player module (without VLC dependency).

This module provides a cross-platform audio player using librosa for loading
and sounddevice for playback, with support for all audio formats via librosa.

Features:
- Support for MP3, WAV, FLAC, OGG, WMA via librosa
- Sample-accurate position tracking and seeking
- Volume control (applied per block, effective immediately)
- Tempo control (tape-style: speed and pitch change together; true
  pitch-preserving time-stretch is planned for a future release)

Requirements:
- librosa (loads audio, supports all formats)
- sounddevice (playback via PortAudio)
- numpy

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 1.1.0
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import numpy as np
import librosa
import sounddevice as sd


class AudioPlayer:
    """
    Native audio player using librosa + sounddevice.

    Position is tracked by sample index (``_current_sample_pos``) rather
    than wall-clock time, which gives exact seeking and correct A–B loop
    behaviour regardless of system load.

    Attributes
    ----------
    current_file_path : Optional[Path]
        Path to the currently loaded audio file, or ``None``.
    """

    _BLOCKSIZE = 2048  # Samples per write block (~46 ms at 44100 Hz)

    def __init__(self) -> None:
        """Initialize the native audio player."""
        # Audio data
        self._audio_data: Optional[np.ndarray] = None  # float32, mono, [-1, 1]
        self._sample_rate: int = 0
        self.current_file_path: Optional[Path] = None

        # Playback state
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._current_sample_pos: int = 0  # Ground-truth position in samples

        # Audio parameters
        self._duration: float = 0.0
        self._volume: int = 80   # 0-100
        self._tempo: float = 1.0  # 0.5-2.0

        # Playback thread / stream
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback_thread: bool = False
        self._stream: Optional[sd.OutputStream] = None

        self._lock = threading.RLock()

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
        Exception
            If the file format is not supported or decoding fails.
        """
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Stop any active playback first.
        self.stop()

        try:
            with self._lock:
                self._audio_data, self._sample_rate = librosa.load(
                    str(file_path), sr=None, mono=True
                )
                self._duration = librosa.get_duration(
                    y=self._audio_data, sr=self._sample_rate
                )
                self.current_file_path = file_path
                self._current_sample_pos = 0
                self._is_playing = False
                self._is_paused = False
        except Exception as exc:
            self._audio_data = None
            self._sample_rate = 0
            raise Exception(f"Could not load audio file: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Playback controls
    # ------------------------------------------------------------------ #
    def play(self) -> None:
        """
        Start or resume playback.

        If playback is already active the call is a no-op so that A–B loop
        seeks (``set_position`` + ``play``) work seamlessly without
        restarting the audio thread.
        """
        if self._audio_data is None or self._sample_rate == 0:
            return

        with self._lock:
            # Already playing → the seek done by set_position() is sufficient.
            if self._is_playing and self._playback_thread is not None \
                    and self._playback_thread.is_alive():
                self._is_paused = False
                return

            # Signal any dying thread to stop.
            self._stop_playback_thread = True

        # Wait for the old thread to finish (one write block ≈ 46 ms max).
        if self._playback_thread is not None and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=0.3)

        with self._lock:
            self._is_playing = True
            self._is_paused = False
            self._stop_playback_thread = False
            self._playback_thread = threading.Thread(
                target=self._playback_worker, daemon=True
            )
            self._playback_thread.start()

    def pause(self) -> None:
        """
        Pause playback.

        The current sample position is preserved so that ``play()`` resumes
        from exactly where playback was paused.
        """
        with self._lock:
            if self._is_playing:
                self._is_playing = False
                self._is_paused = True
                self._stop_playback_thread = True

    def stop(self) -> None:
        """Stop playback and reset position to the beginning."""
        with self._lock:
            self._is_playing = False
            self._is_paused = False
            self._stop_playback_thread = True

        if self._playback_thread is not None and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=0.3)

        with self._lock:
            self._current_sample_pos = 0

    # ------------------------------------------------------------------ #
    # Position and duration
    # ------------------------------------------------------------------ #
    def set_position(self, seconds: float) -> None:
        """
        Set the playback position in seconds.

        Thread-safe. If playback is active the change takes effect on the
        next audio block (within ~46 ms).

        Parameters
        ----------
        seconds : float
            Desired position, clamped to [0, duration].
        """
        if self._audio_data is None or self._sample_rate == 0:
            return

        with self._lock:
            clamped = max(0.0, min(self._duration, seconds))
            self._current_sample_pos = int(clamped * self._sample_rate)

    def get_position(self) -> float:
        """
        Return the current playback position in seconds.

        Returns
        -------
        float
            Position derived from the current sample index.
        """
        if self._audio_data is None or self._sample_rate == 0:
            return 0.0

        with self._lock:
            return self._current_sample_pos / self._sample_rate

    def get_duration(self) -> float:
        """Return the media duration in seconds."""
        with self._lock:
            return self._duration

    # ------------------------------------------------------------------ #
    # Volume
    # ------------------------------------------------------------------ #
    def set_volume(self, volume: int) -> None:
        """Set the audio volume (0-100). Effective from the next block."""
        with self._lock:
            self._volume = max(0, min(100, volume))

    def get_volume(self) -> int:
        """Return the current volume (0-100)."""
        with self._lock:
            return self._volume

    # ------------------------------------------------------------------ #
    # Tempo control
    # ------------------------------------------------------------------ #
    def set_tempo(self, factor: float) -> None:
        """
        Set playback tempo factor.

        Parameters
        ----------
        factor : float
            Tempo factor clamped to [0.5, 2.0].
            1.0 = normal speed, 0.5 = half speed, 2.0 = double speed.

        Notes
        -----
        Implemented as tape-style resampling: speed and pitch change
        together. True pitch-preserving time-stretch is planned.
        """
        with self._lock:
            self._tempo = max(0.5, min(2.0, factor))

    def get_tempo(self) -> float:
        """Return the current tempo factor."""
        with self._lock:
            return self._tempo

    # ------------------------------------------------------------------ #
    # Private: playback worker
    # ------------------------------------------------------------------ #
    def _playback_worker(self) -> None:
        """
        Background thread: feeds audio blocks to the PortAudio stream.

        Design notes
        ------------
        - The lock is held only while reading state and advancing the sample
          position counter. The blocking ``stream.write()`` call is made
          **outside** the lock to avoid stalling the main thread.
        - Volume and tempo are read fresh on every block so that changes
          from the UI take effect within one block (~46 ms).
        - Tempo is applied via linear interpolation (``numpy.interp``):
          fast tempo subsamples the source, slow tempo oversamples it.
          Both speed and pitch change together (tape effect).
        """
        local_stream: Optional[sd.OutputStream] = None
        bs = self._BLOCKSIZE

        try:
            with self._lock:
                if self._audio_data is None or self._sample_rate == 0:
                    return
                sample_rate = self._sample_rate

            local_stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=bs,
                latency="low",
            )
            with self._lock:
                self._stream = local_stream
            local_stream.start()

            while True:
                # ── Read state and prepare audio block (lock held) ───────
                audio_block: Optional[np.ndarray] = None

                with self._lock:
                    if self._stop_playback_thread or not self._is_playing:
                        break
                    if self._audio_data is None:
                        break

                    pos = self._current_sample_pos
                    total = len(self._audio_data)

                    if pos >= total:
                        self._is_playing = False
                        break

                    tempo = self._tempo
                    volume = self._volume / 100.0

                    # Source samples to consume for this output block.
                    source_size = max(1, int(bs * tempo))
                    end_pos = min(pos + source_size, total)
                    chunk = self._audio_data[pos:end_pos].copy() * volume
                    actual = len(chunk)

                    # Resample chunk → exactly bs output samples.
                    if actual > 0 and actual != bs:
                        idx = np.linspace(0, actual - 1, bs)
                        audio_block = np.interp(
                            idx, np.arange(actual), chunk
                        ).astype(np.float32)
                    elif actual > 0:
                        audio_block = chunk.astype(np.float32)
                    else:
                        audio_block = np.zeros(bs, dtype=np.float32)

                    # Advance sample position.
                    self._current_sample_pos = end_pos

                # ── Write to stream OUTSIDE the lock ─────────────────────
                if audio_block is not None:
                    local_stream.write(audio_block)

        except Exception as exc:
            print(f"Playback error: {exc}")
        finally:
            with self._lock:
                self._stream = None
                self._is_playing = False
                self._stop_playback_thread = False

            if local_stream is not None:
                try:
                    local_stream.stop()
                    local_stream.close()
                except Exception:
                    pass

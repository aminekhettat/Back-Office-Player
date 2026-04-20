"""
Native audio player module (without VLC dependency).

This module provides a cross-platform audio player using librosa for loading
and sounddevice for playback, with support for all audio formats via librosa.

Features
--------

- Support for MP3, WAV, FLAC, OGG, WMA via librosa.
- Sample-accurate position tracking and seeking.
- Volume control (applied per block, effective immediately).
- Tempo control (tape-style: speed and pitch change together;
  true pitch-preserving time-stretch is planned for a future release).

Requirements
------------

- librosa (loads audio, supports all formats).
- sounddevice (playback via PortAudio).
- numpy.

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

import logging
import threading
from collections.abc import Callable
from pathlib import Path

import librosa
import numpy as np
import sounddevice as sd

from core.pitch_engine import PitchEngine

_logger = logging.getLogger(__name__)


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
        self._audio_data: np.ndarray | None = None  # float32, mono, [-1, 1]
        self._sample_rate: int = 0
        self.current_file_path: Path | None = None

        # Playback state
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._current_sample_pos: int = 0  # Ground-truth position in samples

        # Audio parameters
        self._duration: float = 0.0
        self._volume: int = 80  # 0-100
        self._tempo: float = 1.0  # 0.5-2.0

        # Pitch parameters
        self._pitch_semitones: float = 0.0  # semitone offset (-12 to +12)
        self._pitch_preserving: bool = False  # use PitchEngine for tempo
        self._processed_audio: np.ndarray | None = None  # pitch/stretch result
        self._pitch_engine = PitchEngine()

        # Playback thread / stream
        self._playback_thread: threading.Thread | None = None
        self._stop_playback_thread: bool = False
        self._stream: sd.OutputStream | None = None

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
                audio_data, sample_rate = librosa.load(str(file_path), sr=None, mono=True)
                self._audio_data = audio_data
                self._sample_rate = int(sample_rate)
                self._duration = librosa.get_duration(y=self._audio_data, sr=self._sample_rate)
                self.current_file_path = file_path
                self._current_sample_pos = 0
                self._is_playing = False
                self._is_paused = False
        except Exception as exc:
            self._audio_data = None
            self._sample_rate = 0
            raise RuntimeError(f"Could not load audio file: {exc}") from exc

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
            if (
                self._is_playing
                and self._playback_thread is not None
                and self._playback_thread.is_alive()
            ):
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
            self._playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
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
            # Map song-time to the index of the active buffer (which may
            # be time-stretched and therefore a different length).
            active = (
                self._processed_audio if self._processed_audio is not None else self._audio_data
            )
            if self._duration > 0 and active is not None:
                self._current_sample_pos = int(clamped / self._duration * len(active))
            else:
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
            active = (
                self._processed_audio if self._processed_audio is not None else self._audio_data
            )
            if active is None or len(active) == 0:
                return 0.0
            # Report song-time regardless of whether the active buffer
            # has been time-stretched.
            return self._current_sample_pos / len(active) * self._duration

    def get_duration(self) -> float:
        """Return the media duration in seconds."""
        with self._lock:
            return self._duration

    def is_playing(self) -> bool:
        """Return ``True`` while audio is actively playing (not paused, not stopped)."""
        with self._lock:
            return self._is_playing

    def get_audio_snapshot(self) -> tuple[np.ndarray | None, int]:
        """
        Return a thread-safe snapshot of the current audio data and sample rate.

        This method is the public API for read-only access to the raw audio
        data (e.g. for waveform rendering). The returned array is a reference
        to the internal buffer — do **not** modify it.

        Returns
        -------
        tuple[np.ndarray or None, int]
            ``(audio_data, sample_rate)`` where *audio_data* is ``None``
            if no file is loaded.
        """
        with self._lock:
            return self._audio_data, self._sample_rate

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
    # Pitch control
    # ------------------------------------------------------------------ #
    def set_pitch_semitones(self, semitones: float) -> None:
        """
        Set the pitch offset in semitones.

        Parameters
        ----------
        semitones : float
            Pitch shift in semitones, clamped to ``[-12, 12]``.
        """
        with self._lock:
            self._pitch_semitones = max(-12.0, min(12.0, semitones))

    def get_pitch_semitones(self) -> float:
        """Return the current pitch offset in semitones."""
        with self._lock:
            return self._pitch_semitones

    def set_pitch_preserving(self, enabled: bool) -> None:
        """
        Enable or disable pitch-preserving time-stretch.

        When ``True``, ``apply_pitch_async`` must be called after any
        tempo or pitch change to regenerate ``_processed_audio``.

        Parameters
        ----------
        enabled : bool
            ``True`` to use the :class:`~core.pitch_engine.PitchEngine`
            for tempo and pitch, ``False`` for tape-style playback.
        """
        with self._lock:
            self._pitch_preserving = enabled

    def get_pitch_preserving(self) -> bool:
        """Return whether pitch-preserving mode is active."""
        with self._lock:
            return self._pitch_preserving

    def clear_processed_audio(self) -> None:
        """Drop any pre-processed buffer so playback uses raw audio.

        Rescales ``_current_sample_pos`` from the stretched buffer's
        length back to the raw buffer's length so playback resumes at
        the same song time.
        """
        with self._lock:
            if self._processed_audio is None or self._audio_data is None:
                self._processed_audio = None
                return
            old_len = len(self._processed_audio)
            new_len = len(self._audio_data)
            if old_len > 0 and new_len > 0 and old_len != new_len:
                self._current_sample_pos = int(self._current_sample_pos * new_len / old_len)
            self._processed_audio = None

    def apply_pitch_async(self, on_ready: Callable[[], None]) -> None:
        """
        Regenerate ``_processed_audio`` in a background thread.

        Applies pitch-shift (if ``_pitch_semitones != 0``) and/or
        time-stretch (if pitch-preserving mode is active and
        ``_tempo != 1.0``) to ``_audio_data``.

        Parameters
        ----------
        on_ready : callable
            Zero-argument callback invoked (from the worker thread) when
            ``_processed_audio`` has been updated.  Qt callers must wrap
            this in ``QTimer.singleShot(0, ...)`` to return to the main
            thread.
        """
        with self._lock:
            if self._audio_data is None:
                on_ready()
                return
            audio = self._audio_data.copy()
            sr = self._sample_rate
            semitones = self._pitch_semitones
            tempo = self._tempo
            pitch_preserving = self._pitch_preserving

        def _swap_buffer(new_buf: np.ndarray | None) -> None:
            """Replace ``_processed_audio`` and rescale sample position
            so the perceived song time stays the same across buffers
            of different lengths (time-stretch changes length)."""
            with self._lock:
                old_buf = (
                    self._processed_audio if self._processed_audio is not None else self._audio_data
                )
                old_len = len(old_buf) if old_buf is not None else 0
                new_len = (
                    len(new_buf)
                    if new_buf is not None
                    else (len(self._audio_data) if self._audio_data is not None else 0)
                )
                if old_len > 0 and new_len > 0 and old_len != new_len:
                    self._current_sample_pos = int(self._current_sample_pos * new_len / old_len)
                self._processed_audio = new_buf

        def _apply_shift(shifted: np.ndarray) -> None:
            if pitch_preserving and tempo != 1.0:

                def _apply_stretch(stretched: np.ndarray) -> None:
                    _swap_buffer(stretched)
                    on_ready()

                def _on_stretch_error(exc: Exception) -> None:
                    _logger.warning("PitchEngine stretch error: %s", exc)
                    _swap_buffer(shifted)
                    on_ready()

                self._pitch_engine.stretch(shifted, sr, tempo, _apply_stretch, _on_stretch_error)
            else:
                _swap_buffer(shifted)
                on_ready()

        def _on_shift_error(exc: Exception) -> None:
            _logger.warning("PitchEngine shift error: %s", exc)
            # Fall back: just use raw audio
            _swap_buffer(None)
            on_ready()

        if semitones != 0.0:
            self._pitch_engine.shift(audio, sr, semitones, _apply_shift, _on_shift_error)
        elif pitch_preserving and tempo != 1.0:

            def _apply_stretch_direct(stretched: np.ndarray) -> None:
                _swap_buffer(stretched)
                on_ready()

            def _on_stretch_error_direct(exc: Exception) -> None:
                _logger.warning("PitchEngine stretch error: %s", exc)
                _swap_buffer(None)
                on_ready()

            self._pitch_engine.stretch(
                audio, sr, tempo, _apply_stretch_direct, _on_stretch_error_direct
            )
        else:
            _swap_buffer(None)
            on_ready()

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
        local_stream: sd.OutputStream | None = None
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
                audio_block: np.ndarray | None = None

                with self._lock:
                    if self._stop_playback_thread or not self._is_playing:
                        break

                    # Use pitch-processed audio when available, else raw data.
                    active_audio = (
                        self._processed_audio
                        if self._processed_audio is not None
                        else self._audio_data
                    )
                    # _audio_data can be cleared from the main thread between
                    # the entry guard and here (race condition).
                    if active_audio is None:
                        break

                    pos = self._current_sample_pos
                    total = len(active_audio)

                    if pos >= total:
                        self._is_playing = False
                        break

                    # When pitch-preserving mode is active the pre-processed
                    # audio already has the correct tempo baked in, so use
                    # tempo=1.0 for the resampling step; otherwise apply the
                    # tape-style speed change as before.
                    if self._pitch_preserving and self._processed_audio is not None:
                        rate = 1.0
                    else:
                        # Tape mode: combine tempo and pitch into one real-time
                        # resampling rate so the pitch slider responds instantly
                        # (raising pitch also speeds up playback — physical tape).
                        pitch_rate = 2.0 ** (self._pitch_semitones / 12.0)
                        rate = self._tempo * pitch_rate
                    volume = self._volume / 100.0

                    # Source samples to consume for this output block.
                    source_size = max(1, int(bs * rate))
                    end_pos = min(pos + source_size, total)
                    chunk = active_audio[pos:end_pos].copy() * volume
                    actual = len(chunk)

                    # Resample chunk → exactly bs output samples.
                    if actual > 0 and actual != bs:
                        idx = np.linspace(0, actual - 1, bs)
                        audio_block = np.interp(idx, np.arange(actual), chunk).astype(np.float32)
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
            _logger.error("Playback error: %s", exc)
        finally:
            with self._lock:
                self._stream = None
                self._is_playing = False
                self._stop_playback_thread = False

            if local_stream is not None:
                try:
                    local_stream.stop()
                    local_stream.close()
                except Exception as exc:
                    _logger.warning("Error closing audio stream: %s", exc)

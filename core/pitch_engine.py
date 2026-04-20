"""
Pitch engine module.

Provides pitch-preserving time-stretch and pitch-shift operations for
audio data using librosa, executed in background threads with an LRU cache.

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

import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import cast

import librosa
import numpy as np


class PitchEngine:
    """
    Background time-stretch and pitch-shift processor with LRU cache.

    Operations are dispatched to a daemon thread so the Qt UI remains
    responsive. Results are cached (up to ``_CACHE_MAX`` entries) keyed
    by ``(operation, id(audio), parameter)`` so repeated calls with the
    same audio and parameter are instant.

    Attributes
    ----------
    _CACHE_MAX : int
        Maximum number of cached results (default 3).
    """

    _CACHE_MAX = 3

    def __init__(self) -> None:
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def stretch(
        self,
        audio: np.ndarray,
        sr: int,
        rate: float,
        on_done: Callable[[np.ndarray], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """
        Time-stretch *audio* by *rate* in a background thread.

        Parameters
        ----------
        audio : np.ndarray
            Source audio (float32, mono).
        sr : int
            Sample rate (Hz).
        rate : float
            Stretch factor (e.g. 1.5 = 50 % faster, pitch preserved).
        on_done : callable
            Invoked with the processed ``np.ndarray`` on success.
        on_error : callable
            Invoked with the ``Exception`` on failure.

        Notes
        -----
        Both callbacks are invoked from the worker thread.  Qt UI
        updates must be marshalled back to the main thread with
        ``QTimer.singleShot(0, lambda: ...)``.
        """
        key = ("stretch", id(audio), rate)
        cached = self._get_cached(key)
        if cached is not None:
            on_done(cached)
            return

        def _worker():
            try:
                result = librosa.effects.time_stretch(y=audio, rate=rate)
                self._set_cached(key, result)
                on_done(result)
            except Exception as exc:
                on_error(exc)

        threading.Thread(target=_worker, daemon=True).start()

    def shift(
        self,
        audio: np.ndarray,
        sr: int,
        semitones: float,
        on_done: Callable[[np.ndarray], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """
        Pitch-shift *audio* by *semitones* in a background thread.

        Parameters
        ----------
        audio : np.ndarray
            Source audio (float32, mono).
        sr : int
            Sample rate (Hz).
        semitones : float
            Semitone shift (positive = up, negative = down).
        on_done : callable
            Invoked with the processed ``np.ndarray`` on success.
        on_error : callable
            Invoked with the ``Exception`` on failure.
        """
        key = ("shift", id(audio), semitones)
        cached = self._get_cached(key)
        if cached is not None:
            on_done(cached)
            return

        def _worker():
            try:
                result = librosa.effects.pitch_shift(y=audio, sr=sr, n_steps=semitones)
                self._set_cached(key, result)
                on_done(result)
            except Exception as exc:
                on_error(exc)

        threading.Thread(target=_worker, daemon=True).start()

    def clear_cache(self) -> None:
        """Evict all cached results."""
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    def _get_cached(self, key: tuple) -> np.ndarray | None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return cast(np.ndarray, self._cache[key])
        return None

    def _set_cached(self, key: tuple, value: np.ndarray) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                self._cache[key] = value
                if len(self._cache) > self._CACHE_MAX:
                    self._cache.popitem(last=False)

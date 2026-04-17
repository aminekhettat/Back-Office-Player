"""
Practice session module.

Manages loop count, progressive tempo, loop delay, and session timer
for structured music practice sessions.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.0
"""

from __future__ import annotations

import time
from typing import Optional, Tuple


class PracticeSession:
    """
    Tracks the state of a single practice session.

    A session encapsulates:

    - An optional loop count (0 = infinite).
    - Optional progressive tempo (tempo increases by ``tempo_step`` after
      each loop until ``tempo_target`` is reached).
    - An optional delay between loops (seconds).
    - A wall-clock start time for elapsed-time reporting.

    Attributes
    ----------
    loop_count : int
        Total loops to perform before the session ends. ``0`` = infinite.
    progressive_tempo : bool
        Whether tempo increases after each completed loop.
    tempo_start : float
        Initial tempo factor (e.g. ``0.8`` = 80 %).
    tempo_step : float
        Increment applied to tempo after each loop.
    tempo_target : float
        Maximum tempo factor (e.g. ``1.0`` = 100 %).
    loop_delay : float
        Seconds to wait between loops (must be handled with
        ``QTimer.singleShot``; never ``time.sleep`` in a Qt callback).
    """

    def __init__(
        self,
        loop_count: int = 0,
        progressive_tempo: bool = False,
        tempo_start: float = 1.0,
        tempo_step: float = 0.05,
        tempo_target: float = 1.0,
        loop_delay: float = 0.0,
    ) -> None:
        self.loop_count = loop_count
        self.progressive_tempo = progressive_tempo
        self.tempo_start = tempo_start
        self.tempo_step = tempo_step
        self.tempo_target = tempo_target
        self.loop_delay = loop_delay

        self._current_loop: int = 0
        self._current_tempo: float = tempo_start
        self._session_start: Optional[float] = None
        self._active: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Start (or restart) the session, resetting all counters."""
        self._current_loop = 0
        self._current_tempo = self.tempo_start
        self._session_start = time.monotonic()
        self._active = True

    def stop(self) -> None:
        """Stop the session."""
        self._active = False

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def is_active(self) -> bool:
        """``True`` while the session is running."""
        return self._active

    @property
    def current_loop(self) -> int:
        """Number of loops completed so far."""
        return self._current_loop

    @property
    def current_tempo(self) -> float:
        """Current tempo factor."""
        return self._current_tempo

    # ------------------------------------------------------------------ #
    # Loop logic
    # ------------------------------------------------------------------ #
    def on_loop_completed(self) -> Tuple[bool, float]:
        """
        Notify the session that one loop has finished.

        Updates the internal loop counter and optionally advances the
        tempo.

        Returns
        -------
        tuple[bool, float]
            ``(should_stop, new_tempo)`` where *should_stop* is ``True``
            when the configured loop count has been reached, and
            *new_tempo* is the tempo factor for the next loop.
        """
        self._current_loop += 1

        should_stop = False
        if self.loop_count > 0 and self._current_loop >= self.loop_count:
            should_stop = True
            self._active = False

        if self.progressive_tempo:
            self._current_tempo = min(
                self._current_tempo + self.tempo_step, self.tempo_target
            )

        return should_stop, self._current_tempo

    # ------------------------------------------------------------------ #
    # Timer
    # ------------------------------------------------------------------ #
    def get_elapsed(self) -> str:
        """
        Return elapsed time as ``HH:MM:SS``.

        Returns ``"00:00:00"`` if the session has not been started.
        """
        if self._session_start is None:
            return "00:00:00"
        elapsed = int(time.monotonic() - self._session_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

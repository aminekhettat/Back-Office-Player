"""
Thread-safety tests for core.audio_player_native.AudioPlayer.

Verifies that concurrent calls to play/pause/stop/set_position/set_volume
from multiple threads do not deadlock, crash, or corrupt internal state.

sounddevice.OutputStream is patched at the test level (not per-thread) so
the mock is active for every worker thread that calls sd.OutputStream().

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.audio_player_native import AudioPlayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_player(tmp_path: Path, audio: np.ndarray, sr: int) -> AudioPlayer:
    """Return an AudioPlayer with fake audio loaded (only librosa mocked)."""
    p = tmp_path / "audio.wav"
    p.touch()
    dur = float(len(audio)) / sr
    with (
        patch("librosa.load", return_value=(audio, sr)),
        patch("librosa.get_duration", return_value=dur),
    ):
        player = AudioPlayer()
        player.load_file(p)
    return player


# ---------------------------------------------------------------------------
# Concurrency: play / pause / stop
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPlayPauseConcurrency:
    def test_concurrent_play_pause_no_deadlock(self, tmp_path, sample_audio, sample_rate):
        """play()/pause() from 4 threads concurrently does not deadlock."""
        mock_stream = MagicMock()
        errors: list[Exception] = []

        # Patch sounddevice for the entire test so every worker thread
        # that calls sd.OutputStream() sees the mock.
        with patch("sounddevice.OutputStream", return_value=mock_stream):
            player = _load_player(tmp_path, sample_audio, sample_rate)

            def _toggle() -> None:
                try:
                    for _ in range(15):
                        player.play()
                        player.pause()
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=_toggle) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
            player.stop()

        assert all(not t.is_alive() for t in threads), "Thread(s) still alive — possible deadlock"
        assert not errors, f"Thread errors: {errors}"

    def test_concurrent_stop_from_multiple_threads(self, tmp_path, sample_audio, sample_rate):
        """Calling stop() from several threads simultaneously is safe."""
        mock_stream = MagicMock()
        errors: list[Exception] = []

        with patch("sounddevice.OutputStream", return_value=mock_stream):
            player = _load_player(tmp_path, sample_audio, sample_rate)
            player.play()

            def _stop() -> None:
                try:
                    player.stop()
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=_stop) for _ in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

        assert not errors
        assert not player._is_playing


# ---------------------------------------------------------------------------
# Concurrency: set_position + play
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSeekConcurrency:
    def test_concurrent_set_position_does_not_corrupt_state(
        self, tmp_path, sample_audio, sample_rate
    ):
        """Simultaneous set_position() calls from many threads leave a valid position."""
        player = _load_player(tmp_path, sample_audio, sample_rate)
        duration = player.get_duration()
        errors: list[Exception] = []

        def _seek(target: float) -> None:
            try:
                for _ in range(20):
                    player.set_position(target)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        targets = [duration * frac for frac in [0.0, 0.25, 0.5, 0.75, 1.0]]
        threads = [threading.Thread(target=_seek, args=(t,)) for t in targets]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors
        pos = player.get_position()
        assert 0.0 <= pos <= duration + 1e-6

    def test_seek_while_playing_does_not_crash(self, tmp_path, sample_audio, sample_rate):
        """set_position() while play() is running completes without error."""
        mock_stream = MagicMock()
        duration = float(len(sample_audio)) / sample_rate
        errors: list[Exception] = []

        with patch("sounddevice.OutputStream", return_value=mock_stream):
            player = _load_player(tmp_path, sample_audio, sample_rate)
            player.play()

            def _seek_loop() -> None:
                try:
                    for i in range(30):
                        player.set_position(duration * (i % 5) / 5)
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            t = threading.Thread(target=_seek_loop)
            t.start()
            t.join(timeout=5)
            player.stop()

        assert not errors


# ---------------------------------------------------------------------------
# Concurrency: volume + tempo writes
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParameterConcurrency:
    def test_concurrent_volume_writes_stay_in_range(self, tmp_path, sample_audio, sample_rate):
        """Concurrent set_volume() calls always leave volume in [0, 100]."""
        player = _load_player(tmp_path, sample_audio, sample_rate)
        errors: list[Exception] = []

        def _set_volume(v: int) -> None:
            try:
                for _ in range(30):
                    player.set_volume(v)
                    vol = player.get_volume()
                    assert 0 <= vol <= 100
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [
            threading.Thread(target=_set_volume, args=(v,))
            for v in [0, 50, 100, 200, -10]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors

    def test_concurrent_tempo_writes_stay_in_range(self, tmp_path, sample_audio, sample_rate):
        """Concurrent set_tempo() calls always leave tempo in [0.5, 2.0]."""
        player = _load_player(tmp_path, sample_audio, sample_rate)
        errors: list[Exception] = []

        def _set_tempo(f: float) -> None:
            try:
                for _ in range(30):
                    player.set_tempo(f)
                    tempo = player.get_tempo()
                    assert 0.5 <= tempo <= 2.0
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [
            threading.Thread(target=_set_tempo, args=(f,))
            for f in [0.1, 0.5, 1.0, 1.5, 2.0, 5.0]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors

    def test_get_set_volume_consistent_under_load(self, tmp_path, sample_audio, sample_rate):
        """Under concurrent writes, get_volume() always returns a value in [0, 100]."""
        player = _load_player(tmp_path, sample_audio, sample_rate)
        range_errors: list[int] = []

        def _set_and_check(target: int) -> None:
            for _ in range(20):
                player.set_volume(target)
                v = player.get_volume()
                if not (0 <= v <= 100):
                    range_errors.append(v)

        threads = [
            threading.Thread(target=_set_and_check, args=(v,))
            for v in [20, 40, 60, 80]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not range_errors, f"Volume out of range: {range_errors}"

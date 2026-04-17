"""
Performance benchmarks for the audio processing pipeline.

These are NOT part of the standard pytest run.  Execute explicitly:
    pytest tests/bench_audio.py -m benchmark -v

They verify that per-block audio processing stays well under the real-time
deadline (2048 samples @ 44100 Hz ≈ 46 ms).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import time

import numpy as np
import pytest

BLOCK_SIZE = 2048
SAMPLE_RATE = 44100
BLOCK_DEADLINE_S = BLOCK_SIZE / SAMPLE_RATE  # ≈ 0.046 s
ITERATIONS = 500  # average over N blocks


pytestmark = pytest.mark.benchmark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio(n_seconds: float = 5.0) -> np.ndarray:
    t = np.linspace(0, n_seconds, int(SAMPLE_RATE * n_seconds), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def _process_block(
    audio: np.ndarray,
    pos: int,
    tempo: float = 1.0,
    volume: float = 0.8,
) -> tuple[np.ndarray, int]:
    """Simulate one iteration of AudioPlayer._playback_worker (no stream write)."""
    source_size = max(1, int(BLOCK_SIZE * tempo))
    end_pos = min(pos + source_size, len(audio))
    chunk = audio[pos:end_pos].copy() * volume
    actual = len(chunk)

    if actual > 0 and actual != BLOCK_SIZE:
        idx = np.linspace(0, actual - 1, BLOCK_SIZE)
        block = np.interp(idx, np.arange(actual), chunk).astype(np.float32)
    elif actual > 0:
        block = chunk.astype(np.float32)
    else:
        block = np.zeros(BLOCK_SIZE, dtype=np.float32)

    return block, end_pos


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
def test_block_processing_at_normal_speed() -> None:
    """Normal tempo (1.0×): average block processing < deadline."""
    audio = _make_audio()
    pos = 0

    start = time.perf_counter()
    for _ in range(ITERATIONS):
        _, pos = _process_block(audio, pos, tempo=1.0)
        if pos >= len(audio):
            pos = 0
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / ITERATIONS) * 1000

    assert avg_ms < BLOCK_DEADLINE_S * 1000, (
        f"Normal-speed block too slow: {avg_ms:.3f} ms (limit {BLOCK_DEADLINE_S * 1000:.1f} ms)"
    )


@pytest.mark.benchmark
def test_block_processing_at_half_speed() -> None:
    """Half tempo (0.5×): resampling overhead must still fit within deadline."""
    audio = _make_audio()
    pos = 0

    start = time.perf_counter()
    for _ in range(ITERATIONS):
        _, pos = _process_block(audio, pos, tempo=0.5)
        if pos >= len(audio):
            pos = 0
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / ITERATIONS) * 1000

    assert avg_ms < BLOCK_DEADLINE_S * 1000, (
        f"Half-speed block too slow: {avg_ms:.3f} ms (limit {BLOCK_DEADLINE_S * 1000:.1f} ms)"
    )


@pytest.mark.benchmark
def test_block_processing_at_double_speed() -> None:
    """Double tempo (2.0×): larger source chunks must still fit within deadline."""
    audio = _make_audio()
    pos = 0

    start = time.perf_counter()
    for _ in range(ITERATIONS):
        _, pos = _process_block(audio, pos, tempo=2.0)
        if pos >= len(audio):
            pos = 0
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / ITERATIONS) * 1000

    assert avg_ms < BLOCK_DEADLINE_S * 1000, (
        f"Double-speed block too slow: {avg_ms:.3f} ms (limit {BLOCK_DEADLINE_S * 1000:.1f} ms)"
    )


@pytest.mark.benchmark
def test_seek_latency() -> None:
    """Position seek (sample-index update) must complete in under 1 ms."""
    from unittest.mock import MagicMock, patch

    from core.audio_player_native import AudioPlayer

    audio = _make_audio()
    sr = SAMPLE_RATE
    p = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "x.wav"
    p.touch()

    with (
        patch("librosa.load", return_value=(audio, sr)),
        patch("librosa.get_duration", return_value=len(audio) / sr),
        patch("sounddevice.OutputStream"),
    ):
        player = AudioPlayer()
        player.load_file(p)

    duration = player.get_duration()
    targets = [duration * i / 100 for i in range(ITERATIONS)]

    start = time.perf_counter()
    for t in targets:
        player.set_position(t)
    elapsed = time.perf_counter() - start
    avg_us = (elapsed / ITERATIONS) * 1_000_000

    assert avg_us < 1000, f"Seek too slow: {avg_us:.1f} µs (limit 1000 µs)"

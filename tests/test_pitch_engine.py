"""
Tests for core.pitch_engine — 100% branch coverage.

Uses threading.Event to synchronise async callbacks.  All librosa calls are
mocked to avoid real DSP computation in CI.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import threading
from unittest.mock import patch

import numpy as np

from core.pitch_engine import PitchEngine

# ---------------------------------------------------------------------------
# Helper: run a PitchEngine call synchronously
# ---------------------------------------------------------------------------

def _sync(fn, *args, **kwargs):
    """
    Call fn(..., on_done, on_error) and block until the callback fires.

    Returns (results, errors) where each is a list with 0 or 1 entry.
    """
    results = []
    errors = []
    evt = threading.Event()

    def on_done(audio):
        results.append(audio)
        evt.set()

    def on_error(exc):
        errors.append(exc)
        evt.set()

    fn(*args, on_done=on_done, on_error=on_error, **kwargs)
    evt.wait(timeout=5)
    return results, errors


# ---------------------------------------------------------------------------
# stretch()
# ---------------------------------------------------------------------------

class TestPitchEngineStretch:
    def test_stretch_cache_miss_success(self, sample_audio, sample_rate):
        """stretch() calls librosa on a cache miss and returns the result."""
        expected = sample_audio * 0.9
        with patch("librosa.effects.time_stretch", return_value=expected) as mock_ts:
            engine = PitchEngine()
            results, errors = _sync(engine.stretch, sample_audio, sample_rate, rate=1.5)
        assert errors == []
        assert len(results) == 1
        np.testing.assert_array_equal(results[0], expected)
        mock_ts.assert_called_once_with(y=sample_audio, rate=1.5)

    def test_stretch_cache_miss_error(self, sample_audio, sample_rate):
        """stretch() propagates a librosa error to on_error."""
        with patch("librosa.effects.time_stretch", side_effect=RuntimeError("fail")):
            engine = PitchEngine()
            results, errors = _sync(engine.stretch, sample_audio, sample_rate, rate=1.5)
        assert results == []
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)

    def test_stretch_cache_hit(self, sample_audio, sample_rate):
        """Second stretch() call with the same args uses the cache (librosa called once)."""
        expected = sample_audio * 0.5
        with patch("librosa.effects.time_stretch", return_value=expected) as mock_ts:
            engine = PitchEngine()
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
            results, errors = _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
        assert errors == []
        np.testing.assert_array_equal(results[0], expected)
        assert mock_ts.call_count == 1  # second call hit the cache


# ---------------------------------------------------------------------------
# shift()
# ---------------------------------------------------------------------------

class TestPitchEngineShift:
    def test_shift_cache_miss_success(self, sample_audio, sample_rate):
        """shift() calls librosa on a cache miss and returns the result."""
        expected = sample_audio * 1.1
        with patch("librosa.effects.pitch_shift", return_value=expected) as mock_ps:
            engine = PitchEngine()
            results, errors = _sync(engine.shift, sample_audio, sample_rate, semitones=2.0)
        assert errors == []
        np.testing.assert_array_equal(results[0], expected)
        mock_ps.assert_called_once_with(y=sample_audio, sr=sample_rate, n_steps=2.0)

    def test_shift_cache_miss_error(self, sample_audio, sample_rate):
        """shift() propagates a librosa error to on_error."""
        with patch("librosa.effects.pitch_shift", side_effect=ValueError("bad")):
            engine = PitchEngine()
            results, errors = _sync(engine.shift, sample_audio, sample_rate, semitones=-3.0)
        assert results == []
        assert isinstance(errors[0], ValueError)

    def test_shift_cache_hit(self, sample_audio, sample_rate):
        """Second shift() call with the same args uses the cache."""
        expected = sample_audio * 1.2
        with patch("librosa.effects.pitch_shift", return_value=expected) as mock_ps:
            engine = PitchEngine()
            _sync(engine.shift, sample_audio, sample_rate, semitones=1.0)
            results, _ = _sync(engine.shift, sample_audio, sample_rate, semitones=1.0)
        assert mock_ps.call_count == 1
        np.testing.assert_array_equal(results[0], expected)


# ---------------------------------------------------------------------------
# clear_cache()
# ---------------------------------------------------------------------------

class TestPitchEngineCache:
    def test_clear_cache_forces_recomputation(self, sample_audio, sample_rate):
        """After clear_cache(), librosa is called again for the same args."""
        with patch("librosa.effects.time_stretch", return_value=sample_audio) as mock_ts:
            engine = PitchEngine()
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
            engine.clear_cache()
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
        assert mock_ts.call_count == 2

    def test_clear_cache_empties_internal_dict(self, sample_audio, sample_rate):
        """clear_cache() leaves the internal cache dict empty."""
        with patch("librosa.effects.time_stretch", return_value=sample_audio):
            engine = PitchEngine()
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
            assert len(engine._cache) == 1
            engine.clear_cache()
            assert len(engine._cache) == 0

    def test_lru_eviction_at_max_capacity(self, sample_audio, sample_rate):
        """Cache evicts the oldest entry when _CACHE_MAX is exceeded."""
        engine = PitchEngine()
        assert engine._CACHE_MAX == 3

        with patch("librosa.effects.time_stretch", return_value=sample_audio):
            for rate in [1.0, 1.1, 1.2]:
                _sync(engine.stretch, sample_audio, sample_rate, rate=rate)
            assert len(engine._cache) == 3
            # Adding a 4th entry should evict the 1st
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.3)
            assert len(engine._cache) == 3

    def test_lru_updates_on_cache_hit(self, sample_audio, sample_rate):
        """Accessing a cached entry moves it to most-recently-used position."""
        engine = PitchEngine()
        with patch("librosa.effects.time_stretch", return_value=sample_audio):
            for rate in [1.0, 1.1, 1.2]:
                _sync(engine.stretch, sample_audio, sample_rate, rate=rate)
            # Access the oldest entry (rate=1.0) to make it MRU
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
            # Add a 4th entry — should evict rate=1.1, not rate=1.0
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.3)
        keys = list(engine._cache.keys())
        rates_in_cache = [k[2] for k in keys]
        assert 1.0 in rates_in_cache, "LRU should have kept rate=1.0 (recently accessed)"

    def test_set_cached_existing_key_moves_to_end(self, sample_audio, sample_rate):
        """_set_cached with an existing key moves it to end without adding a new entry."""
        engine = PitchEngine()
        key = ("stretch", id(sample_audio), 1.0)
        engine._set_cached(key, sample_audio)
        engine._set_cached(key, sample_audio * 2)  # same key again
        assert len(engine._cache) == 1

    def test_different_rates_produce_different_cache_keys(self, sample_audio, sample_rate):
        """Different rate values produce different cache entries."""
        with patch("librosa.effects.time_stretch", return_value=sample_audio):
            engine = PitchEngine()
            _sync(engine.stretch, sample_audio, sample_rate, rate=1.0)
            _sync(engine.stretch, sample_audio, sample_rate, rate=2.0)
        assert len(engine._cache) == 2

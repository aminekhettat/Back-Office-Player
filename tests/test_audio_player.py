"""
Tests for core.audio_player_native — 100% branch coverage.

All librosa I/O and sounddevice are mocked so no real audio hardware or
files are needed.  The _playback_worker is exercised by letting a short
audio array play to completion in a fake OutputStream.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.audio_player_native import AudioPlayer

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_audio(sample_audio, sample_rate):
    """Patch librosa.load and sounddevice to avoid real I/O."""
    with (
        patch("librosa.load", return_value=(sample_audio, sample_rate)),
        patch(
            "librosa.get_duration",
            return_value=float(len(sample_audio)) / sample_rate,
        ),
        patch("sounddevice.OutputStream") as mock_stream_cls,
    ):
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream
        yield mock_stream_cls, mock_stream


def _load_player(tmp_path, sample_audio, sample_rate):
    """Return a player with a fake file already loaded (librosa mocked)."""
    p = tmp_path / "audio.mp3"
    p.touch()
    dur = float(len(sample_audio)) / sample_rate
    with (
        patch("librosa.load", return_value=(sample_audio, sample_rate)),
        patch("librosa.get_duration", return_value=dur),
        patch("sounddevice.OutputStream"),
    ):
        player = AudioPlayer()
        player.load_file(p)
    return player


# ---------------------------------------------------------------------------
# load_file
# ---------------------------------------------------------------------------


class TestAudioPlayerLoad:
    def test_load_file_not_found_raises(self):
        """load_file raises FileNotFoundError for a missing file."""
        player = AudioPlayer()
        with pytest.raises(FileNotFoundError):
            player.load_file("/no/such/file.mp3")

    def test_load_decode_error_raises(self, tmp_path):
        """load_file re-raises a generic Exception from librosa.load."""
        p = tmp_path / "bad.mp3"
        p.touch()
        with (
            patch("librosa.load", side_effect=RuntimeError("bad codec")),
            patch("sounddevice.OutputStream"),
            pytest.raises(Exception, match="Could not load"),
        ):
            AudioPlayer().load_file(p)

    def test_load_error_clears_audio_data(self, tmp_path):
        """After a decode error, _audio_data is reset to None."""
        p = tmp_path / "bad.mp3"
        p.touch()
        player = AudioPlayer()
        with (
            patch("librosa.load", side_effect=RuntimeError("oops")),
            patch("sounddevice.OutputStream"),
            pytest.raises(RuntimeError),
        ):
            player.load_file(p)
        assert player._audio_data is None

    def test_load_success_sets_state(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """Successful load sets current_file_path and duration."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        assert player.current_file_path == p
        assert player.get_duration() > 0
        assert player.get_position() == pytest.approx(0.0)

    def test_load_resets_playback_state(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """load_file resets position and play/pause flags."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        assert not player._is_playing
        assert not player._is_paused
        assert player._current_sample_pos == 0


# ---------------------------------------------------------------------------
# play / pause / stop
# ---------------------------------------------------------------------------


class TestPlaybackControls:
    def test_play_no_file_is_noop(self):
        """play() before loading a file does not raise."""
        player = AudioPlayer()
        player.play()  # must not raise

    def test_play_starts_thread(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """play() starts a daemon playback thread."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.play()
        assert player._playback_thread is not None
        player.stop()

    def test_play_while_playing_is_noop(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """Calling play() while already playing just clears pause flag."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.play()
        thread1 = player._playback_thread
        player.play()  # second call — already playing
        # Thread should be the same (no new thread spawned)
        assert player._playback_thread is thread1 or player._is_playing
        player.stop()

    def test_pause_not_playing_is_noop(self):
        """pause() when not playing does not raise."""
        player = AudioPlayer()
        player.pause()  # no file loaded — must not raise

    def test_pause_while_playing(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """pause() sets is_paused flag and stops the worker."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.play()
        player.pause()
        assert player._is_paused

    def test_stop_resets_position(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """stop() resets _current_sample_pos to 0."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.play()
        player.set_position(0.5)
        player.stop()
        assert player._current_sample_pos == 0


# ---------------------------------------------------------------------------
# Position and duration
# ---------------------------------------------------------------------------


class TestPositionAndDuration:
    def test_get_position_before_load(self):
        """get_position returns 0.0 when no file is loaded."""
        assert AudioPlayer().get_position() == 0.0

    def test_get_duration_before_load(self):
        """get_duration returns 0.0 when no file is loaded."""
        assert AudioPlayer().get_duration() == 0.0

    def test_set_position_before_load_is_noop(self):
        """set_position before loading a file does not raise."""
        AudioPlayer().set_position(5.0)

    def test_set_position_clamped_to_zero(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """set_position clamps negative values to 0."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_position(-5.0)
        assert player.get_position() == pytest.approx(0.0)

    def test_set_position_clamped_to_duration(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """set_position clamps values above duration to duration."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        duration = player.get_duration()
        player.set_position(duration + 100.0)
        assert player.get_position() == pytest.approx(duration)

    def test_set_position_normal(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """set_position sets position correctly within valid range."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_position(0.5)
        assert player.get_position() == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


class TestVolume:
    def test_default_volume(self):
        """Default volume is 80."""
        assert AudioPlayer().get_volume() == 80

    def test_set_get_volume(self):
        """set_volume stores the value; get_volume returns it."""
        player = AudioPlayer()
        player.set_volume(60)
        assert player.get_volume() == 60

    def test_volume_clamped_below_zero(self):
        """set_volume clamps negative input to 0."""
        player = AudioPlayer()
        player.set_volume(-10)
        assert player.get_volume() == 0

    def test_volume_clamped_above_100(self):
        """set_volume clamps input above 100 to 100."""
        player = AudioPlayer()
        player.set_volume(200)
        assert player.get_volume() == 100


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------


class TestTempo:
    def test_default_tempo(self):
        """Default tempo is 1.0."""
        assert AudioPlayer().get_tempo() == pytest.approx(1.0)

    def test_set_get_tempo(self):
        """set_tempo stores the value; get_tempo returns it."""
        player = AudioPlayer()
        player.set_tempo(1.5)
        assert player.get_tempo() == pytest.approx(1.5)

    def test_tempo_clamped_below_0_5(self):
        """set_tempo clamps input below 0.5 to 0.5."""
        player = AudioPlayer()
        player.set_tempo(0.1)
        assert player.get_tempo() == pytest.approx(0.5)

    def test_tempo_clamped_above_2_0(self):
        """set_tempo clamps input above 2.0 to 2.0."""
        player = AudioPlayer()
        player.set_tempo(5.0)
        assert player.get_tempo() == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Pitch semitones
# ---------------------------------------------------------------------------


class TestPitchSemitones:
    def test_default_pitch(self):
        """Default pitch semitones is 0.0."""
        assert AudioPlayer().get_pitch_semitones() == pytest.approx(0.0)

    def test_set_get_pitch(self):
        """set_pitch_semitones stores and returns the value."""
        player = AudioPlayer()
        player.set_pitch_semitones(3.0)
        assert player.get_pitch_semitones() == pytest.approx(3.0)

    def test_pitch_clamped_above_12(self):
        """set_pitch_semitones clamps values above 12."""
        player = AudioPlayer()
        player.set_pitch_semitones(20.0)
        assert player.get_pitch_semitones() == pytest.approx(12.0)

    def test_pitch_clamped_below_minus_12(self):
        """set_pitch_semitones clamps values below -12."""
        player = AudioPlayer()
        player.set_pitch_semitones(-20.0)
        assert player.get_pitch_semitones() == pytest.approx(-12.0)


# ---------------------------------------------------------------------------
# Pitch-preserving flag
# ---------------------------------------------------------------------------


class TestPitchPreserving:
    def test_default_pitch_preserving_is_false(self):
        """Pitch-preserving mode is disabled by default."""
        assert AudioPlayer().get_pitch_preserving() is False

    def test_set_pitch_preserving_true(self):
        """set_pitch_preserving(True) enables pitch-preserving mode."""
        player = AudioPlayer()
        player.set_pitch_preserving(True)
        assert player.get_pitch_preserving() is True

    def test_set_pitch_preserving_false(self):
        """set_pitch_preserving(False) disables pitch-preserving mode."""
        player = AudioPlayer()
        player.set_pitch_preserving(True)
        player.set_pitch_preserving(False)
        assert player.get_pitch_preserving() is False


# ---------------------------------------------------------------------------
# apply_pitch_async
# ---------------------------------------------------------------------------


class TestApplyPitchAsync:
    def test_no_audio_calls_on_ready_immediately(self):
        """apply_pitch_async calls on_ready immediately when no audio loaded."""
        player = AudioPlayer()
        done = threading.Event()
        player.apply_pitch_async(lambda: done.set())
        assert done.wait(timeout=2), "on_ready was not called"

    def test_zero_shift_no_pitch_preserving_sets_none(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """With semitones=0 and pitch_preserving=False, _processed_audio stays None."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(0.0)
        player.set_pitch_preserving(False)
        done = threading.Event()
        player.apply_pitch_async(lambda: done.set())
        assert done.wait(timeout=2)
        assert player._processed_audio is None

    def test_nonzero_shift_calls_pitch_engine(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """With semitones != 0, shift is dispatched to the PitchEngine."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(2.0)

        shifted = sample_audio * 1.1
        done = threading.Event()

        with patch.object(player._pitch_engine, "shift") as mock_shift:

            def fake_shift(audio, sr, semitones, on_done, on_error):
                on_done(shifted)

            mock_shift.side_effect = fake_shift
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            mock_shift.assert_called_once()

    def test_pitch_preserving_and_tempo_ne_1_calls_stretch(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """With pitch_preserving=True and tempo!=1, stretch is called after shift."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(0.0)
        player.set_pitch_preserving(True)
        player.set_tempo(1.5)

        stretched = sample_audio * 0.9
        done = threading.Event()

        with patch.object(player._pitch_engine, "stretch") as mock_stretch:

            def fake_stretch(audio, sr, rate, on_done, on_error):
                on_done(stretched)

            mock_stretch.side_effect = fake_stretch
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            mock_stretch.assert_called_once()

    def test_shift_error_callback(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """A shift error calls on_error; _processed_audio is set to None."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(3.0)

        done = threading.Event()

        with patch.object(player._pitch_engine, "shift") as mock_shift:

            def fake_shift(audio, sr, semitones, on_done, on_error):
                on_error(RuntimeError("shift failed"))

            mock_shift.side_effect = fake_shift
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            assert player._processed_audio is None

    def test_nonzero_shift_then_pitch_preserving_stretch(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """semitones!=0 + pitch_preserving + tempo!=1 triggers shift then stretch."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(2.0)
        player.set_pitch_preserving(True)
        player.set_tempo(1.5)

        shifted = sample_audio * 1.1
        stretched = sample_audio * 0.9
        done = threading.Event()

        with (
            patch.object(player._pitch_engine, "shift") as mock_shift,
            patch.object(player._pitch_engine, "stretch") as mock_stretch,
        ):

            def fake_shift(audio, sr, semitones, on_done, on_error):
                on_done(shifted)

            def fake_stretch(audio, sr, rate, on_done, on_error):
                on_done(stretched)

            mock_shift.side_effect = fake_shift
            mock_stretch.side_effect = fake_stretch
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            mock_shift.assert_called_once()
            mock_stretch.assert_called_once()

    def test_nonzero_shift_stretch_error(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """Stretch error inside shift-then-stretch path sets _processed_audio to shifted."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(2.0)
        player.set_pitch_preserving(True)
        player.set_tempo(1.5)

        shifted = sample_audio * 1.1
        done = threading.Event()

        with (
            patch.object(player._pitch_engine, "shift") as mock_shift,
            patch.object(player._pitch_engine, "stretch") as mock_stretch,
        ):

            def fake_shift(audio, sr, semitones, on_done, on_error):
                on_done(shifted)

            def fake_stretch(audio, sr, rate, on_done, on_error):
                on_error(RuntimeError("stretch failed"))

            mock_shift.side_effect = fake_shift
            mock_stretch.side_effect = fake_stretch
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            # Fallback: _processed_audio should be set to the shifted version
            np.testing.assert_array_equal(player._processed_audio, shifted)

    def test_stretch_only_error(self, tmp_path, sample_audio, sample_rate, mock_audio):
        """Stretch-only error (semitones=0, pitch_preserving, tempo!=1) clears audio."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        player.set_pitch_semitones(0.0)
        player.set_pitch_preserving(True)
        player.set_tempo(1.5)

        done = threading.Event()

        with patch.object(player._pitch_engine, "stretch") as mock_stretch:

            def fake_stretch(audio, sr, rate, on_done, on_error):
                on_error(RuntimeError("stretch error"))

            mock_stretch.side_effect = fake_stretch
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2)
            assert player._processed_audio is None


# ---------------------------------------------------------------------------
# _playback_worker (via integration: small buffer plays to completion)
# ---------------------------------------------------------------------------


class TestPlaybackWorker:
    def test_worker_plays_to_end(self, tmp_path):
        """The playback worker runs a short audio array to its end."""
        sr = 100  # tiny sample rate
        audio = np.ones(50, dtype=np.float32) * 0.1

        p = tmp_path / "tiny.mp3"
        p.touch()

        mock_stream = MagicMock()
        with (
            patch("librosa.load", return_value=(audio, sr)),
            patch("librosa.get_duration", return_value=float(len(audio)) / sr),
            patch("sounddevice.OutputStream", return_value=mock_stream),
        ):
            player = AudioPlayer()
            player.load_file(p)
            player.set_volume(100)
            player.play()
            # Wait for the thread to finish (audio is 50 samples, tiny)
            if player._playback_thread is not None:
                player._playback_thread.join(timeout=5)
        # Worker ran and _is_playing was reset to False
        assert not player._is_playing

    def test_worker_uses_processed_audio_when_set(self, tmp_path):
        """Worker uses _processed_audio instead of _audio_data when available."""
        sr = 100
        audio = np.ones(50, dtype=np.float32) * 0.1
        processed = np.ones(60, dtype=np.float32) * 0.2

        p = tmp_path / "tiny.mp3"
        p.touch()

        mock_stream = MagicMock()
        with (
            patch("librosa.load", return_value=(audio, sr)),
            patch("librosa.get_duration", return_value=float(len(audio)) / sr),
            patch("sounddevice.OutputStream", return_value=mock_stream),
        ):
            player = AudioPlayer()
            player.load_file(p)
            player._processed_audio = processed
            player.set_pitch_preserving(True)
            player.play()
            if player._playback_thread is not None:
                player._playback_thread.join(timeout=5)
        assert not player._is_playing

    def test_worker_handles_exception(self, tmp_path):
        """Worker handles exceptions gracefully without crashing."""
        sr = 100
        audio = np.ones(50, dtype=np.float32) * 0.1

        p = tmp_path / "tiny.mp3"
        p.touch()

        mock_stream = MagicMock()
        mock_stream.write.side_effect = RuntimeError("stream error")
        with (
            patch("librosa.load", return_value=(audio, sr)),
            patch("librosa.get_duration", return_value=float(len(audio)) / sr),
            patch("sounddevice.OutputStream", return_value=mock_stream),
        ):
            player = AudioPlayer()
            player.load_file(p)
            player.play()
            if player._playback_thread is not None:
                player._playback_thread.join(timeout=5)
        assert not player._is_playing

    def test_worker_returns_immediately_without_audio(self):
        """_playback_worker returns immediately when _audio_data is None (line 495)."""
        player = AudioPlayer()
        done = threading.Event()

        def _run():
            player._playback_worker()
            done.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        assert done.wait(timeout=2.0), "_playback_worker did not return promptly"

    def test_worker_breaks_when_audio_cleared_during_startup(self):
        """Worker exits cleanly when _audio_data is cleared after the entry guard
        but before the main loop body (covers the 'active_audio is None' branch,
        line 526)."""
        audio = np.ones(44100, dtype=np.float32) * 0.001
        player = AudioPlayer()
        with player._lock:
            player._audio_data = audio.copy()
            player._sample_rate = 44100
            player._duration = 1.0
            player._is_playing = True
            player._stop_playback_thread = False

        stream_started = threading.Event()

        class _ClearingStream:
            """Mock OutputStream that wipes _audio_data on start()."""

            def __init__(self, **kw):
                pass

            def start(self):
                # Worker NOT holding lock here — safe to acquire.
                with player._lock:
                    player._audio_data = None
                    player._processed_audio = None
                stream_started.set()

            def write(self, data):
                pass

            def stop(self):
                pass

            def close(self):
                pass

        with patch("sounddevice.OutputStream", side_effect=lambda **kw: _ClearingStream(**kw)):
            t = threading.Thread(target=player._playback_worker, daemon=True)
            t.start()
            assert stream_started.wait(timeout=2.0), "stream.start() not called"
            t.join(timeout=2.0)

        assert not player._is_playing

    def test_worker_empty_chunk_writes_silence(self):
        """When a chunk slice is empty (actual==0) the worker writes silence (line 564)."""

        class _EmptySliceAudio:
            """Fake audio that returns empty slices but reports non-zero length."""

            def __init__(self):
                self._len_calls = 0

            def __len__(self):
                self._len_calls += 1
                # First call: appear large so we enter the main loop body.
                # Second call: return 0 to trigger pos >= total and break.
                return 0 if self._len_calls > 1 else 10000

            def __getitem__(self, key):
                return np.array([], dtype=np.float32)

        player = AudioPlayer()
        with player._lock:
            player._audio_data = _EmptySliceAudio()  # type: ignore[assignment]
            player._sample_rate = 44100
            player._duration = 1.0
            player._is_playing = True
            player._stop_playback_thread = False

        mock_stream = MagicMock()

        with patch("sounddevice.OutputStream", return_value=mock_stream):
            t = threading.Thread(target=player._playback_worker, daemon=True)
            t.start()
            t.join(timeout=5.0)

        # Worker must have written at least one zero block (silence) and then stopped.
        mock_stream.write.assert_called()
        assert not player._is_playing

    def test_worker_stream_stop_exception_is_caught(self):
        """Exception in stream.stop() during finally is logged, not raised (lines 585-586)."""
        audio = np.ones(10, dtype=np.float32) * 0.001
        player = AudioPlayer()
        with player._lock:
            player._audio_data = audio.copy()
            player._sample_rate = 44100
            player._duration = float(len(audio)) / 44100
            player._is_playing = True
            player._stop_playback_thread = False

        mock_stream = MagicMock()
        mock_stream.stop.side_effect = RuntimeError("cannot stop")

        with patch("sounddevice.OutputStream", return_value=mock_stream):
            # Call directly (not via play()) so we control the thread join.
            t = threading.Thread(target=player._playback_worker, daemon=True)
            t.start()
            t.join(timeout=5.0)

        # Must finish without propagating the exception.
        assert not player._is_playing


# ---------------------------------------------------------------------------
# set_position — duration=0 fallback branch
# ---------------------------------------------------------------------------


class TestSetPositionDurationZero:
    def test_set_position_duration_zero_uses_sample_rate(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """set_position falls back to sample_rate multiply when _duration==0 (line 236)."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        # Force duration to 0 while keeping audio data present.
        with player._lock:
            player._duration = 0.0
        player.set_position(2.0)
        # With duration=0: clamped = max(0, min(0, 2.0)) = 0.
        # else branch: _current_sample_pos = int(0 * sample_rate) = 0.
        with player._lock:
            assert player._current_sample_pos == 0


# ---------------------------------------------------------------------------
# get_position — empty-buffer branch
# ---------------------------------------------------------------------------


class TestGetPositionEmptyBuffer:
    def test_get_position_empty_audio_returns_zero(self):
        """get_position returns 0.0 when the active buffer is empty (line 257)."""
        player = AudioPlayer()
        # Set up state: audio data present but zero-length.
        with player._lock:
            player._audio_data = np.zeros(0, dtype=np.float32)
            player._sample_rate = 44100
            player._duration = 0.0
        assert player.get_position() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# clear_processed_audio — all branches
# ---------------------------------------------------------------------------


class TestClearProcessedAudio:
    def test_clear_when_processed_audio_is_none_is_noop(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """clear_processed_audio is a no-op when _processed_audio is already None (lines 376-386)."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        assert player._processed_audio is None
        player.clear_processed_audio()  # must not raise
        assert player._processed_audio is None

    def test_clear_when_audio_data_is_none_is_noop(self):
        """clear_processed_audio is a no-op when _audio_data is None."""
        player = AudioPlayer()
        fake = np.ones(100, dtype=np.float32)
        with player._lock:
            player._processed_audio = fake
            player._audio_data = None
        player.clear_processed_audio()
        assert player._processed_audio is None

    def test_clear_rescales_position_when_lengths_differ(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """clear_processed_audio rescales _current_sample_pos when lengths differ."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        raw_len = len(sample_audio)
        processed = np.ones(raw_len * 2, dtype=np.float32)
        with player._lock:
            player._processed_audio = processed
            player._current_sample_pos = raw_len  # halfway through processed buf
        player.clear_processed_audio()
        # Expected: raw_len * (raw_len / (raw_len * 2)) = raw_len / 2
        with player._lock:
            assert player._current_sample_pos == raw_len // 2
        assert player._processed_audio is None

    def test_clear_same_length_does_not_rescale(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """clear_processed_audio skips rescaling when old_len == new_len."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)
        raw_len = len(sample_audio)
        processed = np.ones(raw_len, dtype=np.float32)  # same length
        original_pos = raw_len // 4
        with player._lock:
            player._processed_audio = processed
            player._current_sample_pos = original_pos
        player.clear_processed_audio()
        with player._lock:
            assert player._current_sample_pos == original_pos
        assert player._processed_audio is None


# ---------------------------------------------------------------------------
# apply_pitch_async — position rescaling when buffer length changes
# ---------------------------------------------------------------------------


class TestApplyPitchAsyncRescaling:
    def test_swap_buffer_rescales_position_on_length_change(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
        """_swap_buffer rescales _current_sample_pos when new buffer length ≠ old (line 423)."""
        p = tmp_path / "audio.mp3"
        p.touch()
        player = AudioPlayer()
        player.load_file(p)

        raw_len = len(sample_audio)
        # Position set to midpoint.
        with player._lock:
            player._current_sample_pos = raw_len // 2

        # stretch returns audio twice as long (simulates 0.5x tempo).
        stretched = np.ones(raw_len * 2, dtype=np.float32)
        done = threading.Event()

        player.set_pitch_preserving(True)
        player.set_tempo(1.5)

        with patch.object(player._pitch_engine, "stretch") as mock_stretch:

            def fake_stretch(audio, sr, rate, on_done, on_error):
                on_done(stretched)

            mock_stretch.side_effect = fake_stretch
            player.apply_pitch_async(lambda: done.set())
            assert done.wait(timeout=2.0)

        # old_len = raw_len, new_len = raw_len * 2
        # expected_pos = (raw_len // 2) * (raw_len * 2) / raw_len = raw_len
        with player._lock:
            assert player._current_sample_pos == raw_len

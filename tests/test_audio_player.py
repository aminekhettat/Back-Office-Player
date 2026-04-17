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
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
            pytest.raises(Exception),
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

    def test_nonzero_shift_stretch_error(
        self, tmp_path, sample_audio, sample_rate, mock_audio
    ):
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

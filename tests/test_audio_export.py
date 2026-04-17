"""
Tests for infra.audio_export — 100% branch coverage.

Covers:
* ``export_segment_wav``: None audio, zero sample rate, end ≤ start, empty
  slice, valid export, sample count, int16 dtype, clipping, boundary clamping.
* ``_validate_and_slice``: exercised implicitly by both export functions.
* ``export_segment_mp3``: invalid bitrate, None audio, zero sample rate,
  end ≤ start, empty slice, successful write (soundfile mocked), soundfile
  write failure propagated as RuntimeError.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import scipy.io.wavfile as wav

from infra.audio_export import export_segment_mp3, export_segment_wav


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sine(sr: int = 44100, duration: float = 1.0) -> np.ndarray:
    """Return a 440 Hz sine wave of the requested duration."""
    t = np.arange(int(sr * duration)) / sr
    return (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


# ===========================================================================
# export_segment_wav
# ===========================================================================

class TestExportSegmentWavErrors:
    def test_none_audio_data_raises_runtime_error(self, tmp_path):
        """RuntimeError when audio_data is None."""
        with pytest.raises(RuntimeError, match="Aucune donnée audio"):
            export_segment_wav(None, 44100, 0.0, 1.0, tmp_path / "out.wav")

    def test_zero_sample_rate_raises_runtime_error(self, tmp_path):
        """RuntimeError when sample_rate is 0."""
        audio = np.zeros(100, dtype=np.float32)
        with pytest.raises(RuntimeError, match="Aucune donnée audio"):
            export_segment_wav(audio, 0, 0.0, 1.0, tmp_path / "out.wav")

    def test_end_equal_start_raises_value_error(self, tmp_path):
        """ValueError when end_sec == start_sec."""
        audio = np.zeros(44100, dtype=np.float32)
        with pytest.raises(ValueError, match="borne de fin"):
            export_segment_wav(audio, 44100, 1.0, 1.0, tmp_path / "out.wav")

    def test_end_before_start_raises_value_error(self, tmp_path):
        """ValueError when end_sec < start_sec."""
        audio = np.zeros(44100, dtype=np.float32)
        with pytest.raises(ValueError, match="borne de fin"):
            export_segment_wav(audio, 44100, 2.0, 1.0, tmp_path / "out.wav")

    def test_empty_slice_raises_value_error(self, tmp_path):
        """ValueError when the slice contains no samples."""
        audio = np.zeros(1, dtype=np.float32)
        with pytest.raises(ValueError, match="aucun échantillon"):
            export_segment_wav(audio, 1, 5.0, 10.0, tmp_path / "out.wav")


class TestExportSegmentWavSuccess:
    def test_valid_export_creates_file(self, tmp_path):
        """export_segment_wav creates the output WAV file."""
        audio = _sine()
        out = tmp_path / "segment.wav"
        export_segment_wav(audio, 44100, 0.0, 0.5, out)
        assert out.exists()

    def test_exported_wav_has_correct_sample_count(self, tmp_path):
        """The exported WAV contains the expected number of samples."""
        sr = 44100
        audio = np.zeros(sr * 2, dtype=np.float32)
        out = tmp_path / "segment.wav"
        export_segment_wav(audio, sr, 0.5, 1.0, out)
        _, data = wav.read(str(out))
        assert len(data) == sr // 2  # 0.5 s × 44 100

    def test_exported_wav_is_int16(self, tmp_path):
        """The exported WAV is 16-bit PCM."""
        sr = 22050
        audio = 0.5 * np.ones(sr, dtype=np.float32)
        out = tmp_path / "out.wav"
        export_segment_wav(audio, sr, 0.0, 1.0, out)
        _, data = wav.read(str(out))
        assert data.dtype == np.int16

    def test_clipping_applied_to_out_of_range_values(self, tmp_path):
        """Values outside [-1, 1] are clipped before int16 conversion."""
        sr = 100
        audio = np.array([2.0, -3.0, 0.5], dtype=np.float32)
        out = tmp_path / "clipped.wav"
        export_segment_wav(audio, sr, 0.0, len(audio) / sr, out)
        _, data = wav.read(str(out))
        assert data[0] == 32767    # clipped +1 → 32 767
        assert data[1] == -32767   # clipped -1 → −32 767

    def test_start_before_zero_is_clamped(self, tmp_path):
        """Negative start_sec is silently clamped to sample 0."""
        sr = 44100
        audio = np.zeros(sr, dtype=np.float32)
        out = tmp_path / "out.wav"
        export_segment_wav(audio, sr, -1.0, 0.5, out)
        assert out.exists()

    def test_end_beyond_length_is_clamped(self, tmp_path):
        """end_sec beyond the audio length is clamped to the last sample."""
        sr = 44100
        audio = np.zeros(sr, dtype=np.float32)
        out = tmp_path / "out.wav"
        export_segment_wav(audio, sr, 0.0, 100.0, out)
        _, data = wav.read(str(out))
        assert len(data) == sr


# ===========================================================================
# export_segment_mp3
# ===========================================================================

class TestExportSegmentMp3Errors:
    def test_invalid_bitrate_raises_value_error(self, tmp_path):
        """ValueError when bitrate_kbps is not in the accepted set."""
        audio = _sine()
        with pytest.raises(ValueError, match="Débit invalide"):
            export_segment_mp3(
                audio, 44100, 0.0, 0.5, tmp_path / "out.mp3", bitrate_kbps=999
            )

    def test_none_audio_data_raises_runtime_error(self, tmp_path):
        """RuntimeError when audio_data is None."""
        with pytest.raises(RuntimeError, match="Aucune donnée audio"):
            export_segment_mp3(None, 44100, 0.0, 1.0, tmp_path / "out.mp3")

    def test_zero_sample_rate_raises_runtime_error(self, tmp_path):
        """RuntimeError when sample_rate is 0."""
        audio = np.zeros(100, dtype=np.float32)
        with pytest.raises(RuntimeError, match="Aucune donnée audio"):
            export_segment_mp3(audio, 0, 0.0, 1.0, tmp_path / "out.mp3")

    def test_end_equal_start_raises_value_error(self, tmp_path):
        """ValueError when end_sec == start_sec."""
        audio = np.zeros(44100, dtype=np.float32)
        with pytest.raises(ValueError, match="borne de fin"):
            export_segment_mp3(audio, 44100, 1.0, 1.0, tmp_path / "out.mp3")

    def test_end_before_start_raises_value_error(self, tmp_path):
        """ValueError when end_sec < start_sec."""
        audio = np.zeros(44100, dtype=np.float32)
        with pytest.raises(ValueError, match="borne de fin"):
            export_segment_mp3(audio, 44100, 2.0, 1.0, tmp_path / "out.mp3")

    def test_empty_slice_raises_value_error(self, tmp_path):
        """ValueError when the slice contains no samples."""
        audio = np.zeros(1, dtype=np.float32)
        with pytest.raises(ValueError, match="aucun échantillon"):
            export_segment_mp3(audio, 1, 5.0, 10.0, tmp_path / "out.mp3")

    def test_soundfile_write_failure_raises_runtime_error(self, tmp_path):
        """A soundfile write error is wrapped in a RuntimeError."""
        audio = _sine()
        with patch("infra.audio_export.sf.write", side_effect=OSError("codec error")):
            with pytest.raises(RuntimeError, match="Impossible d'écrire le fichier MP3"):
                export_segment_mp3(audio, 44100, 0.0, 0.5, tmp_path / "out.mp3")


class TestExportSegmentMp3Success:
    def test_valid_bitrates_accepted(self, tmp_path):
        """All accepted bitrate values pass the validation check."""
        audio = _sine()
        valid_bitrates = [64, 96, 128, 160, 192, 256, 320]
        for bps in valid_bitrates:
            out = tmp_path / f"out_{bps}.mp3"
            with patch("infra.audio_export.sf.write") as mock_write:
                export_segment_mp3(audio, 44100, 0.0, 0.5, out, bitrate_kbps=bps)
                mock_write.assert_called_once()
                # Reset for next iteration
                mock_write.reset_mock()

    def test_soundfile_write_called_with_mp3_format(self, tmp_path):
        """export_segment_mp3 calls sf.write with format='MP3'."""
        audio = _sine()
        out = tmp_path / "out.mp3"
        with patch("infra.audio_export.sf.write") as mock_write:
            export_segment_mp3(audio, 44100, 0.0, 0.5, out)
            args, kwargs = mock_write.call_args
            assert kwargs.get("format") == "MP3"
            assert kwargs.get("subtype") == "MPEG_LAYER_III"

    def test_soundfile_write_receives_correct_sample_rate(self, tmp_path):
        """export_segment_mp3 passes the sample_rate to sf.write."""
        sr = 22050
        audio = _sine(sr=sr)
        out = tmp_path / "out.mp3"
        with patch("infra.audio_export.sf.write") as mock_write:
            export_segment_mp3(audio, sr, 0.0, 0.5, out)
            _, call_kwargs = mock_write.call_args
            # Positional args: (path, data, sample_rate)
            call_args = mock_write.call_args[0]
            assert call_args[2] == sr

    def test_soundfile_write_receives_float32_data(self, tmp_path):
        """export_segment_mp3 passes float32 audio data to sf.write."""
        audio = _sine()
        out = tmp_path / "out.mp3"
        written_data = []
        with patch(
            "infra.audio_export.sf.write",
            side_effect=lambda path, data, sr, **kw: written_data.append(data),
        ):
            export_segment_mp3(audio, 44100, 0.0, 0.5, out)
        assert len(written_data) == 1
        assert written_data[0].dtype == np.float32

    def test_default_bitrate_is_192(self, tmp_path):
        """Default bitrate_kbps is 192 (no ValueError raised)."""
        audio = _sine()
        out = tmp_path / "out.mp3"
        with patch("infra.audio_export.sf.write"):
            # Should not raise — 192 is in the valid set
            export_segment_mp3(audio, 44100, 0.0, 0.5, out)

    def test_clipping_applied_before_write(self, tmp_path):
        """Values outside [-1, 1] are clipped to float32 before sf.write."""
        sr = 100
        audio = np.array([2.0, -3.0, 0.5], dtype=np.float32)
        written_data = []
        with patch(
            "infra.audio_export.sf.write",
            side_effect=lambda path, data, sr, **kw: written_data.append(data.copy()),
        ):
            export_segment_mp3(audio, sr, 0.0, len(audio) / sr, tmp_path / "out.mp3")
        assert written_data[0][0] == pytest.approx(1.0)
        assert written_data[0][1] == pytest.approx(-1.0)

    def test_negative_start_clamped(self, tmp_path):
        """Negative start_sec is clamped to 0 without error."""
        audio = _sine()
        out = tmp_path / "out.mp3"
        with patch("infra.audio_export.sf.write"):
            export_segment_mp3(audio, 44100, -2.0, 0.5, out)

    def test_end_beyond_length_clamped(self, tmp_path):
        """end_sec beyond audio length is clamped to last sample."""
        audio = _sine()
        out = tmp_path / "out.mp3"
        written_data = []
        with patch(
            "infra.audio_export.sf.write",
            side_effect=lambda path, data, sr, **kw: written_data.append(len(data)),
        ):
            export_segment_mp3(audio, 44100, 0.0, 999.0, out)
        assert written_data[0] == len(audio)


# ===========================================================================
# _validate_and_slice (direct unit tests for the shared helper)
# ===========================================================================

class TestValidateAndSlice:
    def test_returns_float32_array(self):
        """_validate_and_slice always returns a float32 array."""
        from infra.audio_export import _validate_and_slice
        audio = np.zeros(100, dtype=np.float64)  # float64 input
        result = _validate_and_slice(audio, 100, 0.0, 0.5)
        assert result.dtype == np.float32

    def test_slice_length_matches_seconds(self):
        """Slice length corresponds to the requested time window."""
        from infra.audio_export import _validate_and_slice
        sr = 1000
        audio = np.zeros(sr * 2, dtype=np.float32)
        result = _validate_and_slice(audio, sr, 0.5, 1.0)
        assert len(result) == 500  # 0.5 s × 1000 Hz

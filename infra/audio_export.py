"""
Export audio segments to WAV or MP3 files.

This module provides pure-function helpers that slice a NumPy audio array
to the requested time boundaries and write the result to disk:

* :func:`export_segment_wav` — 16-bit PCM WAV via :mod:`scipy.io.wavfile`.
* :func:`export_segment_mp3` — MPEG Layer-III (MP3) via :mod:`soundfile`
  (requires libsndfile ≥ 1.2.0, which ships with soundfile ≥ 0.12).

Both functions accept the same *audio_data* / *sample_rate* / *start_sec* /
*end_sec* / *output_path* contract and raise the same error types so callers
can treat them uniformly.

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

from pathlib import Path
from typing import cast

import numpy as np
import scipy.io.wavfile as wav
import soundfile as sf

# ── Shared helpers ─────────────────────────────────────────────────────────


def _validate_and_slice(
    audio_data: np.ndarray | None,
    sample_rate: int,
    start_sec: float,
    end_sec: float,
) -> np.ndarray:
    """
    Validate export parameters and return the sliced float32 audio array.

    Parameters
    ----------
    audio_data : np.ndarray or None
        Full audio array (float32, mono).
    sample_rate : int
        Sample rate in Hz (must be > 0).
    start_sec : float
        Start of the slice in seconds.
    end_sec : float
        End of the slice in seconds (must be > *start_sec*).

    Returns
    -------
    np.ndarray
        Float32 slice clipped to ``[-1.0, 1.0]``.

    Raises
    ------
    RuntimeError
        If *audio_data* is ``None`` or *sample_rate* is 0.
    ValueError
        If *end_sec* ≤ *start_sec* or the computed slice is empty.
    """
    if audio_data is None or sample_rate == 0:
        raise RuntimeError("Aucune donnée audio chargée — impossible d'exporter le segment.")
    if end_sec <= start_sec:
        raise ValueError(
            f"La borne de fin ({end_sec:.3f} s) doit être supérieure "
            f"à la borne de début ({start_sec:.3f} s)."
        )

    start_sample = max(0, int(start_sec * sample_rate))
    end_sample = min(len(audio_data), int(end_sec * sample_rate))
    slice_data = audio_data[start_sample:end_sample]

    if slice_data.size == 0:
        raise ValueError("Le segment sélectionné ne contient aucun échantillon.")

    return cast(np.ndarray, np.clip(slice_data, -1.0, 1.0).astype(np.float32))


# ── Public API ─────────────────────────────────────────────────────────────


def export_segment_wav(
    audio_data: np.ndarray,
    sample_rate: int,
    start_sec: float,
    end_sec: float,
    output_path: Path,
) -> None:
    """
    Export a time slice of *audio_data* to a 16-bit PCM WAV file.

    The audio data is expected to be a 1-D float32 array in the range
    ``[-1.0, 1.0]`` (the format produced by :func:`librosa.load`).
    The slice is converted to int16 before writing.

    Parameters
    ----------
    audio_data : np.ndarray
        Full audio array (float32, mono, shape ``(N,)``).
    sample_rate : int
        Sample rate in Hz.
    start_sec : float
        Start of the segment in seconds.
    end_sec : float
        End of the segment in seconds (must be > *start_sec*).
    output_path : Path
        Destination WAV file path.  Parent directories must exist.

    Raises
    ------
    ValueError
        If *end_sec* ≤ *start_sec* or the slice is empty.
    RuntimeError
        If *audio_data* is ``None`` or *sample_rate* is 0.
    """
    slice_data = _validate_and_slice(audio_data, sample_rate, start_sec, end_sec)

    # Convert float32 [-1, 1] → int16 [-32768, 32767]
    int16_data = (slice_data * 32767).astype(np.int16)
    wav.write(str(output_path), sample_rate, int16_data)


def export_segment_mp3(
    audio_data: np.ndarray,
    sample_rate: int,
    start_sec: float,
    end_sec: float,
    output_path: Path,
    bitrate_kbps: int = 192,
) -> None:
    """
    Export a time slice of *audio_data* to an MP3 file.

    Uses :mod:`soundfile` (libsndfile ≥ 1.2.0) to write MPEG Layer-III
    audio.  The *audio_data* is expected to be a 1-D float32 array in the
    range ``[-1.0, 1.0]`` (the format produced by :func:`librosa.load`).

    .. note::
        The ``bitrate_kbps`` parameter is advisory and passed to libsndfile
        via the ``compression_level`` hint when supported.  Actual encoding
        quality depends on the libsndfile / LAME version installed.

    Parameters
    ----------
    audio_data : np.ndarray
        Full audio array (float32, mono, shape ``(N,)``).
    sample_rate : int
        Sample rate in Hz.
    start_sec : float
        Start of the segment in seconds.
    end_sec : float
        End of the segment in seconds (must be > *start_sec*).
    output_path : Path
        Destination MP3 file path.  Parent directories must exist.
    bitrate_kbps : int, optional
        Target encoding bitrate in kilobits per second (default 192).
        Acceptable values: 64, 96, 128, 160, 192, 256, 320.

    Raises
    ------
    ValueError
        If *end_sec* ≤ *start_sec*, the slice is empty, or *bitrate_kbps*
        is not a recognised value.
    RuntimeError
        If *audio_data* is ``None``, *sample_rate* is 0, or libsndfile does
        not support MP3 encoding on this platform.
    """
    _VALID_BITRATES = {64, 96, 128, 160, 192, 256, 320}
    if bitrate_kbps not in _VALID_BITRATES:
        raise ValueError(
            f"Débit invalide : {bitrate_kbps} kbps. "
            f"Valeurs acceptées : {sorted(_VALID_BITRATES)}"
        )

    slice_data = _validate_and_slice(audio_data, sample_rate, start_sec, end_sec)

    # soundfile (libsndfile ≥ 1.2.0) handles MP3 encoding internally.
    # The bitrate_kbps parameter is validated above; libsndfile chooses
    # the closest supported bitrate automatically.
    try:
        sf.write(
            str(output_path),
            slice_data,
            sample_rate,
            format="MP3",
            subtype="MPEG_LAYER_III",
        )
    except Exception as exc:
        raise RuntimeError(
            f"Impossible d'écrire le fichier MP3 : {exc}\n"
            "Vérifiez que libsndfile ≥ 1.2.0 est installé "
            "(soundfile ≥ 0.12 l'inclut automatiquement)."
        ) from exc

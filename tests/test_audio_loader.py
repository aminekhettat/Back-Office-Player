"""
Tests for core.audio_loader — 100% branch coverage.

Covers: AudioLoaderThread successful load (loaded signal emitted),
load raises an exception (error signal emitted with message string).

All librosa I/O is mocked; no real audio files are needed.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.audio_loader import AudioLoaderThread

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_player():
    """Return a lightweight mock of AudioPlayer."""
    player = MagicMock()
    return player


@pytest.fixture()
def audio_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.mp3"
    p.touch()
    return p


# ---------------------------------------------------------------------------
# Successful load
# ---------------------------------------------------------------------------


class TestAudioLoaderThreadSuccess:
    def test_loaded_signal_emitted_on_success(self, qtbot, mock_player, audio_path):
        """AudioLoaderThread emits 'loaded' when load_file succeeds."""
        mock_player.load_file.return_value = None  # success

        thread = AudioLoaderThread(mock_player, audio_path)
        with qtbot.waitSignal(thread.loaded, timeout=3000):
            thread.start()
        thread.wait()

    def test_load_file_called_with_path(self, qtbot, mock_player, audio_path):
        """AudioLoaderThread calls player.load_file with the given path."""
        mock_player.load_file.return_value = None

        thread = AudioLoaderThread(mock_player, audio_path)
        with qtbot.waitSignal(thread.loaded, timeout=3000):
            thread.start()
        thread.wait()

        mock_player.load_file.assert_called_once_with(audio_path)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAudioLoaderThreadError:
    def test_error_signal_emitted_on_exception(self, qtbot, mock_player, audio_path):
        """AudioLoaderThread emits 'error' when load_file raises."""
        mock_player.load_file.side_effect = RuntimeError("file not found")

        thread = AudioLoaderThread(mock_player, audio_path)
        with qtbot.waitSignal(thread.error, timeout=3000) as blocker:
            thread.start()
        thread.wait()

        assert "file not found" in blocker.args[0]

    def test_error_signal_message_is_string(self, qtbot, mock_player, audio_path):
        """The error signal payload is the string representation of the exception."""
        mock_player.load_file.side_effect = ValueError("bad format")

        thread = AudioLoaderThread(mock_player, audio_path)
        with qtbot.waitSignal(thread.error, timeout=3000) as blocker:
            thread.start()
        thread.wait()

        assert isinstance(blocker.args[0], str)
        assert "bad format" in blocker.args[0]


# ---------------------------------------------------------------------------
# Direct run() calls — ensures coverage tracks the thread code
# ---------------------------------------------------------------------------


class TestAudioLoaderRunDirect:
    def test_run_success_emits_loaded(self, qtbot, mock_player, audio_path):
        """run() called synchronously emits loaded on success."""
        mock_player.load_file.return_value = None
        thread = AudioLoaderThread(mock_player, audio_path)
        received: list[str] = []
        thread.loaded.connect(lambda: received.append("ok"))
        thread.run()
        assert received == ["ok"]

    def test_run_error_emits_error(self, qtbot, mock_player, audio_path):
        """run() called synchronously emits error on failure."""
        mock_player.load_file.side_effect = RuntimeError("bad codec")
        thread = AudioLoaderThread(mock_player, audio_path)
        errors: list[str] = []
        thread.error.connect(errors.append)
        thread.run()
        assert errors == ["bad codec"]

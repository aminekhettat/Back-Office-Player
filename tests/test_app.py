"""
Tests for app.py (application entry point).

Verifies that main() can be imported and called without error by mocking
all external dependencies: QApplication, AudioPlayer, SegmentManager,
MainWindowQt, and sys.exit.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestMain:
    def test_main_is_importable(self):
        """app.main can be imported without side effects."""
        import app  # noqa: F401
        assert hasattr(app, "main")

    def test_main_runs_without_real_qt(self, monkeypatch):
        """main() completes without error when all dependencies are mocked."""
        # We need a real QApplication for PySide6 (or at least not crash).
        # Use the global QApplication if available (provided by pytest-qt),
        # and mock everything else.

        mock_player = MagicMock()
        mock_manager = MagicMock()
        mock_window = MagicMock()

        with (
            patch("app.AudioPlayer", return_value=mock_player),
            patch("app.SegmentManager", return_value=mock_manager),
            patch("app.MainWindowQt", return_value=mock_window),
            patch("sys.exit") as mock_exit,
        ):
            # Patch QApplication to avoid creating a second instance
            mock_app = MagicMock()
            mock_app.exec.return_value = 0
            with patch("app.QApplication", return_value=mock_app):
                import app as app_module
                app_module.main()

        # sys.exit should have been called with the exec() return value
        mock_exit.assert_called_once_with(0)

    def test_main_shows_window(self, monkeypatch):
        """main() calls window.show() on the MainWindowQt instance."""
        mock_window = MagicMock()
        mock_app = MagicMock()
        mock_app.exec.return_value = 0

        with (
            patch("app.AudioPlayer", return_value=MagicMock()),
            patch("app.SegmentManager", return_value=MagicMock()),
            patch("app.MainWindowQt", return_value=mock_window),
            patch("app.QApplication", return_value=mock_app),
            patch("sys.exit"),
        ):
            import app as app_module
            app_module.main()

        mock_window.show.assert_called_once()

    def test_main_sets_app_metadata(self, monkeypatch):
        """main() configures the application name and organisation."""
        mock_app = MagicMock()
        mock_app.exec.return_value = 0

        with (
            patch("app.AudioPlayer", return_value=MagicMock()),
            patch("app.SegmentManager", return_value=MagicMock()),
            patch("app.MainWindowQt", return_value=MagicMock()),
            patch("app.QApplication", return_value=mock_app),
            patch("sys.exit"),
        ):
            import app as app_module
            app_module.main()

        mock_app.setApplicationName.assert_called_once_with("BOP")
        mock_app.setOrganizationName.assert_called_once_with("BLINDSYSTEMS")

"""
Application entry point for Back-Office Player (PySide6).

Initialises the main components (AudioPlayer, SegmentManager, MainWindowQt)
and starts the PySide6 Qt event loop.

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

import logging
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from __version__ import __version__
from core.audio_player_native import AudioPlayer
from core.segment_manager import SegmentManager
from infra.i18n import init_language
from infra.settings import load_settings
from ui.main_window import MainWindowQt


def main() -> None:
    """
    Main function of the application.

    Steps
    -----
    - Configure application-wide logging.
    - Create the Qt application.
    - Set the global application icon.
    - Create an :class:`AudioPlayer` instance.
    - Create an empty :class:`SegmentManager` (no audio file yet).
    - Instantiate the :class:`MainWindowQt` with these objects.
    - Start the Qt main loop.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Create the Qt application object.
    app = QApplication(sys.argv)

    # Identify the application for platform services (e.g. user-data dirs).
    app.setApplicationName("BOP")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BLINDSYSTEMS")

    # Set the global application icon (taskbar, Alt+Tab, etc.).
    # The icon file is expected at: resources/BOP.ico
    app.setWindowIcon(QIcon("resources/BOP.ico"))

    # Initialise language from user settings (falls back to OS locale).
    settings = load_settings()
    init_language(settings.get("language"))

    # Create the audio player (core logic).
    audio_player = AudioPlayer()

    # At startup, no audio file is loaded yet, so the segment manager is empty.
    segment_manager = SegmentManager()

    # Instantiate the main window (Qt UI).
    window = MainWindowQt(audio_player, segment_manager)
    window.show()

    # Start the Qt event loop.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

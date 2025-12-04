"""
Application entry point for Back-Office Player (Qt version).

This module initializes the main components (audio player, segment manager,
Qt main window) and starts the Qt event loop.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.3.0
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.audio_player import AudioPlayer
from core.segment_manager import SegmentManager
from ui.main_window import MainWindowQt


def main() -> None:
    """
    Main function of the application.

    Steps
    -----
    - Create the Qt application.
    - Set the global application icon.
    - Create an :class:`AudioPlayer` instance.
    - Create an empty :class:`SegmentManager` (no audio file yet).
    - Instantiate the :class:`MainWindowQt` with these objects.
    - Start the Qt main loop.
    """
    # Create the Qt application object.
    app = QApplication(sys.argv)

    # Set the global application icon (taskbar, Alt+Tab, etc.).
    # The icon file is expected at: resources/BOP.ico
    app.setWindowIcon(QIcon("resources/BOP.ico"))

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

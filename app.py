"""
Application entry point.

This module initializes the main components (audio player, segment manager,
main window) and starts the Tkinter event loop.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2025-12-02
:version: 0.1.0
"""

from tkinter import Tk

from core.audio_player import AudioPlayer
from core.segment_manager import SegmentManager
from ui.main_window import MainWindow


def main() -> None:
    """
    Main function of the application.

    Steps
    -----
    - Create the main Tkinter window.
    - Create an :class:`AudioPlayer` instance.
    - Create an empty :class:`SegmentManager` (no audio file yet).
    - Instantiate the :class:`MainWindow` with these objects.
    - Start the Tkinter main loop.
    """
    # Create the main Tkinter window.
    root = Tk()
    root.title("Boîte à Oeuvre – Practice Tool")

    # Create the audio player (core logic).
    audio_player = AudioPlayer()

    # At startup, no audio file is loaded yet, so the segment manager is empty.
    segment_manager = SegmentManager()

    # Instantiate the main window (UI).
    app = MainWindow(root, audio_player, segment_manager)

    # Start the Tkinter event loop.
    app.run()


if __name__ == "__main__":
    main()

# Back-Office Player – Audio Practice Tool

Back-Office Player is a Windows desktop application written in Python that helps music students practice at home using rehearsal recordings.

The application focuses on:
- Simple, robust audio playback.
- A–B looping (repeat a selected part of the track).
- A keyboard- and screen-reader-friendly user interface.

The project is developed by **BLIND SYSTEMS** for the students of the **Culture Musique** association.

---

## Main Features

- Play common audio formats: `mp3`, `wav`, `wma`, `flac`, `ogg` (depending on VLC support).
- Basic transport controls: **Play**, **Pause**, **Stop**.
- Volume control (0–100) with persistent default volume.
- Time position slider and time display `mm:ss / mm:ss`.
- A–B loop:
  - Set **Point A** and **Point B** on the timeline.
  - Loop continuously between A and B.
  - Clear A/B and disable looping at any time.
- Keyboard shortcuts to keep the app usable without a mouse.
- Settings stored in a simple JSON file (`settings.json`).
- Modular architecture, ready for new features (named segments, bookmarks, etc.).
- Code documented with Sphinx-friendly docstrings and comments.

---

## Accessibility

The UI is designed to be usable with a screen reader and keyboard:

- All buttons and controls have clear text labels.
- The main actions are accessible via keyboard shortcuts.
- No drag-and-drop or complex mouse gestures are required for core usage.
- Status messages (e.g. file loaded, A/B points set) are exposed via a status label that screen readers can announce.

Future improvements may include:
- More shortcuts for A/B management and segment navigation.
- Better focus management and announcements for critical events.

---

## Architecture Overview

The project is organized into three main layers:

- `core/` – Domain logic, independent from the UI:
  - `audio_player.py`: wraps `python-vlc` for audio playback.
  - `segment.py`: defines an A–B segment (name, start time, end time).
  - `segment_manager.py`: manages collections of segments.

- `infra/` – Infrastructure and persistence:
  - `persistence.py`: saves/loads segments associated with an audio file (JSON).
  - `settings.py`: saves/loads simple application settings (last folder, volume).

- `ui/` – Tkinter user interface:
  - `main_window.py`: main window, widgets, callbacks, keyboard shortcuts.

- Root:
  - `app.py`: entry point that wires everything together and starts Tkinter.

This separation makes it easier to maintain and test the non-UI logic and to evolve the UI independently.

---

## Requirements

- **Python** 3.10+ (recommended)
- **VLC** media player installed on the system
- Python packages (installed via `pip`):
  - `python-vlc`
  - `tkinter` (usually comes with standard Python on Windows)
  - (Optional for documentation) `sphinx` and related extensions

A `requirements.txt` file is provided for installing Python dependencies.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR-USER/back-office-player.git
   cd back-office-player

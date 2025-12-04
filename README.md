# Back-Office Player (BOP) – Audio Practice Tool

Back-Office Player (BOP) is a Windows desktop application written in Python that helps music students practice at home using rehearsal recordings.

The application focuses on:
- Simple, robust audio playback.
- A–B looping (repeat a selected part of the track).
- A keyboard- and screen-reader-friendly user interface (Qt / PySide6).
- A clear, minimal design with a dedicated application icon.

The project is developed by **BLIND SYSTEMS** for the students of the **Culture Musique** association.

---

## Main Features

- Play common audio formats supported by VLC: `mp3`, `wav`, `wma`, `flac`, `ogg`, etc.
- Basic transport controls: **Play**, **Pause**, **Stop**.
- Volume control (0–100) with persistent default volume.
- Time position slider and time display `mm:ss / mm:ss`.
- A–B loop:
  - Set **Point A** and **Point B** on the timeline.
  - Loop continuously between A and B.
  - Clear A/B and disable looping at any time.
- Keyboard navigation:
  - Full control of the UI with Tab / Shift+Tab.
  - Position slider controllable with **left/right arrow keys** when focused.
- Keyboard shortcuts for frequent actions.
- Settings stored in a simple JSON file (`settings.json`).
- Modular architecture (core / infra / UI) ready for extensions.
- Custom application icon (`BOP.ico`).

---

## Accessibility

The UI is built with **Qt (PySide6)** for better compatibility with screen readers (NVDA, JAWS, etc.) on Windows:

- All buttons and controls have clear text labels.
- Accessible names and descriptions are set where helpful.
- Standard keyboard behavior is preserved:
  - When a button has focus, **Space** or **Enter** activate it.
  - When the position slider has focus, **left/right arrows** move the cursor and update playback position.
- No drag-and-drop or complex mouse gestures are required for core usage.
- Status messages (e.g. file loaded, A/B points set) are exposed via a status label that screen readers can announce.

Future accessibility improvements may include:
- More shortcuts for segment navigation.
- Additional status announcements for critical events.

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

- `ui/` – Qt user interface:
  - `main_window.py`: main window, widgets, callbacks, keyboard shortcuts, and A–B loop logic.

- Root:
  - `app.py`: entry point that wires everything together and starts the Qt event loop.
  - `resources/BOPIcon.png`: source PNG icon (for design and conversions).
  - `resources/BOP.ico`: Windows icon used by the application.

This separation makes it easier to maintain and test the non-UI logic and to evolve the UI independently.

---

## Requirements

- **Windows**
- **Python** 3.10+ (recommended)
- **VLC media player** installed on the system
- Python packages (installed via `pip`):
  - `PySide6`
  - `python-vlc`
  - (Optional for documentation) `sphinx` and related extensions

A `requirements.txt` file is provided for installing Python dependencies.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR-USER/back-office-player.git
   cd back-office-player

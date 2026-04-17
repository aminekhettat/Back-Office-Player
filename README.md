# Back-Office Player (BOP) – Audio Practice Tool

Back-Office Player (BOP) is a Windows desktop application written in Python that helps music students practice at home using rehearsal recordings.

The application focuses on:
- Simple, robust audio playback (**no VLC required** — native engine using librosa + sounddevice).
- A–B looping (repeat a selected part of the track).
- Named segments (save, navigate and manage practice sections).
- Tempo control (slow down or speed up playback).
- Export / import practice configurations (`.bop` files).
- A keyboard- and screen-reader-friendly user interface (Qt / PySide6).
- A clear, minimal design with a dedicated application icon.

**Current version:** 1.1.1

The project is developed by **[BLIND SYSTEMS](https://www.blindsystems.org)**
for the students of the **[Culture Musique](https://www.sabamusic.fr)**
association.

---

## Main Features

- Play common audio formats supported by librosa: `mp3`, `wav`, `wma`, `flac`, `ogg`, etc.
- Basic transport controls: **Play**, **Pause**, **Stop**.
- Volume control (0–100) with persistent default volume.
- Time position slider and time display `mm:ss / mm:ss`.
- A–B loop:
  - Set **Point A** and **Point B** on the timeline.
  - Loop continuously between A and B.
  - Clear A/B and disable looping at any time.
- **Named segments** (new in v0.3):
  - Save the current A–B loop as a named segment (e.g. "Verse 1", "Chorus").
  - View all segments in a dedicated list widget.
  - Jump to any segment with a single click or keyboard.
  - Delete segments individually.
  - Segments auto-loaded when opening the same audio file again.
- **Tempo control** (new in v0.3):
  - Slider from 50% to 200% of the original speed.
  - Affects playback position tracking.
- **Export / Import practice config** (new in v0.3):
  - Save all segments + volume + tempo to a `.bop` file.
  - Share or reload practice configurations at any time.
- Keyboard navigation:
  - Full control of the UI with Tab / Shift+Tab.
  - Position slider controllable with **left/right arrow keys** when focused.
  - Tempo slider controllable with **up/down arrow keys** when focused.
- Keyboard shortcuts for frequent actions.
- Settings stored in a simple JSON file (`settings.json`).
- Modular architecture (`core` / `infra` / `ui`) ready for extensions.
- Custom application icon (`BOP.ico`).

---

## Accessibility

The UI is built with **Qt (PySide6)** for better compatibility with screen readers (NVDA, JAWS, etc.) on Windows:

- All buttons and controls have clear text labels.
- Accessible names and descriptions are set where useful.
- Standard keyboard behavior is preserved:
  - When a button has focus, **Space** or **Enter** activate it.
  - When the position slider has focus, **left/right arrows** move the cursor and update playback position.
  - When the tempo slider has focus, **up/down arrows** adjust the tempo.
- No drag-and-drop or complex mouse gestures are required for core usage.
- Status messages (file loaded, A/B points set, segments saved, etc.) are exposed via a status label that screen readers can announce.

---

## Architecture Overview

The project is organized into three main layers:

- `core/` – Domain logic, independent from the UI:
  - `audio_player_native.py`: native audio player using `librosa` + `sounddevice` (no VLC). Supports tempo control, seeking, and volume.
  - `audio_player.py`: legacy VLC-based player (kept for reference, not used).
  - `segment.py`: defines an A–B segment (name, start time, end time).
  - `segment_manager.py`: manages collections of segments.

- `infra/` – Infrastructure and persistence:
  - `persistence.py`: saves/loads segments associated with an audio file (JSON, stored next to the audio file as `<filename>.segments.json`).
  - `settings.py`: saves/loads simple application settings (last folder, volume).

- `ui/` – Qt user interface:
  - `main_window.py`: main window, widgets, callbacks, keyboard shortcuts, A–B loop logic, tempo, segment management, and config import/export.
  - `segment_list_widget.py`: reusable Qt widget displaying the segment list with jump and delete controls.

- Root:
  - `app.py`: entry point that wires everything together and starts the Qt event loop.
  - `resources/BOPIcon.png`: source PNG icon (for design and conversions).
  - `resources/BOP.ico`: Windows icon used by the application.

This separation makes it easier to maintain and test the non-UI logic and to evolve the UI independently.

---

## Requirements

- **Windows** (also works on Linux/macOS with minor adjustments)
- **Python** 3.10+ (recommended)
- **No VLC required** — audio is handled natively via `librosa` and `sounddevice`
- Python packages (installed via `pip`):
  - `PySide6`
  - `librosa>=0.10.0`
  - `sounddevice>=0.4.5`
  - `numpy>=1.20.0`
  - `scipy>=1.7.0`
  - (Optional for documentation) `sphinx` and related extensions

A `requirements.txt` file is provided for installing Python dependencies.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/aminekhettat/Back-Office-Player.git
   cd Back-Office-Player
   ```

2. **Create and activate a virtual environment (Windows)**

   ```bash
   python -m venv bopenv
   bopenv\Scripts\activate.bat
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** No VLC installation required. All audio decoding is handled by `librosa` and `sounddevice`.

---

## Icons

The application uses a custom icon provided in the `resources` folder:

- `resources/BOPIcon.png` – base PNG icon (for editing or future conversions).
- `resources/BOP.ico` – icon used by the application and later by installers / .exe packaging.

The icon is applied at two levels:

- Application icon (taskbar, Alt+Tab) set in `app.py`:

  ```python
  app.setWindowIcon(QIcon("resources/BOP.ico"))
  ```

- Window icon set in `ui/main_window.py`:

  ```python
  self.setWindowIcon(QIcon("resources/BOP.ico"))
  ```

---

## Running the Application from Source

With the virtual environment activated in the project folder:

```bash
python app.py
```

A window titled **"Back-Office Player (BOP)"** should appear, with the BOP icon in the title bar.

---

## Building a Windows Executable (PyInstaller)

With your virtual environment active at the project root:

```powershell
pip install pyinstaller
pyinstaller --name BackOfficePlayer --windowed --icon="resources/BOP.ico" --add-data "resources;resources" app.py
```

This produces:

```text
dist/
└─ BackOfficePlayer/
   ├─ BackOfficePlayer.exe
   └─ resources/
      └─ BOP.ico
```

You can then run:

```powershell
cd dist\BackOfficePlayer
.\BackOfficePlayer.exe
```

> **Note:** VLC is no longer required on end-user machines.

---

## Basic Usage

1. **Open an audio file**

   - Click **"Open audio file…"**, or
   - Use the keyboard shortcut **Ctrl+O**.
   - Choose a supported audio file (`.mp3`, `.wav`, etc.).

2. **Play / Pause / Stop**

   - Use the buttons **Play**, **Pause**, **Stop**, or
   - Use keyboard shortcuts:
     - **Ctrl+P**: Play
     - **Ctrl+Shift+P**: Pause
     - **Ctrl+S**: Stop

3. **Seek in the track**

   - Move focus to the position slider via Tab.
   - Use **left/right arrow keys** to move the cursor (1 second per step).
   - The label next to it shows current and total time in `mm:ss / mm:ss`.

4. **Volume**

   - Adjust **Volume** with the slider (0–100).
   - Volume is saved in `settings.json` and restored on next run.

5. **Tempo**

   - Adjust **Tempo** with the slider (50%–200%).
   - 100% = normal speed. Below 100% slows down, above 100% speeds up.
   - Use **up/down arrow keys** when the slider is focused (5% steps).

6. **A–B Loop**

   - Start playback.
   - At the desired start time, click **Set A** or use **Ctrl+Shift+A**.
   - Let the track continue, then at the desired end time, click **Set B** or use **Ctrl+Shift+B**.
   - Check **Loop A–B** to enable the loop.
   - Use **Clear A/B** to remove both points and disable looping.

7. **Named Segments**

   - Set A and B points, then click **Save Segment** (or **Ctrl+Shift+S**).
   - Enter a name for the segment (e.g. "Chorus", "Difficult passage").
   - The segment appears in the list below.
   - Double-click a segment or select it and click **Jump to Segment** to navigate to it.
   - Click **Delete Segment** to remove a segment from the list.

8. **Export / Import Configuration**

   - Click **Export Config** (or **Ctrl+E**) to save all segments, volume, and tempo to a `.bop` file.
   - Click **Import Config** (or **Ctrl+I**) to reload a previously exported `.bop` file.

---

## Keyboard Shortcuts Summary

| Shortcut | Action |
|---|---|
| **Ctrl+O** | Open audio file |
| **Ctrl+P** | Play |
| **Ctrl+Shift+P** | Pause |
| **Ctrl+S** | Stop |
| **Ctrl+Shift+A** | Set point A at current position |
| **Ctrl+Shift+B** | Set point B at current position |
| **Ctrl+Shift+S** | Save current A–B as a named segment |
| **Ctrl+E** | Export practice configuration (.bop) |
| **Ctrl+I** | Import practice configuration (.bop) |

Standard widget behavior:

- With focus on a **button**: **Space** or **Enter** activate it.
- With focus on the **position slider**:
  - **Left arrow**: move backward by 1 second.
  - **Right arrow**: move forward by 1 second.
- With focus on the **tempo slider**:
  - **Up/Down arrows**: adjust tempo by 5%.

---

## Project Structure

```text
Back-Office-Player/
├─ app.py                        # Application entry point (Qt)
├─ requirements.txt              # Python dependencies
├─ settings.json                 # Generated at runtime (user settings)
├─ resources/
│  ├─ BOPIcon.png                # Base PNG icon
│  └─ BOP.ico                   # Application icon
├─ core/
│  ├─ __init__.py
│  ├─ audio_player_native.py     # Native audio player (librosa + sounddevice)
│  ├─ audio_player.py            # Legacy VLC-based player (not used)
│  ├─ segment.py                 # Segment (A–B)
│  └─ segment_manager.py         # Segment collection management
├─ infra/
│  ├─ __init__.py
│  ├─ persistence.py             # Saving/loading segments (JSON per audio file)
│  └─ settings.py                # Saving/loading settings
├─ ui/
│  ├─ __init__.py
│  ├─ main_window.py             # Qt UI, A–B loop, tempo, segment management
│  └─ segment_list_widget.py     # Segment list widget (Qt)
└─ docs/
   ├─ conf.py
   ├─ index.rst
   └─ source/
      ├─ modules.rst
      ├─ core.rst
      ├─ infra.rst
      ├─ ui.rst
      └─ app.rst
```

---

## Documentation (Sphinx)

The code is written with Sphinx-style docstrings (module metadata, parameters, returns, etc.), which makes it easy to generate HTML documentation.

Typical steps from the project root:

```bash
bopenv\Scripts\activate.bat
cd docs
.\make.bat html
```

The generated HTML documentation is available under:

```text
docs/_build/html/index.html
```

---

## Known Limitations

- **Tempo control**: the current implementation adjusts the playback position tracking but does not apply real-time audio time-stretching. True pitch-preserving tempo change (e.g. via `pyrubberband`) is planned for a future release.
- **Volume during playback**: volume changes take effect from the next playback start, not instantly mid-stream.

---

## Future Work

Planned or possible enhancements include:

- **True time-stretching** (pitch-preserving tempo change via `pyrubberband` or similar).
- **Real-time volume control** during playback.
- **Export segment as separate audio file** using `soundfile`.
- **More keyboard shortcuts** for segment navigation.
- **Additional status announcements** for critical events.

---

## Release History

- **v0.3.0** *(current)*
  - Replaced VLC with a native audio engine (librosa + sounddevice) — no VLC required.
  - Added named segment management (save, list, jump, delete).
  - Added tempo control slider (50%–200%).
  - Added practice configuration export/import (`.bop` files).
  - New Qt widget: `SegmentListWidget`.
  - New keyboard shortcuts: Ctrl+Shift+S, Ctrl+E, Ctrl+I.

- **v1.0.0**
  First stable release of Back-Office Player (BOP):
  - Accessible Qt-based UI (keyboard + screen reader friendly).
  - A–B loop practice.
  - Position navigation with arrow keys.
  - Sphinx documentation.
  - PyInstaller Windows executable.

- **v0.2.0**
  Internal development version (not publicly distributed).

---

## Contributing

Contributions are welcome as long as they respect:

- The project's accessibility goals (keyboard / screen-reader first).
- The modular architecture (separating core, infra, and UI).
- The existing coding style and documentation format.

Before submitting a pull request:

1. Make sure the code runs without errors on Windows.
2. Keep docstrings and comments in English.
3. Update or add Sphinx-style docstrings for new modules and functions.

---

## License

This project is licensed under the **Apache License 2.0**.

```text
Copyright (c) 2025 BLIND SYSTEMS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

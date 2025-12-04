# Back-Office Player (BOP) – Audio Practice Tool

Back-Office Player (BOP) is a Windows desktop application written in Python that helps music students practice at home using rehearsal recordings.

The application focuses on:
- Simple, robust audio playback.
- A–B looping (repeat a selected part of the track).
- A keyboard- and screen-reader-friendly user interface (Qt / PySide6).
- A clear, minimal design with a dedicated application icon.

**Current version:** 1.0.0  

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
- Accessible names and descriptions are set where useful.
- Standard keyboard behavior is preserved:
  - When a button has focus, **Space** or **Enter** activate it.
  - When the position slider has focus, **left/right arrows** move the cursor and update playback position.
- No drag-and-drop or complex mouse gestures are required for core usage.
- Status messages (file loaded, A/B points set, etc.) are exposed via a status label that screen readers can announce.

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
   git clone https://github.com/aminekhettat/back-office-player.git
   cd back-office-player
````

2. **Create and activate a virtual environment (Windows)**

   ```bash
   python -m venv bopenv
   bopenv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install VLC**

   * Install VLC media player from the official website.
   * Ensure VLC is correctly installed so that `python-vlc` can find its libraries.

---

## Icons

The application uses a custom icon provided in the `resources` folder:

* `resources/BOPIcon.png` – base PNG icon (for editing or future conversions).
* `resources/BOP.ico` – icon used by the application and later by installers / .exe packaging.

The icon is applied at two levels:

* Application icon (taskbar, Alt+Tab) set in `app.py`:

  ```python
  app.setWindowIcon(QIcon("resources/BOP.ico"))
  ```

* Window icon set in `ui/main_window.py`:

  ```python
  self.setWindowIcon(QIcon("resources/BOP.ico"))
  ```

---

## Running the Application from Source

With the virtual environment activated in the project folder:

```bash
python app.py
```

A window titled **“Back-Office Player (BOP)”** should appear, with the BOP icon in the title bar.

---

## Building a Windows Executable (PyInstaller)

With your virtual environment active at the project root:

```powershell
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

Note: Users must have **VLC installed** on their machine for audio playback to work.

---

## Basic Usage

1. **Open an audio file**

   * Click **“Open audio file…”**, or
   * Use the keyboard shortcut **Ctrl+O**.
   * Choose a supported audio file (`.mp3`, `.wav`, etc.).

2. **Play / Pause / Stop**

   * Use the buttons **Play**, **Pause**, **Stop**, or
   * Use keyboard shortcuts:

     * **Ctrl+P**: Play
     * **Ctrl+Shift+P**: Pause
     * **Ctrl+S**: Stop

3. **Seek in the track**

   * Move focus to the position slider via Tab.
   * Use **left/right arrow keys** to move the cursor (1 second per step).
   * The label next to it shows current and total time in `mm:ss / mm:ss`.

4. **Volume**

   * Adjust **Volume** with the slider (0–100).
   * Volume is saved in `settings.json` and restored on next run.

5. **A–B Loop**

   * Start playback.
   * At the desired start time, click **Set A** or use **Ctrl+Shift+A**.
   * Let the track continue, then at the desired end time, click **Set B** or use **Ctrl+Shift+B**.
   * Check **Loop A–B** to enable the loop.
   * Use **Clear A/B** to remove both points and disable looping.

---

## Keyboard Shortcuts Summary

Global shortcuts:

* **Ctrl+O** – Open audio file
* **Ctrl+P** – Play
* **Ctrl+Shift+P** – Pause
* **Ctrl+S** – Stop
* **Ctrl+Shift+A** – Set point A at current playback position
* **Ctrl+Shift+B** – Set point B at current playback position

Standard widget behavior:

* With focus on a **button**: **Space** or **Enter** activate it.
* With focus on the **position slider**:

  * **Left arrow**: move backward by 1 second and update playback position.
  * **Right arrow**: move forward by 1 second and update playback position.

---

## Project Structure

```text
back-office-player/
├─ app.py                  # Application entry point (Qt)
├─ requirements.txt        # Python dependencies
├─ settings.json           # Generated at runtime (user settings)
├─ resources/
│  ├─ BOPIcon.png          # Base PNG icon
│  └─ BOP.ico              # Application icon
├─ core/
│  ├─ __init__.py
│  ├─ audio_player.py      # VLC-based audio player
│  ├─ segment.py           # Segment (A–B)
│  └─ segment_manager.py   # Segment collection management
├─ infra/
│  ├─ __init__.py
│  ├─ persistence.py       # Saving/loading segments
│  └─ settings.py          # Saving/loading settings
├─ ui/
│  ├─ __init__.py
│  └─ main_window.py       # Qt UI and A–B loop logic
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
bopenv\Scripts\activate
cd docs
.\make.bat html
```

The generated HTML documentation is available under:

```text
docs\_build\html\index.html
```

When you run `sphinx-quickstart` originally, you can set:

* Project name: `Back-Office Player`
* Author: `Amine Khettat`
* Project release: `1.0.0`

---

## Future Work

Planned or possible enhancements include:

* **Named segments**
  Label important parts of a piece (e.g. “Intro”, “Verse 1”, “Chorus”) and store them per audio file using `Segment` and `SegmentManager`.

* **Segment list and navigation**
  A list of segments in the UI for quick navigation and playback.

* **Tempo change (time-stretching)**
  Change playback speed (slower or faster) without modifying pitch, to help students practice difficult passages.

* **Pitch / key change (transposition)**
  Change the pitch of the audio (up/down by semitones) without changing speed, so students can adapt the recording to their vocal range or instrument tuning.

* **Export segment as separate audio file**
  Save a selected A–B segment as a standalone audio file.

* **Import/export practice configurations**
  Save and share sets of segments, loop settings and other practice parameters.

* **More keyboard shortcuts**
  Additional shortcuts for segment navigation and advanced playback controls.

---

## Release History

* **v1.0.0**
  First stable release of Back-Office Player (BOP):

  * Accessible Qt-based UI (keyboard + screen reader friendly)
  * A–B loop practice
  * Position navigation with arrow keys
  * Sphinx documentation
  * PyInstaller Windows executable

* **v0.2.0**
  Internal development version (not publicly distributed).

---

## Contributing

Contributions are welcome as long as they respect:

* The project’s accessibility goals (keyboard / screen-reader first).
* The modular architecture (separating core, infra, and UI).
* The existing coding style and documentation format.

Before submitting a pull request:

1. Make sure the code runs without errors on Windows with VLC installed.
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
distributed under the License is distributed on an “AS IS” BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

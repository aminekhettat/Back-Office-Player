# Back-Office Player (BOP) — Audio Practice Tool

**Back-Office Player (BOP)** is a Windows desktop application written in Python that helps music students practise at home using rehearsal recordings.

**Current version:** 2.0.0 — developed by [BLIND SYSTEMS](https://www.blindsystems.org) for the students of the [Culture Musique](https://www.sabamusic.fr) association.

---

## Key Features

- **Native audio engine** — no VLC required. Playback powered by `librosa` + `sounddevice`.
- **Transport controls** — Play, Pause, Stop with keyboard shortcuts.
- **A–B loop** — set loop start (A) and end (B) anywhere on the timeline; loop continuously or a fixed number of times.
- **Named segments** — save any A–B region as a named segment, then jump to it with one key press.
- **Tempo control** — slider from 50 % to 200 %; remembers your last value across sessions.
- **Pitch control** — shift pitch ±12 semitones independently of tempo.
- **Pitch-preserving tempo** — optional time-stretching mode that changes speed without affecting pitch (via `librosa`).
- **Progressive tempo** — practice panel that automatically ramps the tempo up after each completed loop.
- **Waveform display** — interactive waveform with A/B markers and playhead; click to seek.
- **Practice history** — every session is logged (file, duration, loops, tempo); viewable and exportable as CSV.
- **Segment export** — export any segment to WAV or MP3.
- **Export / import config** — save all segments + settings to a `.bop` file and share or reload them.
- **Undo / redo** — Ctrl+Z / Ctrl+Y for segment add and delete operations.
- **Themes** — default, dark, and high-contrast colour themes.
- **Bilingual UI** — French and English, switchable at runtime from the Settings menu.
- **Accessible** — full keyboard and screen-reader (NVDA, JAWS) support.

---

## Accessibility

The UI is built with **Qt (PySide6)** for screen-reader compatibility on Windows:

- All buttons, sliders, and controls have accessible names and descriptions.
- Full keyboard navigation with Tab / Shift+Tab; explicit tab order puts transport controls first.
- **Position slider is reported as time** (`mm:ss / mm:ss`) rather than a raw second count, via a custom `QAccessible` factory.
- Tempo and pitch slider changes are announced in real time (assertive `QAccessible.announce`), so the screen reader always reports the current value without the user having to re-read the control.
- Position slider: **left/right arrows** to seek ±1 second.
- Tempo slider: **up/down arrows** in 5 % steps.
- Status label announces every significant event (file loaded, A/B set, segment saved, etc.).
- Position is periodically announced to screen readers (configurable interval).

---

## Architecture

The project is organised in three layers:

```
core/       Domain logic — no UI dependency
infra/      Persistence, I/O, and infrastructure helpers
ui/         Qt widgets and main window
```

### `core/`

| Module | Description |
|--------|-------------|
| `audio_player_native.py` | Native audio player (librosa + sounddevice). Tempo, pitch, volume, seek. |
| `audio_loader.py` | `QThread` that loads audio files asynchronously. |
| `pitch_engine.py` | Pitch-shifting and time-stretching using librosa. |
| `segment.py` | `Segment` dataclass (name, start, end, category, color, notes). |
| `segment_manager.py` | Collection of segments with add/remove/move/sort. |
| `practice_session.py` | Session timer, loop counter, progressive-tempo logic. |
| `commands.py` | Command pattern for undo/redo (`AddSegmentCommand`, `RemoveSegmentCommand`, `CommandHistory`). |

### `infra/`

| Module | Description |
|--------|-------------|
| `persistence.py` | Save/load segments as `<audio>.segments.json` next to the audio file. |
| `settings.py` | Save/load user settings to `settings.json` (platformdirs). |
| `practice_history.py` | Log practice sessions to `practice_history.json`; CSV export. |
| `i18n.py` | Lightweight translation engine (French / English). |
| `audio_export.py` | Export a segment slice to WAV (16-bit) or MP3 (via lameenc). |
| `updater.py` | Background GitHub release checker. |

### `ui/`

| Module | Description |
|--------|-------------|
| `main_window.py` | Main window: all widgets, A–B loop logic, shortcuts, session management. |
| `waveform_widget.py` | RMS waveform display with playhead, A/B markers, and segment ticks. |
| `segment_list_widget.py` | Segment list with jump, delete, move-up/down, export, and category filter. |
| `practice_panel.py` | Practice session panel (loop count, delay, progressive tempo, session timer). |
| `settings_dialog.py` | Preferences dialog (shortcuts, theme, accessibility, audio). |
| `history_dialog.py` | Read-only practice history table with CSV export. |

---

## Requirements

- **Windows** (also runs on Linux / macOS with minor path adjustments)
- **Python 3.10+**
- Dependencies listed in `requirements.txt`:

```
librosa>=0.10.0
sounddevice>=0.4.5
numpy>=1.20.0
scipy>=1.7.0
PySide6
platformdirs>=3.0.0
```

> MP3 export requires `lameenc` (`pip install lameenc`). The application runs without it but the MP3 export button will error.

---

## Installation

```bash
git clone https://github.com/aminekhettat/Back-Office-Player.git
cd Back-Office-Player

# Create and activate a virtual environment (Windows)
python -m venv bopenv
bopenv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

---

## Running from Source

```bash
python app.py
```

---

## Building a Windows Executable

```powershell
pip install pyinstaller
pyinstaller --name BackOfficePlayer --windowed --icon="resources/BOP.ico" --add-data "resources;resources" app.py
```

Output: `dist\BackOfficePlayer\BackOfficePlayer.exe`

---

## Basic Usage

### Open a file
Click **Open audio file…** or press **Ctrl+O**.

### Transport
| Button | Shortcut |
|--------|----------|
| Play | Ctrl+P |
| Pause | Ctrl+Shift+P |
| Stop | Ctrl+S |

### A–B Loop
1. Start playback.
2. Press **Set A** (Ctrl+Shift+A) at the loop start.
3. Press **Set B** (Ctrl+Shift+B) at the loop end.
4. Check **Loop A–B** to enable continuous looping.
5. Press **Clear A/B** to remove markers.

### Named Segments
1. Set A and B, then press **Save Segment** (Ctrl+Shift+S) and enter a name.
2. The segment appears in the list. Double-click or select + **Jump to Segment** to navigate.
3. **Ctrl+Z** undoes the last add/delete; **Ctrl+Y** redoes it.

### Tempo & Pitch
- **Tempo slider** (50–200 %): slows down or speeds up playback. Up/down arrows in 5 % steps. Value is saved and restored between sessions.
- **Pitch slider** (−12 to +12 semitones): shifts pitch without changing speed.
- Enable **Pitch-preserving tempo** in Preferences for time-stretching (changes speed without changing pitch).

### Practice Session (Progressive Tempo)
In the **Practice Session** panel you can configure:
- **Loop count** — stop after N loops (0 = infinite).
- **Loop delay** — pause between loops (seconds).
- **Progressive tempo** — automatically increment tempo by a fixed step after each loop until a target is reached.

### Practice History
Open **Settings → Practice History…** (Ctrl+H) to view all past sessions in a table. Click **Export CSV…** to save them.

---

## Keyboard Shortcuts Summary

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open audio file |
| Ctrl+P | Play |
| Ctrl+Shift+P | Pause |
| Ctrl+S | Stop |
| Ctrl+Shift+A | Set point A |
| Ctrl+Shift+B | Set point B |
| Ctrl+Shift+S | Save current A–B as segment |
| Ctrl+E | Export practice config (.bop) |
| Ctrl+I | Import practice config (.bop) |
| Ctrl+H | Open practice history |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+Q | Quit |

---

## Project Structure

```text
Back-Office-Player/
├─ app.py                          # Entry point
├─ __version__.py                  # Single source of truth for version
├─ requirements.txt                # Runtime dependencies
├─ requirements-dev.txt            # Dev dependencies (test, lint, docs, packaging)
├─ resources/
│  ├─ BOPIcon.png                  # Source icon
│  └─ BOP.ico                     # Windows application icon
├─ core/
│  ├─ audio_player_native.py       # Native audio player
│  ├─ audio_loader.py              # Async audio loader (QThread)
│  ├─ pitch_engine.py              # Pitch shift / time-stretch engine
│  ├─ segment.py                   # Segment dataclass
│  ├─ segment_manager.py           # Segment collection
│  ├─ practice_session.py          # Session timer and progressive tempo
│  └─ commands.py                  # Undo/redo command pattern
├─ infra/
│  ├─ persistence.py               # Segment save/load (JSON per audio file)
│  ├─ settings.py                  # User settings (platformdirs)
│  ├─ practice_history.py          # Practice history log + CSV export
│  ├─ i18n.py                      # Translation engine (fr/en)
│  ├─ audio_export.py              # WAV / MP3 export helpers
│  └─ updater.py                   # GitHub update checker
├─ ui/
│  ├─ main_window.py               # Main Qt window
│  ├─ waveform_widget.py           # Waveform display widget
│  ├─ segment_list_widget.py       # Segment list widget
│  ├─ practice_panel.py            # Practice session control panel
│  ├─ settings_dialog.py           # Preferences dialog
│  └─ history_dialog.py            # Practice history viewer
├─ tests/                          # pytest test suite (100 % coverage target)
└─ docs/                           # Sphinx documentation source
   ├─ conf.py
   ├─ index.rst
   └─ source/
      ├─ core.rst
      ├─ infra.rst
      ├─ ui.rst
      └─ ...
```

---

## Running the Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ --ignore=tests/test_app.py --cov --cov-report=term-missing
```

---

## Documentation (Sphinx)

```bash
bopenv\Scripts\activate.bat
cd docs
.\make.bat html
# Open docs/_build/html/index.html
```

---

## Release History

### v2.0.0 *(current)*

Major release — full quality overhaul and professional distribution.

- **100 % test coverage (602 tests).** Every branch, line, and function in `core/`, `infra/`, and `ui/` is covered. Tests are powered by `pytest`, `pytest-qt`, and `hypothesis` (property-based tests).
- **Type-safe codebase.** `mypy` runs in strict mode across all 52 source files with zero errors.
- **Security audit.** `bandit` reports zero issues; only `B101` (assert in non-production code) is suppressed via `pyproject.toml`.
- **No pragma exclusions.** All `# pragma: no cover` annotations have been removed; previously-skipped branches are now exercised by real tests.
- **Ruff replaces Flake8.** The linter is now `ruff` (faster, more rules, isort integration). `B017` replaced bare `pytest.raises(Exception)` with typed `pytest.raises(RuntimeError)` throughout the test suite.
- **Source raises `RuntimeError` on load failure.** `AudioPlayer.load_file` now raises `RuntimeError` instead of the bare `Exception`, giving callers a checkable, typed exception.
- **CI rebuilt on Ubuntu.** All jobs (`lint`, `security`, `typecheck`, `test`, `docs`) now run on `ubuntu-latest` with properly mocked Qt / PortAudio system packages, making the matrix (3.10 / 3.11 / 3.12) fully reliable.
- **Sphinx docs — zero warnings.** Added `soundfile`, `platformdirs`, and `lameenc` to `autodoc_mock_imports`; removed stale `core.audio_player` (VLC legacy) reference; created missing `docs/_static/` directory.
- **User manuals.** Bundled PDF / HTML user guides in French (`docs/user_manual_fr.rst`) and English (`docs/user_manual_en.rst`).
- **Standalone Windows executable.** `BackOfficePlayer.exe` built with PyInstaller 6.x, single-file mode, UPX-compressed, embedded icon.

---

### v1.1.4
- **Accessibility — position slider announced as time.** Introduced a custom `TimeSlider` subclass wired to a `QAccessible` factory so screen readers (JAWS, NVDA) now speak `mm:ss / mm:ss` on focus and while seeking, instead of the raw integer value.
- **Accessibility — real-time slider announcements.** Tempo and pitch sliders now fire assertive `QAccessible.announce` events on every value change, so screen readers report the new value without the user having to re-read the component.
- **Accessibility — button activation fix.** Resolved a regression where pressing Space or Enter on focused buttons (e.g. *Open audio file*) did nothing under JAWS: the default `play_pause` shortcut was moved from `Space` to `Ctrl+P` to stop `QShortcut` from hijacking native button activation.
- **GUI overhaul.** Restructured the main menu bar into five standard Windows sections (File, Edit, Playback, Settings, Help), exposed Undo/Redo in the Edit menu, added an About dialog, and brought the *pitch-preserving tempo* checkbox back to the main UI next to the pitch slider.
- **Shortcut reliability.** Menu actions and global shortcuts no longer collide: all covered shortcuts are now bound once, on their `QAction`, removing Qt's “ambiguous activation” warnings and the silent misfires they caused.
- **Pitch slider — real-time response in tape mode.** Pitch shift is now applied directly in the playback worker via the resampling rate multiplier (`tempo × 2^(semitones/12)`), removing the 150 ms debounce + slow librosa recompute round-trip when the pitch-preserving option is off.
- **Pitch-preserving — correct audio after restart.** When the app reopens with `pitch_preserving=true` and a saved tempo ≠ 100 %, it now pre-computes the stretched buffer as soon as a file is loaded, instead of falling back to tape-rate playback (which previously produced a detuned, “weird” sound).
- **Position correctness across buffer swaps.** The audio engine now stores playback position in *song time* rather than a raw sample index and rescales `_current_sample_pos` whenever the active buffer length changes (pitch-preserving on/off, re-stretch, re-shift). Fixes position drift and loop-point glitches when switching modes mid-playback.

### v1.1.1
- Practice history: session logging (file, duration, loops, tempo) with table view and CSV export.
- Progressive tempo: practice panel with configurable start/step/target, loop count, and loop delay.
- Waveform display: interactive RMS waveform with playhead, A/B markers, and segment tick marks; click to seek.
- Pitch control: ±12 semitone shift independent of tempo.
- Pitch-preserving tempo: optional time-stretching via librosa.
- Segment enhancements: categories, colours, notes, move-up/down reordering.
- Segment export to WAV (16-bit) and MP3.
- Undo / redo for segment add and delete (Ctrl+Z / Ctrl+Y).
- Bilingual UI: French and English, switchable at runtime.
- Themes: default, dark, and high-contrast.
- Settings dialog: shortcut customisation, theme, accessibility (announce interval), audio options.
- Recent files menu.
- Background update checker (GitHub releases).
- Async audio loading (non-blocking UI during decode).

### v1.0.0
- First stable release.
- Accessible Qt UI (keyboard + screen reader).
- A–B loop practice with continuous looping.
- Named segments: save, list, jump, delete.
- Tempo control (50–200 %).
- Export / import practice configurations (`.bop` files).
- Position slider with arrow-key navigation.
- Sphinx documentation and PyInstaller Windows executable.

### v0.3.0
- Replaced VLC with native audio engine (librosa + sounddevice).
- Named segment management.
- Tempo slider.
- Practice config export/import (`.bop` files).

---

## Contributing

Contributions are welcome provided they respect:

- **Accessibility first** — keyboard and screen-reader support must be maintained.
- **Layered architecture** — keep `core/`, `infra/`, and `ui/` concerns separate.
- **Test coverage** — new code should include tests; the suite targets 100 % coverage.
- **English docstrings** — all code documentation is in English.

Before submitting a pull request:

1. Run `pytest tests/ --ignore=tests/test_app.py` and ensure all tests pass.
2. Add or update Sphinx docstrings for any new public API.
3. Update this README and the release history if the change is user-facing.

---

## License

Apache License 2.0 — Copyright (c) 2025 BLIND SYSTEMS.

See [LICENSE](LICENSE) or https://www.apache.org/licenses/LICENSE-2.0.

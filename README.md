# Back-Office Player (BOP)

> **Accessible audio practice tool for music students — A/B looping, named segments, progressive tempo, and full screen-reader support.**

**Version 2.0.0** · Python 3.10+ · PySide6 · Windows · [Documentation](docs/) · [Quickstart](#quick-start) · [Release Notes](#release-history)

---

## What Is Back-Office Player?

**Back-Office Player (BOP)** is a Windows desktop application written in Python that helps music students practise at home using rehearsal recordings.

It provides an A–B loop engine, named segment management, tempo and pitch control, and a progressive-tempo practice mode — all built on a native audio engine (no external player required) and designed from the ground up for keyboard and screen-reader users.

Developed by [BLIND SYSTEMS](https://www.blindsystems.org) for the students of the [Culture Musique](https://www.sabamusic.fr) association.

---

## Why This Project?

| Gap | How BOP fills it |
|-----|-----------------|
| No free tool combines A/B loop + progressive tempo + pitch shift in one place | All three features tightly integrated in a single application |
| Third-party engines (VLC) break silently across Windows updates | Native audio engine built on `librosa` + `sounddevice` — zero external dependencies |
| Practice sessions leave no trace for self-assessment | Full session history (file, duration, loops, tempo) with CSV export |
| Segment work is lost between sessions | Named segments and practice configs saved to portable `.bop` files |
| Speed and pitch are coupled in most players | Independent tempo (50–200 %) and pitch (±12 st) controls, with optional pitch-preserving time-stretch |
| The application is also designed for visually impaired musicians | Full keyboard navigation and screen-reader support (NVDA, JAWS) as a first-class requirement |

---

## Key Features

### Transport & Looping
- **A–B loop** — set loop start (A) and end (B) anywhere on the timeline; loop continuously or a fixed number of times
- **Named segments** — save any A–B region as a named segment; jump to it with one key press
- **Waveform display** — interactive RMS waveform with A/B markers and playhead; click to seek

### Tempo & Pitch
- **Tempo control** — slider from 50 % to 200 %; value is saved across sessions
- **Pitch control** — shift pitch ±12 semitones independently of tempo
- **Pitch-preserving tempo** — optional time-stretching via `librosa`; changes speed without affecting pitch

### Practice System
- **Progressive tempo** — automatically ramps the tempo up after each completed loop
- **Practice history** — every session is logged (file, duration, loops, tempo); viewable and exportable as CSV

### Data Management
- **Segment export** — export any segment to WAV or MP3
- **Export / import config** — save all segments + settings to a `.bop` file and share or reload them
- **Undo / redo** — Ctrl+Z / Ctrl+Y for segment add and delete

### Interface
- **Themes** — default, dark, and high-contrast colour themes
- **Bilingual UI** — French and English, switchable at runtime from the Settings menu
- **Accessible** — full keyboard and screen-reader (NVDA, JAWS) support

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/aminekhettat/Back-Office-Player.git
cd Back-Office-Player
python -m venv bopenv && bopenv\Scripts\activate.bat
pip install -r requirements.txt

# 2. Launch
python app.py

# 3. Run tests
pytest tests/ --ignore=tests/test_app.py
```

---

## Accessibility

The UI is built with **PySide6** for screen-reader compatibility on Windows:

- All buttons, sliders, and controls have accessible names and descriptions.
- Full keyboard navigation with Tab / Shift+Tab; explicit tab order puts transport controls first.
- **Position slider is reported as time** (`mm:ss / mm:ss`) rather than a raw second count, via a custom `QAccessible` factory.
- Tempo and pitch slider changes are announced in real time (assertive `QAccessible.announce`), so the screen reader always reports the current value without the user having to re-read the control.
- Position slider: **left/right arrows** to seek ±1 second.
- Tempo slider: **up/down arrows** in 5 % steps.
- Status label announces every significant event (file loaded, A/B set, segment saved, etc.).
- Position is periodically announced to screen readers (configurable interval).
- Compatible with **NVDA**, **JAWS**.

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
- Enable **Pitch-preserving tempo** in Preferences for time-stretching.

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

## Documentation

| Document | Purpose |
|----------|---------|
| This README | Project overview, installation, and usage |
| [CHANGELOG.md](CHANGELOG.md) | Full version-by-version change log |
| [docs/user_manual_fr.rst](docs/user_manual_fr.rst) | User manual in French |
| [docs/user_manual_en.rst](docs/user_manual_en.rst) | User manual in English |
| [docs/index.rst](docs/index.rst) | Sphinx documentation root |

To build HTML docs locally:

```bash
bopenv\Scripts\activate.bat
cd docs
.\make.bat html
# Open docs/_build/html/index.html
```

---

## Quality Gates

Every commit runs:

- **Ruff** — lint and style (replaces Flake8; includes bugbear, pyupgrade, isort)
- **Mypy** — type checking in strict mode across all source files (zero errors)
- **Bandit** — security scan (zero findings; only B101 suppressed in test code)
- **pytest** — full test suite with 100 % branch + line coverage threshold (602 tests)
- **Sphinx** — HTML documentation build with `-W` (zero warnings)
- **pip-audit** — dependency vulnerability audit

CI runs on `ubuntu-latest` against Python 3.10, 3.11, and 3.12 via GitHub Actions.

To run all gates locally:

```bash
pip install -r requirements-dev.txt
ruff check .
mypy .
bandit -r . -c pyproject.toml
pytest tests/ --ignore=tests/test_app.py --cov --cov-report=term-missing
```

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/).

```bash
bump2version patch   # x.y.Z  — bug fixes
bump2version minor   # x.Y.0  — new features
bump2version major   # X.0.0  — breaking changes
```

The single source of truth for the version number is `__version__.py`.

---

## Release History

### v2.0.0 *(current — 2026-04-19)*

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
- **Accessibility — position slider announced as time.** Introduced a custom `TimeSlider` subclass wired to a `QAccessible` factory so screen readers (JAWS, NVDA) now speak `mm:ss / mm:ss` on focus and while seeking.
- **Accessibility — real-time slider announcements.** Tempo and pitch sliders now fire assertive `QAccessible.announce` events on every value change.
- **Accessibility — button activation fix.** Resolved a regression where pressing Space or Enter on focused buttons did nothing under JAWS.
- **GUI overhaul.** Restructured the main menu bar into five standard Windows sections (File, Edit, Playback, Settings, Help), exposed Undo/Redo in the Edit menu, added an About dialog.
- **Shortcut reliability.** Menu actions and global shortcuts no longer collide.
- **Pitch slider — real-time response in tape mode.** Pitch shift is now applied directly in the playback worker, removing the 150 ms debounce + slow librosa recompute round-trip.
- **Pitch-preserving — correct audio after restart.** Fixes detuned playback when app reopens with `pitch_preserving=true` and a saved tempo ≠ 100 %.
- **Position correctness across buffer swaps.** Engine now stores playback position in *song time* rather than a raw sample index.

### v1.1.1
- Practice history: session logging (file, duration, loops, tempo) with table view and CSV export.
- Progressive tempo: practice panel with configurable start/step/target, loop count, and loop delay.
- Waveform display: interactive RMS waveform with playhead, A/B markers, and segment tick marks.
- Pitch control: ±12 semitone shift independent of tempo.
- Pitch-preserving tempo: optional time-stretching via librosa.
- Segment enhancements: categories, colours, notes, move-up/down reordering.
- Segment export to WAV (16-bit) and MP3.
- Undo / redo for segment add and delete (Ctrl+Z / Ctrl+Y).
- Bilingual UI: French and English, switchable at runtime.
- Themes: default, dark, and high-contrast.
- Settings dialog: shortcut customisation, theme, accessibility options.
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

---

## Author

**Amine Khettat** · [amine.khettat@blindsystems.org](mailto:amine.khettat@blindsystems.org) · [BLIND SYSTEMS](https://www.blindsystems.org)

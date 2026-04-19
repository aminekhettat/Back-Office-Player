# Changelog — Back-Office Player

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-04-19

### Added
- **602-test suite at 100 % branch + line coverage** — every code path in
  `core/`, `infra/`, and `ui/` is exercised; zero `# pragma: no cover`
  annotations remain in the production source.
- **`hypothesis` property-based tests** — commutative / round-trip invariants
  on `SegmentManager`, `AddSegmentCommand`, and `CommandHistory`.
- **`bandit` security job in CI** — automatically detects OWASP Top-10 issues
  on every push; zero findings in v2.0.0.
- **User manual in French** (`docs/user_manual_fr.rst` / PDF).
- **User manual in English** (`docs/user_manual_en.rst` / PDF).
- **Standalone Windows executable** (`BackOfficePlayer.exe`) built with
  PyInstaller 6, single-file mode, UPX-compressed (≈ 50 MB).
- **`docs/_static/` directory** — was missing, causing Sphinx `-W` failures.
- **`soundfile`, `platformdirs`, `lameenc` added to `autodoc_mock_imports`**
  so `sphinx -W` passes with zero warnings.

### Changed
- **Version bump 1.1.4 → 2.0.0** — major release reflecting the complete
  quality and tooling overhaul.
- **CI migrated from `windows-latest` to `ubuntu-latest`** — faster, cheaper,
  and more reliable for headless Qt testing.
- **CI lint job replaced from `flake8` with `ruff`** — covers all previous
  rules plus `bugbear`, `pyupgrade`, `isort` integration, and security checks.
  A dedicated `bandit` security job is also added.
- **`mypy` CI command simplified to `mypy .`** — now uses `pyproject.toml`
  configuration instead of ad-hoc flags.
- **`AudioPlayer.load_file` raises `RuntimeError`** instead of bare
  `Exception`, giving callers a checkable, typed exception class.
- **Tests use `pytest.raises(RuntimeError)`** instead of `pytest.raises(Exception)`,
  correctly enforcing the exception contract (bandit B017 fix).
- **Import sorting fixed** in `core/commands.py` and `infra/audio_export.py`
  (ruff I001 / E302 compliance).
- **`docs/source/core.rst`** — removed stale `core.audio_player` (VLC legacy)
  autodoc reference; the module no longer exists.

### Fixed
- `AudioPlayer` unreachable-code branch in thread safety guard now carries
  `# type: ignore[unreachable]` annotation so `mypy --warn-unreachable` passes.
- `QAccessible.installFactory` moved inside `MainWindowQt.__init__` to
  prevent crash when the module is imported without a running `QApplication`.
- `test_updater.py` thread-run reassignment suppressed with
  `# type: ignore[method-assign]` (mypy `method-assign` rule).
- `test_persistence.py` post-`assert-is-not-None` narrowing prevents mypy
  `union-attr` false positives on `Path | None` return values.
- Removed unused `lameenc.*` override from `[[tool.mypy.overrides]]`.

---

## [1.1.4] — 2026-04-17

### Added
- Custom `TimeSlider` + `_TimeSliderAccessible` factory: screen readers
  (JAWS, NVDA) now speak `mm:ss / mm:ss` instead of raw integer values.
- Assertive `QAccessible.announce` events on tempo/pitch slider changes.

### Fixed
- Play/pause Space hotkey replaced with Ctrl+P to stop `QShortcut` from
  hijacking native button activation under JAWS.
- Pitch slider real-time response in tape mode (removed 150 ms debounce).
- Pitch-preserving mode: correct buffer pre-computation on file open.

### Changed
- Main menu bar restructured into five Windows-standard sections.
- Undo/Redo surfaced in Edit menu.
- About dialog added.

---

## [1.1.3] — 2026-04-16

### Fixed
- VS Code debug configuration corrected.
- All module headers standardised (`:author:`, `:organization:`, `:license:`).

---

## [1.1.2] — 2026-04-15

### Added
- Undo/redo support (`AddSegmentCommand`, `RemoveSegmentCommand`,
  `CommandHistory`); keyboard shortcuts Ctrl+Z / Ctrl+Y.

---

## [1.1.1] — 2026-04-14

### Added
- Practice history viewer (`HistoryDialog`) with CSV export.
- Bilingual UI: French ↔ English switchable at runtime.

---

## [1.1.0] — 2026-04-13

### Added
- Native audio engine (librosa + sounddevice) replaces VLC dependency.
- Progressive-tempo practice panel.
- Waveform widget with interactive A/B markers.
- Segment export to WAV and MP3 (via lameenc).
- Export / import practice config (`.bop` format).
- Dark and high-contrast themes.
